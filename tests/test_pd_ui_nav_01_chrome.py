"""TDD-PD-UI-NAV-01 — main-path nav / empty chrome.

Asserts desktop UI sidebar primary tabs
(Diagram → Tasks status → Git status → Setting),
Tasks drawer entries (Agent／佈版／監聽／報告), plus clickable empty hooks.
No WebView click driver.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"
PROTOTYPE = ROOT / "git_workbench_interactive.html"

# Prototype main-path sidebar anchors (legacy checklist; product shell uses tabs)
PROTO_MAIN_PATH = (
    "btnAgentNav",
    "secTasksStatus",
    "btnReleaseNav",
    "btnArchNav",
)


def test_ui_and_prototype_exist():
    for path in (HTML, JS, CSS, PROTOTYPE):
        assert path.is_file(), f"missing: {path}"


def test_prototype_main_path_anchors_present():
    proto = PROTOTYPE.read_text(encoding="utf-8")
    for anchor in PROTO_MAIN_PATH:
        assert anchor in proto, f"prototype missing main-path anchor: {anchor}"
    # Full design tool exists in prototype but is out of scope for this card
    assert "btnUiNav" in proto


def test_sidebar_main_path_order_matches_prototype():
    html = HTML.read_text(encoding="utf-8")
    assert 'data-nav-main-path="1"' in html
    # Toolbar view-tabs after project path (not menubar data-panel hints)
    path_pos = html.find('id="project-path-box"')
    rail_start = html.find('id="side-rail"')
    body_start = html.find('id="shell-body"')
    assert path_pos != -1 and rail_start != -1 and body_start != -1
    assert path_pos < rail_start < body_start
    tabs = html[html.rfind("<", 0, rail_start) : body_start]
    side_start = html.find('<nav class="sidebar"')
    side_end = html.find("</nav>", side_start)
    assert side_start != -1 and side_end != -1
    side = html[side_start:side_end]
    arch = tabs.find('id="nav-arch"')
    tasks = tabs.find('id="nav-tasks"')
    git = tabs.find('id="nav-git"')
    settings = tabs.find('id="nav-settings"')
    board_filter = side.find('data-filter="overview"')
    assert arch != -1 and tasks != -1 and git != -1 and settings != -1
    assert arch < tasks < git < settings, (
        "top tabs must be Diagram→Tasks status→Git status→Setting"
    )
    assert board_filter != -1
    # Tasks Status zone filters live in the drawer
    for filt in ("overview", "gray", "yellow", "orange", "red", "green", "accepted"):
        assert f'data-filter="{filt}"' in side, f"missing Tasks Status filter: {filt}"
    assert "待核准" in side
    # Agent／佈版／監聽／報告掛在 Tasks 左側；無「更多」抽屜
    assert 'id="side-more-menu"' not in side
    assert 'id="side-more-toggle"' not in html
    assert 'id="nav-agent"' in side
    assert 'id="nav-deploy"' in side
    assert 'id="nav-listen"' in side
    assert 'id="nav-report"' in side
    assert 'id="sec-tasks-status"' in side
    assert 'id="nav-ports"' not in html
    assert 'id="panel-ports"' not in html
    assert 'id="nav-spec"' not in html
    assert 'id="panel-spec"' not in html
    assert "ModuleSpec" not in html
    tasks_sec = side[side.find('id="sec-tasks-status"') :]
    for nid in ("nav-agent", "nav-deploy", "nav-listen", "nav-report"):
        assert f'id="{nid}"' in tasks_sec
    assert (
        tasks_sec.find('id="nav-agent"')
        < tasks_sec.find('id="nav-deploy"')
        < tasks_sec.find('id="nav-listen"')
        < tasks_sec.find('id="nav-report"')
    )
    # Out of scope: no full UI design tool panel
    assert 'data-panel="ui-design"' not in html
    assert "viewUiDesign" not in html


def test_clickable_empty_states_on_main_panels():
    html = HTML.read_text(encoding="utf-8")
    for empty_id in ("board-empty", "agent-empty", "deploy-empty", "git-empty"):
        assert f'id="{empty_id}"' in html, f"missing empty root: {empty_id}"
    # arch panel: DAG canvas（無獨立 empty 卡；工具列直接編輯）
    assert 'id="panel-arch"' in html
    assert 'id="arch-canvas-shell"' in html or 'id="archBoard"' in html
    # Empty CTAs must be present and wired via data-empty-action and/or data-cmd
    assert html.count("data-empty-action=") >= 8
    assert 'data-empty="board-error"' in html or 'id="board-error"' in html
    assert 'id="btn-board-add"' in html


def test_js_wires_filters_empty_and_no_crash_guards():
    js = JS.read_text(encoding="utf-8")
    assert "setBoardFilter" in js
    assert "filterTasks" in js
    assert "showBoardError" in js
    assert "renderBoard(null)" in js
    assert "data-empty-action" in js or "[data-empty-action]" in js
    # Command path wrapped so empty-state clicks cannot take down the shell
    assert "命令已攔截錯誤" in js or "已攔截" in js
    assert "deploy.check" in js
    assert "arch.refresh" in js


def test_css_supports_status_list_and_error_empty():
    css = CSS.read_text(encoding="utf-8")
    assert ".status-list" in css
    assert ".status-item" in css
    assert ".error-state" in css or "error-state" in css
    assert ".tag-chip" in css
