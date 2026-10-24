"""TDD-PD-SHELL-SIDEBAR-01 — sidebar IA: primary tabs + bottom More menu.

Primary tabs: Diagram → Tasks status → Git status → Setting.
Other panels (Agent／佈版／Spec／Report／Ports／Listen) live in bottom dropdown.
Tasks Status keeps four-zone filters. No WebView driver.
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

MORE_PANELS = ("agent", "deploy", "spec", "report", "ports", "listen")
ZONE_FILTERS = ("gray", "yellow", "red", "green")
ALL_FILTERS = ("overview",) + ZONE_FILTERS + ("accepted",)


def _sidebar(html: str) -> str:
    start = html.find('<nav class="sidebar"')
    end = html.find("</nav>", start)
    assert start != -1 and end != -1, "sidebar nav missing"
    return html[start:end]


def test_assets_and_prototype_ssot_exist():
    for path in (HTML, JS, CSS, PROTOTYPE):
        assert path.is_file(), f"missing: {path}"


def test_prototype_main_path_includes_ui_design():
    proto = PROTOTYPE.read_text(encoding="utf-8")
    for anchor in PROTO_MAIN:
        assert anchor in proto, f"prototype missing: {anchor}"
    for filt in ALL_FILTERS:
        assert f'data-filter="{filt}"' in proto, f"prototype filter missing: {filt}"


def test_sidebar_primary_tabs_order_diagram_tasks_git_setting():
    html = HTML.read_text(encoding="utf-8")
    side = _sidebar(html)
    assert 'data-nav-main-path="1"' in side
    assert 'data-nav-ssot="side-tabs"' in side
    assert 'id="side-tabs"' in side
    positions = []
    for nid in MAIN_TAB_IDS:
        pos = side.find(f'id="{nid}"')
        assert pos != -1, f"primary tab missing id={nid}"
        positions.append(pos)
    assert positions == sorted(positions), (
        "sidebar tabs must be Diagram→Tasks status→Git status→Setting"
    )
    assert "Diagram" in side
    assert "Tasks status" in side
    assert "Git status" in side
    assert "Setting" in side
    assert 'id="side-rail"' in side
    assert 'id="side-drawer"' in side
    # UI 設計改為獨立視窗：側欄不再有 UI 設計入口
    assert 'id="sec-uidesign"' not in side
    assert 'data-panel="uidesign"' not in side


def test_tasks_status_four_zone_filters_and_workbench_chrome():
    html = HTML.read_text(encoding="utf-8")
    side = _sidebar(html)
    assert 'id="sec-tasks-status"' in side
    assert 'id="btn-clear-status-filter"' in side
    assert "overview-dots" in side
    assert "status-item-left" in side
    assert "counter-badge" in side
    for filt in ALL_FILTERS:
        assert f'data-filter="{filt}"' in side, f"missing filter: {filt}"
    for filt in ZONE_FILTERS:
        assert f'data-filter="{filt}"' in side
        idx = side.find(f'data-filter="{filt}"')
        chunk = side[idx : idx + 220]
        assert 'data-zone-filter="1"' in chunk, f"zone filter not marked: {filt}"


def test_more_menu_demoted_routes_at_bottom():
    html = HTML.read_text(encoding="utf-8")
    side = _sidebar(html)
    assert 'data-nav-secondary="1"' in side or 'id="sec-nav-secondary"' in side
    assert 'id="side-more-toggle"' in side
    assert 'id="side-more-menu"' in side
    sec_start = side.find('id="side-more-menu"')
    assert sec_start != -1
    more = side[sec_start:]
    settings_pos = side.find('id="nav-settings"')
    assert settings_pos != -1 and settings_pos < sec_start, "More menu must follow primary tabs"
    for panel in MORE_PANELS:
        assert f'id="nav-{panel}"' in more, f"More menu missing nav-{panel}"
        assert f'data-panel="{panel}"' in more


def test_panel_routes_intact_including_uidesign_shell():
    html = HTML.read_text(encoding="utf-8")
    for panel in ("agent", "board", "deploy", "arch", "git", "settings", *MORE_PANELS):
        assert f'id="panel-{panel}"' in html, f"missing panel-{panel}"
        assert f'data-panel="{panel}"' in html
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
    assert "setSideMoreOpen" in js
    assert "side-more-toggle" in js


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
        ".side-drawer",
        ".side-tab-body",
        ".side-more",
        ".side-more-menu",
        "aria-orientation=\"horizontal\"",
    ):
        assert sel in css or sel in HTML.read_text(encoding="utf-8"), (
            f"missing: {sel}"
        )
    html = HTML.read_text(encoding="utf-8")
    assert 'id="side-rail"' in html
    assert 'id="side-drawer"' in html
    assert 'data-drawer-open=' in html
    assert "side-tab-label" in html
    assert 'aria-orientation="horizontal"' in html
