#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPRECATED / SAFETY LOCK.

No tool may batch-close cards or write docs/board.json. This script always refuses (exit 2).
To see the next open work card:

  python tools/board/poll_next_work.py
"""
from __future__ import annotations

import sys

EXIT_REFUSED = 2


def main() -> int:
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    print(
        "REFUSED: poll_extinguish must NOT close cards or write docs/board.json.\n"
        "硬性規則（PRODUCT-DEVELOPMENT §7.1）：未產出 → 不可結案。\n"
        "只有高階模型／使用者才可設 Done／Blue；須先有獨立 TDD 代理回報 TDD_PASS，且 PR 已合併。\n"
        "實作代理不可設 Done／Blue，也不可自稱 TDD PASS。\n"
        "Use: python tools/board/poll_next_work.py\n",
        file=sys.stderr,
    )
    return EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(main())
