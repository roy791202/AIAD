"""TDD — Scene save/load is project-scoped; dirty prompts on project switch."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HTML = UI / "index.html"
JS = UI / "app.js"
HOST_IPC = ROOT / "apps" / "sgenaxis-desktop" / "crates" / "sgenaxis-host" / "src" / "ipc.rs"
SCENE_DOC = (
    ROOT / "apps" / "sgenaxis-desktop" / "crates" / "sgenaxis-host" / "src" / "scene_doc.rs"
)
PERM = ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "permissions" / "dispatch.toml"


def test_scene_ipc_allowlisted_and_under_scene_dir():
    ipc = HOST_IPC.read_text(encoding="utf-8")
    assert 'SceneSave => "scene_save"' in ipc or '"scene_save"' in ipc
    assert 'SceneLoad => "scene_load"' in ipc or '"scene_load"' in ipc
    doc = SCENE_DOC.read_text(encoding="utf-8")
    assert 'DEFAULT_SGS_REL: &str = "scene/default.ess"' in doc
    assert "scene path must be under scene/" in doc
    perm = PERM.read_text(encoding="utf-8")
    assert "allow-scene-save" in perm
    assert "allow-scene-load" in perm
    assert '"scene_save"' in perm or "scene_save" in perm


def test_ui_project_scoped_scene_and_dirty_prompt():
    js = JS.read_text(encoding="utf-8")
    assert "SCENE_SGS_REL" in js
    assert "scene/default.ess" in js
    assert "scene_save" in js
    assert "scene_load" in js
    assert "confirmLeaveSceneIfDirty" in js
    assert "markSceneDirty" in js
    assert "clearSceneDirty" in js
    assert "saveSceneSgsToProject" in js
    assert "loadSceneSgsFromProject" in js
    assert "tryLoadProjectSceneQuiet" in js
    assert "saveSceneBundleToProject" in js
    # 不再用任意路徑 file input 存場景
    html = HTML.read_text(encoding="utf-8")
    assert 'id="sgb-file-input"' not in html
    assert 'id="sgs-file-input"' not in html
    assert "儲存場景到專案" in html or "scene.saveXml" in html
    assert 'id="status-scene-dirty"' in html
