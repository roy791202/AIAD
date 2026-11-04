"""TDD — shell columns resizable via split grips."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"


def test_split_grips_in_body():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="split-sidebar"' in html
    assert 'id="split-inspector"' in html
    assert 'role="separator"' in html
    assert 'id="shell-body"' in html


def test_split_css_and_js():
    css = CSS.read_text(encoding="utf-8")
    assert ".split-grip" in css
    assert "col-resize" in css
    assert "--split-grip" in css
    js = JS.read_text(encoding="utf-8")
    assert "wireShellSplitters" in js
    assert "applyShellColumnWidths" in js
    assert "SHELL_LAYOUT_LS" in js
