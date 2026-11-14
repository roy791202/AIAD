"""TDD — Scene pack .ess (XML) = work + architecture + design in one document."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
FIXDIR = ROOT / "fixtures" / "sgenaxis-scene"
ESS = FIXDIR / "sample.ess"


def test_scene_ess_ui_and_codec_hooks():
    html = HTML.read_text(encoding="utf-8")
    assert 'data-cmd="scene.saveXml"' in html
    assert 'data-cmd="scene.openXml"' in html
    assert ".ess" in html
    assert 'id="toolbar-scene-open"' in html
    assert 'id="toolbar-scene-save"' in html
    js = JS.read_text(encoding="utf-8")
    assert "sceneDocToSgsXml" in js
    assert "sceneDocFromSgsXml" in js
    assert "applySceneSgsXml" in js
    assert "saveSceneSgsToProject" in js
    assert "loadSceneSgsFromProject" in js
    assert "SCENE_SGS_REL" in js
    assert "scene/default.ess" in js
    assert 'format="eluslot.ess"' in js or "eluslot.ess" in js
    assert 'cmd === "scene.saveXml"' in js
    assert 'cmd === "scene.openXml"' in js


def test_sample_ess_fixture_is_xml_scene():
    assert ESS.is_file()
    raw = ESS.read_text(encoding="utf-8")
    assert "<eluslotScene" in raw
    assert 'format="eluslot.ess"' in raw
    assert 'encoding="xml"' in raw
    assert "<work" in raw
    assert "<architecture" in raw
    assert "<eluslotArch" in raw
    assert "<design" in raw
    root = ET.fromstring(raw)
    assert re.sub(r"\{.*\}", "", root.tag) == "eluslotScene"
    assert root.attrib.get("format") == "eluslot.ess"
    work = root.find("work")
    arch = root.find("architecture")
    design = root.find("design")
    assert work is not None
    assert arch is not None
    assert design is not None
    assert arch.find("eluslotArch") is not None
    assert design.find("nodes") is not None
    board = work.find("board")
    assert board is not None
    assert board.find("task") is not None
