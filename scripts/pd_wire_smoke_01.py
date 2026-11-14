#!/usr/bin/env python3
"""PD-WIRE-SMOKE-01 re-runnable wire smoke (command-path, not raw adapters).

Coverage (BDD-PD-WIRE-SMOKE-01):
  fixture bind → DispatchHost start_run／board projection observable;
  UI invoke wiring for start_run／load_local_board／git_workbench_*;
  no Tauri → honest NOT RUN (never fake full-feature PASS).

Usage (from repo root)::

    python scripts/pd_wire_smoke_01.py
    # or
    python -m pytest tests/test_pd_wire_smoke_01.py -q
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "tests" / "test_pd_wire_smoke_01.py"


def main() -> int:
    if not TEST.is_file():
        print(f"FAIL: missing {TEST}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    cargo_bin = Path.home() / ".cargo" / "bin"
    env["Path"] = str(cargo_bin) + os.pathsep + env.get("Path", "")

    cmd = [sys.executable, "-m", "pytest", str(TEST), "-q", "--tb=short"]
    print("PD-WIRE-SMOKE-01 running:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env, check=False)
    if proc.returncode != 0:
        print("PD-WIRE-SMOKE-01 FAIL", file=sys.stderr)
        return 1
    print(
        "PD-WIRE-SMOKE-01 PASS|PARTIAL (command-path DispatchHost; "
        "Tauri IPC may be NOT RUN — not full-feature Live PASS)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
