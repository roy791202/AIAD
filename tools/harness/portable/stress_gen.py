# -*- coding: utf-8 -*-
"""Generate fake board JSON for harness stress (PD-HARNESS-STRESS-01)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ZONES = ("gray", "yellow", "red", "green")


def gen_tasks(n: int) -> list[dict]:
    tasks = []
    for i in range(n):
        z = ZONES[i % 4]
        tasks.append(
            {
                "id": f"FAKE-{i + 1:04d}",
                "ref": f"FAKE-{i + 1:04d}",
                "title": f"假工項壓力 #{i + 1}",
                "zone": z,
                "kind": "task",
                "bdd": f"BDD-FAKE-{i + 1}",
                "tdd": "PENDING",
                "note": "harness fake — not product evidence",
            }
        )
    return tasks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=500)
    ap.add_argument(
        "-o",
        type=Path,
        default=Path(__file__).resolve().parent / "out" / "stress-board.json",
    )
    args = ap.parse_args()
    if args.n < 1 or args.n > 50000:
        print("n out of range 1..50000", file=sys.stderr)
        return 2
    payload = {
        "asOf": datetime.now(timezone.utc).isoformat(),
        "overall": "PARTIAL",
        "harness": True,
        "stressN": args.n,
        "tasks": gen_tasks(args.n),
    }
    args.o.parent.mkdir(parents=True, exist_ok=True)
    args.o.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", args.o, "tasks", args.n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
