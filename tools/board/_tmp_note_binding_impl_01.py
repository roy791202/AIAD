"""One-shot: append yellow note on PD-ELU-BINDING-IMPL-01 only. Do not change zone."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from board_core import snapshot_safe

ROOT = Path(__file__).resolve().parents[2]
BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
CARD_ID = "PD-ELU-BINDING-IMPL-01"
TS = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
MARKER = "BLK-01 fixed: Phase-1 preview vs Phase-2 exec"
LINE = (
    f"[{TS}] PLANNING_ONLY READY_FOR_TDD zone=yellow: "
    f"{MARKER}; DEC-BV-4 gate before full C09/F04 exec RED; "
    "packet reports/dispatch-pd/PD-ELU-BINDING-IMPL-01.md; NOT_READY_FOR_IMPLEMENTATION."
)


def add_note(data):
    for t in data.get("tasks", []):
        if t.get("id") == CARD_ID:
            note = t.get("note") or ""
            if MARKER in note:
                print("BLK-01 note already present; zone=", t.get("zone"))
                return t
            t["note"] = (note.rstrip() + "\n" + LINE).strip() + "\n"
            print("appended note; zone=", t.get("zone"), "kind=", t.get("kind"))
            return t
    raise KeyError(CARD_ID)


def main():
    snapshot_safe.mutate_snapshot_file(BOARD, add_note)
    print("ok", CARD_ID)


if __name__ == "__main__":
    main()
