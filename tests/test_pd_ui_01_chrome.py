"""TDD-PD-UI-01 — chrome structure vs BDD-PD-UI-01 (test infra only).

Asserts desktop shell assets expose menubar / sidebar / main / empty-state
hooks and JS panel navigation wiring aligned with the workbench main path.
Does not drive WebView clicks; pairs with release-exe smoke in the review.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"
EXE = (
    ROOT
    / "apps"
    / "sgenaxis-desktop"
    / "src-tauri"
    / "target"
    / "release"
    / "sgenaxis-desktop.exe"
)
TAURI_CONF = ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "tauri.conf.json"


def test_ui_assets_exist():
    for path in (HTML, JS, CSS, TAURI_CONF):
        assert path.is_file(), f"missing UI deliverable: {path}"


def test_menubar_sidebar_main_empty_chrome():
    html = HTML.read_text(encoding="utf-8")
    assert 'role="menubar"' in html
    assert 'class="sidebar"' in html or "class='sidebar'" in html
    assert 'id="app"' in html
    assert "board-empty" in html or "empty-state" in html or "empty" in html
    assert "inspector" in html
    assert "toast" in html.lower() or 'id="toast-root"' in html
    # main-path panels shared with workbench interactive prototype
    for panel in ("board", "git", "agent", "arch", "settings"):
        assert f'data-panel="{panel}"' in html, f"missing panel hook: {panel}"


def test_js_wires_panel_navigation_and_toast():
    js = JS.read_text(encoding="utf-8")
    assert "PANEL_TITLES" in js or "data-panel" in js
    assert "function toast" in js
    assert "nav-item" in js or "data-panel" in js
    # clickable wiring: listeners on menu/nav actions
    assert "addEventListener" in js
    assert "menu-action" in js or "data-cmd" in js


def test_tauri_frontend_dist_points_at_ui():
    conf = TAURI_CONF.read_text(encoding="utf-8")
    assert "../ui" in conf or '"frontendDist"' in conf


def test_release_exe_artifact_present_for_desktop_opens_ac():
    # Build smoke evidence (process start is reviewed separately); file must exist
    # when READY_FOR_GREEN claims tauri build succeeded.
    assert EXE.is_file(), f"missing release exe for desktop-opens AC: {EXE}"
    assert EXE.stat().st_size > 100_000
