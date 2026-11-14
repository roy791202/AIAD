"""PD-HARNESS-MOCK-01 — mock bridge covers key commands; harness flagged."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "tools" / "harness" / "portable" / "mock_tauri_bridge.js"


def test_bridge_sets_tauri_and_harness_flag():
    text = BRIDGE.read_text(encoding="utf-8")
    assert "__TAURI__" in text
    assert "__SGENAXIS_HARNESS__" in text
    assert "harness: true" in text or "harness = true" in text or 'harness: true' in text


def test_bridge_handles_core_commands():
    text = BRIDGE.read_text(encoding="utf-8")
    for cmd in (
        "host_get_settings",
        "load_local_board",
        "get_board",
        "start_run",
        "poll_chunks",
        "git_workbench_summary",
        "ports_status",
        "listen_get_projection",
        "arch_get_projection",
        "file_save",
    ):
        assert cmd in text, cmd


def test_bridge_stress_param_and_no_demo_root_claim():
    text = BRIDGE.read_text(encoding="utf-8")
    assert "stress" in text
    assert "/demo/root" not in text or "forbidden" in text.lower()
    assert re.search(r"not product evidence|假", text, re.I)
