# -*- coding: utf-8 -*-
"""Seed default verify data for installed / local SGenAxis.

Writes:
  1) fixtures/sgenaxis-verify-default/PROJECT-BOARD.html (if missing, keep)
  2) %LOCALAPPDATA%\\sgenaxis\\host-settings.json  (and SGenAxis twin)
     binding project_root + board_path to the fixture.

  python tools/verify/seed_default_data.py
  python tools/verify/seed_default_data.py --launch

假資料 ≠ 產品 PASS。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "fixtures" / "sgenaxis-verify-default"
BOARD = FIXTURE_DIR / "PROJECT-BOARD.html"
README = FIXTURE_DIR / "README.md"


def local_appdata() -> Path:
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(local)


def write_host_settings(path: Path, project_root: str, board_path: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    prev: dict = {}
    if path.is_file():
        try:
            prev = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = {}
    agent = prev.get("agent") or {
        "cli": {
            "selected": "Claude",
            "claude": {"path": "claude", "args": ["--print"]},
            "cursor_agent": {"path": "cursor-agent", "args": []},
            "codex": {"path": "codex", "args": ["exec"]},
            "antigravity": {"path": "antigravity", "args": []},
            "live_approved": False,
        },
        "mcp": {
            "transport": "Stdio",
            "server_name": "local-agent",
            "endpoint": "stdio://local-agent",
            "approved_tools": ["list_tools"],
            "secret_token": None,
        },
    }
    payload = {
        "version": 4,
        "ui_theme": prev.get("ui_theme") or "system",
        "locale": prev.get("locale") or "zh-Hant",
        "project_root": project_root,
        "board_path": board_path,
        "agent": agent,
        "agent_active": False,
        "verify_default_seed": True,
        "product_pass": False,
        "note": "seeded by tools/verify/seed_default_data.py — fake≠product PASS",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", path)


def ensure_readme() -> None:
    if README.is_file():
        return
    README.write_text(
        "# SGenAxis 驗證預設專案\n\n"
        "假資料看板，供安裝版／`tauri dev` 功能對照。\n\n"
        "**假資料 ≠ 產品證據 ≠ 正式 PASS。**\n\n"
        "```powershell\n"
        "python tools/verify/seed_default_data.py --launch\n"
        "```\n"
        "然後在 App 內按「載入本機看板」。\n",
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--project-root",
        default=str(FIXTURE_DIR.resolve()),
        help="project_root to bind (default: fixtures/sgenaxis-verify-default)",
    )
    ap.add_argument(
        "--board",
        default="",
        help="board_path absolute or relative (default: PROJECT-BOARD.html under fixture)",
    )
    ap.add_argument("--launch", action="store_true", help="start installed SGenAxis.exe")
    args = ap.parse_args()

    if not BOARD.is_file():
        print("missing fixture board:", BOARD, file=sys.stderr)
        return 2
    ensure_readme()

    project_root = str(Path(args.project_root).resolve())
    board_path = args.board.strip() or str(BOARD.resolve())

    local = local_appdata()
    targets = [
        local / "sgenaxis" / "host-settings.json",
        local / "SGenAxis" / "host-settings.json",
    ]
    for t in targets:
        write_host_settings(t, project_root, board_path)

    print("project_root=", project_root)
    print("board_path=", board_path)
    print("tasks in fixture: open PROJECT-BOARD.html #board-snapshot")

    if args.launch:
        exe = Path(r"C:\Program Files\SGenAxis\SGenAxis.exe")
        if not exe.is_file():
            print("installed exe missing:", exe, file=sys.stderr)
            return 3
        subprocess.Popen([str(exe)], cwd=str(exe.parent))
        print("launched", exe)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
