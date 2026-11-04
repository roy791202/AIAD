"""TDD — Designer Shell IA: system Inspector + float-window Widget Box + Viewer canvas-only."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"


def _panel_uidesign_chunk(html: str) -> str:
    m = re.search(
        r'<section[^>]*id="panel-uidesign"[^>]*>.*?</section>',
        html,
        re.DOTALL,
    )
    assert m, "panel-uidesign missing"
    return m.group(0)


def test_widget_box_inside_uidesign_float_window():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="uidesign-window"' in html
    assert 'id="sec-uidesign-widgets"' in html
    win_i = html.index('id="uidesign-window"')
    widgets_i = html.index('id="sec-uidesign-widgets"')
    assert widgets_i > win_i
    assert "uidesign-cat" in html
    assert "文件" in html and "輸入" in html and "顯示" in html
    assert 'data-palette="Button"' in html
    assert 'data-uidesign-mode="designer"' in html
    assert 'id="sec-uidesign"' not in html
    css = CSS.read_text(encoding="utf-8")
    assert ".uidesign-window" in css
    assert ".uidesign-cat" in css
    js = JS.read_text(encoding="utf-8")
    assert "openUiDesignWindow" in js
    assert "closeUiDesignWindow" in js
    assert "tryOpenUiDesignOsWindow" in js
    assert "standalone" in js and "uidesign" in js
    assert "WebviewWindow" in js
    assert "is-uidesign-standalone" in js or "isUiDesignStandalone" in js
    cap = (
        ROOT
        / "apps"
        / "sgenaxis-desktop"
        / "src-tauri"
        / "capabilities"
        / "default.json"
    ).read_text(encoding="utf-8")
    assert "core:webview:allow-create-webview-window" in cap
    assert (
        ROOT
        / "apps"
        / "sgenaxis-desktop"
        / "src-tauri"
        / "capabilities"
        / "uidesign-window.json"
    ).is_file()
    css = CSS.read_text(encoding="utf-8")
    assert "is-uidesign-standalone" in css


def test_inspector_design_holds_props_behavior_testing():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="inspector"' in html
    assert 'id="inspector-design"' in html
    assert 'id="desName"' in html
    assert 'id="desBehavior"' in html
    assert 'id="desBdd"' in html
    assert 'id="desTdd"' in html
    assert 'data-design-tab="props"' in html
    assert 'data-design-tab="behavior"' in html
    assert 'data-design-tab="testing"' in html
    panel = _panel_uidesign_chunk(html)
    assert "designer-props" not in panel
    assert 'id="desName"' not in panel
    assert "aside.designer-props" not in panel
    assert "designer-palette" not in panel
    js = JS.read_text(encoding="utf-8")
    assert "setDesignInspectorActive" in js
    assert "inspector-design" in js
    assert "syncDesignSelectionToInspector" in js


def test_viewer_hides_widgets_and_inspector_canvas_preview():
    js = JS.read_text(encoding="utf-8")
    assert "setUidesignMode" in js
    assert "panel-uidesign-viewer" in js
    assert "is-preview" in js
    assert "setUidesignWidgetsVisible" in js
    assert "inspectorDisplayBeforeViewer" in js
    assert 'mode === "viewer"' in js or '=== "viewer"' in js
    css = CSS.read_text(encoding="utf-8")
    assert ".panel-uidesign-viewer" in css
    assert "is-preview" in css
    html = HTML.read_text(encoding="utf-8")
    assert "designer-shell--stage" in html
    assert 'data-uidesign-mode="viewer"' in html
    assert "設計包對照" not in html
    assert 'id="uidesign-disclaimer"' not in html
