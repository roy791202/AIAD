# -*- coding: utf-8 -*-
"""TDD_PASS 後母對話滅燈：三實作卡＋epic → green。"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from board_core import snapshot_safe

BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
IDS = (
    "PD-ARCH-DAG-SHELL-01",
    "PD-ARCH-NODE-IO-01",
    "PD-ARCH-ACL-LIVE-01",
    "PRODUCT-ARCH-DAG-20261024",
)


def mutate(data):
    for t in data.get("tasks") or []:
        tid = t.get("id")
        if tid not in IDS:
            continue
        t["zone"] = "green"
        t["doneAt"] = NOW
        t["updatedAt"] = NOW
        t["updatedBy"] = "parent-pm"
        t["version"] = int(t.get("version") or 1) + 1
        note = (t.get("note") or "").rstrip()
        if tid.startswith("PD-ARCH-"):
            note += (
                f"\n[{NOW}] TDD_PASS → parent green. "
                f"reports/dispatch-pd/{tid}.md + {tid}-TDD-REVIEW.md."
            )
        else:
            note += (
                f"\n[{NOW}] epic green：子卡 DAG-SHELL／NODE-IO／ACL-LIVE 皆 TDD_PASS；"
                f"決策 PD-DEC-ARCH-KINDS-01 已決。"
            )
        t["note"] = note
        log = list(t.get("log") or [])
        log.append({"t": NOW, "zone": "green", "by": "parent-pm"})
        t["log"] = log[-20:]
        print("green", tid)
    data["asOf"] = NOW
    return list(IDS)


def main():
    snapshot_safe.mutate_snapshot_file(BOARD, mutate)
    print("OK")


if __name__ == "__main__":
    main()
