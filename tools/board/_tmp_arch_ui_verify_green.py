# -*- coding: utf-8 -*-
"""Parent green: ARCH-UI VERIFY cards after pytest TDD_PASS (§7.1)."""
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
    "PD-ARCH-UI-V-01",
    "PD-ARCH-UI-V-02",
    "PD-ARCH-UI-V-03",
    "PD-ARCH-UI-V-04",
    "PD-ARCH-UI-V-05",
    "PD-ARCH-UI-V-06",
    "PD-ARCH-UI-V-07",
    "PD-ARCH-UI-V-08",
    "PD-ARCH-UI-V-09",
    "PRODUCT-ARCH-UI-VERIFY-20261025",
)

NOTE = (
    f"\n[{NOW}] 母對話滅燈（§7.1）：pytest tests/test_pd_arch_ui_verify_01.py "
    f"10 passed（含 V-09 drawerless 字串對齊現況 diagram|git|settings）。"
    f" VERIFY 靜態 AC 全過 → zone=green。"
)


def mutate(data):
    tasks = data.get("tasks") or []
    by_id = {t.get("id"): t for t in tasks}
    for tid in IDS:
        t = by_id.get(tid)
        if not t:
            print("MISSING", tid)
            continue
        if t.get("zone") == "green":
            print("already-green", tid)
            continue
        t["zone"] = "green"
        t["doneAt"] = NOW
        t["updatedAt"] = NOW
        t["updatedBy"] = "human"
        t["version"] = int(t.get("version") or 1) + 1
        t["note"] = (t.get("note") or "").rstrip() + NOTE
        log = list(t.get("log") or [])
        log.append({"t": NOW, "zone": "green", "by": "parent-pm"})
        t["log"] = log
        print("green", tid)
    data["asOf"] = NOW


def main():
    snapshot_safe.mutate_snapshot_file(BOARD, mutate)
    print("OK")


if __name__ == "__main__":
    main()
