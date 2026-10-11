"""Read-only Git queries for a project folder that has its own repository.

Every command runs with --no-optional-locks (status never refreshes the index),
GIT_CEILING_DIRECTORIES set to the parent folder, and inherited GIT_DIR-style
variables removed, so a query can only ever see the project's own `.git`.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess

from sgenaxis.core.ports import GitChange, GitSnapshot, GitUnavailable

GIT_TIMEOUT_SECONDS = 5.0
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_REDIRECT_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY")
_NO_COMMITS = ("No commits yet on ", "Initial commit on ")


class GitCliReader:
    def __init__(self, git: str | None = None, timeout: float = GIT_TIMEOUT_SECONDS) -> None:
        self.git = git or shutil.which("git")
        self.timeout = timeout

    def snapshot(self, folder: str) -> GitSnapshot:
        root = os.path.abspath(folder)
        if not os.path.exists(os.path.join(root, ".git")):
            raise GitUnavailable(f"專案資料夾沒有自己的 .git，不讀 Git：{root}")
        if not self.git:
            raise GitUnavailable("找不到 git 執行檔")
        status = self._run(root, "status", "--porcelain=v1", "--branch", "--untracked-files=all", "-z")
        heads = self._run(root, "for-each-ref", "--format=%(refname:short)", "refs/heads")
        branch, ahead, behind, changes = parse_status(status)
        names = tuple(line.strip() for line in heads.splitlines() if line.strip())
        if branch and branch not in names:
            names = (branch, *names)
        return GitSnapshot(branch, names, changes, ahead, behind)

    def _run(self, root: str, *args: str) -> str:
        env = {key: value for key, value in os.environ.items() if key not in _REDIRECT_VARS}
        env["GIT_OPTIONAL_LOCKS"] = "0"
        env["GIT_CEILING_DIRECTORIES"] = os.path.dirname(root)
        command = [self.git, "--no-optional-locks", "-c", "core.quotepath=off", "-C", root, *args]
        try:
            done = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=self.timeout,
                env=env,
                creationflags=_NO_WINDOW,
            )
        except subprocess.TimeoutExpired:
            raise GitUnavailable(f"git {args[0]} 超過 {self.timeout:g} 秒沒有回應") from None
        except OSError as exc:
            raise GitUnavailable(f"無法執行 git：{exc}") from exc
        if done.returncode != 0:
            detail = done.stderr.decode("utf-8", "replace").strip().splitlines()
            raise GitUnavailable(f"git {args[0]} 失敗：{detail[-1] if detail else done.returncode}")
        return done.stdout.decode("utf-8", "replace")


def parse_status(raw: str) -> tuple[str, int, int, tuple[GitChange, ...]]:
    """`git status --porcelain=v1 --branch -z` → (branch, ahead, behind, changes)."""
    branch, ahead, behind = "", 0, 0
    changes: list[GitChange] = []
    parts = raw.split("\0")
    index = 0
    while index < len(parts):
        entry = parts[index]
        index += 1
        if not entry:
            continue
        if entry.startswith("## "):
            branch, ahead, behind = _branch_line(entry[3:])
            continue
        x, y, path = entry[0], entry[1], entry[3:]
        if x in "RC":
            index += 1
        if x == "!":
            continue
        if x == "?":
            changes.append(GitChange(path, "??", False))
            continue
        if x != " ":
            changes.append(GitChange(path, x, True))
        if y != " ":
            changes.append(GitChange(path, y, False))
    return branch, ahead, behind, tuple(changes)


def _branch_line(text: str) -> tuple[str, int, int]:
    for lead in _NO_COMMITS:
        if text.startswith(lead):
            return text[len(lead):].strip(), 0, 0
    head, _, tracking = text.partition(" [")
    name = head.split("...")[0].strip()
    if name == "HEAD (no branch)":
        name = "HEAD（分離）"
    ahead = re.search(r"ahead (\d+)", tracking)
    behind = re.search(r"behind (\d+)", tracking)
    return name, int(ahead.group(1)) if ahead else 0, int(behind.group(1)) if behind else 0
