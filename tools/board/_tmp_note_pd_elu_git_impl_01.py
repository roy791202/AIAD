"""Append yellow-only note for PD-ELU-GIT-IMPL-01. Do not change zone."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from board_core import snapshot_safe

BOARD = Path(__file__).resolve().parents[2] / "docs" / "PROJECT-BOARD.html"
CARD_ID = "PD-ELU-GIT-IMPL-01"
TS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
LINE = (
    f"\n[{TS}] PLANNING_ONLY → READY_FOR_TDD "
    f"reports/dispatch-pd/PD-ELU-GIT-IMPL-01.md; "
    f"G02/G03/G04/G05/G08/G09/G11/G13 RED designs + envelope/GitPort gates; "
    f"G11 rejection-only; zone stays yellow; no production/tests."
)


def add_note(data):
    for t in data.get("tasks", []):
        if t.get("id") == CARD_ID:
            zone = t.get("zone")
            if zone == "green":
                raise RuntimeError("refusing to touch green card")
            # stay yellow (or leave non-green as-is but force yellow if gray)
            if zone != "yellow":
                t["zone"] = "yellow"
            t["note"] = (t.get("note") or "") + LINE
            t["tdd"] = (
                "NOT_READY_FOR_IMPLEMENTATION. Cases G02,G03,G04,G05,G08,G09,G11,G13 "
                "NOT RUN. Planning packet READY_FOR_TDD at "
                "reports/dispatch-pd/PD-ELU-GIT-IMPL-01.md."
            )
            return t
    raise KeyError(CARD_ID)


def main() -> None:
    snapshot_safe.mutate_snapshot_file(BOARD, add_note)
    print("OK note appended; zone yellow; READY_FOR_TDD")


if __name__ == "__main__":
    main()
