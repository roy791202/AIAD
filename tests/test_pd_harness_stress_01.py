"""PD-HARNESS-STRESS-01 — fake board generator + mock stress wiring."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H = ROOT / "tools" / "harness" / "portable"
GEN = H / "stress_gen.py"
BRIDGE = H / "mock_tauri_bridge.js"


def test_stress_gen_writes_n_tasks(tmp_path: Path):
    out = tmp_path / "board.json"
    r = subprocess.run(
        [sys.executable, str(GEN), "-n", "120", "-o", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("harness") is True
    assert data.get("stressN") == 120
    assert len(data["tasks"]) == 120
    zones = {t["zone"] for t in data["tasks"]}
    assert zones <= {"gray", "yellow", "red", "green"}
    assert all("假" in t["title"] or "FAKE" in t["id"] for t in data["tasks"])


def test_bridge_supports_stress_query():
    text = BRIDGE.read_text(encoding="utf-8")
    assert "stressN" in text or "stress" in text
    assert "makeTasks" in text or "FAKE-" in text


def test_stress_gen_rejects_absurd_n():
    r = subprocess.run(
        [sys.executable, str(GEN), "-n", "999999"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0


def test_anti_forge_note_in_generator_output(tmp_path: Path):
    out = tmp_path / "b.json"
    subprocess.run(
        [sys.executable, str(GEN), "-n", "4", "-o", str(out)],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
    )
    raw = out.read_text(encoding="utf-8")
    assert "not product evidence" in raw or "harness" in raw
