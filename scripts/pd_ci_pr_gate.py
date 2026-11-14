#!/usr/bin/env python3
"""PD-CI-01 — PR gate entry (lint + fixed unit/smoke-adjacent pytest subset).

Local equivalent of ``.github/workflows/pr-gate.yml``.
Any step failure → exit 1 (never treat as green).

Usage (from repo root)::

    python scripts/pd_ci_pr_gate.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINT = ROOT / "scripts" / "pd_ci_lint.py"

# Fixed PR test subset (unit; no cargo / no elevated MSI).
# Keep in sync with docs/CI-PR-GATE.md and .github/workflows/pr-gate.yml.
PR_TEST_SUBSET = (
    "tests/test_board_rules.py",
    "tests/test_board_files.py",
    "tests/test_stats.py",
    "tests/test_schedule.py",
    "tests/test_dispatcher.py",
)


def _run(cmd: list[str], label: str) -> int:
    print(f"PD-CI-01 {label}:", " ".join(cmd), flush=True)
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env, check=False)
    if proc.returncode != 0:
        print(f"PD-CI-01 {label} FAIL (exit {proc.returncode})", file=sys.stderr, flush=True)
        return 1
    print(f"PD-CI-01 {label} PASS", flush=True)
    return 0


def main() -> int:
    if not LINT.is_file():
        print(f"FAIL: missing {LINT}", file=sys.stderr)
        return 1

    if _run([sys.executable, str(LINT)], "lint") != 0:
        print("PD-CI-01 PR gate FAIL", file=sys.stderr)
        return 1

    missing = [p for p in PR_TEST_SUBSET if not (ROOT / p).is_file()]
    if missing:
        for p in missing:
            print(f"FAIL: missing test {p}", file=sys.stderr)
        print("PD-CI-01 PR gate FAIL", file=sys.stderr)
        return 1

    cmd = [sys.executable, "-m", "pytest", *PR_TEST_SUBSET, "-q", "--tb=short"]
    if _run(cmd, "test-subset") != 0:
        print("PD-CI-01 PR gate FAIL", file=sys.stderr)
        return 1

    print("PD-CI-01 PR gate PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
