"""TDD — Arch DAG persistence SSOT is XML (.sgenarch.xml)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
FIXTURE = ROOT / "fixtures" / "sgenaxis-arch" / "sample.sgenarch.xml"


def test_arch_xml_codec_and_ui():
    js = JS.read_text(encoding="utf-8")
    assert "archDocToXml" in js
    assert "archDocFromXml" in js
    assert "sgenaxisArch" in js
    assert "encoding" in js and "xml" in js
    assert "downloadArchXml" in js
    assert "importArchXmlText" in js
    assert "default.sgml" in js or 'ARCH_XML_DEFAULT_NAME = "default.sgml"' in js
    # localStorage 以 XML 為主（非 JSON.stringify(archDoc)）
    assert "archDocToXml(archDoc)" in js
    assert "JSON.stringify(archDoc)" not in js
    assert "<modules>" in js or "modules>" in js
    assert "modules > module" in js
    assert 'archAttr("layerRef"' in js
    assert 'archAttr("moduleRef"' in js
    assert 'archAttr("order"' in js
    assert 'archAttr("uiLayerId"' in js
    assert 'archAttr("uiDefinitionRef"' in js
    assert 'archAttr("themeRef"' in js
    assert 'archAttr("direction"' in js
    html = HTML.read_text(encoding="utf-8")
    assert 'id="arch-save-xml"' in html
    assert 'id="arch-load-xml"' in html
    assert 'id="arch-xml-file"' in html
    assert 'id="arch-xml-path"' in html


def test_sample_sgenarch_xml_fixture():
    assert FIXTURE.is_file()
    raw = FIXTURE.read_text(encoding="utf-8")
    assert "<sgenaxisArch" in raw
    assert 'format="sgenaxis.arch"' in raw
    assert 'encoding="xml"' in raw
    assert 'kind="API"' in raw
    assert "<edge" in raw
    assert 'kind="Layer"' in raw
    assert "<modules>" in raw
    assert "<module" in raw
    assert 'slotId=' in raw
    assert "moduleId=" in raw
    assert "layerRef=" in raw or 'layerRef="' in raw
    assert "moduleRef=" in raw or 'moduleRef="' in raw
    assert 'kind="UI"' in raw
    assert "uiDefinitionRef=" in raw
    assert "uiLayerId=" in raw
