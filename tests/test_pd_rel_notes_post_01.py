# -*- coding: utf-8 -*-
"""PD-REL-NOTES-POST-01 — Remain closed + still Go-with-PARTIAL; anti-GA."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "docs" / "RELEASE-NOTES-v0.1.md"

REQUIRED_PHRASES = (
    "BDD-PD-REL-NOTES-POST-01",
    "PD-REL-NOTES-POST-01",
    "Go-with-PARTIAL",
    "NOT RUN",
    "Remain",
    "已關",
    "未 tag",
    "未買證",
    "signing",
)

REQUIRED_SECTION_MARKERS = (
    "## 1. 本佈版範圍",
    "### 1.1 佈版刷新範圍",
    "## 2. Go-with-PARTIAL",
    "## 3. 簽章 NOT RUN",
    "## 5. Anti-forge",
)

FORBIDDEN_AFFIRMATIVE = (
    "已正式商店發布",
    "已正式對外 GA",
    "v0.1 GA 已上線",
    "正式商店發布已完成",
    "formally released to the store",
    "external GA complete",
)

FORBIDDEN_CLAIM_PATTERNS = (
    r"已正式商店發布",
    r"已正式對外\s*GA",
    r"v0\.1\s*GA\s*已上線",
    r"formally released to the store",
    r"formal (store|external) (release|GA) (complete|done|PASS)",
)


def _read() -> str:
    assert NOTES.is_file(), f"missing {NOTES}"
    return NOTES.read_text(encoding="utf-8")


def test_release_notes_exist() -> None:
    assert NOTES.is_file()


def test_required_phrases() -> None:
    text = _read()
    missing = [p for p in REQUIRED_PHRASES if p not in text]
    assert missing == [], f"missing phrases: {missing}"


def test_required_sections() -> None:
    text = _read()
    missing = [m for m in REQUIRED_SECTION_MARKERS if m not in text]
    assert missing == [], f"missing sections: {missing}"


def test_remain_closed_not_ga_upgrade() -> None:
    text = _read()
    assert "Remain" in text and "已關" in text
    assert "仍" in text and "Go-with-PARTIAL" in text
    idx = text.find("### 1.1 佈版刷新範圍")
    assert idx >= 0
    chunk = text[idx : idx + 1200]
    assert "已關" in chunk
    assert "仍 Go-with-PARTIAL" in chunk or "仍**為 Go-with-PARTIAL" in chunk or "仍** Go-with-PARTIAL" in chunk
    assert "NOT RUN" in chunk
    assert "未 tag" in chunk
    assert "未買證" in chunk


def test_signing_still_not_run() -> None:
    text = _read()
    idx = text.find("## 3. 簽章 NOT RUN")
    assert idx >= 0
    chunk = text[idx : idx + 900]
    assert "仍 NOT RUN" in chunk or "仍** NOT RUN" in chunk
    assert "未買證" in chunk
    assert "改寫為 PASS" in chunk or "禁止" in chunk


def test_no_tag_no_cert() -> None:
    text = _read()
    assert "未 tag" in text
    assert "未買證" in text


def test_anti_forge_remain_vs_ga() -> None:
    text = _read()
    assert "Remain 已關＝正式 GA" in text or "Remain 已關" in text
    assert "禁止" in text
    for bad in FORBIDDEN_AFFIRMATIVE:
        for m in re.finditer(re.escape(bad), text, flags=re.IGNORECASE):
            line_start = text.rfind("\n", 0, m.start()) + 1
            line_end = text.find("\n", m.end())
            if line_end < 0:
                line_end = len(text)
            line = text[line_start:line_end]
            ban_ctx = (
                "禁止" in line
                or "Forbidden" in line
                or "≠" in line
                or "不是" in line
                or "must not" in line.lower()
                or "false" in line.lower()
                or "Anti-forge" in line
                or "不得" in line
                or "非正式" in line
            )
            assert ban_ctx, f"forged GA/store claim without ban context: {line!r}"


def test_forbids_ga_claim_patterns() -> None:
    text = _read()
    for pat in FORBIDDEN_CLAIM_PATTERNS:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            line_start = text.rfind("\n", 0, m.start()) + 1
            line_end = text.find("\n", m.end())
            if line_end < 0:
                line_end = len(text)
            line = text[line_start:line_end]
            ban_ctx = (
                "禁止" in line
                or "Forbidden" in line
                or "≠" in line
                or "不是" in line
                or "must not" in line.lower()
                or "false" in line.lower()
                or "Anti-forge" in line
                or "不得" in line
                or "非正式" in line
                or "Is not" in line
            )
            assert ban_ctx, f"forged formal-GA claim without ban context: {line!r}"
