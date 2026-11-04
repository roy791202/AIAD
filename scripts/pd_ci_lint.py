#!/usr/bin/env python3
"""PD-CI-01 — PR lint gate (stdlib only; no paid runners).

Compiles fixed Python trees with ``compileall``. Any failure → exit 1
(must not be treated as green).

Usage (from repo root)::

    python scripts/pd_ci_lint.py
"""

from __future__ import annotations

import compileall
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Fixed lint roots for the PR gate (keep in sync with docs/CI-PR-GATE.md).
LINT_DIRS = (
    ROOT / "scripts",
    ROOT / "sgenaxis",
    ROOT / "tests",
    ROOT / "tools" / "board",
)


def main() -> int:
    missing = [p for p in LINT_DIRS if not p.is_dir()]
    if missing:
        for p in missing:
            print(f"FAIL: missing lint root {p}", file=sys.stderr)
        return 1

    print("PD-CI-01 lint: compileall on", ", ".join(str(p.relative_to(ROOT)) for p in LINT_DIRS))
    ok = True
    for path in LINT_DIRS:
        # quiet=1: only print errors; return False on any failure
        if not compileall.compile_dir(str(path), quiet=1, force=False):
            print(f"FAIL: compileall errors under {path.relative_to(ROOT)}", file=sys.stderr)
            ok = False

    if not ok:
        print("PD-CI-01 lint FAIL", file=sys.stderr)
        return 1
    print("PD-CI-01 lint PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
