#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPRECATED / SAFETY LOCK.

Owner clarified: 「滅燈」= 實際做完工項後才改綠，禁止排程直接改綠。

本檔保留為明確拒絕，避免誤用舊 cmd。
請改用實際實作 + 驗收改綠；查下一張待做：

  python tools/board/poll_next_work.py
"""
from __future__ import annotations

import sys


def main() -> int:
    print(
        "REFUSED: poll_extinguish must NOT admin-green cards.\n"
        "硬性規則（PRODUCT-DEVELOPMENT §7.1）：未產出 → 不可滅；\n"
        "且須獨立 TDD Agent 回報 TDD_PASS 後，母對話才可標綠。\n"
        "實作代理不可改綠／不可自稱 TDD PASS。\n"
        "Use: python tools/board/poll_next_work.py\n",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
