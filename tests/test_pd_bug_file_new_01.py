"""PD-BUG-FILE-NEW-01 — 新增專案：prompt 名稱 + pick 父目錄 + create（非 save_file）。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_JS = ROOT / "apps" / "sgenaxis-desktop" / "ui" / "app.js"
COMMANDS = ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "src" / "commands.rs"
IPC = ROOT / "apps" / "sgenaxis-desktop" / "crates" / "sgenaxis-host" / "src" / "ipc.rs"
PROJECT_NEW = (
    ROOT / "apps" / "sgenaxis-desktop" / "crates" / "sgenaxis-host" / "src" / "project_new.rs"
)
PORTS_FS = ROOT / "apps" / "sgenaxis-desktop" / "crates" / "sgenaxis-ports" / "src" / "fs.rs"
HOST_TOML = ROOT / "apps" / "sgenaxis-desktop" / "src-tauri" / "permissions" / "host.toml"


def test_ui_cmd_new_project_uses_create_not_save_dialog():
    js = UI_JS.read_text(encoding="utf-8")
    assert "host_create_project_directory" in js
    assert "host_pick_project_directory" in js
    # Primary new-project path must not invoke legacy save dialog.
    assert "async function cmdNewProject" in js
    idx = js.index("async function cmdNewProject")
    body = js[idx : idx + 1800]
    assert "host_create_project_directory" in body
    assert 'invoke("host_new_project_directory")' not in body
    assert "window.prompt" in body
    assert "無 IPC" in body or "NOT RUN" in body


def test_command_and_allowlist_registered():
    cmds = COMMANDS.read_text(encoding="utf-8")
    assert "fn host_create_project_directory" in cmds
    assert "CreateProjectDirectoryArgs" in cmds
    ipc = IPC.read_text(encoding="utf-8")
    assert "HostCreateProjectDirectory" in ipc
    assert "host_create_project_directory" in ipc
    toml = HOST_TOML.read_text(encoding="utf-8")
    assert "allow-host-create-project-directory" in toml
    assert "host_create_project_directory" in toml


def test_port_remove_file_and_residue_handling():
    ports = PORTS_FS.read_text(encoding="utf-8")
    assert "fn remove_file" in ports
    assert "fn is_file" in ports
    pn = PROJECT_NEW.read_text(encoding="utf-8")
    assert "create_new_project_under" in pn
    assert "remove_file" in pn
    assert "create_replaces_existing_file_residue" in pn


def test_no_ui_direct_fs_writes_in_cmd_new():
    js = UI_JS.read_text(encoding="utf-8")
    idx = js.index("async function cmdNewProject")
    body = js[idx : idx + 1800]
    for forbidden in ("fs.write", "writeFile", "mkdirSync", "createWriteStream"):
        assert forbidden not in body
