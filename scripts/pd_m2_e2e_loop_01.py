#!/usr/bin/env python3
"""PD-M2-E2E-LOOP-01 re-runnable M2 closed-loop orchestrator (DryRun only).

Coverage (BDD-PD-M2-E2E-LOOP-01):
  load_board＋git summarize＋Cli｜Mcp DryRun start→chunk／exit
Missing cargo → pytest skip／NOT RUN. Does **not** claim full Live PASS.

Usage (from repo root)::

    python scripts/pd_m2_e2e_loop_01.py
    # or
    python -m pytest tests/test_pd_m2_e2e_loop_01.py -q
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "tests" / "test_pd_m2_e2e_loop_01.py"


def main() -> int:
    if not TEST.is_file():
        print(f"FAIL: missing {TEST}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    cargo_bin = Path.home() / ".cargo" / "bin"
    env["Path"] = str(cargo_bin) + os.pathsep + env.get("Path", "")

    cmd = [sys.executable, "-m", "pytest", str(TEST), "-q", "--tb=short"]
    print("PD-M2-E2E-LOOP-01 running:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env, check=False)
    if proc.returncode != 0:
        print("PD-M2-E2E-LOOP-01 FAIL", file=sys.stderr)
        return 1
    print("PD-M2-E2E-LOOP-01 PASS (DryRun E2E - not full Live PASS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
