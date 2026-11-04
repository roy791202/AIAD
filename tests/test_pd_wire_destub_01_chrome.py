"""TDD-PD-WIRE-DESTUB-01 — destub labels vs BDD-PD-WIRE-DESTUB-01.

Wired main paths (UI→Command→DispatchHost→domain) must not be labelled「示意」.
After PD-WIRE-OPEN-01 + PD-REMAIN-DESTUB-OPEN-01, file.open／project.switch
are wired (see test_pd_remain_destub_open_01_chrome). Sibling Remain cards
(FILE-NEW／ARCH-UI／PORTS-UI／…) own their destub — this suite must not
require those keys to stay「尚未實作」. Never fake OPEN wired.
No WebView click driver.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"

# Commands with runCommand → invoke／domain handler (not toast-only stub).
# Includes OPEN + sibling Remain wires so labels must not say「示意」.
WIRED_CMD_KEYS = (
    "file.new",
    "file.open",
    "file.save",
    "project.switch",
    "project.rescan",
    "git.refresh",
    "git.commit",
    "git.push",
    "work.new",
    "board.load",
    "work.assign",
    "work.tags",
    "agent.cancel",
    "deploy.check",
    "deploy.refresh",
    "arch.refresh",
    "report.openEmpty",
    "report.openHappy",
    "settings.activate",
    "settings.draft",
    "settings.revoke",
    "settings.project",
    "win.inspector",
    "edit.undo",
    "edit.redo",
    "edit.selectAll",
    "edit.clear",
)

# Keys still toast-only／no domain path for THIS destub suite.
UNWIRED_MAIN_KEYS = ()


def _cmd_label(js: str, key: str) -> str:
    pat = re.compile(
        r'"' + re.escape(key) + r'"\s*:\s*"([^"]*)"',
    )
    m = pat.search(js)
    assert m, f"missing CMD_LABELS entry for {key}"
    return m.group(1)


def test_ui_assets_exist():
    assert HTML.is_file()
    assert JS.is_file()


def test_wired_cmd_labels_have_no_shiyi():
    js = JS.read_text(encoding="utf-8")
    for key in WIRED_CMD_KEYS:
        label = _cmd_label(js, key)
        assert "示意" not in label, f"{key} is wired — must not say 示意: {label}"


def test_unwired_cmds_explicit_not_implemented():
    js = JS.read_text(encoding="utf-8")
    for key in UNWIRED_MAIN_KEYS:
        label = _cmd_label(js, key)
        assert "示意" not in label, f"{key} must not use vague 示意: {label}"
        assert (
            "尚未實作" in label or "NOT RUN" in label
        ), f"{key} unwired — need 尚未實作／NOT RUN: {label}"


def test_file_open_and_switch_wired_after_open():
    """OPEN residual: handlers real; labels destubbed (REMAIN-DESTUB-OPEN-01)."""
    js = JS.read_text(encoding="utf-8")
    assert 'cmd === "file.open" || cmd === "project.switch"' in js
    assert "尚未實作" not in _cmd_label(js, "file.open")
    assert "尚未實作" not in _cmd_label(js, "project.switch")
    # rescan IS wired via git path
    assert 'cmd === "git.refresh" || cmd === "project.rescan"' in js
    assert "示意" not in _cmd_label(js, "project.rescan")


def test_arch_not_shiyi_after_sibling_wires():
    """Sibling ARCH-UI destubbed — must not regress to「示意」. Ports shell UI removed."""
    js = JS.read_text(encoding="utf-8")
    html = HTML.read_text(encoding="utf-8")
    assert "示意" not in _cmd_label(js, "arch.refresh")
    assert "重新整理（示意）" not in html
    assert 'id="panel-ports"' not in html
    assert 'id="panel-spec"' not in html


def test_no_shiyi_in_chrome_copy():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert "示意" not in html
    # CMD_LABELS／status／toast must not use 示意 for stub ambiguity
    assert "（示意）" not in js
    assert "示意 —" not in js
    assert "瀏覽器示意" not in js
    assert "示意 NOT RUN" not in js


def test_browser_no_ipc_is_not_run_not_demo():
    js = JS.read_text(encoding="utf-8")
    assert "NOT RUN — 無 IPC" in js or "NOT RUN）" in js
    assert "瀏覽器 NOT RUN" in js or "無 IPC（NOT RUN）" in js
