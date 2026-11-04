# -*- coding: utf-8 -*-
"""PD-UIDESIGN-SPEC-01 — ui-spec.json §5.3 / Workbench alignment fields."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "docs" / "ui-design" / "ui-spec.json"

ALLOWED_IMPL = frozenset(
    {"IMPLEMENTED", "PARTIAL", "MERGED", "OUT_OF_SCOPE_V01"}
)
WORKBENCH_VIEWS = (
    "viewTaskBoard",
    "viewAgentDispatch",
    "viewGitWorkspace",
    "viewRelease",
    "viewArchDag",
    "viewUiDesign",
)


def _load() -> dict:
    assert SPEC_PATH.is_file(), f"missing {SPEC_PATH}"
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def test_structure_14_pages_8_dialogs() -> None:
    spec = _load()
    assert len(spec["pages"]) == 14
    assert len(spec["dialogs"]) == 8
    assert len({p["id"] for p in spec["pages"]}) == 14
    assert {p["id"] for p in spec["pages"]} == {
        f"UI-{i:02d}" for i in range(1, 15)
    }


def test_metadata_ssot_and_gaps() -> None:
    meta = _load()["metadata"]
    assert meta.get("ia_ssot") == "git_workbench_interactive.html"
    assert meta.get("mock_as_product_pass") is False
    assert meta.get("product_test_results") == "NOT RUN"
    assert meta.get("product_implementation") == "PARTIAL"
    views = meta.get("workbench_main_views") or []
    assert list(views) == list(WORKBENCH_VIEWS)
    gaps = meta.get("alignment_gaps") or {}
    wb_gap = gaps.get("workbench_view_without_ui_page") or []
    assert any(g.get("workbench_view") == "viewUiDesign" for g in wb_gap)
    desk_gap = gaps.get("desktop_panel_without_ui_page") or []
    panels = {g.get("product_panel") for g in desk_gap}
    assert "ports" in panels
    assert "listen" in panels
    note = meta.get("image_note") or ""
    assert "mock" in note.lower() or "示意" in note
    assert "PASS" in note


def test_each_page_has_implementation_mapping() -> None:
    spec = _load()
    mapped_views = set()
    for page in spec["pages"]:
        pid = page["id"]
        impl = page.get("implementation")
        assert impl in ALLOWED_IMPL, f"{pid} implementation={impl!r}"
        assert "product_panel" in page, f"{pid} missing product_panel"
        assert "workbench_view" in page, f"{pid} missing workbench_view"
        assert "implementation_note" in page and page["implementation_note"]
        assert page.get("verification") == "NOT RUN", (
            f"{pid} must not treat design mock as product verification PASS"
        )
        wv = page.get("workbench_view")
        if wv is not None:
            assert wv in WORKBENCH_VIEWS, f"{pid} unknown workbench_view={wv!r}"
            mapped_views.add(wv)
        pp = page.get("product_panel")
        if pp is not None:
            assert isinstance(pp, str) and pp
    # Core §5.3 / Workbench main path pages map to these views
    for required in (
        "viewTaskBoard",
        "viewAgentDispatch",
        "viewGitWorkspace",
        "viewRelease",
        "viewArchDag",
    ):
        assert required in mapped_views, f"no page maps to {required}"
    # viewUiDesign has no UI-xx page by design (documented in metadata)
    assert "viewUiDesign" not in mapped_views


def test_main_path_panels_referenced() -> None:
    """§5.3 primary surfaces appear via product_panel on at least one page."""
    panels = {p.get("product_panel") for p in _load()["pages"]}
    for required in ("board", "agent", "git", "arch", "deploy", "settings"):
        assert required in panels, f"missing product_panel mapping for {required}"


def test_dialogs_unchanged_count_and_ids() -> None:
    dialogs = _load()["dialogs"]
    assert len(dialogs) == 8
    assert {d["id"] for d in dialogs} == {f"DLG-{i:02d}" for i in range(1, 9)}
    page_ids = {p["id"] for p in _load()["pages"]}
    for d in dialogs:
        assert set(d["pages"]) <= page_ids
