"""TDD — Scene pack .sgb (bin) = default.es + default.esml + default.esui."""

from __future__ import annotations

import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
FIXDIR = ROOT / "fixtures" / "sgenaxis-scene"
SGB = FIXDIR / "sample.sgb"


def _pack_sgb(entries: list[tuple[str, bytes]]) -> bytes:
    out = bytearray(b"SGB1")
    out += struct.pack("<H", len(entries))
    for name, data in entries:
        nb = name.encode("utf-8")
        out += struct.pack("<H", len(nb))
        out += nb
        out += struct.pack("<I", len(data))
        out += data
    return bytes(out)


def _unpack_sgb(blob: bytes) -> dict[str, str]:
    assert blob[:4] == b"SGB1"
    (count,) = struct.unpack_from("<H", blob, 4)
    o = 6
    out: dict[str, str] = {}
    for _ in range(count):
        (nlen,) = struct.unpack_from("<H", blob, o)
        o += 2
        name = blob[o : o + nlen].decode("utf-8")
        o += nlen
        (dlen,) = struct.unpack_from("<I", blob, o)
        o += 4
        out[name] = blob[o : o + dlen].decode("utf-8")
        o += dlen
    return out


def test_scene_sgb_ui_and_codec_hooks():
    html = HTML.read_text(encoding="utf-8")
    assert 'data-cmd="scene.save"' in html
    assert 'data-cmd="scene.open"' in html
    assert ".es＋.esml＋.esui" in html or ".es" in html
    js = JS.read_text(encoding="utf-8")
    assert "packSgbBinary" in js
    assert "unpackSgbBinary" in js
    assert "buildSceneSgbBytes" in js
    assert "applySceneSgbBytes" in js
    assert "saveSceneBundleToProject" in js
    assert "loadSceneBundleFromProject" in js
    assert 'SGB_ENTRY_WORK = "default.es"' in js
    assert 'SGB_ENTRY_ARCH = "default.esml"' in js
    assert 'SGB_ENTRY_DESIGN = "default.esui"' in js
    assert "scene/default.es" in js
    assert 'SGB_MAGIC = "SGB1"' in js or "SGB1" in js
    assert 'cmd === "scene.save"' in js
    assert 'cmd === "scene.open"' in js
    assert "eluslot.es" in js
    assert "eluslot.esui" in js


def test_sample_sgb_fixture_roundtrip():
    FIXDIR.mkdir(parents=True, exist_ok=True)
    work = {
        "format": "eluslot.es",
        "formatVersion": 1,
        "encoding": "json",
        "meta": {"boardFilter": "overview", "product_pass": False},
        "board": {"tasks": [], "active_run_id": None},
    }
    arch = """<?xml version="1.0" encoding="UTF-8"?>
<eluslotArch format="eluslot.esml" formatVersion="1">
  <meta formSize="1280x720" gridSize="8" product_pass="false" encoding="xml" />
  <nodes>
    <node id="n-api" name="API" kind="API" x="40" y="80" collapsed="false">
      <inputs><port id="n-api-in" label="request" /></inputs>
      <outputs><port id="n-api-out" label="response" /></outputs>
    </node>
  </nodes>
  <edges></edges>
</eluslotArch>
"""
    design = {
        "format": "eluslot.esui",
        "formatVersion": 1,
        "meta": {"title": "Sample", "encoding": "json"},
        "nodes": [
            {
                "id": "node-form-root",
                "type": "Form",
                "parentId": None,
                "props": {"name": "Form", "x": 0, "y": 0, "w": 800, "h": 600},
            }
        ],
        "selection": "node-form-root",
        "product_pass": False,
    }
    blob = _pack_sgb(
        [
            ("default.es", json.dumps(work, ensure_ascii=False).encode("utf-8")),
            ("default.esml", arch.encode("utf-8")),
            ("default.esui", json.dumps(design, ensure_ascii=False).encode("utf-8")),
        ]
    )
    SGB.write_bytes(blob)
    parsed = _unpack_sgb(SGB.read_bytes())
    assert set(parsed) == {"default.es", "default.esml", "default.esui"}
    assert json.loads(parsed["default.es"])["format"] == "eluslot.es"
    assert "<eluslotArch" in parsed["default.esml"]
    assert json.loads(parsed["default.esui"])["format"] == "eluslot.esui"


def test_arch_xml_default_filename_is_default_esml():
    js = JS.read_text(encoding="utf-8")
    assert 'ARCH_XML_DEFAULT_NAME = "default.esml"' in js
    html = HTML.read_text(encoding="utf-8")
    assert "default.esml" in html
