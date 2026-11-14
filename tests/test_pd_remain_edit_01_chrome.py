"""TDD-PD-REMAIN-EDIT-01 path C — Edit menu → Command → Core.

Asserts 編輯選單 wires edit_* invoke (not NOT RUN half-stub), and
DispatchHost catalogue exposes edit commands. Host unit tests cover domain.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
DISPATCH = ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "src" / "dispatch.rs"
CORE_EDIT = (
    ROOT / "apps" / "sgenaxis-desktop" / "crates" / "sgenaxis-core" / "src" / "edit.rs"
)
LIB = ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "src" / "lib.rs"


def test_edit_assets_exist():
    for path in (HTML, JS, DISPATCH, CORE_EDIT, LIB):
        assert path.is_file(), f"missing: {path}"


def test_menu_labels_not_not_run():
    html = HTML.read_text(encoding="utf-8")
    assert 'data-cmd="edit.undo"' in html
    assert 'data-cmd="edit.redo"' in html
    assert 'data-cmd="edit.selectAll"' in html
    assert 'data-cmd="edit.clear"' in html
    menu = html[html.find('data-menu="編輯"') : html.find('data-menu="專案"')]
    assert "尚未實作" not in menu
    assert "NOT RUN" not in menu
    assert "復原" in menu and "重做" in menu
    assert "全選變更" in menu and "清除選取" in menu


def test_js_invokes_edit_commands():
    js = JS.read_text(encoding="utf-8")
    for name in ("edit_undo", "edit_redo", "edit_select_all", "edit_clear"):
        assert f'"{name}"' in js or f"'{name}'" in js, f"missing invoke {name}"
    assert "cmdEditUndo" in js
    assert "cmdEditSelectAll" in js
    assert "applyEditProjection" in js
    assert 'invokeName' in js or 'edit_undo' in js
    for key, bad in (
        ("edit.undo", "復原（尚未實作"),
        ("edit.redo", "重做（尚未實作"),
        ("edit.selectAll", "全選變更（尚未實作"),
        ("edit.clear", "清除選取（尚未實作"),
    ):
        assert f'"{key}": "{bad}' not in js


def test_dispatch_and_core_edit_session():
    core = CORE_EDIT.read_text(encoding="utf-8")
    assert "struct EditSession" in core
    assert "fn select_all" in core
    assert "fn undo" in core
    dispatch = DISPATCH.read_text(encoding="utf-8")
    assert "fn edit_undo" in dispatch
    assert "fn edit_select_all" in dispatch
    assert 'name: "edit_undo"' in dispatch
    lib = LIB.read_text(encoding="utf-8")
    assert "commands::edit_undo" in lib
    assert "commands::edit_select_all" in lib
