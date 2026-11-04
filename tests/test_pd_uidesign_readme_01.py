# -*- coding: utf-8 -*-
"""PD-UIDESIGN-README-01 — README gap table asserts (Workbench-first)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "docs" / "ui-design" / "README.md"
WORKBENCH = ROOT / "git_workbench_interactive.html"

# Workbench view ids that must appear as primary-column anchors in the README.
WORKBENCH_VIEWS = (
    "viewAgentDispatch",
    "viewTaskBoard",
    "viewGitWorkspace",
    "viewRelease",
    "viewArchDag",
    "viewUiDesign",
)

# Desktop panel ids that must be annotated beside Workbench rows / OUT_OF_SCOPE rows.
DESKTOP_PANELS = (
    "agent",
    "board",
    "git",
    "deploy",
    "arch",
    "settings",
    "spec",
    "report",
    "listen",
    "ports",
)

UI_IDS = tuple(f"UI-{i:02d}" for i in range(1, 15))


def test_readme_exists() -> None:
    assert README.is_file(), f"missing {README}"


def test_readme_declares_workbench_ia_ssot() -> None:
    text = README.read_text(encoding="utf-8")
    assert "Workbench" in text
    assert "IA" in text and "SSOT" in text
    assert "git_workbench_interactive.html" in text
    assert "圖稿非證據" in text or "不是產品執行" in text or "非證據" in text


def test_readme_table_is_workbench_primary() -> None:
    text = README.read_text(encoding="utf-8")
    assert "Workbench" in text and ("主欄" in text or "為主欄" in text)
    for view_id in WORKBENCH_VIEWS:
        assert view_id in text, f"README must list Workbench view {view_id}"
        assert view_id in WORKBENCH.read_text(encoding="utf-8"), (
            f"Workbench HTML missing {view_id} — README/SSOT drift"
        )


def test_readme_annotates_ui_xx_and_desktop_panels() -> None:
    text = README.read_text(encoding="utf-8")
    for ui_id in UI_IDS:
        assert ui_id in text, f"README must annotate {ui_id}"
    for panel in DESKTOP_PANELS:
        assert panel in text, f"README must annotate desktop panel {panel}"


def test_readme_bdd_id() -> None:
    text = README.read_text(encoding="utf-8")
    assert "BDD-PD-UIDESIGN-README-01" in text
    assert "PD-UIDESIGN-README-01" in text or "UIDESIGN-README" in text
