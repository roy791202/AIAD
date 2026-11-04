#!/usr/bin/env python3
"""PD-SIGN-STUB-01 re-runnable Authenticode signing stub entry.

Delegates to ``packaging/windows/sign_authenticode.py``.
No certificate configured → NOT RUN (never forged PASS). Does not purchase certs.

Usage (from repo root)::

    python scripts/pd_sign_stub_01.py
    python scripts/pd_sign_stub_01.py --dry-cert
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIN = ROOT / "packaging" / "windows"
if str(WIN) not in sys.path:
    sys.path.insert(0, str(WIN))

from sign_authenticode import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
