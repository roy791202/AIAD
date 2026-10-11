"""Output ports owned by the core. Adapters implement them; the core never imports adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from sgenaxis.core.board import WorkItem
from sgenaxis.core.release import Release


class StoreError(ValueError):
    """The board file could not be read or written; the stored data is unchanged."""


class TaskStore(Protocol):
    """SSOT for tasks. Every write is all-or-nothing and checks the expected version."""

    location: str | None

    def list(self) -> list[WorkItem]: ...

    def get(self, item_id: str) -> WorkItem | None: ...

    def create(self, item: WorkItem) -> None: ...

    def commit(self, item: WorkItem, expected_version: int) -> None: ...

    def delete(self, item_id: str, expected_version: int) -> None: ...


class DispatchStateStore(Protocol):
    """Lanes, schedules, history and needs-human list kept across restarts (not task data)."""

    def load(self) -> dict | None: ...

    def save(self, state: dict) -> None: ...


class ReportInbox(Protocol):
    """Report files <inbox>/<runId>.json written by agents (INV-BD-44/46). Handled files are moved, never deleted."""

    def path(self, run_id: str) -> str: ...

    def read(self, run_id: str) -> bytes | None: ...

    def archive(self, run_id: str, kind: str) -> str | None: ...


class ReleaseSource(Protocol):
    """Release records of a board, newest first. Read-only for the workbench."""

    def list(self) -> list[Release]: ...


class ProjectRegistry(Protocol):
    """Projects the user opened or created, kept across restarts (name, path, branch, opened)."""

    def load(self) -> list[dict]: ...

    def save(self, projects: list[dict]) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True)
class FileInfo:
    path: str
    name: str
    is_dir: bool
    size: int
    modified: datetime
    files: int = 0


class FileProbe(Protocol):
    """Read-only look at artifact paths and the project's dist folder."""

    def stat(self, path: str) -> FileInfo | None: ...

    def entries(self, folder: str) -> list[FileInfo]: ...


class GitUnavailable(RuntimeError):
    """The folder cannot be read as its own Git repository; nothing was run or written."""


@dataclass(frozen=True)
class GitChange:
    path: str
    code: str
    staged: bool


@dataclass(frozen=True)
class GitSnapshot:
    branch: str
    branches: tuple[str, ...]
    changes: tuple[GitChange, ...]
    ahead: int = 0
    behind: int = 0


class GitReader(Protocol):
    """Read-only Git queries (no optional locks, never above the project folder)."""

    def snapshot(self, folder: str) -> GitSnapshot: ...


@dataclass(frozen=True)
class ProjectBoard:
    """Everything the workbench persists for one project folder."""

    store: TaskStore
    state: DispatchStateStore
    inbox: ReportInbox
    logs_dir: str
    releases: ReleaseSource


class ProjectBoards(Protocol):
    def exists(self, folder: str) -> bool: ...

    def managed(self, folder: str) -> bool:
        """The folder already has a SGenAxis board folder (created by SGenAxis)."""
        ...

    def open(self, folder: str) -> ProjectBoard: ...

    def create(self, folder: str) -> ProjectBoard: ...


class LaunchFailed(RuntimeError):
    """The agent CLI could not be started (missing executable, bad argv)."""


@dataclass(frozen=True)
class LaunchRequest:
    """argv never carries card text (INV-BD-15). A launcher must expand %VAR% in argv[0]
    and re-check it against dispatch.SAFE_ARG when it is a .cmd/.bat shim (INV-BD-39)."""

    run_id: str
    lane_id: str
    agent: str
    card_id: str
    argv: tuple[str, ...]
    prompt: str
    prompt_via: str = "stdin"
    prompt_file: str = ""
    cwd: str = ""
    detached: bool = False
    env: dict[str, str] = field(default_factory=dict)


class RunHandle(Protocol):
    def poll(self) -> int | None: ...

    def output(self) -> str: ...

    def terminate(self) -> None: ...


class AgentLauncher(Protocol):
    def launch(self, request: LaunchRequest) -> RunHandle: ...
