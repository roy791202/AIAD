"""PD-WIRE-SMOKE-01 — desktop wire smoke vs BDD-PD-WIRE-SMOKE-01.

Asserts **command-path** wiring (UI invoke → DispatchHost／allowlisted commands),
not raw AgentRouter／FakeGit／load_board_file adapter calls.

Under fixture: DispatchHost bind＋board＋DryRun at least one observable (cargo).
No Tauri CLI／WebView → explicit NOT RUN (never fake full-feature PASS).
Pairs with scripts/pd_wire_smoke_01.py.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "apps" / "sgenaxis-desktop"
TAURI = DESKTOP / "src-tauri"
MANIFEST = TAURI / "Cargo.toml"
DISPATCH = TAURI / "src" / "dispatch.rs"
LIB_RS = TAURI / "src" / "lib.rs"
COMMANDS = TAURI / "src" / "commands.rs"
UI_JS = DESKTOP / "ui" / "app.js"
SCRIPT = ROOT / "scripts" / "pd_wire_smoke_01.py"
REPORT = ROOT / "reports" / "dispatch-pd" / "PD-WIRE-SMOKE-01.md"

FILTER = "pd_wire_smoke_01_bind_fixture_dispatch_host_observable"


def _cargo_bin() -> str:
    home = Path.home() / ".cargo" / "bin" / ("cargo.exe" if os.name == "nt" else "cargo")
    if home.is_file():
        return str(home)
    return "cargo"


def _path_with_cargo() -> dict:
    env = os.environ.copy()
    cargo_home = Path.home() / ".cargo" / "bin"
    env["Path"] = str(cargo_home) + os.pathsep + env.get("Path", "")
    return env


def test_deliverables_present():
    assert SCRIPT.is_file(), f"missing re-runnable script: {SCRIPT}"
    assert DISPATCH.is_file()
    assert UI_JS.is_file()
    assert MANIFEST.is_file()
    text = DISPATCH.read_text(encoding="utf-8")
    assert "PD-WIRE-SMOKE-01" in text
    assert "BDD-PD-WIRE-SMOKE-01" in text or "pd_wire_smoke_01" in text
    assert FILTER in text
    # Must go through DispatchHost — not raw adapter smoke.
    assert "DispatchHost::new" in text or "DispatchHost::new()" in text
    assert "start_run" in text
    assert "NOT a full-feature" in text or "NOT a full" in text


def test_ui_invoke_command_path_wiring():
    """UI must invoke start_run／load_local_board／git_* (command path), not adapters."""
    js = UI_JS.read_text(encoding="utf-8")
    assert 'invoke("start_run"' in js or "invoke(\"start_run\"" in js
    assert 'invoke("load_local_board"' in js
    assert 'invoke("git_workbench_summary"' in js
    assert 'invoke("git_workbench_diff"' in js
    # Browser／no-IPC must surface need for Tauri — not silent fake PASS.
    assert "tauri" in js.lower() or "無 IPC" in js
    for banned in ("msiexec", "child_process.spawn", "FakeGit", "AgentRouter"):
        assert banned not in js, f"UI must not embed {banned}"


def test_tauri_handlers_register_wire_commands():
    """generate_handler／commands must register the invoke targets → DispatchHost／HOST."""
    lib = LIB_RS.read_text(encoding="utf-8")
    cmds = COMMANDS.read_text(encoding="utf-8")
    for name in (
        "start_run",
        "load_local_board",
        "git_workbench_summary",
        "git_workbench_diff",
        "poll_chunks",
    ):
        assert f"commands::{name}" in lib or f"pub fn {name}" in cmds, name
    assert "DispatchHost" in cmds or "host.start_run" in cmds
    assert "host.start_run" in cmds


def test_dispatch_host_wire_smoke_cargo_or_not_run():
    """Run DispatchHost command-path smoke; missing cargo → NOT RUN (not FAIL)."""
    cargo = _cargo_bin()
    if shutil.which(cargo) is None and not Path(cargo).is_file():
        pytest.skip(
            "NOT RUN: cargo／rustc missing — cannot execute DispatchHost wire smoke"
        )

    # src-tauri is a standalone package ([workspace] in its Cargo.toml).
    cmd = [
        cargo,
        "test",
        "--lib",
        FILTER,
        "--",
        "--nocapture",
    ]
    print("PD-WIRE-SMOKE-01 cargo:", " ".join(cmd), "(cwd=%s)" % TAURI)
    proc = subprocess.run(
        cmd,
        cwd=str(TAURI),
        env=_path_with_cargo(),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    print(out[-6000:])
    if proc.returncode != 0:
        pytest.fail(
            f"PD-WIRE-SMOKE-01 FAIL: cargo test exit {proc.returncode}\n{out[-4000:]}"
        )
    assert FILTER in out or "PD-WIRE-SMOKE-01 PASS" in out
    assert "full-feature Live" in out or "NOT a full" in out


def test_no_tauri_means_not_run_not_fake_pass():
    """No Tauri CLI／WebView → NOT RUN for IPC E2E; must not claim full GA PASS."""
    has_tauri = bool(
        shutil.which("tauri")
        or shutil.which("cargo-tauri")
        or (Path.home() / ".cargo" / "bin" / "cargo-tauri.exe").is_file()
        or (Path.home() / ".cargo" / "bin" / "tauri.exe").is_file()
    )
    script = SCRIPT.read_text(encoding="utf-8")
    assert "NOT RUN" in script or "not full-feature" in script.lower()
    assert "pytest" in script
    if not has_tauri:
        # Honest skip marker for live IPC — contract tests above still run.
        pytest.skip(
            "NOT RUN: no Tauri CLI／WebView — IPC E2E (git_workbench_*／load_local_board "
            "live invoke) not executed; DispatchHost command-path cargo path remains "
            "the mandatory observable. Not a full-feature PASS."
        )


def test_script_documents_fail_and_honesty():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "def main" in text
    assert "return 1" in text or "sys.exit" in text
    assert "DispatchHost" in text or "command-path" in text.lower()
    assert "full-feature" in text.lower() or "Live PASS" in text


@pytest.mark.skipif(not REPORT.is_file(), reason="report written after implementer PASS")
def test_report_exists_when_present():
    text = REPORT.read_text(encoding="utf-8")
    assert "PD-WIRE-SMOKE-01" in text
    assert "READY_FOR_GREEN" in text
    assert "yellow" in text.lower()
    assert "green" in text.lower()  # must mention never-green policy
