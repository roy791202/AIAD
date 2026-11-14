"""PD-OPEN-FUNC-01 — functional checks require open evidence."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "reports" / "dispatch-pd" / "PD-OPEN-FUNC-01-evidence.json"
LAUNCH = ROOT / "reports" / "dispatch-pd" / "PD-OPEN-LAUNCH-01-evidence.json"


def test_func_requires_launch_and_checks():
    assert LAUNCH.is_file(), "missing launch evidence — open program first"
    launch = json.loads(LAUNCH.read_text(encoding="utf-8"))
    assert launch.get("opened") is True

    assert EV.is_file(), "missing func evidence — run open_stress_gate.py"
    data = json.loads(EV.read_text(encoding="utf-8"))
    assert data.get("ok") is True
    assert data.get("product_pass") is False
    checks = {c["id"]: c["ok"] for c in data.get("checks") or []}
    for need in ("ui_index", "workbench", "mock_bridge", "checklist", "file_new_wired"):
        assert checks.get(need) is True, f"check failed: {need}"
