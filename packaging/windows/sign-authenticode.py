#!/usr/bin/env python3
"""Hyphenated CLI alias for sign_authenticode (PD-SIGN-STUB-01)."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from sign_authenticode import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
