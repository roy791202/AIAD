"""TDD — PD-UIDESIGNER-EDIT-P2 (duplicate / z-order / align / layout / snap)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "apps" / "sgenaxis-desktop" / "ui" / "index.html"
JS = ROOT / "apps" / "sgenaxis-desktop" / "ui" / "app.js"
CSS = ROOT / "apps" / "sgenaxis-desktop" / "ui" / "styles.css"
WB = ROOT / "git_workbench_interactive.html"


def test_product_p2_controls():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert 'data-cmd="uidesign.dup"' in html
    assert 'data-cmd="uidesign.raise"' in html
    assert 'data-cmd="uidesign.lower"' in html
    for kind in ("left", "hmid", "right", "top", "vmid", "bottom"):
        assert f'data-cmd="uidesign.align.{kind}"' in html
    assert 'id="desLayoutMode"' in html
    assert "duplicateSelectedDesignNode" in js
    assert "bumpDesignZ" in js
    assert "alignSelectedDesign" in js
    assert "DESIGN_SNAP_PX" in js
    assert "is-layout-hbox" in css
    assert "is-layout-vbox" in css
    assert "is-layout-grid" in css


def test_workbench_p2_controls():
    wb = WB.read_text(encoding="utf-8")
    assert "btnDesignDup" in wb
    assert "duplicateSelected" in wb
    assert "btnDesignRaise" in wb and "btnDesignLower" in wb
    assert "btnAlignLeft" in wb and "btnAlignBottom" in wb
    assert "alignSelected" in wb
    assert "desLayoutMode" in wb
    assert "is-layout-hbox" in wb
    assert "SNAP_PX" in wb


def test_layout_options_present():
    html = HTML.read_text(encoding="utf-8")
    wb = WB.read_text(encoding="utf-8")
    for mode in ("none", "hbox", "vbox", "grid"):
        assert f'value="{mode}"' in html
        assert f'value="{mode}"' in wb
