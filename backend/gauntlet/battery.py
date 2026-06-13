"""Run a generated battery through the contestants and report tail risk.

Each curated case is Monte-Carlo'd with small structural jitter so the per-case
number is stable, not a single lucky draw. The battery report then aggregates
the per-case scores: pass-rate (share of cases recovering at least TAU), the
worst-case P10 (tail risk: the bad days behind the average), and the single
hardest case per worker.

The deterministic contestants (noop, rules, mock-llm) run offline here. Real
model workers (Claude, the DeepSeek personas) are added afterwards by
add_real_workers (needs the API keys), once per case, and merged into the same
per-case report basis so every worker is scored on the same unit. Their results
are frozen into the battery JSON so the demo stays offline.
"""

import dataclasses
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from .agents import personas
from .agents.llm import MockLLM, make_claude_agent, make_persona_agent
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
    "llm": {"label": "Reference agent", "kind": "reference"},
}
# canonical display order across the leaderboard, battery report and charts
WORKER_ORDER = ["noop", "rules", "llm", "claude", "ds-cautious", "ds-balanced", "ds-aggressive"]


def _agent(name: str):
    return {"noop": DoNothingAgent, "rules": RuleAgent, "llm": MockLLM}[name]()


def _real_agent(wid: str):
    """A real-model (API-backed) worker by id: claude or a ds-* persona."""
    return make_claude_agent() if wid == "claude" else make_persona_agent(wid)


def _real_meta(wid: str) -> dict:
    if wid == "claude":
        return {"label": "Claude Sonnet", "kind": "claude"}
    return {"label": personas.label(wid), "kind": "persona"}


def _report_row(per_case_means: list, cases_out: list) -> dict:
    """Aggregate one worker's per-case mean scores into the report KPIs."""
    if not per_case_means:
        return {"pass_rate": 0.0, "p10": 0.0, "mean": 0.0, "hardest": None}
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


def add_real_workers(payload: dict, worker_ids: list, max_workers: int = 6,
                     base_seed: int = PERSONA_SEED0) -> dict:
    """Run each real-model worker (claude or ds-* persona) once per case and merge.

    Additive and idempotent: it updates only the given worker_ids and preserves
    any real workers already frozen into the battery, so claude can be added on
    top of pre-existing personas (or vice versa). Per-case base scenario plus
    floor/oracle are computed once (deterministic, no API); only the model
    episodes hit the network, run concurrently since they are I/O bound. Real
    workers are single-run per case; the report aggregates over the same per-case
    basis as the deterministic workers."""
    cases = payload["cases"]
    bases = []
    for i, case in enumerate(cases):
        sc = build_from_genome(CaseGenome.from_dict(case["genome"]), seed=base_seed + i)
        floor = float(run_episode(sc, DoNothingAgent())["_cum_cost"][-1])
        bases.append((sc, floor, oracle_cost(sc)))

    def run_one(i: int, wid: str):
        sc, floor, oracle = bases[i]
        try:
            cost = run_episode(sc, _real_agent(wid))["totals"]["cost_eur"]
            return i, wid, score(cost, floor, oracle)
        except Exception:
            return i, wid, 0.0

    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(run_one, i, wid) for i in range(len(cases)) for wid in worker_ids]
        for f in as_completed(futs):
            i, wid, val = f.result()
            results[(i, wid)] = val

    per_case = {wid: [] for wid in worker_ids}
    for i, case in enumerate(cases):
        for wid in worker_ids:
            s = results[(i, wid)]
            case["agents"][wid] = {"mean": round(s, 4), "pass_rate": 1.0 if s >= TAU else 0.0,
                                   "p10": round(s, 4), "single_run": True}
            per_case[wid].append(s)

    for wid in worker_ids:
        payload["report"][wid] = _report_row(per_case[wid], cases)
    # merge into the roster, then sort by the canonical worker order
    roster = {w["id"]: w for w in payload.get("workers", [])}
    for wid in worker_ids:
        roster[wid] = {"id": wid, **_real_meta(wid)}
    payload["workers"] = sorted(
        roster.values(),
        key=lambda w: WORKER_ORDER.index(w["id"]) if w["id"] in WORKER_ORDER else 99)
    payload["persona_single_run"] = True   # real workers are single-run per case
    return payload


def save(payload: dict, mode: str, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{mode.replace(':', '_')}.json"
    f.write_text(json.dumps(payload))
    return f
