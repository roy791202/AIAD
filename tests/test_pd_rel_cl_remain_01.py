# -*- coding: utf-8 -*-
"""PD-REL-CL-REMAIN-01 — CHANGELOG [0.1.0] Remain 接通摘要 + anti-forge."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"

SECTION_MARKER = "### Changed — Remain 接通摘要（BDD-PD-REL-CL-REMAIN-01）"

REQUIRED_PHRASES = (
    "BDD-PD-REL-CL-REMAIN-01",
    "file.new",
    "file.save",
    "file.quit",
    "ports",
    "arch",
    "work.tags",
    "Live CLI",
    "Live MCP",
    "listen",
    "listen_get_projection",
    "NOT RUN",
    "0.1.0",
)

# Affirmative completion claims that must not appear as fact.
FORBIDDEN_AFFIRMATIVE = (
    "已簽章",
    "已 Authenticode",
    "signing PASS",
    "已 git tag",
    "已打 tag",
    "已商店 GA",
    "商店 GA 已上線",
    "正式商店發布已完成",
    "external GA complete",
    "formally released to the store",
)


def _read() -> str:
    assert CHANGELOG.is_file(), f"missing {CHANGELOG}"
    return CHANGELOG.read_text(encoding="utf-8")


def _section_010(text: str) -> str:
    m = re.search(r"^## \[0\.1\.0\].*$", text, flags=re.MULTILINE)
    assert m, "missing ## [0.1.0] section"
    start = m.start()
    nxt = re.search(r"^## \[", text[m.end() :], flags=re.MULTILINE)
    end = m.end() + nxt.start() if nxt else len(text)
    return text[start:end]


def test_changelog_exists() -> None:
    assert CHANGELOG.is_file()


def test_v010_section_has_remain_summary() -> None:
    section = _section_010(_read())
    assert SECTION_MARKER in section
    missing = [p for p in REQUIRED_PHRASES if p not in section]
    assert missing == [], f"missing Remain phrases in [0.1.0]: {missing}"


def test_remain_covers_required_wires() -> None:
    section = _section_010(_read())
    idx = section.find(SECTION_MARKER)
    assert idx >= 0
    chunk = section[idx:]
    for token in (
        "file.new",
        "file.save",
        "file.quit",
        "ports",
        "arch",
        "work.tags",
        "Live CLI",
        "Live MCP",
        "listen_get_projection",
    ):
        assert token in chunk, f"Remain summary missing {token!r}"


def test_no_major_bump_or_tag_claim() -> None:
    section = _section_010(_read())
    chunk = section[section.find(SECTION_MARKER) :]
    assert "no MAJOR bump" in chunk or "不做 bump MAJOR" in chunk or "no MAJOR" in chunk
    assert "no git tag" in chunk.lower() or "git tag" in chunk.lower()
    # Must not claim tag was applied as done.
    for bad in ("已 git tag", "已打 tag", "tag applied", "git tag created"):
        if bad.lower() in chunk.lower():
            line = next(
                (ln for ln in chunk.splitlines() if bad.lower() in ln.lower()),
                bad,
            )
            ban = any(
                k in line
                for k in ("not", "NOT", "不得", "禁止", "optional", "optional", "不", "Anti-forge")
            )
            assert ban, f"forged tag claim: {line!r}"


def test_signing_still_not_run() -> None:
    section = _section_010(_read())
    assert "Signing" in section or "簽章" in section or "signing" in section.lower()
    assert "NOT RUN" in section
    chunk = section[section.find(SECTION_MARKER) :]
    assert "NOT RUN" in chunk
    assert "Signing remains **NOT RUN**" in chunk or "signing remains **NOT RUN**" in chunk.lower()


def test_anti_forge_no_signed_tag_ga() -> None:
    section = _section_010(_read())
    chunk = section[section.find(SECTION_MARKER) :]
    assert "Anti-forge" in chunk
    for bad in FORBIDDEN_AFFIRMATIVE:
        for m in re.finditer(re.escape(bad), chunk, flags=re.IGNORECASE):
            line_start = chunk.rfind("\n", 0, m.start()) + 1
            line_end = chunk.find("\n", m.end())
            if line_end < 0:
                line_end = len(chunk)
            line = chunk[line_start:line_end]
            ban_ctx = any(
                k in line
                for k in (
                    "禁止",
                    "不得",
                    "not",
                    "NOT",
                    "does **not**",
                    "does not",
                    "Anti-forge",
                    "≠",
                    "不是",
                    "false",
                    "Forbidden",
                )
            )
            assert ban_ctx, f"forged signed/tag/GA claim without ban context: {line!r}"
