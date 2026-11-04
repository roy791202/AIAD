"""PD-OPEN-LAUNCH-01 — hard gate: program must have been opened (evidence)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "reports" / "dispatch-pd" / "PD-OPEN-LAUNCH-01-evidence.json"


def test_launch_evidence_exists_and_opened():
    assert EV.is_file(), (
        "missing launch evidence — run: "
        "python tools/harness/portable/open_stress_gate.py --stress 500"
    )
    data = json.loads(EV.read_text(encoding="utf-8"))
    assert data.get("opened") is True
    assert data.get("ok") is True
    assert data.get("product_pass") is False
    assert "28790" in str(data.get("base_url", "")) or data.get("port") == 28790
