"""CLI: add real-model worker rows to an existing battery JSON (needs API keys).

    python -m gauntlet.precompute --mode discrimination                 # the 3 DeepSeek personas
    python -m gauntlet.precompute --mode discrimination --add claude     # add Claude on top

Runs each named worker once per case, merges the results and the per-worker
report into the battery file (additively, preserving workers already frozen in),
and freezes them so the demo stays offline. Run after `make battery` has produced
the deterministic battery.
"""

import argparse
import json
from pathlib import Path

from . import battery as B
from .agents.personas import PERSONA_IDS

DEFAULT_OUT = B.REPO_ROOT / "traces" / "battery"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="discrimination",
                    help="battery file stem, e.g. discrimination | adversarial_rules | adversarial_llm")
    ap.add_argument("--add", default=",".join(PERSONA_IDS),
                    help="comma-separated worker ids to run, e.g. claude or ds-cautious,ds-balanced")
    ap.add_argument("--concurrency", type=int, default=6, help="concurrent API requests")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    worker_ids = [w.strip() for w in args.add.split(",") if w.strip()]
    f = args.out / f"{args.mode.replace(':', '_')}.json"
    if not f.exists():
        ap.error(f"no battery at {f}; run `make battery` first")
    payload = json.loads(f.read_text())

    print(f"running {worker_ids} x {payload['k']} cases for {args.mode} "
          f"({args.concurrency} concurrent) ...")
    B.add_real_workers(payload, worker_ids, max_workers=args.concurrency)
    f.write_text(json.dumps(payload))

    print(f"\nmerged {worker_ids} into {f}")
    print(f"\n{'worker':16s} {'pass':>6s} {'P10':>6s} {'mean':>6s}   hardest")
    for w in payload["workers"]:
        r = payload["report"][w["id"]]
        print(f"{w['label']:16s} {r['pass_rate']*100:5.0f}% {r['p10']*100:5.0f}% {r['mean']*100:5.0f}%   "
              f"{r['hardest']['label'][:44]}")


if __name__ == "__main__":
    main()
