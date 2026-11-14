"""PD-REGRESS-01 — contract tests vs BDD-PD-REGRESS-01.

BDD: 單一入口跑 smoke＋約定 crate／pytest 子集；輸出摘要；失敗非零退出。
Pairs with scripts/pd_regress.py. Does not require elevated MSI.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pd_regress.py"
SMOKE = ROOT / "scripts" / "pd_smoke_01.py"


def test_regress_script_exists():
    assert SCRIPT.is_file(), f"missing single-entry regress script: {SCRIPT}"


def test_smoke_dep_present():
    """deps: PD-SMOKE-01 — regress matrix includes smoke entry."""
    assert SMOKE.is_file(), f"missing smoke script dependency: {SMOKE}"
    text = SCRIPT.read_text(encoding="utf-8")
    assert "pd_smoke_01" in text
    assert "test_pd_smoke_01" in text or "PD-SMOKE-01" in text


def test_matrix_lists_key_crates_and_summary():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "KEY_CRATES" in text
    for pkg in (
        "sgenaxis-core",
        "sgenaxis-ports",
        "sgenaxis-adapters",
        "sgenaxis-exec",
        "sgenaxis-work",
        "sgenaxis-host",
        "sgenaxis-guard",
        "sgenaxis-listen",
        "sgenaxis-evid",
        "sgenaxis-spec",
    ):
        assert pkg in text, f"matrix must include {pkg}"
    assert "SUMMARY" in text or "summary" in text.lower()
    assert "return 1" in text or "SystemExit" in text


def test_list_mode_prints_matrix_exits_zero():
    env = os.environ.copy()
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--list"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "PD-REGRESS-01" in out
    assert "smoke" in out.lower()
    assert "sgenaxis-core" in out
    assert "sgenaxis-exec" in out


def test_no_elevated_msi_required():
    """BDD / allow: no elevated MSI."""
    script = SCRIPT.read_text(encoding="utf-8")
    for banned in (
        "msiexec /",
        "Start-Process -Verb RunAs",
        "ShellExecuteW",
        "packaging/windows/wix",
    ):
        assert banned not in script, f"regress must not require {banned}"
    assert "msiexec /i" not in script.lower()


def test_failure_nonzero_exit_contract():
    """Script encodes fail→non-zero; smoke missing would FAIL."""
    # Import-free structural check: main returns 1 when any step fails.
    text = SCRIPT.read_text(encoding="utf-8")
    assert "all(r.ok for r in results)" in text or "return 1" in text
    assert "PD-REGRESS-01 FAIL" in text
