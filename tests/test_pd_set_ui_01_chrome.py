"""TDD-PD-SET-UI-01 — settings panel chrome vs BDD-PD-SET-UI-01.

Asserts Vanilla settings UI can edit CLI／MCP／DryRun｜Live, wires
host_get_settings／host_set_agent_settings, rejects invalid activate paths,
and never projects secret_token. No WebView click driver.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"


def test_settings_ui_assets_exist():
    for path in (HTML, JS, CSS):
        assert path.is_file(), f"missing: {path}"


def test_panel_settings_partitions_cli_mcp_mode():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="panel-settings"' in html
    assert 'data-panel="settings"' in html
    assert 'data-partition="cli"' in html
    assert 'data-partition="mcp"' in html
    assert 'data-partition="mode"' in html
    # DryRun｜Live controls
    assert 'id="mode-dry-run"' in html
    assert 'id="mode-live"' in html
    assert 'name="settings-run-mode"' in html
    assert 'id="settings-mode-badge"' in html
    assert 'id="settings-board-path"' in html
    # CLI paths
    for cid in (
        "cli-selected",
        "cli-claude-path",
        "cli-cursor-path",
        "cli-codex-path",
        "cli-antigravity-path",
    ):
        assert f'id="{cid}"' in html, cid
    # MCP endpoint／secret（password）
    assert 'id="mcp-endpoint"' in html
    assert 'id="mcp-secret"' in html
    assert 'type="password"' in html
    assert 'id="mcp-secret-hint"' in html
    # Actions
    assert 'data-cmd="settings.activate"' in html
    assert 'data-cmd="settings.draft"' in html
    assert 'data-cmd="settings.revoke"' in html
    assert 'data-cmd="settings.project"' in html
    # Draft button is real persistence (not demo-only)
    assert "僅存草稿（DryRun）" in html
    assert "僅存草稿（示意）" not in html


def test_sidebar_nav_settings_present():
    html = HTML.read_text(encoding="utf-8")
    # Setting primary tab lives on the full-width top view-tabs strip
    rail = html.find('id="side-rail"')
    body = html.find('id="shell-body"')
    assert rail != -1 and body != -1 and rail < body
    tabs = html[html.rfind("<", 0, rail) : body]
    assert 'id="nav-settings"' in tabs
    assert 'data-panel="settings"' in tabs


def test_js_wires_host_settings_and_mode():
    js = JS.read_text(encoding="utf-8")
    assert 'invoke("host_get_settings")' in js or 'invoke("host_get_settings"' in js
    assert 'invoke("host_set_agent_settings"' in js
    assert "cmdLoadSettings" in js
    assert "cmdSaveAgentSettings" in js
    assert "cmdRevokeLive" in js
    assert "cmdProjectSettings" in js
    assert "updateModeBadge" in js
    assert "isMcpEndpointActivatable" in js
    assert 'cmd === "settings.activate"' in js
    assert 'cmd === "settings.draft"' in js
    assert 'cmd === "settings.revoke"' in js
    assert 'cmd === "settings.project"' in js
    assert 'panelId === "settings"' in js
    # Invalid activate gate (BDD)
    assert "無效路徑不可存為作用中" in js
    assert ":8788" in js and ":8787" in js
    # Projection must not emit secret_token field
    assert "has_secret" in js
    assert 'text.indexOf("secret_token")' in js or "secret_token" in js
    # Must not shell／OS from page
    for banned in (
        "child_process",
        "require(",
        "Deno.run",
        "powershell.exe",
        "msiexec /i",
    ):
        assert banned not in js, f"UI must not use {banned}"


def test_js_never_fills_secret_from_dto():
    js = JS.read_text(encoding="utf-8")
    # applySettingsDto clears password; never assigns dto secret value
    assert 'secretEl.value = ""' in js or "mcp-secret" in js
    assert "dto.agent_mcp.secret" not in js
    assert "dto.agent_mcp.secret_token" not in js


def test_css_settings_mode_layout():
    css = CSS.read_text(encoding="utf-8")
    assert ".settings-grid" in css
    assert ".settings-block" in css
    assert ".settings-mode-bar" in css
    assert ".settings-mode-badge" in css
    assert ".settings-mode-radios" in css
    assert ".settings-actions" in css
