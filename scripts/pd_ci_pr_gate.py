#!/usr/bin/env python3
"""PD-CI-01 — PR gate entry (lint + fixed unit/smoke-adjacent pytest subset + AI-dev skills checks).

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
SKILLS_SYNC = ROOT / "tools" / "skills" / "sync_skills.py"
SKILLS_TEST = "tests/test_skills_sync.py"

# Fixed PR test subset (unit; no cargo / no elevated MSI).
# Keep in sync with docs/CI-PR-GATE.md and .github/workflows/pr-gate.yml.
PR_TEST_SUBSET = (
    "tests/test_board_rules.py",
    "tests/test_board_files.py",
    "tests/test_stats.py",
    "tests/test_schedule.py",
    "tests/test_dispatcher.py",
    # PD-CI-GUARD-CLOSEOUT-01: AI Dev Guard behaviour (needs pwsh; built into ubuntu-latest).
    "tests/test_ai_dev_guard_closeout.py",
    # PD-CI-GUARD-HARDEN-01: the three validate-board.ps1 copies stay byte-identical.
    "tests/test_validate_board_copies.py",
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

    # PD-CI-SKILLS-GATE-01: AI-dev skills generated copies in sync + skills tests.
    # --check covers tracked targets only (gitignored .claude/skills is skipped),
    # so CI needs no local generation step.
    if not SKILLS_SYNC.is_file() or not (ROOT / SKILLS_TEST).is_file():
        print(f"FAIL: missing {SKILLS_SYNC} or {SKILLS_TEST}", file=sys.stderr)
        print("PD-CI-01 PR gate FAIL", file=sys.stderr)
        return 1
    skills_steps = (
        ([sys.executable, "-X", "utf8", str(SKILLS_SYNC), "--check"], "skills-sync-check"),
        ([sys.executable, "-X", "utf8", "-m", "pytest", SKILLS_TEST, "-q", "--tb=short"], "skills-test"),
    )
    for skills_cmd, label in skills_steps:
        if _run(skills_cmd, label) != 0:
            print("PD-CI-01 PR gate FAIL", file=sys.stderr)
            return 1

    print("PD-CI-01 PR gate PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
