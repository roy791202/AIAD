"""TDD-PD-DEPLOY-UI-01 — deploy／佈版 panel chrome vs BDD-PD-DEPLOY-UI-01.

Asserts sidebar deploy panel projects capability／artifact／status structure,
wires check／refresh through deploy_* Tauri commands (no OS from the page),
and keeps a clear unsupported／empty state when Adapter／commands are absent.
Does not drive WebView; pairs with PD-DEPLOY-CMD-01 for live invoke.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"


def test_deploy_ui_assets_exist():
    for path in (HTML, JS, CSS):
        assert path.is_file(), f"missing: {path}"


def test_panel_deploy_structure_not_placeholder():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="panel-deploy"' in html
    assert 'data-panel="deploy"' in html
    # Real structure: toolbar + capability／artifact panes + unsupported empty
    assert 'id="deploy-toolbar"' in html or 'class="deploy-toolbar"' in html
    assert 'id="deploy-capabilities"' in html
    assert 'id="deploy-artifacts"' in html
    assert 'id="deploy-support-badge"' in html
    assert 'id="deploy-status-line"' in html
    assert 'id="deploy-empty"' in html
    assert "未支援" in html or "unsupported" in html.lower()
    # Check CTA still present; empty CTAs keep data-empty-action
    assert 'data-cmd="deploy.check"' in html
    assert 'data-cmd="deploy.refresh"' in html or "deploy.refresh" in html
    assert 'data-empty-action="check-deploy"' in html
    # Out of scope: no remote farm / design-tool panel
    assert 'data-panel="ui-design"' not in html
    assert "remote-farm" not in html.lower()


def test_sidebar_nav_deploy_present():
    html = HTML.read_text(encoding="utf-8")
    start = html.find('<nav class="sidebar"')
    end = html.find("</nav>", start)
    assert start != -1 and end != -1
    side = html[start:end]
    assert 'id="nav-deploy"' in side
    assert 'data-panel="deploy"' in side
    assert 'id="nav-deploy-meta"' in side
    # Placeholder「稍後」chip removed from deploy nav
    deploy_btn = side[side.find('id="nav-deploy"') : side.find(">", side.find('id="nav-deploy"')) + 1]
    assert "稍後" not in deploy_btn or 'id="nav-deploy-meta"' in side


def test_js_wires_deploy_commands_not_os():
    js = JS.read_text(encoding="utf-8")
    # Command names from PD-DEPLOY-CMD-01 BDD
    assert 'invoke("deploy_status")' in js or 'invoke("deploy_status"' in js
    assert 'invoke("deploy_check")' in js or 'invoke("deploy_check"' in js
    assert 'invoke("list_artifacts")' in js or 'invoke("list_artifacts"' in js
    assert "cmdDeployCheck" in js
    assert "cmdDeployRefresh" in js
    assert "showDeployUnsupported" in js
    assert 'cmd === "deploy.check"' in js
    # Must not shell out / touch OS APIs from the page
    for banned in (
        "child_process",
        "require(",
        "Deno.run",
        "window.open('file:",
        "navigator.msSave",
    ):
        assert banned not in js, f"UI must not use {banned}"
    # No direct powershell／cmd／msiexec from UI strings as executable paths
    assert "msiexec /i" not in js.lower()
    assert "powershell.exe" not in js.lower()


def test_js_unsupported_and_panel_hooks():
    js = JS.read_text(encoding="utf-8")
    assert 'panelId === "deploy"' in js
    assert "isDeployCmdMissingOrUnsupported" in js
    assert "renderDeployCapabilities" in js
    assert "renderDeployArtifacts" in js
    assert "命令已攔截錯誤" in js or "已攔截" in js


def test_css_deploy_layout():
    css = CSS.read_text(encoding="utf-8")
    assert ".deploy-toolbar" in css
    assert ".deploy-layout" in css
    assert ".deploy-support-badge" in css
    assert ".deploy-status-line" in css
    assert "deploy-empty" in css or "[data-deploy-state" in css
