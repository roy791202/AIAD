"""VERIFY batch PRODUCT-ARCH-UI-VERIFY-20261025 — static AC for recent arch/Diagram UI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_v01_slot_drop_highlight():
    js, css = _read(JS), _read(CSS)
    assert ".arch-module-slot.is-drop-target" in css
    assert "scale(1.05)" in css or "transform: scale" in css
    assert 'classList.add("is-drop-target")' in js
    assert "arch-module-slot" in js


def test_v02_top_tabs_icon_and_label():
    html = _read(HTML)
    assert 'id="side-rail"' in html
    for label in ("Diagram", "Tasks", "Git", "Setting"):
        assert f'<span class="side-tab-label">{label}</span>' in html
    assert "side-tab-icon" in html
    assert 'src="icons/nav/diagram.svg"' in html


def test_v03_shift_twist_recursive():
    js = _read(JS)
    assert "function setArchTreeOpenState" in js
    assert "setArchTreeOpenState(key, !open, !!ev.shiftKey)" in js
    assert "Shift+左鍵" in js or "含所有子層" in js
    assert 'openKey === "root"' in js


def test_v04_packs_clear_and_edge_delete():
    html, js = _read(HTML), _read(JS)
    assert 'id="arch-clear-layer-packs"' in html
    assert 'id="archNodePacksKind"' in html
    assert "disabled" in html[html.find("archNodePacksKind") : html.find("archNodePacksKind") + 200]
    assert "function clearArchLayerPacks" in js
    assert "function deleteArchSelectedEdge" in js
    assert "packsKind 只由子物件推導" in js or "由子物件推導" in js


def test_v05_shared_panel_toolbar_with_delete():
    html = _read(HTML)
    start = html.find('id="panel-arch"')
    end = html.find("</section>", start)
    arch = html[start:end]
    assert 'id="arch-panel-chrome"' in arch
    assert "arch-panel-toolbar" in arch
    assert 'id="arch-delete-node"' in arch
    assert 'id="arch-refresh"' not in arch
    assert 'id="arch-edit"' not in arch
    assert 'id="arch-add-node"' not in arch
    assert 'id="arch-node-strip"' in arch


def test_v06_canvas_only_zoom_arrange_grid():
    html = _read(HTML)
    chrome_start = html.find('id="arch-panel-chrome"')
    chrome_end = html.find('id="arch-panel-body"')
    chrome = html[chrome_start:chrome_end]
    assert 'id="arch-zoom-in"' not in chrome
    assert 'id="archGridSize"' not in chrome
    workspace = html[html.find('id="arch-workspace"') : html.find('id="arch-canvas-shell"') + 80]
    assert 'id="arch-zoom-in"' in workspace
    assert 'id="arch-arrange-auto"' in workspace
    assert 'id="archGridSize"' in workspace
    assert 'class="arch-canvas-toolbar"' in workspace


def test_v07_independent_canvas_keyword():
    html, js = _read(HTML), _read(JS)
    assert 'id="arch-tree-filter-q"' in html
    assert 'id="arch-canvas-filter-q"' in html
    assert "let archCanvasKeyword" in js
    assert "let archTreeKeyword" in js


def test_v08_icon_btn_compact_tokens():
    css = _read(CSS)
    assert "--icon-btn-h: 22px" in css
    assert "--icon-btn-icon: 12px" in css
    assert "height: var(--icon-btn-h)" in css
    # .nav-item 大 padding 不得蓋掉頂部分頁
    assert ".side-tab.nav-item.nav-main" in css or ".toolbar .side-tab.nav-item" in css
    assert "max-height: var(--icon-btn-h)" in css


def test_arch_tree_pane_resizable():
    html, js, css = _read(HTML), _read(JS), _read(CSS)
    assert 'id="split-arch-tree"' in html
    assert "--arch-tree-w" in css
    assert "function wireArchTreeSplitter" in js
    assert 'getElementById("split-arch-tree")' in js
    assert "var(--arch-tree-w" in css


def test_v09_diagram_no_left_drawer():
    html, js, css = _read(HTML), _read(JS), _read(CSS)
    assert "side-panel-diagram" not in html
    assert 'aria-controls="panel-arch"' in html
    # diagram／git／settings 皆 drawerless（可跨行）
    assert 'sideKey === "diagram"' in js
    assert "drawerless" in js
    assert "is-sidebar-collapsed" in js
    assert ".body.is-sidebar-collapsed" in css
    assert 'id="panel-arch"' in html
    assert 'id="arch-unassigned"' in html
    # 收合側欄不可 display:none（會讓 #main 掉進 0 寬 grid 欄，只剩 Inspector）
    rule_at = css.find(".body.is-sidebar-collapsed #sidebar")
    assert rule_at != -1
    rule = css[rule_at : rule_at + 280]
    assert "visibility: hidden" in rule
    assert "display: none" not in rule
