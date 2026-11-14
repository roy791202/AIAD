"""TDD-PD-SPEC-UI-01 — ModuleSpec shell UI removed; host spec_* retained.

Shell no longer exposes ModuleSpec／契約 panel or menu. DispatchHost／Tauri
spec_* commands remain for domain. No WebView driver.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"
DISPATCH = (
    ROOT
    / "apps"
    / "sgenaxis-desktop"
    / "src-tauri"
    / "src"
    / "dispatch.rs"
)
LIB = ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "src" / "lib.rs"


def test_spec_ui_assets_exist():
    for path in (HTML, JS, CSS, DISPATCH, LIB):
        assert path.is_file(), f"missing: {path}"


def test_panel_spec_removed_from_shell():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert 'id="panel-spec"' not in html
    assert 'id="nav-spec"' not in html
    assert 'data-cmd="nav.spec"' not in html
    assert 'data-cmd="spec.load"' not in html
    assert "ModuleSpec" not in html
    assert "cmdSpecLoad" not in js
    assert "renderSpecProjection" not in js
    assert ".spec-toolbar" not in css


def test_tauri_registers_spec_commands():
    lib = LIB.read_text(encoding="utf-8")
    for name in (
        "spec_load_fixture",
        "spec_get_projection",
        "spec_get_revision",
        "spec_approve",
        "spec_try_set_contract",
        "spec_revise",
    ):
        assert f"commands::{name}" in lib, name


def test_dispatch_hosts_spec_replan_path():
    src = DISPATCH.read_text(encoding="utf-8")
    assert "spec_try_set_contract" in src
    assert "spec_revise" in src
    assert "REPLAN_REQUIRED" in src
    assert "spec_ui_load_display_replan_and_revise_entry" in src
