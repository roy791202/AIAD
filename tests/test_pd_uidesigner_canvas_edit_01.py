"""TDD — Designer canvas: drag place, align guides, grid + rulers."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"


def test_rulers_and_grid_markup():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="designBoard"' in html
    assert 'id="designRulerH"' in html
    assert 'id="designRulerV"' in html
    assert "designer-ruler-corner" in html
    assert 'id="designGrid"' in html or "form-grid" in html
    assert 'id="designGuides"' in html
    css = CSS.read_text(encoding="utf-8")
    assert ".designer-ruler" in css
    assert ".form-grid" in css or "--grid-size" in css
    assert ".design-guide" in css


def test_drag_and_align_guide_logic():
    js = JS.read_text(encoding="utf-8")
    assert "beginDesignDrag" in js
    assert "onDesignPointerMove" in js
    assert "collectDesignAlignGuides" in js
    assert "snapNodeToGuides" in js
    assert "showDesignGuides" in js
    assert "renderDesignRulers" in js
    assert "getDesignGridPx" in js or "DESIGN_GRID_DEFAULT" in js
    assert "setDesignGridPx" in js
    assert "pointerdown" in js
    assert 'uidesignChromeMode !== "designer"' in js


def test_pull_reference_guides_from_rulers():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert 'id="designUserGuides"' in html
    assert "wireDesignGuidePull" in js
    assert "beginGuideDragFromRuler" in js
    assert "renderUserGuides" in js
    assert "meta.guides" in js or 'guides: { v: [], h: [] }' in js
    assert ".design-user-guide" in css
    assert "designRulerH" in js and "designRulerV" in js


def test_grid_size_control_adjustable():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="desGridSize"' in html
    assert 'value="8"' in html
    assert 'value="16"' in html
    assert 'value="0"' in html
    js = JS.read_text(encoding="utf-8")
    assert "desGridSize" in js
    assert "meta.gridSize" in js
    assert "is-grid-off" in js
    assert "ensureDesignWorldExtent" in js
    assert "DESIGN_WORLD_PAD" in js or "is-infinite-grid" in js
    css = CSS.read_text(encoding="utf-8")
    assert ".form-frame.is-grid-off" in css
    assert ".uidesign-grid-label" in css
    assert ".designer-artboard" in css


def test_design_grid_infinite_extend():
    js = JS.read_text(encoding="utf-8")
    assert "ensureDesignWorldExtent" in js
    assert "is-infinite-grid" in js
    css = CSS.read_text(encoding="utf-8")
    assert "designer-artboard.is-grid-off" in css or ".designer-artboard.is-grid-off" in css


def test_form_size_presets_adjustable():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="desFormSize"' in html
    assert 'value="800x800"' in html
    assert 'value="1920x1080"' in html
    assert 'value="1280x720"' in html
    assert 'value="custom"' in html
    js = JS.read_text(encoding="utf-8")
    assert "setDesignFormSize" in js
    assert "syncDesFormSizeSelect" in js
    assert "DESIGN_FORM_SIZE_PRESETS" in js
    assert "meta.formSize" in js
    assert "desFormSize" in js


def test_css_drag_cursor_and_preview_blocks_grab():
    css = CSS.read_text(encoding="utf-8")
    assert "cursor: grab" in css
    assert "is-design-dragging" in css
    assert ".designer-canvas.is-preview .design-node" in css


def test_middle_button_nav_wired_for_designer():
    js = JS.read_text(encoding="utf-8")
    assert "wireCanvasMiddleNav" in js
    assert "designCanvas" in js
    assert "setDesignZoom" in js
    assert "button !== 1" in js or "button === 1" in js
    assert "推進" in js or "zoomBy" in js
