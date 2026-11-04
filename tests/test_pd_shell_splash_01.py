"""TDD-PD-SHELL-SPLASH-01 — startup splash uses brand splash art + progress chrome.

Reference: soft light splash with progress + "Starting up...".
Asset: ui/icons/brand/splash.png (product-provided artwork).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"
SPLASH = UI / "icons" / "brand" / "splash.png"
MARK = UI / "icons" / "brand" / "mark-64.png"


def test_splash_asset_and_mark_exist():
    assert SPLASH.is_file(), f"missing splash art: {SPLASH}"
    assert MARK.is_file(), f"missing brand mark: {MARK}"
    assert SPLASH.stat().st_size > 10_000


def test_html_splash_overlay_uses_art_and_caption():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="app-splash"' in html
    assert 'data-splash="1"' in html
    assert 'icons/brand/splash.png' in html
    assert 'id="app-splash-progress-fill"' in html
    assert "Starting up..." in html
    assert 'id="app-splash-caption"' in html


def test_css_and_js_dismiss_splash():
    css = CSS.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert ".app-splash" in css
    assert ".app-splash-progress-fill" in css
    assert "splash-progress-run" in css
    assert "dismissAppSplash" in js
    assert "SPLASH_MIN_MS" in js
    assert "SPLASH_MAX_MS" in js
    assert 'getElementById("app-splash")' in js
