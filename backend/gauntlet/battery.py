"""Run a generated battery through the contestants and report tail risk.

Each curated case is Monte-Carlo'd with small structural jitter so the per-case
number is stable, not a single lucky draw. The battery report then aggregates
the per-case scores: pass-rate (share of cases recovering at least TAU), the
worst-case P10 (tail risk: the bad days behind the average), and the single
hardest case per worker.

The deterministic contestants (noop, rules, mock-llm) run offline here. Real
DeepSeek personas are added afterwards by add_personas (needs the API key), once
per case, and merged into the same per-case report basis so every worker is
scored on the same unit. Their results are frozen into the battery JSON so the
demo stays offline.
"""

import dataclasses
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from .agents import personas
from .agents.llm import MockLLM, make_persona_agent
from .agents.noop import DoNothingAgent
from .agents.rules import RuleAgent
from .fitness import TAU
from .genome import CaseGenome
from .oracle import oracle_cost
from .scenarios import build_from_genome
from .scoring import score
from .sim import run_episode

CONTESTANTS = ("noop", "rules", "llm")
MC_N = 16
SEED0 = 5000
PERSONA_SEED0 = 7000
REPO_ROOT = Path(__file__).resolve().parents[2]

WORKER_META = {
    "noop": {"label": "Do nothing", "kind": "baseline"},
    "rules": {"label": "Rule-based", "kind": "rules"},
    "llm": {"label": "LLM worker (mock)", "kind": "mock"},
}


def _agent(name: str):
    return {"noop": DoNothingAgent, "rules": RuleAgent, "llm": MockLLM}[name]()


def _report_row(per_case_means: list, cases_out: list) -> dict:
    """Aggregate one worker's per-case mean scores into the report KPIs."""
    arr = np.array(per_case_means)
    hardest_i = int(np.argmin(per_case_means))
    return {
        "pass_rate": round(float((arr >= TAU).mean()), 4),
        "p10": round(float(np.percentile(arr, 10)), 4),
        "mean": round(float(arr.mean()), 4),
        "hardest": {"name": cases_out[hardest_i]["name"],
                    "label": cases_out[hardest_i]["label"],
                    "mean": round(float(per_case_means[hardest_i]), 4)},
    }


def run_battery(battery: list, contestants=CONTESTANTS, mc_n: int = MC_N, seed0: int = SEED0) -> dict:
    cases_out = []
    per_case_mean = {a: [] for a in contestants}

    for ci, case in enumerate(battery):
        base = case["genome"]
        case_scores = {a: [] for a in contestants}
        for s in range(mc_n):
            seed = seed0 + ci * 1000 + s
            g = base.jitter(np.random.default_rng(seed))
            sc = build_from_genome(g, seed=seed)
            floor = float(run_episode(sc, DoNothingAgent())["_cum_cost"][-1])
            oracle = oracle_cost(sc)
            for a in contestants:
                cost = run_episode(sc, _agent(a))["totals"]["cost_eur"]
                case_scores[a].append(score(cost, floor, oracle))
        agents_block = {}
        for a in contestants:
            arr = np.array(case_scores[a])
            per_case_mean[a].append(float(arr.mean()))
            agents_block[a] = {
                "mean": round(float(arr.mean()), 4),
                "pass_rate": round(float((arr >= TAU).mean()), 4),
                "p10": round(float(np.percentile(arr, 10)), 4),
            }
        cases_out.append({
            "name": case["name"], "label": case["label"], "category": base.category(),
            "stake": case["eval"]["stake"], "floor": case["eval"]["floor"],
            "oracle": case["eval"]["oracle"], "fitness": case["eval"]["fitness"],
            "genome": dataclasses.asdict(base), "agents": agents_block,
        })

    report = {a: _report_row(per_case_mean[a], cases_out) for a in contestants}
    workers = [{"id": a, **WORKER_META[a]} for a in contestants]
    return {"mc_n": mc_n, "k": len(battery), "cases": cases_out, "report": report,
            "contestants": list(contestants), "workers": workers}


def add_personas(payload: dict, persona_ids: list, max_workers: int = 8,
                 base_seed: int = PERSONA_SEED0) -> dict:
    """Run each DeepSeek persona once per case (API-bound) and merge into the report.

    Per-case base scenario plus floor/oracle are computed once (deterministic, no
    API); only the persona episodes hit the network, run concurrently since they
    are I/O bound. Personas are single-run per case; the report aggregates over
    the same per-case basis as the deterministic workers."""
    cases = payload["cases"]
    bases = []
    for i, case in enumerate(cases):
        sc = build_from_genome(CaseGenome.from_dict(case["genome"]), seed=base_seed + i)
        floor = float(run_episode(sc, DoNothingAgent())["_cum_cost"][-1])
        bases.append((sc, floor, oracle_cost(sc)))

    def run_one(i: int, pid: str):
        sc, floor, oracle = bases[i]
        try:
            cost = run_episode(sc, make_persona_agent(pid))["totals"]["cost_eur"]
            return i, pid, score(cost, floor, oracle)
        except Exception:
            return i, pid, 0.0

    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(run_one, i, pid) for i in range(len(cases)) for pid in persona_ids]
        for f in as_completed(futs):
            i, pid, val = f.result()
            results[(i, pid)] = val

    per_case = {pid: [] for pid in persona_ids}
    for i, case in enumerate(cases):
        for pid in persona_ids:
            s = results[(i, pid)]
            case["agents"][pid] = {"mean": round(s, 4), "pass_rate": 1.0 if s >= TAU else 0.0,
                                   "p10": round(s, 4), "single_run": True}
            per_case[pid].append(s)

    for pid in persona_ids:
        payload["report"][pid] = _report_row(per_case[pid], cases)
    # rebuild the workers roster, deduped, deterministic ids first then personas
    base_workers = [w for w in payload.get("workers", []) if w["kind"] != "persona"]
    persona_workers = [{"id": pid, "label": personas.label(pid), "kind": "persona"}
                       for pid in persona_ids]
    payload["workers"] = base_workers + persona_workers
    payload["persona_single_run"] = True
    return payload


def save(payload: dict, mode: str, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{mode.replace(':', '_')}.json"
    f.write_text(json.dumps(payload))
    return f
