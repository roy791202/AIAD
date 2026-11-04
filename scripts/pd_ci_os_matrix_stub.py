#!/usr/bin/env python3
"""PD-M4-CI-MATRIX-01 — multi-OS CI matrix stub (windows / macos / linux).

Prints the matrix with status PASS | FAIL | NOT RUN | PARTIAL.
Missing / disabled runners → NOT RUN (never forge PASS for absent OS).
Does not require a paid macOS runner.

Local dry-run (from repo root)::

    python scripts/pd_ci_os_matrix_stub.py
    python scripts/pd_ci_os_matrix_stub.py --ci --os windows

Cross-ref PD-CI-01 (same gate commands)::

    python scripts/pd_ci_pr_gate.py
    # see docs/CI-PR-GATE.md · docs/CI-OS-MATRIX.md
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PR_GATE = ROOT / "scripts" / "pd_ci_pr_gate.py"

# Canonical matrix cells (BDD-PD-M4-CI-MATRIX-01).
OS_CELLS = ("windows", "macos", "linux")

VALID_STATUS = frozenset({"PASS", "FAIL", "BLOCKED", "NOT RUN", "PARTIAL"})


def _host_os_cell() -> str:
    sysname = platform.system().lower()
    if sysname.startswith("win"):
        return "windows"
    if sysname == "darwin":
        return "macos"
    return "linux"


def _macos_runner_enabled() -> bool:
    """True only when explicitly enabled (free macos-latest). Never implies paid runner."""
    raw = (os.environ.get("PD_MATRIX_MACOS_ENABLED") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _run_pr_gate() -> str:
    """Run PD-CI-01 local-equivalent gate; map exit → PASS|FAIL."""
    if not PR_GATE.is_file():
        print(f"FAIL: missing PD-CI-01 gate script {PR_GATE}", file=sys.stderr)
        return "FAIL"
    print(f"PD-M4-CI-MATRIX-01 invoke PD-CI-01: {sys.executable} {PR_GATE}", flush=True)
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    proc = subprocess.run([sys.executable, str(PR_GATE)], cwd=str(ROOT), env=env, check=False)
    return "PASS" if proc.returncode == 0 else "FAIL"


def _cell_active(cell: str, focus: str | None, host: str) -> bool:
    """Active only when this process is actually on that OS runner.

    Focus selects which cell this job owns; other cells → NOT RUN.
    Wrong-host focus (e.g. ``--os linux`` on Windows) → NOT RUN, never forge PASS.
    """
    if focus is not None and cell != focus:
        return False
    return cell == host


def build_matrix(focus: str | None, run_gate: bool) -> list[tuple[str, str]]:
    host = _host_os_cell()
    rows: list[tuple[str, str]] = []
    for cell in OS_CELLS:
        if not _cell_active(cell, focus, host):
            status = "NOT RUN"
        elif run_gate:
            status = _run_pr_gate()
        else:
            status = "PARTIAL"  # listed dry stub; gate not invoked
        if status not in VALID_STATUS:
            raise RuntimeError(f"invalid status {status!r} for {cell}")
        rows.append((cell, status))
    return rows


def print_matrix(rows: list[tuple[str, str]]) -> None:
    print("PD-M4-CI-MATRIX-01 OS matrix stub")
    print(f"host={_host_os_cell()}  macos_enabled={_macos_runner_enabled()}")
    print("| os | status |")
    print("|----|--------|")
    for cell, status in rows:
        print(f"| {cell} | {status} |")
    print("Cross-ref PD-CI-01: python scripts/pd_ci_pr_gate.py  (docs/CI-PR-GATE.md)")
    print("Matrix docs: docs/CI-OS-MATRIX.md")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--ci",
        action="store_true",
        help="CI mode: run PD-CI-01 gate on the focused OS cell when a runner is present",
    )
    ap.add_argument(
        "--os",
        choices=OS_CELLS,
        default=None,
        help="Focus one matrix cell (others → NOT RUN). Default: host OS dry stub",
    )
    args = ap.parse_args(argv)

    rows = build_matrix(focus=args.os, run_gate=bool(args.ci))
    print_matrix(rows)

    if args.os == "macos" and not _macos_runner_enabled() and _host_os_cell() != "macos":
        print("PD-M4-CI-MATRIX-01 macos cell NOT RUN (no paid mac runner required)", flush=True)

    for _cell, status in rows:
        if status == "FAIL":
            print("PD-M4-CI-MATRIX-01 FAIL", file=sys.stderr)
            return 1

    print("PD-M4-CI-MATRIX-01 stub complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
