"""CLI runner: python -m gauntlet.run --scenario S1 --agent rules [--seed 42] [--out traces/]"""

import argparse
import json
from pathlib import Path

from .agents.llm import make_llm_agent
from .agents.noop import DoNothingAgent
from .agents.rules import RuleAgent
from .config import DEFAULT_SEED, SCENARIOS
from .oracle import oracle_cost
from .scenarios import build
from .scoring import score
from .sim import run_episode

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "traces"


def make_agent(name: str):
    if name == "noop":
        return DoNothingAgent()
    if name == "rules":
        return RuleAgent()
    if name == "llm":
        return make_llm_agent()
    raise ValueError(f"unknown agent {name}")


def run_one(scenario_name: str, agent_name: str, seed: int = DEFAULT_SEED, out: Path = DEFAULT_OUT) -> dict:
    scenario = build(scenario_name, seed)
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
    trace.pop("_cum_cost", None)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{scenario_name}_{agent_name}.json").write_text(json.dumps(trace))
    return trace


def run_all(seed: int = DEFAULT_SEED, out: Path = DEFAULT_OUT) -> dict:
    results = []
    for sc in SCENARIOS:
        for ag in ["noop", "rules", "llm"]:
            trace = run_one(sc, ag, seed, out)
            t = trace["totals"]
            results.append({
                "scenario": sc, "agent": ag, "score": t["score"],
                "cost_eur": t["cost_eur"], "floor_eur": t["floor_eur"],
                "oracle_eur": t["oracle_eur"], "false_dispatches": t["false_dispatches"],
                "steps_to_first_action": t["steps_to_first_action"],
                **({"brain": t["brain"]} if "brain" in t else {}),
            })
    payload = {"seed": seed, "results": results}
    (out / "results.json").write_text(json.dumps(payload))
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", choices=SCENARIOS)
    ap.add_argument("--agent", default="llm")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if args.all:
        payload = run_all(args.seed, args.out)
        for r in payload["results"]:
            print(f"{r['scenario']}/{r['agent']}: score={r['score']:.2f} "
                  f"cost={r['cost_eur']:.0f} floor={r['floor_eur']:.0f} "
                  f"oracle={r['oracle_eur']:.0f} false_dispatches={r['false_dispatches']}")
    else:
        if not args.scenario:
            ap.error("--scenario required unless --all")
        trace = run_one(args.scenario, args.agent, args.seed, args.out)
        print(json.dumps(trace["totals"], indent=2))


if __name__ == "__main__":
    main()
