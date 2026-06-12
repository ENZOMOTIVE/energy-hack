"""CLI runner: python -m gauntlet.run --scenario S1 --agent rules [--seed 42] [--out traces/]"""

import argparse
import json
from pathlib import Path

import numpy as np

from .agents.llm import MockLLM, make_claude_agent, make_deepseek_agent, make_llm_agent
from .agents.noop import DoNothingAgent
from .agents.rules import RuleAgent
from .config import DEFAULT_SEED, SCENARIOS
from .oracle import oracle_cost
from .scenarios import build
from .scoring import score
from .sim import run_episode

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "traces"


STANDARD_AGENTS = ["noop", "rules", "llm"]
REAL_BRAIN_AGENTS = ["deepseek", "claude"]


def make_agent(name: str):
    if name == "noop":
        return DoNothingAgent()
    if name == "rules":
        return RuleAgent()
    if name == "llm":
        return make_llm_agent()
    if name == "deepseek":
        return make_deepseek_agent()
    if name == "claude":
        return make_claude_agent()
    raise ValueError(f"unknown agent {name}")


def run_one(scenario_name: str, agent_name: str, seed: int = DEFAULT_SEED, out: Path = DEFAULT_OUT,
            data: str = "synthetic") -> dict:
    scenario = build(scenario_name, seed, data=data)
    floor_trace = run_episode(scenario, DoNothingAgent())
    floor_cum = floor_trace["_cum_cost"]
    if agent_name == "noop":
        trace = floor_trace
        trace["steps"] = [dict(s, cum_cost_floor_eur=s["cum_cost_eur"]) for s in trace["steps"]]
    else:
        trace = run_episode(scenario, make_agent(agent_name), floor_cum=floor_cum)
    oracle = oracle_cost(scenario)
    floor = float(floor_cum[-1])
    trace["totals"]["floor_eur"] = round(floor, 2)
    trace["totals"]["oracle_eur"] = round(oracle, 2)
    trace["totals"]["score"] = round(score(trace["totals"]["cost_eur"], floor, oracle), 4)
    trace["data"] = data
    trace["day"] = scenario.day
    trace.pop("_cum_cost", None)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{scenario_name}_{agent_name}.json").write_text(json.dumps(trace))
    return trace


def run_all(seed: int = DEFAULT_SEED, out: Path = DEFAULT_OUT, data: str = "synthetic",
            agents: list | None = None) -> dict:
    if agents is None:
        agents = STANDARD_AGENTS
    results = []
    for sc in SCENARIOS:
        for ag in agents:
            trace = run_one(sc, ag, seed, out, data=data)
            t = trace["totals"]
            results.append({
                "scenario": sc, "agent": ag, "score": t["score"],
                "cost_eur": t["cost_eur"], "floor_eur": t["floor_eur"],
                "oracle_eur": t["oracle_eur"], "false_dispatches": t["false_dispatches"],
                "steps_to_first_action": t["steps_to_first_action"],
                **({"day": trace["day"]} if trace.get("day") else {}),
                **({"brain": t["brain"]} if "brain" in t else {}),
            })
    # merge into existing results so partial runs (e.g. --agents deepseek) keep
    # the other rows and standard runs keep real-model rows
    results_file = out / "results.json"
    if results_file.exists():
        existing = json.loads(results_file.read_text())
        key = lambda r: (r["scenario"], r["agent"])
        new_keys = {key(r) for r in results}
        results = [r for r in existing["results"] if key(r) not in new_keys] + results
        results.sort(key=lambda r: (r["scenario"], STANDARD_AGENTS.index(r["agent"])
                                    if r["agent"] in STANDARD_AGENTS else 99))
    payload = {"seed": seed, "data": data, "results": results}
    results_file.write_text(json.dumps(payload))
    return payload


MC_SEED0 = 1000
MC_LLM_CAP = 20  # API-cost bound in spirit; MC always uses the mock brain


def run_mc(scenario_name: str, n: int, out: Path = DEFAULT_OUT) -> dict:
    """M8: robustness scoring across n seeded scenario variations.

    Cheap agents get the full n; the llm slot runs the deterministic mock capped
    at MC_LLM_CAP episodes (stated openly: error bars are part of the product)."""
    per_agent = {"noop": [], "rules": [], "llm": []}
    for i in range(n):
        seed = MC_SEED0 + i
        sc = build(scenario_name, seed)
        floor = float(run_episode(sc, DoNothingAgent())["_cum_cost"][-1])
        oracle = oracle_cost(sc)
        per_agent["noop"].append(0.0)
        rules_cost = run_episode(sc, RuleAgent())["totals"]["cost_eur"]
        per_agent["rules"].append(score(rules_cost, floor, oracle))
        if i < MC_LLM_CAP:
            llm_cost = run_episode(sc, MockLLM())["totals"]["cost_eur"]
            per_agent["llm"].append(score(llm_cost, floor, oracle))
    summary = {
        ag: {"mean": round(float(np.mean(v)), 4), "p10": round(float(np.percentile(v, 10)), 4), "n": len(v)}
        for ag, v in per_agent.items()
    }
    out.mkdir(parents=True, exist_ok=True)
    payload = {"scenario": scenario_name, "seed0": MC_SEED0, "n": n,
               "summary": summary, "scores": per_agent}
    (out / f"mc_{scenario_name}.json").write_text(json.dumps(payload))
    results_file = out / "results.json"
    if results_file.exists():
        results = json.loads(results_file.read_text())
        for row in results["results"]:
            if row["scenario"] == scenario_name and row["agent"] in summary:
                row["mc"] = summary[row["agent"]]
        results_file.write_text(json.dumps(results))
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", choices=SCENARIOS)
    ap.add_argument("--agent", default="llm")
    ap.add_argument("--agents", default=None,
                    help="comma-separated list for --all, e.g. noop,rules,llm,deepseek")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--data", choices=["synthetic", "real"], default="synthetic")
    ap.add_argument("--mc", type=int, metavar="N",
                    help="robustness scoring over N seeded variations (all agents)")
    args = ap.parse_args()
    if args.data == "real" and args.out == DEFAULT_OUT:
        args.out = DEFAULT_OUT / "real"
    if args.mc and args.data == "real":
        ap.error("MC runs on synthetic data only: a single real day has no seeded variations")
    if args.mc:
        scenarios = [args.scenario] if args.scenario else SCENARIOS
        for sc in scenarios:
            payload = run_mc(sc, args.mc, args.out)
            for ag, s in payload["summary"].items():
                print(f"{sc}/{ag}: mc mean={s['mean']:.2f} p10={s['p10']:.2f} n={s['n']}")
        return
    agents_list = [a.strip() for a in args.agents.split(",")] if args.agents else None
    if args.all:
        payload = run_all(args.seed, args.out, data=args.data, agents=agents_list)
        for r in payload["results"]:
            print(f"{r['scenario']}/{r['agent']}: score={r['score']:.2f} "
                  f"cost={r['cost_eur']:.0f} floor={r['floor_eur']:.0f} "
                  f"oracle={r['oracle_eur']:.0f} false_dispatches={r['false_dispatches']}")
    else:
        if not args.scenario:
            ap.error("--scenario required unless --all")
        trace = run_one(args.scenario, args.agent, args.seed, args.out, data=args.data)
        print(json.dumps(trace["totals"], indent=2))


if __name__ == "__main__":
    main()
