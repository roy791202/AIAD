"""TDD-PD-REMAIN-DESTUB-OPEN-01 — OPEN destub labels only.

BDD-PD-REMAIN-DESTUB-OPEN-01: once OPEN is wired, CMD_LABELS must not mark
file.open／project.switch as「尚未實作」; handlers stay Command path
(cmdOpenProject → host_pick／host_set_settings). Sibling Remain wires
(file.new／arch／ports／…) are out of scope — do not require them NOT RUN.
No WebView click driver.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"

# OPEN path: UI → Command → DispatchHost → domain (no UI→adapter).
OPEN_WIRED_KEYS = (
    "file.open",
    "project.switch",
)


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


def test_open_and_switch_labels_not_unimplemented():
    js = JS.read_text(encoding="utf-8")
    for key in OPEN_WIRED_KEYS:
        label = _cmd_label(js, key)
        assert "尚未實作" not in label, f"{key} wired after OPEN — no 尚未實作: {label}"
        assert "示意" not in label, f"{key} must not use vague 示意: {label}"
        assert "NOT RUN" not in label, f"{key} wired — must not say NOT RUN: {label}"


def test_open_and_switch_have_command_handlers():
    """ARCH: UI → Tauri Command → DispatchHost → domain; no UI→adapter."""
    js = JS.read_text(encoding="utf-8")
    assert 'cmd === "file.open" || cmd === "project.switch"' in js
    assert "cmdOpenProject" in js
    assert 'invoke("host_pick_project_directory")' in js
    assert "host_set_settings" in js


def test_open_path_not_ui_to_adapter():
    """Open／switch go Command invoke only — no UI→adapter bypass."""
    js = JS.read_text(encoding="utf-8")
    idx = js.index("async function cmdOpenProject")
    rest = js[idx:]
    end = re.search(r"\n  (?:async )?function ", rest[1:])
    snippet = rest[: end.start() + 1] if end else rest[: 1200]
    assert 'invoke("host_pick_project_directory")' in snippet
    assert "host_set_settings" in snippet
    # No direct FS／git APIs in the OPEN chrome handler body.
    assert ".readTextFile(" not in snippet
    assert ".writeTextFile(" not in snippet
    assert "child_process" not in snippet
