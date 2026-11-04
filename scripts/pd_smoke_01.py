#!/usr/bin/env python3
"""PD-SMOKE-01 re-runnable main-path smoke (no elevated MSI).

Coverage (BDD-PD-SMOKE-01):
  載入 UI／選專案／看板可見／DryRun start＋結束
Any step failure → exit 1 (FAIL).

Usage (from repo root)::

    python scripts/pd_smoke_01.py
    # or
    python -m pytest tests/test_pd_smoke_01.py -q
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "tests" / "test_pd_smoke_01.py"


def main() -> int:
    if not TEST.is_file():
        print(f"FAIL: missing {TEST}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    cargo_bin = Path.home() / ".cargo" / "bin"
    env["Path"] = str(cargo_bin) + os.pathsep + env.get("Path", "")

    cmd = [sys.executable, "-m", "pytest", str(TEST), "-q", "--tb=short"]
    print("PD-SMOKE-01 running:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env, check=False)
    if proc.returncode != 0:
        print("PD-SMOKE-01 FAIL", file=sys.stderr)
        return 1
    print("PD-SMOKE-01 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
