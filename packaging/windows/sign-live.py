#!/usr/bin/env python3
"""Hyphenated CLI alias for sign_live (PD-REMAIN-SIGN-LIVE-01)."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from sign_live import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
