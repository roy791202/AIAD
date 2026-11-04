"""TDD-PD-SHELL-CHROME-01 — static DOM/CSS/cmd asserts for shell chrome.

BDD-PD-SHELL-CHROME-01: menubar＋toolbar＋status 資訊層級／間距／專案列
接近 Workbench（非像素逐點）；既有 data-cmd 保留；空／未綁定態可讀。
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
CSS = UI / "styles.css"
JS = UI / "app.js"

# Chrome-facing commands that must remain wired (no new business Commands).
CHROME_CMDS = (
    "file.new",
    "file.open",
    "file.save",
    "file.quit",
    "project.switch",
    "project.rescan",
    "work.assign",
    "work.new",
    "win.reset",
    "win.inspector",
    "help.about",
)


def _css_var(css: str, name: str) -> str | None:
    m = re.search(rf"--{re.escape(name)}\s*:\s*([^;]+);", css)
    return m.group(1).strip() if m else None


def _px(value: str | None) -> int | None:
    if not value:
        return None
    m = re.match(r"(\d+)px", value.strip())
    return int(m.group(1)) if m else None


def test_chrome_assets_exist():
    for path in (HTML, CSS, JS):
        assert path.is_file(), f"missing: {path}"


def test_titlebar_menubar_toolbar_status_hierarchy():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="app-titlebar"' in html or 'class="titlebar"' in html
    assert 'role="menubar"' in html
    assert "desktop-menubar" in html or 'class="menubar' in html
    assert "desktop-toolbar" in html or 'class="toolbar' in html
    assert "window-statusbar" in html or 'class="statusbar' in html
    # Nested: titlebar contains menubar then toolbar (Workbench QMenuBar+QToolBar)
    titlebar_idx = html.find("titlebar")
    menubar_idx = html.find('role="menubar"')
    toolbar_idx = html.find('aria-label="工具列"')
    status_idx = html.find('aria-label="狀態列"')
    assert 0 <= titlebar_idx < menubar_idx < toolbar_idx < status_idx


def test_project_row_unbound_readable():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="project-bind-chip"' in html
    assert 'id="project-bind-label"' in html
    assert 'id="project-path"' in html
    assert "未綁定" in html
    assert "project_root" in html
    assert "path-box" in html or "project-combo" in html
    assert 'id="status-project"' in html
    assert "專案：未綁定" in html


def test_chrome_data_cmds_preserved():
    html = HTML.read_text(encoding="utf-8")
    for cmd in CHROME_CMDS:
        assert f'data-cmd="{cmd}"' in html, f"missing chrome data-cmd: {cmd}"


def test_css_chrome_heights_near_workbench():
    css = CSS.read_text(encoding="utf-8")
    menubar = _px(_css_var(css, "menubar-h"))
    toolbar = _px(_css_var(css, "toolbar-h"))
    status = _px(_css_var(css, "statusbar-h"))
    assert menubar == 44, f"menubar-h expected 44px, got {menubar}"
    assert toolbar is not None and 40 <= toolbar <= 48, f"toolbar-h near Workbench 44: {toolbar}"
    assert status is not None and 28 <= status <= 48, f"statusbar-h near Workbench: {status}"
    assert ".titlebar" in css
    assert ".path-box" in css or ".project-combo" in css
    assert ".window-statusbar" in css or ".statusbar" in css


def test_no_pyside_in_shell_ui():
    for path in (HTML, CSS, JS):
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        assert "pyside" not in lower, f"PySide must not appear in {path.name}"
        assert "from pyqt" not in lower


def test_js_still_binds_chrome_ids():
    js = JS.read_text(encoding="utf-8")
    for eid in (
        "project-path",
        "project-bind-label",
        "project-bind-dot",
        "status-project",
        "status-msg",
        "status-agent",
    ):
        assert eid in js, f"app.js must keep binding id {eid}"
