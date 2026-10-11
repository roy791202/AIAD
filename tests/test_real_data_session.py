"""Session rules for read-only Git/release data and the simulated/real launch switch."""

from datetime import datetime, timedelta

import pytest

from sgenaxis.core.board import WorkItem
from sgenaxis.core.in_memory import (
    DryRunLauncher,
    InMemoryProjectBoards,
    StaticFileProbe,
    StaticGitReader,
    StaticReleases,
)
from sgenaxis.core.ports import FileInfo, GitChange, GitSnapshot
from sgenaxis.core.release import Artifact, Release
from sgenaxis.core.session import WorkbenchSession

SANDBOX = r"D:\AIAD\_sandbox"
WHEN = datetime(2026, 10, 11, 12, 0)


def _session(**kwargs) -> WorkbenchSession:
    kwargs.setdefault("boards", InMemoryProjectBoards())
    return WorkbenchSession(**kwargs)


def _info(path: str, size: int = 10, is_dir: bool = False) -> FileInfo:
    return FileInfo(path, path.rsplit("\\", 1)[-1], is_dir, size, WHEN)


# ── Git page ─────────────────────────────────────────────


def test_demo_board_never_reads_git():
    reader = StaticGitReader()
    snapshot, message = _session(git_reader=reader).git_status()
    assert snapshot is None
    assert "未開啟專案" in message
    assert reader.asked == []


def test_folder_not_created_by_sgenaxis_is_not_read():
    reader = StaticGitReader({r"D:\AutoCode\AutoRig_Core": GitSnapshot("main", ("main",), ())})
    session = _session(git_reader=reader)
    session.open_named("AutoRig_Core")
    snapshot, message = session.git_status()
    assert snapshot is None
    assert "不是 SGenAxis 建立的專案" in message
    assert reader.asked == []


def test_created_project_shows_its_own_git_snapshot():
    path = SANDBOX + r"\agent-test"
    snap = GitSnapshot("main", ("main", "dev"), (GitChange("a.txt", "M", False),), ahead=1)
    reader = StaticGitReader({path: snap})
    session = _session(git_reader=reader)
    session.create_project("agent-test", SANDBOX)
    assert session.git_status() == (snap, "")
    assert reader.asked == [path]


def test_created_project_without_its_own_repo_reports_why():
    session = _session(git_reader=StaticGitReader())
    session.create_project("agent-test", SANDBOX)
    snapshot, message = session.git_status()
    assert snapshot is None
    assert "沒有自己的 .git" in message


def test_no_git_reader_means_git_is_not_connected():
    session = _session()
    session.create_project("agent-test", SANDBOX)
    assert session.git_status() == (None, "Git 讀取未接上")


# ── release page ─────────────────────────────────────────


RELEASE = Release(
    "v1.0.0",
    "1.0.0",
    "portable",
    "2026-10-10T14:49:00+08:00",
    "2026-10-10T15:00:00+08:00",
    "agent",
    artifacts=(
        Artifact("ZIP", r"D:\out\app.zip", False, "2026-10-10T15:00:00+08:00"),
        Artifact("安裝程式", r"D:\out\setup.exe", True, "2026-10-10T15:00:00+08:00"),
    ),
)


def test_artifacts_are_checked_live_when_a_probe_is_connected():
    probe = StaticFileProbe([_info(r"D:\out\app.zip", 2048)])
    checks = _session(file_probe=probe).artifact_checks(RELEASE)
    assert [(check.label, check.exists, check.size, check.live) for check in checks] == [
        ("ZIP", True, 2048, True),
        ("安裝程式", False, 0, True),
    ]


def test_without_a_probe_the_recorded_state_is_shown():
    checks = _session().artifact_checks(RELEASE)
    assert [(check.exists, check.live) for check in checks] == [(False, False), (True, False)]


def test_dist_listing_needs_an_open_project():
    probe = StaticFileProbe([_info(r"D:\AutoCode\dist\x.zip")])
    folder, entries, message = _session(file_probe=probe).dist_listing()
    assert (folder, entries) == ("", [])
    assert "未開啟專案" in message
    assert probe.asked == []


def test_dist_listing_lists_the_project_dist_folder():
    path = SANDBOX + r"\agent-test"
    probe = StaticFileProbe(
        [_info(path + r"\dist\b.zip", 5), _info(path + r"\dist\a", 0, True), _info(path + r"\dist\a\deep.txt")]
    )
    session = _session(file_probe=probe)
    session.create_project("agent-test", SANDBOX)
    folder, entries, message = session.dist_listing()
    assert folder == path + r"\dist"
    assert [entry.name for entry in entries] == ["a", "b.zip"]
    assert message == ""


def test_release_versions_come_from_the_board():
    session = _session(releases=StaticReleases([RELEASE]))
    assert [item.version for item in session.release_list()] == ["1.0.0"]


# ── launch mode ──────────────────────────────────────────


def _real_session(real=None, roots=(SANDBOX,)) -> WorkbenchSession:
    return _session(real_launcher=real if real is not None else DryRunLauncher(), real_launch_roots=roots)


def test_launch_mode_starts_simulated():
    session = _real_session()
    assert session.launch_mode == "simulated"
    assert session.dispatcher.launcher is session.launcher


def test_demo_board_cannot_launch_for_real():
    session = _real_session()
    with pytest.raises(ValueError, match="示範資料不能實際啟動"):
        session.set_launch_mode("real")
    assert session.launch_mode == "simulated"


def test_real_launch_is_limited_to_the_sandbox_roots():
    session = _real_session()
    session.open_named("AutoRig_Core")
    assert "沙盒" in session.real_launch_block_reason()
    with pytest.raises(ValueError, match="沙盒"):
        session.set_launch_mode("real")


def test_parent_traversal_does_not_escape_the_sandbox():
    session = _real_session()
    session.create_project("..", SANDBOX)
    assert "沙盒" in session.real_launch_block_reason()


def test_sandbox_project_switches_the_dispatcher_to_the_real_launcher():
    real = DryRunLauncher()
    session = _real_session(real)
    session.create_project("agent-test", SANDBOX)
    assert session.real_launch_block_reason() == ""
    session.set_launch_mode("real")
    assert session.launch_mode == "real"
    assert session.dispatcher.launcher is real
    assert session.dispatcher.report_grace == timedelta(seconds=120)
    session.set_launch_mode("simulated")
    assert session.dispatcher.launcher is session.launcher
    assert session.dispatcher.report_grace == timedelta(seconds=0)


def test_launch_mode_cannot_change_while_an_agent_runs():
    session = _real_session()
    session.create_project("agent-test", SANDBOX)
    session.dispatcher.add_lane("claude")
    session.store.create(_card())
    session.dispatcher.start_lane("L1")
    with pytest.raises(ValueError, match="派工中"):
        session.set_launch_mode("real")


def test_switching_project_returns_to_simulated():
    session = _real_session()
    session.create_project("agent-test", SANDBOX)
    session.set_launch_mode("real")
    session.open_named("AutoRig_Core")
    assert session.launch_mode == "simulated"
    assert session.dispatcher.launcher is session.launcher


def test_real_launch_needs_a_real_launcher():
    session = _session(real_launch_roots=(SANDBOX,))
    session.create_project("agent-test", SANDBOX)
    assert session.real_launch_block_reason() == "實際啟動未接上"


def test_unknown_launch_mode_is_rejected():
    with pytest.raises(ValueError):
        _real_session().set_launch_mode("turbo")


def _card() -> WorkItem:
    return WorkItem("CARD-1", "CARD-1", "t", "red", "manual", (), "", "", "2026-10-11T12:00:00+08:00", "", kind="bug")
