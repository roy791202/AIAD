# -*- coding: utf-8 -*-
"""PD-UIDESIGN-INDEX-01 — index.html alignment banner / page pills ≡ ui-spec."""
from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "ui-design"
INDEX = OUT / "index.html"
SPEC = OUT / "ui-spec.json"


class Doc(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.embedded = ""
        self.mode = None
        self.ids: list[str] = []
        self.attrs_by_id: dict[str, dict[str, str]] = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
            self.attrs_by_id[a["id"]] = a
        if tag == "script":
            self.mode = "json" if a.get("type") == "application/json" else "js"

    def handle_endtag(self, tag):
        if tag == "script":
            self.mode = None

    def handle_data(self, data):
        if self.mode == "json":
            self.embedded += data


def _load_index() -> tuple[str, Doc, dict]:
    assert INDEX.is_file(), f"missing {INDEX}"
    assert SPEC.is_file(), f"missing {SPEC}"
    text = INDEX.read_text(encoding="utf-8")
    doc = Doc()
    doc.feed(text)
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    return text, doc, spec


def test_embedded_ui_spec_equals_file() -> None:
    _, doc, spec = _load_index()
    assert json.loads(doc.embedded) == spec


def test_align_banner_present() -> None:
    text, doc, _ = _load_index()
    assert "align-banner" in doc.ids
    assert "align-banner-pills" in doc.ids
    assert "align-banner-detail" in doc.ids
    assert "對齊狀態" in text
    assert "Workbench" in text or "IA SSOT" in text


def test_page_status_pill_targets() -> None:
    text, _, spec = _load_index()
    for page in spec["pages"]:
        pid = page["id"]
        assert f'data-page-id="{pid}"' in text
        assert "page-status-pills" in text
    assert text.count("page-status-pills") >= 14


def test_hydrate_reads_implementation_fields() -> None:
    text, _, spec = _load_index()
    assert "align-banner-pills" in text
    assert "product_implementation" in text
    assert "workbench_view" in text
    assert "product_panel" in text
    # Must not claim product PASS from design mock.
    assert "非產品 PASS" in text or "mock" in text.lower()
    meta = spec["metadata"]
    assert meta.get("product_test_results") == "NOT RUN"
    assert meta.get("mock_as_product_pass") is False


def test_bdd_id_trace() -> None:
    # Card BDD id lives in report; index must stay consistent with SPEC alignment.
    _, _, spec = _load_index()
    assert "ia_ssot" in spec["metadata"]
    assert spec["metadata"]["ia_ssot"] == "git_workbench_interactive.html"
