# -*- coding: utf-8 -*-
"""PD-REL-NOTES-01 — release notes structure + anti-GA forge phrases."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "docs" / "RELEASE-NOTES-v0.1.md"

REQUIRED_PHRASES = (
    "BDD-PD-REL-NOTES-01",
    "PD-REL-NOTES-01",
    "Go-with-PARTIAL",
    "NOT RUN",
    "未做另案",
    "signing",
    "DCC",
    "SSH",
    "買證",
)

REQUIRED_SECTION_MARKERS = (
    "## 1. 本佈版範圍",
    "## 2. Go-with-PARTIAL",
    "## 3. 簽章 NOT RUN",
    "## 4. 未做另案",
    "## 5. Anti-forge",
)

# Affirmative GA / store completion claims that must NOT appear as fact.
FORBIDDEN_AFFIRMATIVE = (
    "已正式商店發布",
    "已正式對外 GA",
    "v0.1 GA 已上線",
    "正式商店發布已完成",
    "formally released to the store",
    "external GA complete",
)

# Patterns that may appear only inside ban / anti-forge context.
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


def test_signing_not_run_honest() -> None:
    text = _read()
    assert "signing" in text.lower() or "簽章" in text
    assert "NOT RUN" in text
    idx = text.find("## 3. 簽章 NOT RUN")
    assert idx >= 0
    chunk = text[idx : idx + 800]
    assert "NOT RUN" in chunk
    assert "PASS" not in chunk.split("禁止")[0] or "改寫為 PASS" in chunk


def test_go_with_partial_not_full_ga() -> None:
    text = _read()
    assert "Go-with-PARTIAL" in text
    assert "不是" in text or "≠" in text or "非正式" in text
    assert "對外 GA" in text or "external GA" in text.lower()


def test_deferred_items_explicit() -> None:
    text = _read()
    assert "未做另案" in text
    for token in ("DCC", "SSH", "買證"):
        assert token in text
    assert "行銷網站" in text
    assert "不做" in text


def test_anti_forge_framing() -> None:
    text = _read()
    assert "Anti-forge" in text or "禁止" in text
    assert (
        "正式商店" in text
        or "對外 GA" in text
        or "formally released" in text.lower()
    )
    for bad in FORBIDDEN_AFFIRMATIVE:
        # May appear only with ban context on the same line.
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
