"""TDD — PD-UIDESIGNER-EDIT-P1 (geometry + delete + behavior on both surfaces)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "apps" / "sgenaxis-desktop" / "ui" / "index.html"
JS = ROOT / "apps" / "sgenaxis-desktop" / "ui" / "app.js"
CSS = ROOT / "apps" / "sgenaxis-desktop" / "ui" / "styles.css"
WB = ROOT / "git_workbench_interactive.html"
FIXTURE = ROOT / "fixtures" / "sgenaxis-design" / "sample.sgendesign"
DESKTOP = ROOT / "apps" / "sgenaxis-desktop"


def test_product_has_xy_delete_and_absolute_canvas():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert 'id="desX"' in html and 'id="desY"' in html
    assert 'data-cmd="uidesign.delete"' in html
    assert "deleteSelectedDesignNode" in js
    assert "applyDesignSnap" in js
    assert "desX" in js and "props.x" in js
    assert "position: absolute" in css or "position:absolute" in css.replace(" ", "")
    assert ".design-node" in css


def test_workbench_has_dynamic_create_delete_geometry():
    wb = WB.read_text(encoding="utf-8")
    assert "createPaletteNode" in wb
    assert "deleteSelectedNode" in wb
    assert "btnDesignDelete" in wb
    assert "applySnapToEntry" in wb or "SNAP_PX" in wb
    assert "desBehavior" in wb
    assert "desBddHint" in wb
    assert "designNodesHost" in wb
    assert "Form 根節點不可刪除" in wb


def test_fixture_has_xy_geometry():
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    kids = [n for n in doc["nodes"] if n.get("parentId")]
    assert kids, "need child nodes"
    for n in kids:
        assert "x" in n["props"] and "y" in n["props"]
        assert "w" in n["props"] and "h" in n["props"]


def test_host_uidesign_geom_preview():
    r = subprocess.run(
        [
            "cargo",
            "test",
            "-p",
            "sgenaxis-host",
            "preview_includes_geometry",
            "--",
            "--nocapture",
        ],
        cwd=str(DESKTOP),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (r.stdout or "") + (r.stderr or "")
    assert r.returncode == 0, out
