"""TDD-PD-SHELL-SIDEBAR-01 — shell IA: top primary tabs + Tasks drawer.

Primary tabs (full-width top strip): Diagram → Tasks status → Git status → Setting.
Agent／佈版／監聽／報告 live in the Tasks drawer (no More menu / Ports panel).
Tasks Status keeps zone filters. No WebView driver.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"
PROTOTYPE = ROOT / "git_workbench_interactive.html"

PROTO_MAIN = (
    "btnAgentNav",
    "secTasksStatus",
    "btnReleaseNav",
    "btnArchNav",
    "btnUiNav",
)

MAIN_TAB_IDS = (
    "nav-arch",
    "nav-tasks",
    "nav-git",
    "nav-settings",
)

TASKS_DRAWER_NAVS = ("agent", "deploy", "listen", "report")
ZONE_FILTERS = ("gray", "yellow", "orange", "red", "green")
ALL_FILTERS = ("overview",) + ZONE_FILTERS + ("accepted",)


def _sidebar(html: str) -> str:
    start = html.find('<nav class="sidebar"')
    end = html.find("</nav>", start)
    assert start != -1 and end != -1, "sidebar nav missing"
    return html[start:end]


def _view_tabs(html: str) -> str:
    start = html.find('id="side-rail"')
    assert start != -1, "toolbar view tabs (#side-rail) missing"
    # include opening tag
    start = html.rfind("<", 0, start)
    end = html.find("</div>", html.find('id="nav-settings"', start))
    assert end != -1, "nav-settings close missing"
    # close outer side-rail wrapper (side-tabs + rail)
    end = html.find("</div>", end + 1)
    assert end != -1
    end = html.find("</div>", end + 1)
    assert end != -1
    return html[start : end + len("</div>")]


def test_assets_and_prototype_ssot_exist():
    for path in (HTML, JS, CSS, PROTOTYPE):
        assert path.is_file(), f"missing: {path}"


def test_prototype_main_path_includes_ui_design():
    proto = PROTOTYPE.read_text(encoding="utf-8")
    for anchor in PROTO_MAIN:
        assert anchor in proto, f"prototype missing: {anchor}"
    # Prototype predates 待核准(orange); product shell has the full filter set.
    for filt in ("overview", "gray", "yellow", "red", "green", "accepted"):
        assert f'data-filter="{filt}"' in proto, f"prototype filter missing: {filt}"


def test_sidebar_primary_tabs_order_diagram_tasks_git_setting():
    html = HTML.read_text(encoding="utf-8")
    tabs = _view_tabs(html)
    side = _sidebar(html)
    assert 'data-nav-main-path="1"' in tabs
    assert 'data-nav-ssot="side-tabs"' in tabs
    assert 'id="side-tabs"' in tabs
    assert "toolbar-view-tabs" in tabs
    path_pos = html.find('id="project-path-box"')
    rail_pos = html.find('id="side-rail"')
    assert path_pos != -1 and rail_pos != -1 and path_pos < rail_pos, (
        "view-tab icons must sit after project path"
    )
    positions = []
    for nid in MAIN_TAB_IDS:
        pos = tabs.find(f'id="{nid}"')
        assert pos != -1, f"primary tab missing id={nid}"
        positions.append(pos)
    assert positions == sorted(positions), (
        "tabs must be Diagram→Tasks status→Git status→Setting"
    )
    assert "Diagram" in tabs
    assert "Tasks status" in tabs
    assert "Git status" in tabs
    assert "Setting" in tabs
    assert 'id="side-more-toggle"' not in tabs
    assert "icons/nav/diagram.svg" in tabs
    assert "icons/nav/tasks.svg" in tabs
    assert "icons/nav/git.svg" in tabs
    assert "icons/nav/settings.svg" in tabs
    assert "side-tab-icon" in tabs
    assert 'id="side-drawer"' in side
    # Primary tabs live in toolbar, not inside the drawer column
    for nid in MAIN_TAB_IDS:
        assert f'id="{nid}"' not in side
    # UI 設計改為獨立視窗：側欄不再有 UI 設計入口
    assert 'id="sec-uidesign"' not in side
    assert 'data-panel="uidesign"' not in side


def test_tasks_status_four_zone_filters_and_workbench_chrome():
    html = HTML.read_text(encoding="utf-8")
    side = _sidebar(html)
    assert 'id="sec-tasks-status"' in side
    assert 'id="btn-clear-status-filter"' in side
    assert "status-item-left" in side
    assert "counter-badge" in side
    assert ".overview-dots" in CSS.read_text(encoding="utf-8")
    for filt in ALL_FILTERS:
        assert f'data-filter="{filt}"' in side, f"missing filter: {filt}"
    for filt in ZONE_FILTERS:
        assert f'data-filter="{filt}"' in side
        idx = side.find(f'data-filter="{filt}"')
        chunk = side[idx : idx + 220]
        assert 'data-zone-filter="1"' in chunk, f"zone filter not marked: {filt}"


def test_tasks_drawer_entries_no_more_menu():
    html = HTML.read_text(encoding="utf-8")
    side = _sidebar(html)
    assert 'id="side-more-toggle"' not in html
    assert 'id="side-more-menu"' not in side
    assert 'id="sec-nav-secondary"' not in side
    assert 'id="nav-ports"' not in html
    assert 'id="panel-ports"' not in html
    assert 'id="nav-spec"' not in html
    assert 'id="panel-spec"' not in html
    tasks = side[side.find('id="sec-tasks-status"') :]
    for panel in TASKS_DRAWER_NAVS:
        assert f'id="nav-{panel}"' in tasks, f"Tasks drawer missing nav-{panel}"
        assert f'data-panel="{panel}"' in tasks


def test_panel_routes_intact_including_uidesign_shell():
    html = HTML.read_text(encoding="utf-8")
    for panel in (
        "agent",
        "board",
        "deploy",
        "arch",
        "git",
        "settings",
        "listen",
        "report",
    ):
        assert f'id="panel-{panel}"' in html, f"missing panel-{panel}"
        assert f'data-panel="{panel}"' in html
    assert 'id="panel-ports"' not in html
    assert 'id="panel-spec"' not in html
    assert 'id="panel-uidesign"' in html
    assert 'id="uidesign-window"' in html
    assert 'id="uidesign-designer"' in html or 'id="designCanvas"' in html


def test_js_wires_clear_filter_and_side_tabs():
    js = JS.read_text(encoding="utf-8")
    assert "clearStatusFilter" in js
    assert "btn-clear-status-filter" in js
    assert "openUiDesignWindow" in js
    assert "ZONE_FILTERS" in js
    assert "setBoardFilter" in js
    assert "showPanel" in js
    assert "syncSideTabs" in js
    assert "setSideMoreOpen" not in js
    assert "side-more-toggle" not in js
    assert "cmdPortsRefresh" not in js


def test_css_status_and_side_tabs_chrome():
    css = CSS.read_text(encoding="utf-8")
    for sel in (
        ".status-list",
        ".status-item",
        ".status-item-left",
        ".overview-dots",
        ".counter-badge",
        ".section-badge-action",
        ".side-rail",
        ".side-tabs-bar",
        ".side-tabs",
        ".side-tab-label",
        ".side-tab-icon",
        ".side-drawer",
        ".side-tab-body",
        'aria-orientation="horizontal"',
    ):
        assert sel in css or sel in HTML.read_text(encoding="utf-8"), (
            f"missing: {sel}"
        )
    html = HTML.read_text(encoding="utf-8")
    assert 'id="side-rail"' in html
    assert 'id="side-drawer"' in html
    assert "data-drawer-open=" in html
    assert "side-tab-label" in html
    assert "side-tab-icon" in html
    assert "visually-hidden" in html
    assert 'aria-orientation="horizontal"' in html
    for name in ("diagram", "tasks", "git", "settings"):
        assert (UI / "icons" / "nav" / f"{name}.svg").is_file()
    assert ".side-more-menu" not in css
    assert ".ports-toolbar" not in css
