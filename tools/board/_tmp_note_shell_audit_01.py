# -*- coding: utf-8 -*-
"""Append READY_FOR_GREEN yellow note for PD-SHELL-AUDIT-01 only."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "board"))

from board_core import snapshot_safe  # noqa: E402

CARD_ID = "PD-SHELL-AUDIT-01"
BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
TZ = timezone(timedelta(hours=8))
TS = datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S%z")
if len(TS) >= 5 and TS[-5] in "+-" and TS[-3] != ":":
    TS = TS[:-2] + ":" + TS[-2:]

NOTE_LINE = (
    f"[{TS}] READY_FOR_GREEN — docs/shell-audit-PD-SHELL-AUDIT-01.md + "
    f"tests/test_pd_shell_audit_01.py；Must/Should/Won't v0.1；"
    f"禁止暗示 MSI 視覺對齊業已完成；zone 維持 yellow（§7.1 不自改綠）。"
    f"報告: reports/dispatch-pd/PD-SHELL-AUDIT-01.md"
)


def add_note(data: dict) -> dict:
    for t in data.get("tasks") or []:
        if t.get("id") == CARD_ID:
            if t.get("zone") == "green":
                raise AssertionError("refusing to touch green card")
            note = (t.get("note") or "").rstrip()
            t["note"] = note + "\n" + NOTE_LINE
            t["updatedAt"] = TS
            t["updatedBy"] = "agent"
            t["zone"] = "yellow"
            if not t.get("startedAt"):
                t["startedAt"] = TS
            log = t.get("log") or []
            log.append({"t": TS, "zone": "yellow", "by": "agent", "note": "READY_FOR_GREEN"})
            t["log"] = log
            return t
    raise KeyError(CARD_ID)


def main() -> None:
    card = snapshot_safe.mutate_snapshot_file(BOARD, add_note)
    print("OK", card["id"], card["zone"])
    print(NOTE_LINE)


if __name__ == "__main__":
    main()
