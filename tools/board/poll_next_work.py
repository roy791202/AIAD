#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List the next open work card from docs/board.json (read-only; never writes the board).

Filters status in {Todo, Backlog, In Progress}; skips Epics (unless --include-epic)
and pending-decision cards (light=Red with lightReason starting with 「待決策：」).
Order: light Red > Yellow > Gray > Green, then oldest updatedAt, then id.
Exit 0 on success (including QUEUE_EMPTY); exit 2 if the board is missing or not valid JSON.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_BOARD = REPO / "docs" / "board.json"

EXIT_OK = 0
EXIT_BOARD_UNREADABLE = 2

OPEN_STATUSES = frozenset({"Todo", "Backlog", "In Progress"})
LIGHT_RANK = {"Red": 0, "Yellow": 1, "Gray": 2, "Green": 3}
EPIC_LEVEL = "Epic"
PENDING_DECISION_PREFIX = "待決策："
TITLE_WIDTH = 80


class BoardUnreadable(Exception):
    """The board file is missing or is not valid JSON."""


def load_items(board: Path) -> list[dict]:
    try:
        data = json.loads(board.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BoardUnreadable(f"{board}: {exc}") from exc
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise BoardUnreadable(f"{board}: no 'items' list")
    return [item for item in items if isinstance(item, dict)]


def is_pending_decision(card: dict) -> bool:
    reason = card.get("lightReason") or ""
    return card.get("light") == "Red" and reason.startswith(PENDING_DECISION_PREFIX)


def is_open_work(card: dict, include_epic: bool) -> bool:
    if card.get("status") not in OPEN_STATUSES:
        return False
    if card.get("level") == EPIC_LEVEL and not include_epic:
        return False
    return not is_pending_decision(card)


def sort_key(card: dict) -> tuple:
    light_rank = LIGHT_RANK.get(card.get("light"), len(LIGHT_RANK))
    return (light_rank, str(card.get("updatedAt") or ""), str(card.get("id") or ""))


def pending_work(items: list[dict], include_epic: bool) -> list[dict]:
    return sorted((c for c in items if is_open_work(c, include_epic)), key=sort_key)


def format_row(card: dict) -> str:
    title = str(card.get("title") or "")[:TITLE_WIDTH]
    return f"{card.get('light')}\t{card.get('status')}\t{card.get('id')}\t{title}"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--board", type=Path, default=DEFAULT_BOARD, help="board JSON (default docs/board.json)")
    ap.add_argument("--all", action="store_true", help="list every open card, not only the first")
    ap.add_argument("--include-epic", action="store_true", help="also list Epic-level cards")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args(argv)
    try:
        items = load_items(args.board)
    except BoardUnreadable as exc:
        print(f"BOARD_UNREADABLE: {exc}", file=sys.stderr)
        return EXIT_BOARD_UNREADABLE

    pending = pending_work(items, args.include_epic)
    if not pending:
        print("QUEUE_EMPTY: no open Todo/Backlog/In Progress work cards")
        return EXIT_OK

    rows = pending if args.all else pending[:1]
    for card in rows:
        print(format_row(card))
    if not args.all and len(pending) > 1:
        print(f"# ... and {len(pending) - 1} more; use --all", file=sys.stderr)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
