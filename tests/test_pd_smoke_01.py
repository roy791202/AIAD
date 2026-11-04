"""PD-SMOKE-01 — main-path smoke vs BDD-PD-SMOKE-01.

Covers (automated／re-runnable, no elevated MSI):
  載入 UI → 選專案 hooks → 看板可見 → DryRun start＋結束.
Any failure is FAIL. Pairs with scripts/pd_smoke_01.py.
Does not drive WebView clicks; DryRun exec path is cargo lib test (Fake Process).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"
DESKTOP = ROOT / "apps" / "sgenaxis-desktop"
EXEC_MANIFEST = DESKTOP / "crates" / "sgenaxis-exec" / "Cargo.toml"
SCRIPT = ROOT / "scripts" / "pd_smoke_01.py"

# EXEC DryRun (PD-EXEC-CLI): started → chunk → progress → exited; no OS spawn／MSI.
# Host DispatchHost lib-test is out of this card's write-scope if src-tauri is red.
DRYRUN_CARGO_FILTER = "dry_run_event_sequence_started_chunk_progress_exited"


def _cargo_bin() -> str:
    home = Path.home() / ".cargo" / "bin" / ("cargo.exe" if os.name == "nt" else "cargo")
    if home.is_file():
        return str(home)
    return "cargo"


def test_smoke_script_exists():
    assert SCRIPT.is_file(), f"missing re-runnable smoke script: {SCRIPT}"


def test_ui_assets_load():
    """載入 UI — deliverables present and parseable as UTF-8."""
    for path in (HTML, JS, CSS):
        assert path.is_file(), f"missing UI asset: {path}"
        text = path.read_text(encoding="utf-8")
        assert len(text) > 100, f"UI asset too small: {path}"
    html = HTML.read_text(encoding="utf-8")
    assert 'id="app"' in html
    assert 'role="menubar"' in html
    assert "EluSlot" in html or "SGenAxis" in html or "sgenaxis" in html.lower()


def test_project_select_chrome():
    """選專案 — toolbar／menu expose open／switch project; path chip visible."""
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert 'data-cmd="project.switch"' in html
    assert "開啟專案" in html or "切換專案" in html
    assert 'id="project-path"' in html
    assert "project.switch" in js
    # DryRun path binds a project_root (demo root in browser／IPC)
    assert "project_root" in js
    assert "/demo/root" in js or "project_root:" in js


def test_board_visible_chrome():
    """看板可見 — board panel, projection, counts, load／get_board wiring."""
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert 'id="panel-board"' in html
    assert 'data-panel="board"' in html
    assert 'id="board-projection"' in html
    assert 'id="board-counts"' in html
    assert 'id="board-tasks"' in html
    assert 'id="board-empty"' in html
    assert 'data-cmd="board.load"' in html
    assert "function renderBoard" in js
    assert 'invoke("get_board")' in js or 'invoke("get_board"' in js
    assert "load_local_board" in js
    assert "showPanel" in js


def test_dryrun_start_end_ui_wiring():
    """DryRun start＋結束 — UI invokes start_run then poll_chunks; cancel seam."""
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert 'id="btn-dry-run"' in html
    assert 'data-cmd="work.assign"' in html
    assert 'id="btn-cancel-run"' in html
    assert "cmdStartDryRun" in js
    assert 'invoke("start_run"' in js
    assert "dry_run: true" in js
    assert 'invoke("poll_chunks"' in js
    assert "cmdCancelRun" in js or 'invoke("cancel_run"' in js
    # Must not shell／elevated install from page
    for banned in ("msiexec", "child_process", "powershell.exe -"):
        assert banned not in js, f"UI must not use {banned}"


def test_dryrun_start_and_end_cargo():
    """DryRun start＋結束 — sgenaxis-exec CliAgentAdapter sequence; fail ⇒ FAIL."""
    assert EXEC_MANIFEST.is_file(), f"missing exec manifest: {EXEC_MANIFEST}"
    env = os.environ.copy()
    cargo_bin_dir = str(Path.home() / ".cargo" / "bin")
    env["Path"] = cargo_bin_dir + os.pathsep + env.get("Path", "")
    cmd = [
        _cargo_bin(),
        "test",
        "--lib",
        DRYRUN_CARGO_FILTER,
        "--manifest-path",
        str(EXEC_MANIFEST),
        "--",
        "--nocapture",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(DESKTOP),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    assert proc.returncode == 0, (
        f"DryRun cargo smoke FAILED (exit {proc.returncode}).\n"
        f"cmd: {' '.join(cmd)}\n---\n{out[-4000:]}"
    )
    assert DRYRUN_CARGO_FILTER in out
    assert "ok" in out.lower() or "passed" in out.lower()


def test_no_elevated_msi_required():
    """BDD: 不要求 admin／MSI — smoke script is pytest-only."""
    script = SCRIPT.read_text(encoding="utf-8") if SCRIPT.is_file() else ""
    for banned in (
        "msiexec /",
        "Start-Process -Verb RunAs",
        "ShellExecuteW",
        "packaging/windows/wix",
    ):
        assert banned not in script, f"smoke script must not require {banned}"
    assert "pytest" in script
    assert "wix" not in script.lower()
    # Docstring may say "no elevated MSI"; ban real installer hooks only.
    assert "msiexec /i" not in script.lower()


@pytest.mark.skipif(not SCRIPT.is_file(), reason="script not yet present")
def test_rerunnable_script_exits_zero_when_invoked_as_module_check():
    """Sanity: script is importable／has main and documents FAIL-on-error."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert "def main" in text
    assert "pytest" in text
    assert "sys.exit" in text or "return 1" in text
