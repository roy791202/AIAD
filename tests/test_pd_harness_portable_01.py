"""PD-HARNESS-PORTABLE-01 — portable launcher artifacts exist; no MSI required."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H = ROOT / "tools" / "harness" / "portable"


def test_portable_files_exist():
    for name in ("serve.py", "run.ps1", "README.md", "mock_tauri_bridge.js"):
        assert (H / name).is_file(), name


def test_readme_documents_no_msi_and_ports():
    text = (H / "README.md").read_text(encoding="utf-8")
    assert "MSI" in text or "msiexec" in text.lower()
    assert "28790" in text
    assert "8788" in text  # forbidden port called out
    assert "workbench" in text.lower()


def test_serve_defaults_avoid_board_and_8788():
    src = (H / "serve.py").read_text(encoding="utf-8")
    assert "28790" in src
    assert "8788" in src
    assert "ThreadingHTTPServer" in src or "HTTPServer" in src


def test_ui_and_workbench_targets_exist():
    assert (ROOT / "apps" / "sgenaxis-desktop" / "ui" / "index.html").is_file()
    assert (ROOT / "git_workbench_interactive.html").is_file()
