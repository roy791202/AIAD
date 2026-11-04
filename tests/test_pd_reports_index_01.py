# -*- coding: utf-8 -*-
"""PD-REPORTS-INDEX-01 — lightweight assert on reports index sections / anti-PASS-forge."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "REPORTS-INDEX-v0.1.md"

REQUIRED_SECTION_FRAGMENTS = (
    "Build Result",
    "SBOM",
    "Go",
    "dispatch-pd",
    "缺檔",
)

REQUIRED_PATH_HINTS = (
    "reports/build-",
    "reports/sbom-",
    "reports/gonogo-",
    "reports/dispatch-pd/",
)

REQUIRED_PHRASES = (
    "BDD-PD-REPORTS-INDEX-01",
    "PD-REPORTS-INDEX-01",
    "用途",
    "缺檔",
    "不得暗示未列項已 PASS",
)

ANTI_PASS_MARKERS = (
    "列出路徑 ≠ 該項已 PASS",
    "不得暗示未列項已 PASS",
    "Anti-PASS-forge",
)


def test_reports_index_exists() -> None:
    assert DOC.is_file(), f"missing {DOC}"


def test_reports_index_required_sections() -> None:
    text = DOC.read_text(encoding="utf-8")
    for frag in REQUIRED_SECTION_FRAGMENTS:
        assert frag in text, f"expected section fragment {frag!r}"


def test_reports_index_lists_main_path_families() -> None:
    text = DOC.read_text(encoding="utf-8")
    for hint in REQUIRED_PATH_HINTS:
        assert hint in text, f"expected path family hint {hint!r}"


def test_reports_index_required_phrases() -> None:
    text = DOC.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        assert phrase in text, f"expected phrase {phrase!r}"


def test_reports_index_anti_pass_forge() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert any(m in text for m in ANTI_PASS_MARKERS), "expected anti-PASS-forge language"
    # Affirmative forge claims (substring-safe vs「不得暗示未列項已 PASS」)
    forbidden = (
        "本索引整體=PASS",
        "全部已 PASS",
        "索引即 PASS",
        "未列項＝PASS",
        "未列項=PASS",
    )
    for bad in forbidden:
        assert bad not in text, f"anti-forge: must not contain {bad!r}"
    # Required negation must appear (BDD: 不得暗示未列項已 PASS)
    assert "不得暗示未列項已 PASS" in text


def test_reports_index_marks_missing() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "**缺檔**" in text or "缺檔" in text
    assert "缺檔≠PASS" in text or "缺檔不得當成 PASS" in text
