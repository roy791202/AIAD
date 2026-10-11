"""File adapters for one project's board folder `<project>/.sgenaxis` (spec-BOARD-LOCAL-01 §2.3).

Layout:
  tasks.json            hb-board/1 task list; every Agent run must reflect its result here
  releases.json         hb-board/1 release records (read only here; optional)
  dispatch.json         lanes, schedules, history, needs-human list
  report-inbox/         report files written by agents (<runId>.json)
  reports/{processed,ignored,rejected}/   handled report files (moved, never deleted)
  logs/<runId>/         prompt files and launcher logs
  .lock                 O_CREAT|O_EXCL mutex for tasks.json and dispatch.json

Writes follow the reference transaction: lock -> read -> check version -> write tmp ->
fsync -> os.replace -> unlock. Any failure leaves the data file byte-identical.
"""

from __future__ import annotations

import json
import os
import time

from sgenaxis.core import board_json, release
from sgenaxis.core.board import VersionConflict, WorkItem
from sgenaxis.core.ports import ProjectBoard, StoreError
from sgenaxis.core.release import Release

BOARD_DIR = ".sgenaxis"
STALE_LOCK_SECONDS = 30.0
ARCHIVE_KINDS = ("processed", "ignored", "rejected")
_WIN_SHARING_RETRIES = 40
_WIN_SHARING_DELAY = 0.025


class FileLock:
    """Mutex via an O_CREAT|O_EXCL lock file; one older than STALE_LOCK_SECONDS was left by a crash."""

    def __init__(self, path: str, timeout: float = 5.0, poll: float = 0.05) -> None:
        self.path = path
        self.timeout = timeout
        self.poll = poll
        self._fd: int | None = None

    def __enter__(self) -> FileLock:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self._fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self._fd, str(os.getpid()).encode("ascii"))
                return self
            except FileExistsError:
                self._reclaim_if_stale()
                if time.monotonic() >= deadline:
                    raise StoreError(f"看板檔案正被其他程式寫入，請稍後再試：{self.path}") from None
                time.sleep(self.poll)

    def __exit__(self, *exc) -> bool:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        try:
            os.remove(self.path)
        except OSError:
            pass
        return False

    def _reclaim_if_stale(self) -> None:
        try:
            age = time.time() - os.path.getmtime(self.path)
        except OSError:
            return
        if age > STALE_LOCK_SECONDS:
            try:
                os.remove(self.path)
            except OSError:
                pass


def _retry_sharing(fn):
    """On Windows a reader holding the file open makes replace/open fail briefly with PermissionError."""
    for attempt in range(_WIN_SHARING_RETRIES):
        try:
            return fn()
        except PermissionError:
            if attempt == _WIN_SHARING_RETRIES - 1:
                raise
            time.sleep(_WIN_SHARING_DELAY)


def atomic_write_json(path: str, data) -> None:
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=1, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        _retry_sharing(lambda: os.replace(tmp, path))
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def read_json(path: str):
    def read() -> str:
        with open(path, encoding="utf-8-sig") as handle:
            return handle.read()

    try:
        return json.loads(_retry_sharing(read))
    except ValueError as exc:
        raise StoreError(f"看板檔案無法解析：{path}：{exc}") from exc
    except OSError as exc:
        raise StoreError(f"看板檔案無法讀取：{path}：{exc}") from exc


class JsonTaskStore:
    """TaskStore over tasks.json. Reads are cached by file mtime and size; writes go through the lock."""

    def __init__(self, path: str, lock_path: str | None = None, lock_timeout: float = 5.0) -> None:
        self.location = os.path.abspath(path)
        self.lock_path = lock_path or os.path.join(os.path.dirname(self.location), ".lock")
        self.lock_timeout = lock_timeout
        self._cache: tuple[tuple[int, int], dict[str, WorkItem]] | None = None

    def list(self) -> list[WorkItem]:
        return list(self._items().values())

    def get(self, item_id: str) -> WorkItem | None:
        return self._items().get(item_id)

    def create(self, item: WorkItem) -> None:
        with self._lock():
            items = self._read()
            if item.item_id in items:
                raise ValueError(f"工項編號已存在：{item.item_id}")
            items[item.item_id] = item
            self._write(items)

    def commit(self, item: WorkItem, expected_version: int) -> None:
        with self._lock():
            items = self._read()
            current = self._current(items, item.item_id, expected_version)
            if item.version != current.version + 1:
                raise ValueError("寫入必須把版本加一")
            items[item.item_id] = item
            self._write(items)

    def delete(self, item_id: str, expected_version: int) -> None:
        with self._lock():
            items = self._read()
            self._current(items, item_id, expected_version)
            del items[item_id]
            self._write(items)

    def _lock(self) -> FileLock:
        return FileLock(self.lock_path, self.lock_timeout)

    def _items(self) -> dict[str, WorkItem]:
        try:
            info = os.stat(self.location)
        except FileNotFoundError:
            return {}
        signature = (info.st_mtime_ns, info.st_size)
        if self._cache is None or self._cache[0] != signature:
            self._cache = (signature, self._read())
        return dict(self._cache[1])

    def _read(self) -> dict[str, WorkItem]:
        if not os.path.isfile(self.location):
            return {}
        document = read_json(self.location)
        try:
            items = board_json.items_from_document(document)
        except (KeyError, TypeError, ValueError) as exc:
            raise StoreError(f"看板檔案內容不符 hb-board/1：{self.location}：{exc}") from exc
        return {item.item_id: item for item in items}

    def _write(self, items: dict[str, WorkItem]) -> None:
        try:
            atomic_write_json(self.location, board_json.document(list(items.values())))
        except OSError as exc:
            raise StoreError(f"看板檔案寫入失敗，原檔未變更：{self.location}：{exc}") from exc
        self._cache = None

    @staticmethod
    def _current(items: dict[str, WorkItem], item_id: str, expected_version: int) -> WorkItem:
        current = items.get(item_id)
        if current is None:
            raise ValueError("這筆已不存在，已重新載入。")
        if current.version != expected_version:
            raise VersionConflict("這筆剛被別人改過，已重新載入。")
        return current


class JsonDispatchState:
    def __init__(self, path: str, lock_path: str | None = None) -> None:
        self.path = os.path.abspath(path)
        self.lock_path = lock_path or os.path.join(os.path.dirname(self.path), ".lock")

    def load(self) -> dict | None:
        if not os.path.isfile(self.path):
            return None
        data = read_json(self.path)
        if not isinstance(data, dict):
            raise StoreError(f"派工狀態檔內容不符：{self.path}")
        return data

    def save(self, state: dict) -> None:
        with FileLock(self.lock_path):
            try:
                atomic_write_json(self.path, state)
            except OSError as exc:
                raise StoreError(f"派工狀態寫入失敗：{self.path}：{exc}") from exc


class JsonReleaseStore:
    """releases.json of a board; a missing file means no releases."""

    def __init__(self, path: str) -> None:
        self.path = os.path.abspath(path)

    def list(self) -> list[Release]:
        if not os.path.isfile(self.path):
            return []
        document = read_json(self.path)
        try:
            return release.releases_from_document(document)
        except (AttributeError, TypeError, ValueError) as exc:
            raise StoreError(f"佈版檔案內容不符 hb-board/1：{self.path}：{exc}") from exc


class JsonProjectRegistry:
    """Projects the user opened or created, in a per-user file outside any project."""

    def __init__(self, path: str) -> None:
        self.path = os.path.abspath(path)

    def load(self) -> list[dict]:
        if not os.path.isfile(self.path):
            return []
        data = read_json(self.path)
        rows = data.get("projects") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            raise StoreError(f"專案清單檔內容不符：{self.path}")
        return [row for row in rows if isinstance(row, dict) and row.get("name") and row.get("path")]

    def save(self, projects: list[dict]) -> None:
        try:
            with FileLock(self.path + ".lock"):
                atomic_write_json(self.path, {"schema": "sgenaxis-projects/1", "projects": projects})
        except OSError as exc:
            raise StoreError(f"專案清單寫入失敗：{self.path}：{exc}") from exc


def user_registry_path(env: dict[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    base = env.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "SGenAxis", "projects.json")


class FileReportInbox:
    def __init__(self, inbox_dir: str, archive_dir: str) -> None:
        self.inbox_dir = os.path.abspath(inbox_dir)
        self.archive_dir = os.path.abspath(archive_dir)

    def path(self, run_id: str) -> str:
        return os.path.join(self.inbox_dir, f"{run_id}.json")

    def read(self, run_id: str) -> bytes | None:
        path = self.path(run_id)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "rb") as handle:
                return handle.read()
        except OSError:
            return None

    def archive(self, run_id: str, kind: str) -> str | None:
        if kind not in ARCHIVE_KINDS:
            raise ValueError(kind)
        source = self.path(run_id)
        if not os.path.isfile(source):
            return None
        folder = os.path.join(self.archive_dir, kind)
        os.makedirs(folder, exist_ok=True)
        target = os.path.join(folder, f"{run_id}.json")
        if os.path.exists(target):
            target = os.path.join(folder, f"{run_id}-{time.time_ns()}.json")
        _retry_sharing(lambda: os.replace(source, target))
        return target


class FileProjectBoards:
    """ProjectBoards over `<folder>/.sgenaxis`. Opening never writes; creating writes an empty tasks.json."""

    def exists(self, folder: str) -> bool:
        return os.path.isdir(folder)

    def managed(self, folder: str) -> bool:
        return os.path.isdir(os.path.join(folder, BOARD_DIR))

    def open(self, folder: str) -> ProjectBoard:
        if not self.exists(folder):
            raise StoreError(f"路徑不存在，未開啟：{folder}")
        return _board(folder)

    def create(self, folder: str) -> ProjectBoard:
        project = _board(folder)
        root = os.path.join(folder, BOARD_DIR)
        try:
            os.makedirs(os.path.join(root, "report-inbox"), exist_ok=True)
            os.makedirs(os.path.join(root, "logs"), exist_ok=True)
            if not os.path.exists(project.store.location):
                with FileLock(project.store.lock_path):
                    atomic_write_json(project.store.location, board_json.document([]))
        except OSError as exc:
            raise StoreError(f"無法建立專案看板：{root}：{exc}") from exc
        return project


def _board(folder: str) -> ProjectBoard:
    root = os.path.join(os.path.abspath(folder), BOARD_DIR)
    return ProjectBoard(
        JsonTaskStore(os.path.join(root, "tasks.json")),
        JsonDispatchState(os.path.join(root, "dispatch.json")),
        FileReportInbox(os.path.join(root, "report-inbox"), os.path.join(root, "reports")),
        os.path.join(root, "logs"),
        JsonReleaseStore(os.path.join(root, "releases.json")),
    )
