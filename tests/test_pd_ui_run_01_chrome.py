"""Chrome／wiring — PD-UI-RUN-01 vs BDD-PD-UI-RUN-01.

Asserts Run panel chrome can show chunk stream, cancel, and exit
classification (ok／cancelled／failed); wires start_run／poll_chunks／cancel_run
only (no direct CLI／MCP from the page). Pairs with dispatch unit tests.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"
DISPATCH = (
    ROOT
    / "apps"
    / "sgenaxis-desktop"
    / "src-tauri"
    / "src"
    / "dispatch.rs"
)
LIB = ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "src" / "lib.rs"


def test_run_ui_assets_exist():
    for path in (HTML, JS, CSS):
        assert path.is_file(), f"missing: {path}"


def test_panel_agent_run_structure():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="panel-agent"' in html
    assert 'data-panel="agent"' in html
    assert 'id="run-panel"' in html
    assert 'id="run-class-badge"' in html
    assert 'id="agent-log"' in html
    assert 'id="run-stream"' in html
    assert 'id="btn-cancel-run"' in html
    assert 'data-cmd="agent.cancel"' in html
    assert 'data-cmd="work.assign"' in html
    assert "poll_chunks" in html or "串流" in html
    for label in ("ok", "cancelled", "failed"):
        assert label in html, f"classification label missing in chrome: {label}"


def test_js_wires_run_commands_not_cli_mcp():
    js = JS.read_text(encoding="utf-8")
    assert 'invoke("start_run"' in js
    assert 'invoke("poll_chunks"' in js
    assert 'invoke("cancel_run"' in js
    assert "mapExitClassification" in js
    assert "appendChunksStreaming" in js or "pollRunStream" in js
    assert "setRunClassification" in js
    assert 'cmd === "work.assign"' in js
    assert 'cmd === "agent.cancel"' in js
    # UI maps host success → ok; cancelled／failed buckets present.
    assert 'return "ok"' in js
    assert 'return "cancelled"' in js
    assert 'return "failed"' in js
    for banned in (
        "child_process",
        "require(",
        "Deno.run",
        "spawnSync",
        "execSync",
        "fetch('http://127.0.0.1:8788",
        "fetch(\"http://127.0.0.1:8788",
    ):
        assert banned not in js, f"UI must not use {banned}"


def test_css_run_panel():
    css = CSS.read_text(encoding="utf-8")
    assert ".run-class-badge" in css
    assert ".run-stream" in css or ".agent-log" in css
    assert ".run-status-line" in css
    assert '[data-class="ok"]' in css or 'data-class="ok"' in css
    assert "cancelled" in css
    assert "failed" in css


def test_tauri_registers_run_commands():
    lib = LIB.read_text(encoding="utf-8")
    for name in ("start_run", "poll_chunks", "cancel_run"):
        assert f"commands::{name}" in lib, name


def test_dispatch_hosts_ui_run_tests():
    src = DISPATCH.read_text(encoding="utf-8")
    assert "cancel_run" in src
    assert "poll_chunks" in src
    assert "ui_run_cancel_before_poll_yields_cancelled" in src
    assert "ui_run_poll_streams_chunks_and_ok_exit" in src
    assert "ui_run_errors_are_readable_strings" in src
    assert "BDD-PD-UI-RUN-01" in src
