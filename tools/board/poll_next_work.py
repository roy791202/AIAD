#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""排程輪詢：列出下一張「尚未真正做完」的工項（紅 > 黃 > 灰），不改燈號。

滅燈規則：實作完成 → cargo/tauri/驗收通過 → 才手動或由母對話改綠。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_BOARD = REPO / "docs" / "PROJECT-BOARD.html"
PRIORITY = ("red", "yellow", "gray")
# epic is tracking only — skip for "next implement" unless --include-epic
SKIP_DEFAULT = {"PRODUCT-DEV-20261023"}


def load_tasks(board: Path) -> list[dict]:
    html = board.read_text(encoding="utf-8")
    m = re.search(r'id="board-snapshot">(.*?)</script>', html, re.S)
    if not m:
        raise SystemExit("board-snapshot missing")
    data = json.loads(m.group(1))
    return list(data.get("tasks") or [])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", type=Path, default=DEFAULT_BOARD)
    ap.add_argument("--include-epic", action="store_true")
    ap.add_argument("--all", action="store_true", help="list all pending, not only first")
    args = ap.parse_args(argv)
    board = args.board.resolve()
    if not board.is_file():
        print("missing", board, file=sys.stderr)
        return 2

    skip = set() if args.include_epic else set(SKIP_DEFAULT)
    pending: list[dict] = []
    for z in PRIORITY:
        for t in load_tasks(board):
            if t.get("zone") != z:
                continue
            if t.get("id") in skip:
                continue
            pending.append(t)

    if not pending:
        print("QUEUE_EMPTY: no red/yellow/gray work cards (epic ignored)")
        return 0

    rows = pending if args.all else pending[:1]
    for t in rows:
        print(
            f"{t.get('zone')}\t{t.get('id')}\t{t.get('title', '')[:80]}"
        )
    if not args.all and len(pending) > 1:
        print(f"# … and {len(pending) - 1} more; use --all", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
