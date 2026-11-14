"""PD-OPEN-STRESS-GATE-01 — hard gate: open program + stress must pass."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "reports" / "dispatch-pd" / "PD-OPEN-STRESS-GATE-01-evidence.json"
LAUNCH = ROOT / "reports" / "dispatch-pd" / "PD-OPEN-LAUNCH-01-evidence.json"


def test_stress_hard_gate_requires_open_and_ok():
    assert LAUNCH.is_file(), "missing launch evidence"
    assert json.loads(LAUNCH.read_text(encoding="utf-8")).get("opened") is True

    assert EV.is_file(), (
        "missing stress evidence — run: "
        "python tools/harness/portable/open_stress_gate.py --stress 500"
    )
    data = json.loads(EV.read_text(encoding="utf-8"))
    assert data.get("hard_gate") is True
    assert data.get("opened_program") is True
    assert data.get("ok") is True, f"stress gate failed: {data.get('error')}"
    assert int(data.get("n") or 0) >= 500
    assert int(data.get("stress_board_bytes") or 0) > 1000
    assert data.get("product_pass") is False
    assert data.get("fetches_ok") is True
