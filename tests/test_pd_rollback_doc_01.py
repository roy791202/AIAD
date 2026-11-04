# -*- coding: utf-8 -*-
"""PD-ROLLBACK-DOC-01 — lightweight assert on rollback doc headings/phrases."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "ROLLBACK-v0.1.md"

REQUIRED_HEADING_FRAGMENTS = (
    "靜默卸載",
    "失敗復原",
    "風險",
    "NOT RUN",
)

REQUIRED_PHRASES = (
    "silent uninstall",
    "msiexec",
    "/qn",
    "NOT RUN",
    "風險",
    "正式發布回滾演練",
    "BDD-PD-ROLLBACK-DOC-01",
    "PD-ROLLBACK-DOC-01",
)


def test_rollback_doc_exists() -> None:
    assert DOC.is_file(), f"missing {DOC}"


def test_rollback_doc_required_headings() -> None:
    text = DOC.read_text(encoding="utf-8")
    for frag in REQUIRED_HEADING_FRAGMENTS:
        assert frag in text, f"expected heading/section fragment {frag!r}"


def test_rollback_doc_required_phrases() -> None:
    text = DOC.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        assert phrase in text, f"expected phrase {phrase!r}"


def test_rollback_doc_forbids_claiming_drill_done() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "禁止暗示" in text or "不是正式發布回滾演練" in text
    assert "≠" in text or "不得暗示" in text or "禁止暗示" in text


def test_rollback_doc_cross_links() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "VERIFY-ELEVATED-AND-LIVE-SMOKE.md" in text
    assert "packaging/windows/wix/README.md" in text
