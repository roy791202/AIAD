"""TDD-PD-REMAIN-ARCH-UI-01 — 架構圖面板 vs BDD-PD-REMAIN-ARCH-UI-01.

Asserts arch panel refresh wires through arch_get_projection Command,
shows empty／NOT RUN without IPC, and never embeds a static fake as live.
Pairs with dispatch unit test arch_ui_command_projects_modules_and_deps.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
CSS = UI / "styles.css"
DISPATCH = (
    ROOT
    / "apps"
    / "sgenaxis-desktop"
    / "src-tauri"
    / "src"
    / "dispatch.rs"
)
LIB = ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "src" / "lib.rs"
CMDS = ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "src" / "commands.rs"


def test_arch_ui_assets_exist():
    for path in (HTML, JS, CSS):
        assert path.is_file(), f"missing: {path}"


def test_panel_arch_structure():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="panel-arch"' in html
    assert 'data-panel="arch"' in html
    assert 'id="arch-toolbar"' in html or 'class="arch-toolbar"' in html
    assert 'id="archStage"' in html or 'id="archNodes"' in html
    assert 'data-cmd="arch.refresh"' in html
    # Empty edge SVG scaffold OK；禁硬編碼模組節點冒充 live 圖。
    arch_start = html.find('id="panel-arch"')
    arch_end = html.find("</section>", arch_start)
    assert arch_start != -1 and arch_end != -1
    arch_html = html[arch_start:arch_end]
    assert 'data-module="' not in arch_html
    assert 'id="archStage"' in arch_html
    # 禁假 live 語意在 JS（面板已精簡說明文字）
    js = JS.read_text(encoding="utf-8")
    assert "假圖" in js or "冒充" in js or "live=false" in js


def test_sidebar_nav_arch_present():
    html = HTML.read_text(encoding="utf-8")
    # Primary Diagram tab lives on the full-width top view-tabs strip
    rail = html.find('id="side-rail"')
    body = html.find('id="shell-body"')
    assert rail != -1 and body != -1 and rail < body
    tabs = html[html.rfind("<", 0, rail) : body]
    assert 'id="nav-arch"' in tabs
    assert 'data-panel="arch"' in tabs


def test_js_wires_arch_command_not_static_live():
    js = JS.read_text(encoding="utf-8")
    assert 'invoke("arch_get_projection")' in js or 'invoke("arch_get_projection"' in js
    assert "cmdArchRefresh" in js
    assert 'cmd === "arch.refresh"' in js
    assert "renderArchProjection" in js
    assert "showArchEmpty" in js
    assert "NOT RUN" in js
    assert "live" in js
    # Must not hard-code a fake live module graph in UI as success path.
    assert "FAKE_LIVE_ARCH" not in js
    assert "/demo/arch" not in js
    for banned in (
        "child_process",
        "require(",
        "Deno.run",
    ):
        assert banned not in js, f"UI must not use {banned}"


def test_css_arch_layout():
    css = CSS.read_text(encoding="utf-8")
    assert ".arch-toolbar" in css
    assert ".arch-stage" in css or ".arch-canvas-shell" in css


def test_tauri_registers_arch_get_projection():
    lib = LIB.read_text(encoding="utf-8")
    assert "commands::arch_get_projection" in lib
    cmds = CMDS.read_text(encoding="utf-8")
    assert "pub fn arch_get_projection" in cmds


def test_dispatch_hosts_arch_projection():
    src = DISPATCH.read_text(encoding="utf-8")
    assert "arch_get_projection" in src
    assert "arch_ui_command_projects_modules_and_deps" in src
    assert "dispatch_host.arch_get_projection" in src
