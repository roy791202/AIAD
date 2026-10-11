"""Adapters that touch the OS: read-only Git, file probe, and the real agent launcher."""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from sgenaxis.adapters.file_probe import LocalFileProbe
from sgenaxis.adapters.git_reader import GitCliReader, parse_status
from sgenaxis.adapters.json_board import FileProjectBoards
from sgenaxis.adapters.process_launcher import ProcessLauncher
from sgenaxis.core.ports import GitChange, GitUnavailable, LaunchFailed, LaunchRequest

windows_only = pytest.mark.skipif(os.name != "nt", reason="Windows process tree and .cmd shims")
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


def _wait(handle, seconds: float = 15.0) -> int:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        code = handle.poll()
        if code is not None:
            return code
        time.sleep(0.05)
    raise AssertionError("process did not exit in time")


def _alive(pid: int) -> bool:
    kernel = ctypes.windll.kernel32
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    code = ctypes.c_ulong()
    kernel.GetExitCodeProcess(handle, ctypes.byref(code))
    kernel.CloseHandle(handle)
    return code.value == 259


def _request(tmp_path: Path, argv, **kwargs) -> LaunchRequest:
    defaults = dict(
        run_id="R1",
        lane_id="L1",
        agent="claude",
        card_id="CARD-1",
        argv=tuple(argv),
        prompt="提示 prompt",
        prompt_via="stdin",
        prompt_file=str(tmp_path / "logs" / "R1" / "prompt.md"),
        cwd=str(tmp_path),
        detached=False,
        env={"HB_DISPATCH_RUN_ID": "R1", "PYTHONIOENCODING": "utf-8"},
    )
    defaults.update(kwargs)
    return LaunchRequest(**defaults)


def _script(tmp_path: Path, name: str, body: str) -> str:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return str(path)


# ── git ─────────────────────────────────────────────────


def test_parse_status_reads_branch_tracking_and_changes():
    raw = "## main...origin/main [ahead 2, behind 1]\0M  staged.py\0 M edited.py\0MM both.py\0?? new.txt\0R  to.py\0from.py\0"
    branch, ahead, behind, changes = parse_status(raw)
    assert (branch, ahead, behind) == ("main", 2, 1)
    assert changes == (
        GitChange("staged.py", "M", True),
        GitChange("edited.py", "M", False),
        GitChange("both.py", "M", True),
        GitChange("both.py", "M", False),
        GitChange("new.txt", "??", False),
        GitChange("to.py", "R", True),
    )


def test_parse_status_handles_a_repo_without_commits():
    assert parse_status("## No commits yet on main\0?? a.txt\0")[:3] == ("main", 0, 0)


def _git(folder: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(folder), *args], check=True, capture_output=True)


@needs_git
def test_git_reader_reads_its_own_repo_without_writing(tmp_path: Path):
    repo = tmp_path / "proj"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "--allow-empty", "-m", "init")
    _git(repo, "branch", "dev")
    (repo / "a.txt").write_text("x", encoding="utf-8")
    index = repo / ".git" / "index"
    before = index.stat().st_mtime_ns if index.exists() else None
    snap = GitCliReader().snapshot(str(repo))
    assert snap.branch == "main"
    assert set(snap.branches) == {"main", "dev"}
    assert snap.changes == (GitChange("a.txt", "??", False),)
    assert (index.stat().st_mtime_ns if index.exists() else None) == before
    assert not (repo / ".git" / "index.lock").exists()


@needs_git
def test_git_reader_never_reads_a_parent_repo(tmp_path: Path):
    _git(tmp_path, "init", "-b", "main")
    child = tmp_path / "child"
    child.mkdir()
    with pytest.raises(GitUnavailable, match="沒有自己的 .git"):
        GitCliReader().snapshot(str(child))


def test_managed_means_the_folder_has_a_board(tmp_path: Path):
    boards = FileProjectBoards()
    assert not boards.managed(str(tmp_path))
    boards.open(str(tmp_path))
    assert not boards.managed(str(tmp_path))
    boards.create(str(tmp_path))
    assert boards.managed(str(tmp_path))


# ── file probe ──────────────────────────────────────────


def test_file_probe_reports_files_folders_and_missing_paths(tmp_path: Path):
    (tmp_path / "dist" / "portable").mkdir(parents=True)
    (tmp_path / "dist" / "portable" / "a.bin").write_bytes(b"x" * 100)
    (tmp_path / "dist" / "portable" / "b.bin").write_bytes(b"x" * 50)
    (tmp_path / "dist" / "app.zip").write_bytes(b"z" * 7)
    probe = LocalFileProbe()
    folder = probe.stat(str(tmp_path / "dist" / "portable"))
    assert (folder.is_dir, folder.size, folder.files) == (True, 150, 2)
    assert probe.stat(str(tmp_path / "dist" / "app.zip")).size == 7
    assert probe.stat(str(tmp_path / "missing.exe")) is None
    assert [entry.name for entry in probe.entries(str(tmp_path / "dist"))] == ["app.zip", "portable"]
    assert probe.entries(str(tmp_path / "nope")) == []


# ── launcher ────────────────────────────────────────────


ECHO = (
    "import os, sys\n"
    "data = sys.stdin.buffer.read().decode('utf-8')\n"
    "sys.stdout.buffer.write(('got:' + data + '|run:' + os.environ['HB_DISPATCH_RUN_ID'] + '|cwd:' + os.getcwd()).encode('utf-8'))\n"
    "sys.exit(3)\n"
)


def test_stdin_prompt_env_and_output_reach_the_dispatcher(tmp_path: Path):
    script = _script(tmp_path, "echo.py", ECHO)
    handle = ProcessLauncher().launch(_request(tmp_path, [sys.executable, script]))
    assert _wait(handle) == 3
    text = handle.output()
    assert "got:提示 prompt" in text
    assert "|run:R1" in text
    assert f"|cwd:{tmp_path}" in text
    assert (tmp_path / "logs" / "R1" / "prompt.md").read_text(encoding="utf-8") == "提示 prompt"
    assert "got:提示 prompt" in (tmp_path / "logs" / "R1" / "output.log").read_text(encoding="utf-8")


def test_arg_mode_gives_the_agent_no_stdin(tmp_path: Path):
    script = _script(tmp_path, "echo.py", ECHO)
    handle = ProcessLauncher().launch(_request(tmp_path, [sys.executable, script], prompt_via="arg"))
    assert _wait(handle) == 3
    assert "got:|run:R1" in handle.output()


def test_output_keeps_only_the_tail(tmp_path: Path):
    script = _script(tmp_path, "loud.py", "print('x' * 5000 + 'END')\n")
    handle = ProcessLauncher(output_limit=100).launch(_request(tmp_path, [sys.executable, script]))
    _wait(handle)
    assert len(handle.output()) <= 100
    assert "END" in handle.output()


def test_missing_executable_or_folder_fails_to_launch(tmp_path: Path):
    with pytest.raises(LaunchFailed, match="找不到"):
        ProcessLauncher().launch(_request(tmp_path, ["no-such-agent-cli-xyz"]))
    with pytest.raises(LaunchFailed, match="工作目錄"):
        ProcessLauncher().launch(_request(tmp_path, [sys.executable], cwd=str(tmp_path / "gone")))


@windows_only
def test_cmd_shim_is_expanded_and_rechecked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    shim_dir = tmp_path / "bin"
    shim_dir.mkdir()
    (shim_dir / "agent.cmd").write_text("@echo off\r\necho shim-ok %1\r\n", encoding="ascii")
    monkeypatch.setenv("SGX_TEST_BIN", str(shim_dir))
    handle = ProcessLauncher().launch(_request(tmp_path, [r"%SGX_TEST_BIN%\agent.cmd", "hello"], prompt_via="arg"))
    assert _wait(handle) == 0
    assert "shim-ok hello" in handle.output()
    with pytest.raises(LaunchFailed, match="不安全"):
        ProcessLauncher().launch(_request(tmp_path, [r"%SGX_TEST_BIN%\agent.cmd", "a&calc"], prompt_via="arg"))


@windows_only
def test_terminate_ends_the_whole_process_tree(tmp_path: Path):
    pid_file = tmp_path / "child.pid"
    script = _script(
        tmp_path,
        "tree.py",
        "import subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"open(r'{pid_file}', 'w').write(str(child.pid))\n"
        "time.sleep(60)\n",
    )
    handle = ProcessLauncher(kill_grace=0.5).launch(_request(tmp_path, [sys.executable, script]))
    deadline = time.monotonic() + 10
    while not pid_file.exists() or not pid_file.read_text():
        assert time.monotonic() < deadline
        time.sleep(0.05)
    child = int(pid_file.read_text())
    assert _alive(child)
    handle.terminate()
    _wait(handle)
    deadline = time.monotonic() + 10
    while _alive(child):
        assert time.monotonic() < deadline, "child process survived terminate"
        time.sleep(0.1)


def test_detached_run_is_not_captured(tmp_path: Path):
    marker = tmp_path / "ran.txt"
    script = _script(tmp_path, "win.py", f"open(r'{marker}', 'w').write('ok')\n")
    handle = ProcessLauncher().launch(_request(tmp_path, [sys.executable, script], prompt_via="arg", detached=True))
    _wait(handle)
    assert marker.read_text() == "ok"
    assert "視窗模式" in handle.output()
