# -*- coding: utf-8 -*-
"""ELU IMPL batch: epic→red 待決策; IMPL gray→yellow PLANNING_ONLY."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe
from board_core.domain import apply_zone

BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
IMPL = [
    "PD-ELU-BINDING-IMPL-01",
    "PD-ELU-DOCUMENT-IMPL-01",
    "PD-ELU-FIXTURE-IMPL-01",
    "PD-ELU-GIT-IMPL-01",
    "PD-ELU-IMPORT-IMPL-01",
    "PD-ELU-INTEGRATION-IMPL-01",
    "PD-ELU-PROJECT-IMPL-01",
    "PD-ELU-RECOVERY-IMPL-01",
    "PD-ELU-UX-IMPL-01",
    "PD-ELU-VERIFY-IMPL-01",
]
EPIC = "PD-ELU-COLLAB-20261026"
PLAN_NOTE = (
    f"\n[{NOW}] 母對話開工：灰→黃 PLANNING_ONLY（tdd=NOT_READY_FOR_IMPLEMENTATION；"
    f"formal envelope 未批；依賴 ARCH 仍紅）。禁止 production fill。"
    f"完成後 reports/dispatch-pd/<ID>.md 含 READY_FOR_TDD；禁止自改綠。"
)
EPIC_NOTE = (
    f"\n[{NOW}] 母對話：epic→紅燈待決策（§7.3）。IMPL 10 卡僅 PLANNING_ONLY，"
    f"不得實作派工至 envelope/ARCH 核准。\n"
    f"待決策事項:\n"
    f"- [ ] DEC-ELU-1: 核准 7 張 PD-ELU-*-ARCH-01"
    f"（IDENTITY/IMPORT/BINDING/MERGE/FIXTURE/GIT/RECOVERY）或書面改規\n"
    f"- [ ] DEC-ELU-2: 各 Primary Module formal file envelope"
    f"（module.html/contract）就緒並標 READY_FOR_SKELETON/IMPLEMENTATION\n"
    f"- [ ] DEC-ELU-3: 44-case 執行面（C/F/G/R）何者可轉 executable RED vs 維持 NOT RUN\n"
    f"狀態: 紅燈阻塞 production 實作派工直至 owner 回覆；PLANNING_ONLY 黃燈可並行。\n"
    f"本批 PLANNING 黃燈: " + ", ".join(IMPL)
)


def mutate(data):
    tasks = data.get("tasks") or []
    by = {t.get("id"): i for i, t in enumerate(tasks)}
    if EPIC in by:
        e = tasks[by[EPIC]]
        e2 = apply_zone(e, "red", "user", NOW)
        e2["note"] = (e2.get("note") or "").rstrip() + EPIC_NOTE
        e2["version"] = int(e.get("version") or 1) + 1
        log = list(e2.get("log") or [])
        if log:
            log[-1] = dict(log[-1])
            log[-1]["note"] = "epic red 待決策"
            e2["log"] = log
        tasks[by[EPIC]] = e2
        print("epic-red", EPIC)
    for cid in IMPL:
        if cid not in by:
            print("MISSING", cid)
            continue
        t = tasks[by[cid]]
        if t.get("zone") == "yellow":
            print("already-yellow", cid)
            continue
        t2 = apply_zone(t, "yellow", "user", NOW)
        t2["note"] = (t2.get("note") or "").rstrip() + PLAN_NOTE
        t2["version"] = int(t.get("version") or 1) + 1
        log = list(t2.get("log") or [])
        if log:
            log[-1] = dict(log[-1])
            log[-1]["note"] = "dispatch PLANNING_ONLY"
            t2["log"] = log
        tasks[by[cid]] = t2
        print("yellow", cid)
    data["tasks"] = tasks
    data["asOf"] = NOW


def main():
    snapshot_safe.mutate_snapshot_file(BOARD, mutate)
    print("OK")


if __name__ == "__main__":
    main()
