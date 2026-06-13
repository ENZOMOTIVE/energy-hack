"""CLI: add real DeepSeek persona rows to an existing battery JSON (needs the key).

    python -m gauntlet.precompute --mode discrimination

Runs each persona once per case, merges the results and the per-worker report
into the battery file, and freezes them so the demo stays offline. Run after
`make battery` has produced the deterministic battery.
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
    ap.add_argument("--workers", type=int, default=8, help="concurrent API requests")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    f = args.out / f"{args.mode.replace(':', '_')}.json"
    if not f.exists():
        ap.error(f"no battery at {f}; run `make battery` first")
    payload = json.loads(f.read_text())

    print(f"running {len(PERSONA_IDS)} personas x {payload['k']} cases for {args.mode} "
          f"({args.workers} concurrent) ...")
    B.add_personas(payload, PERSONA_IDS, max_workers=args.workers)
    f.write_text(json.dumps(payload))

    print(f"\nmerged personas into {f}")
    print(f"\n{'worker':14s} {'pass':>6s} {'P10':>6s} {'mean':>6s}   hardest")
    for w in payload["workers"]:
        r = payload["report"][w["id"]]
        print(f"{w['label']:14s} {r['pass_rate']*100:5.0f}% {r['p10']*100:5.0f}% {r['mean']*100:5.0f}%   "
              f"{r['hardest']['label'][:46]}")


if __name__ == "__main__":
    main()
