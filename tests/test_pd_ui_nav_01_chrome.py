"""TDD-PD-UI-NAV-01 — main-path nav / empty chrome.

Asserts desktop UI sidebar primary tabs
(Diagram → Tasks status → Git status → Setting) + More dropdown,
plus clickable empty hooks. No WebView click driver.
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
    # Scope to sidebar only — menubar also carries data-panel hints
    start = html.find('<nav class="sidebar"')
    end = html.find("</nav>", start)
    assert start != -1 and end != -1
    side = html[start:end]
    arch = side.find('id="nav-arch"')
    tasks = side.find('id="nav-tasks"')
    git = side.find('id="nav-git"')
    settings = side.find('id="nav-settings"')
    board_filter = side.find('data-filter="overview"')
    assert arch != -1 and tasks != -1 and git != -1 and settings != -1
    assert arch < tasks < git < settings, (
        "sidebar tabs must be Diagram→Tasks status→Git status→Setting"
    )
    assert board_filter != -1 and tasks < board_filter
    # Tasks Status zone filters
    for filt in ("overview", "gray", "yellow", "red", "green", "accepted"):
        assert f'data-filter="{filt}"' in side, f"missing Tasks Status filter: {filt}"
    # More dropdown holds demoted routes
    assert 'id="side-more-menu"' in side
    assert 'id="nav-agent"' in side
    assert 'id="nav-deploy"' in side
    # Out of scope: no full UI design tool panel
    assert 'data-panel="ui-design"' not in html
    assert "viewUiDesign" not in html


def test_clickable_empty_states_on_main_panels():
    html = HTML.read_text(encoding="utf-8")
    for empty_id in ("board-empty", "agent-empty", "deploy-empty", "git-empty"):
        assert f'id="{empty_id}"' in html, f"missing empty root: {empty_id}"
    # arch panel: DAG canvas（無獨立 empty 卡；工具列 arch.refresh）
    assert 'id="panel-arch"' in html
    assert 'data-cmd="arch.refresh"' in html
    # Empty CTAs must be present and wired via data-empty-action and/or data-cmd
    assert html.count("data-empty-action=") >= 8
    assert 'data-empty="board-error"' in html or 'id="board-error"' in html


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
