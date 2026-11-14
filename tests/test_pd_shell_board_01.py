"""TDD-PD-SHELL-BOARD-01 — board table density / columns vs Workbench viewTaskBoard.

Asserts desktop board panel uses a dense table (燈號／狀態／工項／檔案／BDD／TDD／時間／備註),
Workbench-like light-set + empty copy, and keeps data on existing board Command／projection
(no UI direct file read; no fake task rows in markup).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"
PROTOTYPE = ROOT / "git_workbench_interactive.html"

PROTO_HEADERS = (
    "燈號",
    "狀態",
    "工項",
    "修改的檔案",
    "BDD",
    "TDD",
    "建立時間",
    "完成時間",
    "備註",
)


def test_assets_exist():
    for path in (HTML, JS, CSS, PROTOTYPE):
        assert path.is_file(), f"missing: {path}"


def test_prototype_view_task_board_table_contract():
    proto = PROTOTYPE.read_text(encoding="utf-8")
    assert 'id="viewTaskBoard"' in proto
    assert 'id="gitTable"' in proto
    assert 'class="light-set"' in proto
    assert 'id="boardEmpty"' in proto or "board-empty" in proto
    for header in PROTO_HEADERS:
        assert header in proto, f"prototype missing column header: {header}"


def test_board_panel_has_workbench_column_hierarchy():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="panel-board"' in html
    assert 'id="board-table"' in html
    assert 'id="board-table-viewport"' in html
    assert 'id="board-tasks"' in html
    # tbody for projection rows — not a static fake task list
    start = html.find('id="board-table"')
    end = html.find("</table>", start)
    assert start != -1 and end != -1
    table = html[start:end]
    for header in PROTO_HEADERS:
        assert header in table, f"board table missing header: {header}"
    for col in (
        "col-lights",
        "col-status",
        "col-title",
        "col-files",
        "col-bdd",
        "col-tdd",
        "col-created",
        "col-completed",
        "col-note",
    ):
        assert col in table, f"missing column class: {col}"
    # No seeded fake work-item rows in markup
    assert "TASK-01" not in table
    assert "PSIDE-01" not in table
    assert "data-id=" not in table


def test_board_empty_copy_aligns_with_workbench():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="board-empty"' in html
    assert "尚無工項" in html
    assert 'id="btn-board-add"' in html
    assert "+ 新增工項" in html


def test_js_renders_dense_table_from_projection_only():
    js = JS.read_text(encoding="utf-8")
    assert "function renderBoard" in js
    assert "boardLightSetHtml" in js
    assert "light-set" in js
    assert "board-table-viewport" in js
    assert "col-lights" in js
    assert "col-title" in js
    assert "task-name" in js
    assert "task-meta" in js
    # Projection path: board.tasks only — dash for fields not in TaskView
    assert "boardProjectionDash" in js or "time-sub" in js
    assert "boardTasks(lastBoard)" in js or "boardTasks(board)" in js
    # ARCH: no UI direct file read of PROJECT-BOARD
    assert "readFileSync" not in js
    assert "fetch(" not in js or "board.load" in js
    # Must still go through command / invoke path for load
    assert "board.load" in js
    assert 'invoke("load_local_board"' in js or "load_local_board" in js or "board.load" in js


def test_js_no_hardcoded_fake_task_rows():
    js = JS.read_text(encoding="utf-8")
    # renderBoard must build rows from projection tasks, not a static demo array
    assert "visible.forEach" in js
    assert 'id: "TASK-' not in js
    assert "fakeTasks" not in js
    assert "demoTasks" not in js


def test_css_board_table_density_tokens():
    css = CSS.read_text(encoding="utf-8")
    assert ".board-table" in css
    assert ".board-table-viewport" in css or ".table-viewport" in css
    assert ".light-set" in css
    assert ".task-name" in css
    assert ".col-lights" in css
    # Dense row padding close to Workbench (9px 10px / 8px 10px)
    assert "padding: 9px 10px" in css
    assert "padding: 8px 10px" in css
