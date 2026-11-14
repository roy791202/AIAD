# -*- coding: utf-8 -*-
"""PD-SHELL-AUDIT-01 — Workbench↔desktop gap checklist exists + priority tags + no false align-complete claim."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs" / "shell-audit-PD-SHELL-AUDIT-01.md"
REPORT = ROOT / "reports" / "dispatch-pd" / "PD-SHELL-AUDIT-01.md"
WB = ROOT / "git_workbench_interactive.html"
DESKTOP_UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"

REQUIRED_SECTIONS = (
    "殼區",
    "側欄",
    "六視圖",
    "密度",
    "缺項",
)

REQUIRED_PRIORITY_TAGS = ("Must", "Should", "Won't")

# Workbench six views (IA SSOT) — checklist must cite these ids.
WB_SIX_VIEWS = (
    "viewTaskBoard",
    "viewGitWorkspace",
    "viewArchDag",
    "viewUiDesign",
    "viewAgentDispatch",
    "viewRelease",
)

# Affirmative claims that would falsely imply MSI / install shell visual alignment is done.
# Keep distinct from required ban phrasing ("禁止暗示…業已完成").
FORBIDDEN_AFFIRMATIVE = (
    "MSI 已視覺對齊完成",
    "安裝版已視覺對齊完成",
    "視覺對齊已完成",
    "已視覺對齊完成",
    "aligned complete",
    "visually aligned complete",
    "MSI visual alignment complete",
    "shell visually aligned",
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_checklist_exists() -> None:
    assert CHECKLIST.is_file(), f"expected checklist at {CHECKLIST}"


def test_checklist_sections_and_ssot_paths() -> None:
    text = _read(CHECKLIST)
    for section in REQUIRED_SECTIONS:
        assert section in text, f"checklist missing section cue {section!r}"
    assert "git_workbench_interactive.html" in text
    assert "apps/sgenaxis-desktop/ui" in text
    assert "BDD-PD-SHELL-AUDIT-01" in text
    assert "v0.1" in text
    assert "IA SSOT" in text or "Workbench" in text


def test_must_should_wont_tags() -> None:
    text = _read(CHECKLIST)
    for tag in REQUIRED_PRIORITY_TAGS:
        assert tag in text, f"expected priority tag {tag!r}"
        # At least one markdown table cell or bold label usage
        assert re.search(rf"\*\*{re.escape(tag)}\*\*|\|\s*{re.escape(tag)}\s*\|", text), (
            f"tag {tag!r} should appear as labeled priority in checklist"
        )


def test_workbench_selectors_and_desktop_paths_cited() -> None:
    text = _read(CHECKLIST)
    for vid in WB_SIX_VIEWS:
        assert vid in text, f"checklist must cite Workbench view id #{vid}"
    assert "#appTitlebar" in text or ".desktop-menubar" in text
    assert "#secTasksStatus" in text or "secTasksStatus" in text
    assert "index.html" in text
    assert "styles.css" in text
    # Desktop panel anchors for present counterparts
    for panel in ("panel-board", "panel-agent", "panel-deploy", "panel-arch", "panel-git"):
        assert panel in text, f"checklist should cite desktop #{panel}"


def test_checkboxes_present() -> None:
    text = _read(CHECKLIST)
    assert "[ ]" in text, "expected unchecked markdown checkboxes for gap items"


def test_no_false_aligned_complete_claim() -> None:
    """Must not imply MSI / install visual alignment is already complete."""
    for path in (CHECKLIST, REPORT):
        if not path.is_file():
            continue
        blob = _read(path)
        if path == CHECKLIST:
            assert "禁止暗示" in blob
            assert "業已完成" in blob or "仍為未完成" in blob
            assert "明確聲明" in blob
        for bad in FORBIDDEN_AFFIRMATIVE:
            assert bad not in blob, f"{path.name} must not claim {bad!r}"


def test_ssot_and_desktop_sources_readable() -> None:
    """Sanity: allow-scoped sources exist so checklist citations are not vacuous."""
    assert WB.is_file()
    wb = _read(WB)
    for vid in WB_SIX_VIEWS:
        assert f'id="{vid}"' in wb
    assert (DESKTOP_UI / "index.html").is_file()
    assert (DESKTOP_UI / "styles.css").is_file()
    desktop = _read(DESKTOP_UI / "index.html")
    assert 'data-panel="board"' in desktop
    # Audit SSOT: Workbench six-view ids must remain in WB; desktop may lag or partially catch up.
    checklist = _read(CHECKLIST)
    assert "viewUiDesign" in checklist


def test_dispatch_report_ready_marker() -> None:
    text = _read(REPORT)
    assert "PD-SHELL-AUDIT-01" in text
    assert "READY_FOR_GREEN" in text
    assert "PASS" in text or "READY_FOR_GREEN" in text
    # Report must instruct parent not to self-green (ban wording OK; no "zone → green" claim).
    assert "不自改綠" in text or "zone 維持 yellow" in text or "NEVER zone=green" in text
    assert "→ green" not in text.lower()
    assert "zone → green" not in text
