"""TDD-PD-SHELL-UIDESIGN-VIEW-01 — UI design tool view vs BDD-PD-SHELL-UIDESIGN-VIEW-01.

UI Layer Edit／視窗→UI 編輯開啟獨立 UI 設計工具視窗；內嵌或受控開啟 docs/ui-design/index.html；
標示設計稿非產品證據；無則空態＋路徑；禁當正式驗收 PASS。
Does not regenerate screens/*.png. Panel id is `uidesign` (not `ui-design`).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"
DESIGN_INDEX = ROOT / "docs" / "ui-design" / "index.html"
LIB = ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "src" / "lib.rs"
CMDS = ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "src" / "commands.rs"


def test_assets_exist():
    for path in (HTML, JS, CSS, DESIGN_INDEX, LIB, CMDS):
        assert path.is_file(), f"missing: {path}"


def test_panel_uidesign_structure_and_disclaimer():
    html = HTML.read_text(encoding="utf-8")
    assert html.count('id="panel-uidesign"') == 1
    assert 'data-panel="uidesign"' in html
    # 標題／免責／設計包對照 chrome 已清除；主區保留 Designer 畫布
    assert 'id="uidesign-disclaimer"' not in html
    assert "設計包對照" not in html
    assert 'id="uidesign-designer"' in html or "designer-shell" in html
    assert 'id="designCanvas"' in html
    js = JS.read_text(encoding="utf-8")
    assert "uidesign_package_status" in js
    # Must not use legacy id that older NAV tests forbid as "full tool"
    assert 'data-panel="ui-design"' not in html


def test_ui_design_opens_via_window_menu_not_sidebar():
    html = HTML.read_text(encoding="utf-8")
    start = html.find('<nav class="sidebar"')
    end = html.find("</nav>", start)
    assert start != -1 and end != -1
    side = html[start:end]
    assert 'id="sec-uidesign"' not in side
    assert 'id="btn-uidesign-toggle"' not in side
    assert 'data-cmd="nav.uidesign"' not in html
    assert 'data-cmd="win.uiEditor"' in html
    assert "UI 編輯" in html
    assert 'id="uidesign-window"' in html
    assert 'id="sec-uidesign-widgets"' in html


def test_js_wires_command_path_and_not_formal_pass():
    js = JS.read_text(encoding="utf-8")
    assert "openUiDesignWindow" in js
    assert 'invoke("uidesign_package_status")' in js or 'invoke("uidesign_package_status"' in js
    assert 'invoke("uidesign_open_package")' in js or 'invoke("uidesign_open_package"' in js
    assert "cmdUidesignRefresh" in js
    assert "cmdUidesignOpen" in js
    assert "cmdUidesignEmbed" in js or "showUidesignEmbed" in js
    assert "showUidesignEmpty" in js
    assert 'cmd === "uidesign.refresh"' in js or "uidesign.refresh" in js
    assert 'cmd === "win.uiEditor"' in js
    assert "product_evidence" in js
    assert "formal_acceptance_pass" in js
    assert "非產品證據" in js or "非驗收 PASS" in js or "正式驗收 PASS" in js
    for banned in ("child_process", "require(", "Deno.run"):
        assert banned not in js, f"UI must not use {banned}"


def test_css_uidesign_panel():
    css = CSS.read_text(encoding="utf-8")
    assert ".uidesign-toolbar" in css
    assert ".uidesign-status-line" in css
    assert ".uidesign-window" in css
    assert ".designer-shell" in css or ".designer-canvas" in css


def test_host_registers_controlled_uidesign_commands():
    lib = LIB.read_text(encoding="utf-8")
    assert "commands::uidesign_package_status" in lib
    assert "commands::uidesign_open_package" in lib
    cmds = CMDS.read_text(encoding="utf-8")
    assert "pub fn uidesign_package_status" in cmds
    assert "pub fn uidesign_open_package" in cmds
    assert "product_evidence: false" in cmds
    assert "formal_acceptance_pass: false" in cmds
    assert "docs/ui-design/index.html" in cmds
    assert "UIDESIGN_INDEX_REL" in cmds or "ui-design" in cmds


def test_design_package_on_disk_readable_not_regenerated_here():
    """Card allows read of docs/ui-design; does not regenerate 14 PNGs."""
    assert DESIGN_INDEX.is_file()
    text = DESIGN_INDEX.read_text(encoding="utf-8", errors="replace")
    assert len(text) > 100
    screens = ROOT / "docs" / "ui-design" / "screens"
    if screens.is_dir():
        pngs = list(screens.glob("UI-*.png"))
        assert len(pngs) >= 1  # pre-existing; this card must not delete them
