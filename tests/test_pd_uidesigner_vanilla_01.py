"""TDD — PRODUCT-UIDESIGNER-VANILLA cards (SHELL／FORMAT／BUILD／ASK).

概念 Qt Designer · 實作 Vanilla／Tauri · .sgendesign · Build 溝通預覽 · Ask Agent。
設計 ≠ 產品 PASS。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"
HOST_DOC = (
    ROOT
    / "apps"
    / "sgenaxis-desktop"
    / "crates"
    / "sgenaxis-host"
    / "src"
    / "uidesign_doc.rs"
)
CMDS = ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "src" / "commands.rs"
PERM = ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "permissions" / "dispatch.toml"
FIXTURE = ROOT / "fixtures" / "sgenaxis-design" / "sample.sgendesign"
DESKTOP = ROOT / "apps" / "sgenaxis-desktop"


def test_shell_stage_and_modes():
    """Shell IA: stage-only designer; Widget Box + props live outside the stage."""
    html = HTML.read_text(encoding="utf-8")
    assert 'id="panel-uidesign"' in html
    assert "designer-shell" in html or 'id="uidesign-designer"' in html
    assert "designer-stage" in html or 'id="designCanvas"' in html
    assert 'id="sec-uidesign-widgets"' in html
    assert 'id="inspector-design"' in html
    assert 'data-uidesign-mode="designer"' in html
    assert 'data-uidesign-mode="viewer"' in html
    # 面板標題／免責／設計包對照 chrome 已清除
    assert 'id="uidesign-disclaimer"' not in html
    assert "設計包對照" not in html
    assert 'data-cmd="uidesign.save"' in html
    assert 'data-cmd="uidesign.load"' in html
    assert 'data-cmd="uidesign.build"' in html
    assert 'data-cmd="uidesign.ask"' in html
    css = CSS.read_text(encoding="utf-8")
    assert ".designer-shell" in css
    assert "designer-shell--stage" in css or ".designer-shell--stage" in css


def test_format_fixture_and_commands():
    raw = FIXTURE.read_text(encoding="utf-8")
    doc = json.loads(raw)
    assert doc["format"] == "sgenaxis.design"
    assert doc["formatVersion"] == 1
    assert doc.get("product_pass") is False
    assert "meta" in doc and "nodes" in doc
    assert doc["meta"].get("targetStack") == "vanilla-tauri"
    assert any(n.get("type") for n in doc["nodes"])

    rs = HOST_DOC.read_text(encoding="utf-8")
    assert 'DESIGN_FORMAT: &str = "sgenaxis.design"' in rs
    assert "DESIGN_FORMAT_VERSION: u32 = 1" in rs
    assert "DEFAULT_REL_PATH" in rs
    assert "save_design_file" in rs
    assert "load_design_file" in rs
    assert "product_pass" in rs

    cmds = CMDS.read_text(encoding="utf-8")
    assert "uidesign_save_design" in cmds
    assert "uidesign_load_design" in cmds
    perm = PERM.read_text(encoding="utf-8")
    assert "allow-uidesign-save-design" in perm
    assert "allow-uidesign-load-design" in perm


def test_build_preview_contract_in_source():
    rs = HOST_DOC.read_text(encoding="utf-8")
    assert "PREVIEW_BANNER" in rs
    assert "溝通用" in rs
    assert "非正式 PASS" in rs or "非產品" in rs
    assert "build_preview_html" in rs
    assert "build_preview_file" in rs
    assert "product_pass=false" in rs
    cmds = CMDS.read_text(encoding="utf-8")
    assert "uidesign_build_preview" in cmds
    assert "product_pass: false" in cmds


def test_ask_agent_contract():
    rs = HOST_DOC.read_text(encoding="utf-8")
    assert "ask_agent_draft" in rs
    assert "設計草稿" in rs or "≠產品驗收 PASS" in rs
    cmds = CMDS.read_text(encoding="utf-8")
    assert "uidesign_ask_agent" in cmds
    assert "upsert_gray" in cmds
    js = JS.read_text(encoding="utf-8")
    assert 'invoke("uidesign_ask_agent"' in js
    assert "cmdUidesignAsk" in js
    assert "NOT RUN" in js


def test_js_design_doc_binding():
    js = JS.read_text(encoding="utf-8")
    assert "blankDesignDoc" in js
    assert 'format: "sgenaxis.design"' in js
    assert "formatVersion: 1" in js
    assert "product_pass: false" in js or "product_pass = false" in js
    assert 'invoke("uidesign_save_design"' in js
    assert 'invoke("uidesign_load_design"' in js
    assert 'invoke("uidesign_build_preview"' in js
    assert "wireDesignerUi" in js
    for banned in ("child_process", "require(", "Deno.run"):
        assert banned not in js


def test_host_uidesign_unit_tests_pass():
    r = subprocess.run(
        [
            "cargo",
            "test",
            "-p",
            "sgenaxis-host",
            "uidesign_doc",
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
    assert "7 passed" in out or "passed" in out
