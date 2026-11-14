"""TDD-PD-REMAIN-PORTS-UI-01 — Ports shell UI removed; host ports_status retained.

Shell no longer exposes Ports 檢視／More menu. Host Command ports_status
projection remains for adapters／IPC. No WebView driver.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"
HOST_PORTS = (
    ROOT
    / "apps"
    / "sgenaxis-desktop"
    / "crates"
    / "sgenaxis-host"
    / "src"
    / "ports_view.rs"
)
IPC = (
    ROOT
    / "apps"
    / "sgenaxis-desktop"
    / "crates"
    / "sgenaxis-host"
    / "src"
    / "ipc.rs"
)
COMMANDS = (
    ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "src" / "commands.rs"
)


def test_ports_ui_assets_exist():
    for path in (HTML, JS, CSS, HOST_PORTS, IPC, COMMANDS):
        assert path.is_file(), f"missing: {path}"


def test_panel_ports_removed_from_shell():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert 'id="panel-ports"' not in html
    assert 'id="nav-ports"' not in html
    assert 'id="side-more-toggle"' not in html
    assert 'id="side-more-menu"' not in html
    assert 'data-cmd="nav.ports"' not in html
    assert 'data-cmd="ports.refresh"' not in html
    assert "cmdPortsRefresh" not in js
    assert ".ports-toolbar" not in css


def test_host_ports_projection_and_allowlist():
    ports_rs = HOST_PORTS.read_text(encoding="utf-8")
    assert "project_ports_status" in ports_rs
    assert "PortsStatusView" in ports_rs
    assert "no ports registered" in ports_rs or "empty" in ports_rs
    ipc = IPC.read_text(encoding="utf-8")
    assert "PortsStatus" in ipc
    assert '"ports_status"' in ipc or "ports_status" in ipc
    assert "list_os_devices" in ipc  # forbidden assertion in tests
    cmds = COMMANDS.read_text(encoding="utf-8")
    assert "pub fn ports_status" in cmds
    assert "PortsStatusDto" in cmds
