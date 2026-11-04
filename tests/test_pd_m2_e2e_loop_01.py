"""PD-M2-E2E-LOOP-01 — M2 closed-loop integration orchestrator.

BDD-PD-M2-E2E-LOOP-01: re-runnable chain of load_board＋git summarize＋
Cli｜Mcp DryRun start_run→chunk／exit. Missing cargo／rustc → explicit FIXTURE_SETUP failure.
Never claims full Live PASS (DryRun only; no DCC).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "apps" / "sgenaxis-desktop"
HOST_DIR = DESKTOP / "crates" / "sgenaxis-host"
HOST_MANIFEST = HOST_DIR / "Cargo.toml"
E2E_RS = HOST_DIR / "tests" / "m2_e2e_loop.rs"
SCRIPT = ROOT / "scripts" / "pd_m2_e2e_loop_01.py"
REPORT = ROOT / "reports" / "dispatch-pd" / "PD-M2-E2E-LOOP-01.md"

FILTER = "m2_e2e_loop_board_git_cli_mcp_dryrun_chain"


def _cargo_bin() -> str:
    home = Path.home() / ".cargo" / "bin" / ("cargo.exe" if os.name == "nt" else "cargo")
    if home.is_file():
        return str(home)
    return "cargo"


def test_deliverables_present():
    assert HOST_MANIFEST.is_file()
    assert E2E_RS.is_file()
    assert SCRIPT.is_file()
    text = E2E_RS.read_text(encoding="utf-8")
    assert "PD-M2-E2E-LOOP-01" in text
    assert "BDD-PD-M2-E2E-LOOP-01" in text
    assert "load_board_file" in text
    assert "summarize_worktree" in text
    assert "cli_dry_run" in text
    assert "mcp_dry_run" in text
    assert "NOT RUN" in text
    assert "Live PASS" in text or "full Live" in text


def test_no_live_forced_in_source():
    """Guard: integration source must not force Live spawn／DCC."""
    text = E2E_RS.read_text(encoding="utf-8")
    assert "cli_live" not in text
    assert "mcp_live" not in text
    assert "real-spawn" not in text
    assert "maya" not in text.lower()
    assert "houdini" not in text.lower()


def test_m2_e2e_loop_cargo_or_not_run():
    """Run DryRun closed-loop via cargo; missing toolchain is FIXTURE_SETUP failure."""
    cargo = _cargo_bin()
    if shutil.which(cargo) is None and not Path(cargo).is_file():
        pytest.fail("FIXTURE_SETUP: cargo／rustc required — cannot execute M2 E2E DryRun binary")

    env = os.environ.copy()
    cargo_home = Path.home() / ".cargo" / "bin"
    env["PATH"] = str(cargo_home) + os.pathsep + env.get("PATH", "")

    cmd = [
        cargo,
        "test",
        "-p",
        "sgenaxis-host",
        "--test",
        "m2_e2e_loop",
        FILTER,
        "--",
        "--nocapture",
    ]
    print("PD-M2-E2E-LOOP-01 running:", " ".join(cmd))
    proc = subprocess.run(
        cmd,
        cwd=str(DESKTOP),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    print(out)
    if proc.returncode != 0:
        pytest.fail(
            f"PD-M2-E2E-LOOP-01 FAIL: cargo test exit {proc.returncode}\n{out[-4000:]}"
        )
    assert "PD-M2-E2E-LOOP-01 PASS" in out or "test result: ok" in out.lower()
    # Must not claim full Live PASS in the DryRun chain output.
    assert "full Live PASS" not in out or "NOT a full Live PASS" in out
