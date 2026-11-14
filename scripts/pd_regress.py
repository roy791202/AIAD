#!/usr/bin/env python3
"""PD-REGRESS-01 — single-entry regression matrix (smoke + key crates).

BDD-PD-REGRESS-01:
  單一入口跑 smoke＋約定 crate／pytest 子集；輸出摘要；失敗非零退出。
Does **not** require elevated MSI or WiX installers.

Usage (from repo root)::

    python scripts/pd_regress.py
    python scripts/pd_regress.py --list

Steps (agreed matrix):
  1. pytest subset — PD-SMOKE-01 (`tests/test_pd_smoke_01.py` via scripts/pd_smoke_01.py)
  2. cargo test --lib for each key desktop crate (manifest-path; no workspace root required)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "apps" / "sgenaxis-desktop"
SMOKE_SCRIPT = ROOT / "scripts" / "pd_smoke_01.py"

# Agreed key crates (desktop) — Pure/domain + adapters; no elevated install.
# Paths relative to apps/sgenaxis-desktop.
KEY_CRATES: list[tuple[str, str]] = [
    ("sgenaxis-core", "crates/sgenaxis-core/Cargo.toml"),
    ("sgenaxis-ports", "crates/sgenaxis-ports/Cargo.toml"),
    ("sgenaxis-adapters", "crates/sgenaxis-adapters/Cargo.toml"),
    ("sgenaxis-exec", "crates/sgenaxis-exec/Cargo.toml"),
    ("sgenaxis-work", "crates/sgenaxis-work/Cargo.toml"),
    ("sgenaxis-host", "crates/sgenaxis-host/Cargo.toml"),
    ("sgenaxis-guard", "crates/sgenaxis-guard/Cargo.toml"),
    ("sgenaxis-listen", "crates/sgenaxis-listen/Cargo.toml"),
    ("sgenaxis-evid", "crates/sgenaxis-evid/Cargo.toml"),
    ("sgenaxis-spec", "crates/sgenaxis-spec/Cargo.toml"),
]


@dataclass
class StepResult:
    name: str
    ok: bool
    seconds: float
    detail: str


def _cargo_bin() -> str:
    home = Path.home() / ".cargo" / "bin" / ("cargo.exe" if os.name == "nt" else "cargo")
    if home.is_file():
        return str(home)
    return "cargo"


def _env_with_cargo() -> dict[str, str]:
    env = os.environ.copy()
    cargo_bin = Path.home() / ".cargo" / "bin"
    env["Path"] = str(cargo_bin) + os.pathsep + env.get("Path", "")
    return env


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=_env_with_cargo(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def run_smoke() -> StepResult:
    name = "smoke:PD-SMOKE-01"
    if not SMOKE_SCRIPT.is_file():
        return StepResult(name, False, 0.0, f"missing {SMOKE_SCRIPT}")
    t0 = time.perf_counter()
    code, out = _run([sys.executable, str(SMOKE_SCRIPT)], ROOT)
    elapsed = time.perf_counter() - t0
    # Keep last non-empty lines for summary
    tail = "\n".join(line for line in out.strip().splitlines()[-8:] if line.strip())
    ok = code == 0
    return StepResult(name, ok, elapsed, tail or f"exit {code}")


def run_crate(pkg: str, rel_manifest: str) -> StepResult:
    name = f"cargo:{pkg}"
    manifest = DESKTOP / rel_manifest
    if not manifest.is_file():
        return StepResult(name, False, 0.0, f"missing manifest {manifest}")
    cmd = [
        _cargo_bin(),
        "test",
        "--lib",
        "--manifest-path",
        str(manifest),
        "--color",
        "never",
    ]
    t0 = time.perf_counter()
    code, out = _run(cmd, DESKTOP)
    elapsed = time.perf_counter() - t0
    # Prefer cargo's result line
    summary = ""
    for line in out.splitlines():
        low = line.lower()
        if "passed" in low or "failed" in low or "error" in low:
            summary = line.strip()
    if not summary:
        summary = f"exit {code}"
    return StepResult(name, code == 0, elapsed, summary)


def print_matrix() -> None:
    print("PD-REGRESS-01 matrix (agreed):")
    print("  1. smoke  → python scripts/pd_smoke_01.py")
    print("             (pytest subset: tests/test_pd_smoke_01.py)")
    print("  2. crates → cargo test --lib --manifest-path <crate>")
    for pkg, rel in KEY_CRATES:
        print(f"             - {pkg}  ({rel})")


def print_summary(results: list[StepResult]) -> None:
    width = max(len(r.name) for r in results)
    print()
    print("=== PD-REGRESS-01 SUMMARY ===")
    failed = 0
    for r in results:
        status = "PASS" if r.ok else "FAIL"
        if not r.ok:
            failed += 1
        print(f"  [{status}] {r.name:<{width}}  {r.seconds:6.1f}s  {r.detail}")
    total = len(results)
    print(f"--- {total - failed}/{total} steps ok ---")
    if failed:
        print("PD-REGRESS-01 FAIL")
    else:
        print("PD-REGRESS-01 PASS")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PD-REGRESS-01 regression matrix")
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print agreed matrix and exit 0 (no tests)",
    )
    args = parser.parse_args(argv)

    if args.list:
        print_matrix()
        return 0

    print("PD-REGRESS-01 running...")
    print_matrix()
    print()

    results: list[StepResult] = []
    results.append(run_smoke())
    print(f"  [{'PASS' if results[-1].ok else 'FAIL'}] {results[-1].name}")

    for pkg, rel in KEY_CRATES:
        r = run_crate(pkg, rel)
        results.append(r)
        print(f"  [{'PASS' if r.ok else 'FAIL'}] {r.name}")

    print_summary(results)
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
