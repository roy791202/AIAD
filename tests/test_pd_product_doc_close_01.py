# -*- coding: utf-8 -*-
"""PD-PRODUCT-DOC-CLOSE-01 — assert Rel-Freeze close phrases in PRODUCT-DEVELOPMENT."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_MD = ROOT / "docs" / "PRODUCT-DEVELOPMENT.md"
DOC_HTML = ROOT / "docs" / "PRODUCT-DEVELOPMENT.html"

REQUIRED_PHRASES = (
    "BDD-PD-PRODUCT-DOC-CLOSE-01",
    "PD-PRODUCT-DOC-CLOSE-01",
    "Rel-Freeze",
    "Go-with-PARTIAL",
    "DCC",
    "SSH",
    "商店",
    "另案",
    "禁止暗示完整跨平台發行已完成",
)

# Affirmative completion sentences that must NOT appear (ban wording is OK).
FORBIDDEN_AFFIRMATIVE = (
    "已完成完整跨平台發行",
    "完整跨平台發行已完成。",
    "正式商店發布已完成",
    "三平台已發行完成",
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_product_doc_md_exists() -> None:
    assert DOC_MD.is_file()


def test_product_doc_html_exists() -> None:
    assert DOC_HTML.is_file()


def test_md_required_phrases() -> None:
    text = _read(DOC_MD)
    for phrase in REQUIRED_PHRASES:
        assert phrase in text, f"expected phrase {phrase!r} in PRODUCT-DEVELOPMENT.md"


def test_html_required_phrases() -> None:
    text = _read(DOC_HTML)
    for phrase in REQUIRED_PHRASES:
        assert phrase in text, f"expected phrase {phrase!r} in PRODUCT-DEVELOPMENT.html"


def test_md_changelog_and_paths_sections() -> None:
    text = _read(DOC_MD)
    assert "## 9. 相關路徑" in text
    assert "## 10. 變更紀錄" in text
    assert "reports/gonogo-v0.1.0-" in text
    assert "milestone-validation-v0.1.md" in text


def test_forbids_full_cross_platform_claim() -> None:
    """Ban wording required; no affirmative full cross-platform / store-done claim."""
    for path in (DOC_MD, DOC_HTML):
        blob = _read(path)
        assert "禁止暗示完整跨平台發行已完成" in blob
        assert "另案" in blob
        assert "Go-with-PARTIAL" in blob
        assert (
            "非正式商店發布" in blob
            or "≠ 正式商店發布" in blob
            or "不是**正式商店發布" in blob
        )
        for bad in FORBIDDEN_AFFIRMATIVE:
            assert bad not in blob, f"{path.name} must not claim {bad!r}"
