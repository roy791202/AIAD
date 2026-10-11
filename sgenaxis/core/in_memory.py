"""In-memory adapters for the core ports: store, dispatch state, report inbox, project boards, clock, launcher.

These never touch disk, processes, or the system clock. The workbench uses them
until a project folder is opened; tests use them as deterministic fakes.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta

from sgenaxis.core import board
from sgenaxis.core.board import VersionConflict, WorkItem
from sgenaxis.core.ports import FileInfo, GitSnapshot, GitUnavailable, LaunchFailed, LaunchRequest, ProjectBoard
from sgenaxis.core.release import Release

ARCHIVE_KINDS = ("processed", "ignored", "rejected")


class InMemoryTaskStore:
    location: str | None = None

    def __init__(self, items=()) -> None:
        self._items: dict[str, WorkItem] = {}
        for item in items:
            self.create(item)

    def list(self) -> list[WorkItem]:
        return list(self._items.values())

    def get(self, item_id: str) -> WorkItem | None:
        return self._items.get(item_id)

    def create(self, item: WorkItem) -> None:
        board.check(item)
        if item.item_id in self._items:
            raise ValueError(f"工項編號已存在：{item.item_id}")
        self._items[item.item_id] = item

    def commit(self, item: WorkItem, expected_version: int) -> None:
        current = self._current(item.item_id, expected_version)
        if item.version != current.version + 1:
            raise ValueError("寫入必須把版本加一")
        board.check(item)
        self._items[item.item_id] = item

    def delete(self, item_id: str, expected_version: int) -> None:
        self._current(item_id, expected_version)
        del self._items[item_id]

    def _current(self, item_id: str, expected_version: int) -> WorkItem:
        current = self._items.get(item_id)
        if current is None:
            raise ValueError("這筆已不存在，已重新載入。")
        if current.version != expected_version:
            raise VersionConflict("這筆剛被別人改過，已重新載入。")
        return current


class InMemoryDispatchState:
    def __init__(self, state: dict | None = None) -> None:
        self.state = copy.deepcopy(state)
        self.saves = 0

    def load(self) -> dict | None:
        return copy.deepcopy(self.state)

    def save(self, state: dict) -> None:
        self.state = copy.deepcopy(state)
        self.saves += 1


class InMemoryReportInbox:
    def __init__(self, folder: str = "report-inbox") -> None:
        self.folder = folder
        self.files: dict[str, bytes] = {}
        self.archived: dict[str, list[str]] = {kind: [] for kind in ARCHIVE_KINDS}

    def path(self, run_id: str) -> str:
        return f"{self.folder}\\{run_id}.json"

    def put(self, run_id: str, raw: bytes) -> None:
        self.files[run_id] = raw

    def read(self, run_id: str) -> bytes | None:
        return self.files.get(run_id)

    def archive(self, run_id: str, kind: str) -> str | None:
        if kind not in ARCHIVE_KINDS:
            raise ValueError(kind)
        if self.files.pop(run_id, None) is None:
            return None
        self.archived[kind].append(run_id)
        return f"{kind}\\{run_id}.json"


class StaticReleases:
    def __init__(self, releases=()) -> None:
        self._releases: list[Release] = list(releases)

    def list(self) -> list[Release]:
        return list(self._releases)


class InMemoryProjectRegistry:
    def __init__(self, projects=()) -> None:
        self.projects: list[dict] = [dict(row) for row in projects]
        self.saves = 0

    def load(self) -> list[dict]:
        return [dict(row) for row in self.projects]

    def save(self, projects: list[dict]) -> None:
        self.projects = [dict(row) for row in projects]
        self.saves += 1


class InMemoryProjectBoards:
    """Project folders that exist only in memory; `missing` folders cannot be opened."""

    def __init__(self, missing=(), managed=()) -> None:
        self.missing = set(missing)
        self.managed_folders = set(managed)
        self.boards: dict[str, ProjectBoard] = {}

    def exists(self, folder: str) -> bool:
        return folder not in self.missing

    def managed(self, folder: str) -> bool:
        return folder in self.managed_folders

    def open(self, folder: str) -> ProjectBoard:
        if folder not in self.boards:
            self.boards[folder] = ProjectBoard(
                InMemoryTaskStore(),
                InMemoryDispatchState(),
                InMemoryReportInbox(),
                f"{folder}\\.sgenaxis\\logs",
                StaticReleases(),
            )
        return self.boards[folder]

    def create(self, folder: str) -> ProjectBoard:
        self.missing.discard(folder)
        self.managed_folders.add(folder)
        return self.open(folder)


class ManualClock:
    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta

    def set(self, moment: datetime) -> None:
        self._now = moment


class DryRunHandle:
    """A run that never started a process. It ends only when told to."""

    def __init__(self) -> None:
        self.exit_code: int | None = None
        self.text = ""
        self.terminated = False

    def poll(self) -> int | None:
        return self.exit_code

    def output(self) -> str:
        return self.text

    def terminate(self) -> None:
        self.terminated = True
        if self.exit_code is None:
            self.exit_code = -1

    def finish(self, code: int, output: str = "") -> None:
        self.exit_code = code
        self.text += output


class DryRunLauncher:
    """Records launch requests instead of starting agent CLIs."""

    def __init__(self) -> None:
        self.launched: list[LaunchRequest] = []
        self.handles: dict[str, DryRunHandle] = {}
        self.fail_next: str | None = None

    def launch(self, request: LaunchRequest) -> DryRunHandle:
        if self.fail_next is not None:
            message, self.fail_next = self.fail_next, None
            raise LaunchFailed(message)
        self.launched.append(request)
        handle = DryRunHandle()
        handle.text = f"[模擬] 未啟動 {request.argv[0]}；等待回報 {request.run_id}\n"
        self.handles[request.run_id] = handle
        return handle


class StaticFileProbe:
    """Files keyed by path; `entries` lists the direct children of a folder."""

    def __init__(self, files=()) -> None:
        self.files: dict[str, FileInfo] = {info.path: info for info in files}
        self.asked: list[str] = []

    def stat(self, path: str) -> FileInfo | None:
        self.asked.append(path)
        return self.files.get(path)

    def entries(self, folder: str) -> list[FileInfo]:
        self.asked.append(folder)
        prefix = folder.rstrip("\\/") + "\\"
        return sorted(
            (info for path, info in self.files.items() if path.startswith(prefix) and "\\" not in path[len(prefix):]),
            key=lambda info: info.name,
        )


class StaticGitReader:
    """Snapshots keyed by folder; any other folder is not a repository."""

    def __init__(self, snapshots=None) -> None:
        self.snapshots: dict[str, GitSnapshot] = dict(snapshots or {})
        self.asked: list[str] = []

    def snapshot(self, folder: str) -> GitSnapshot:
        self.asked.append(folder)
        if folder not in self.snapshots:
            raise GitUnavailable(f"專案資料夾沒有自己的 .git，不讀 Git：{folder}")
        return self.snapshots[folder]
