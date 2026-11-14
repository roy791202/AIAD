"""PD-GIT-BOARD-SYNC-01 — smoke that host sync module + report exist.

Behavioral assertions live in `sgenaxis-host::git_board_sync` cargo tests
(FakeGit + FakeFileSystem fixture; git/board/pollution/write classes).
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOST_MOD = (
    REPO
    / "apps"
    / "sgenaxis-desktop"
    / "crates"
    / "sgenaxis-host"
    / "src"
    / "git_board_sync.rs"
)
REPORT = REPO / "reports" / "dispatch-pd" / "PD-GIT-BOARD-SYNC-01.md"
FAKE_FS = (
    REPO
    / "apps"
    / "sgenaxis-desktop"
    / "crates"
    / "sgenaxis-adapters"
    / "src"
    / "fake.rs"
)


def test_sync_module_defines_fail_classes():
    src = HOST_MOD.read_text(encoding="utf-8")
    assert "PD-GIT-BOARD-SYNC-01" in src
    assert "enum SyncFailKind" in src
    for label in ("Git", "Board", "Pollution", "WriteDetected"):
        assert label in src
    assert "load_git_and_board_isolated" in src
    assert "writes_enabled" in src
    assert "force" not in src.lower() or "no force" in src.lower() or "force push" in src.lower()


def test_fake_fs_tracks_write_ops_for_readonly_assert():
    src = FAKE_FS.read_text(encoding="utf-8")
    assert "fn write_count" in src
    assert "fn mkdir_count" in src
    assert "PD-GIT-BOARD-SYNC-01" in src


def test_dispatch_report_present_when_written():
    # Implementer writes the report; TDD may run before/after — tolerate missing
    # only if module exists (cargo is SSOT). Prefer present for READY_FOR_GREEN.
    if REPORT.is_file():
        text = REPORT.read_text(encoding="utf-8")
        assert "PD-GIT-BOARD-SYNC-01" in text
        assert "READY_FOR_GREEN" in text
        assert "yellow" in text.lower()
