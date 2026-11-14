"""PD-HARNESS-CHECKLIST-01 — Workbench checklist covers shell + views."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CL = ROOT / "tools" / "harness" / "portable" / "checklist-workbench.md"


def test_checklist_exists_and_status_vocab():
    text = CL.read_text(encoding="utf-8")
    for token in ("PASS", "FAIL", "NOT RUN", "PARTIAL"):
        assert token in text
    assert "Workbench" in text or "workbench" in text


def test_checklist_covers_main_path_and_stress():
    text = CL.read_text(encoding="utf-8")
    for needle in (
        "Agent",
        "Tasks",
        "佈版",
        "架構",
        "UI 設計",
        "stress",
        "假",
    ):
        assert needle in text, needle


def test_checklist_forbids_product_pass_from_fake():
    text = CL.read_text(encoding="utf-8")
    assert "假資料" in text or "fake" in text.lower()
    assert "產品" in text or "product" in text.lower()
