"""Driven adapter: tasks / releases stored as docs/board/*.json.

Transaction (spec §2.3): lock -> read -> check expected_version -> apply domain rule
-> write <file>.tmp -> flush + fsync -> os.replace -> unlock. Any failure leaves the
data file byte-identical and raises.
"""
import json
import os
import time

from . import domain, ports

SCHEMA = "hb-board/1"
STALE_LOCK_SECONDS = 30.0
_WIN_SHARING_RETRIES = 40
_WIN_SHARING_DELAY = 0.025


class FileLock:
    """Mutex via O_CREAT|O_EXCL lock file. A lock older than STALE_LOCK_SECONDS is treated as
    left behind by a crashed writer and reclaimed (a real transaction takes milliseconds)."""

    def __init__(self, path, timeout=5.0, poll=0.05):
        self.path = path
        self.timeout = timeout
        self.poll = poll
        self._fd = None

    def _reclaim_if_stale(self):
        try:
            age = time.time() - os.path.getmtime(self.path)
        except OSError:
            return
        if age > STALE_LOCK_SECONDS:
            try:
                os.remove(self.path)
            except OSError:
                pass

    def __enter__(self):
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self._fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self._fd, str(os.getpid()).encode("ascii"))
                return self
            except FileExistsError:
                self._reclaim_if_stale()
                if time.monotonic() >= deadline:
                    raise ports.LockTimeout("lock busy: %s" % self.path)
                time.sleep(self.poll)

    def __exit__(self, *exc):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        try:
            os.remove(self.path)
        except OSError:
            pass
        return False


def _retry_sharing(fn):
    """On Windows a reader holding the file open makes replace/open fail briefly with PermissionError."""
    for attempt in range(_WIN_SHARING_RETRIES):
        try:
            return fn()
        except PermissionError:
            if attempt == _WIN_SHARING_RETRIES - 1:
                raise
            time.sleep(_WIN_SHARING_DELAY)


def atomic_write_json(path, data):
    """Write tmp -> flush + fsync -> os.replace. On failure remove tmp; the target is untouched."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        _retry_sharing(lambda: os.replace(tmp, path))
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _read_json(path):
    def read():
        with open(path, encoding="utf-8") as f:
            return f.read()
    try:
        return json.loads(_retry_sharing(read))
    except ValueError as e:
        raise ports.StoreCorrupt("cannot parse %s: %s" % (path, e))


class JsonFileStore:
    """ITaskStore over {"schema": ..., "tasks": [...]}."""

    def __init__(self, path, lock_path=None, lock_timeout=5.0):
        self.path = path
        self.lock_path = lock_path or os.path.join(os.path.dirname(os.path.abspath(path)), ".lock")
        self.lock_timeout = lock_timeout

    def _read_doc(self):
        if not os.path.isfile(self.path):
            return {"schema": SCHEMA, "tasks": []}
        data = _read_json(self.path)
        if isinstance(data, list):
            data = {"schema": SCHEMA, "tasks": data}
        if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
            raise ports.StoreCorrupt("%s has no tasks list" % self.path)
        return data

    @staticmethod
    def _index(tasks, task_id):
        return next((i for i, t in enumerate(tasks) if t.get("id") == task_id), None)

    def _lock(self):
        return FileLock(self.lock_path, self.lock_timeout)

    def load(self):
        return sorted(self._read_doc()["tasks"], key=lambda t: t.get("id", ""))

    def get(self, task_id):
        tasks = self._read_doc()["tasks"]
        idx = self._index(tasks, task_id)
        if idx is None:
            raise ports.NotFound("no task %s" % task_id)
        return tasks[idx]

    def create(self, task):
        with self._lock():
            data = self._read_doc()
            if self._index(data["tasks"], task["id"]) is not None:
                raise ports.AlreadyExists("task id already exists: %s" % task["id"])
            stored = domain.validate(dict(task, version=1))
            data["tasks"].append(stored)
            atomic_write_json(self.path, data)
            return stored

    def update(self, task_id, expected_version, mutate):
        with self._lock():
            data = self._read_doc()
            idx = self._index(data["tasks"], task_id)
            if idx is None:
                raise ports.NotFound("no task %s" % task_id)
            cur = data["tasks"][idx]
            version = cur.get("version", 1)
            if expected_version is not None and expected_version != version:
                raise ports.VersionConflict("version mismatch for %s: stored %r, given %r"
                                            % (task_id, version, expected_version))
            stored = domain.validate(dict(mutate(cur), version=version + 1))
            data["tasks"][idx] = stored
            atomic_write_json(self.path, data)
            return stored

    def remove(self, task_id):
        with self._lock():
            data = self._read_doc()
            idx = self._index(data["tasks"], task_id)
            if idx is None:
                raise ports.NotFound("no task %s" % task_id)
            del data["tasks"][idx]
            atomic_write_json(self.path, data)


class JsonReleaseStore:
    """IReleaseStore over {"schema": ..., "releases": [...]} (read-only for the board)."""

    def __init__(self, path):
        self.path = path

    def load(self):
        if not os.path.isfile(self.path):
            return []
        data = _read_json(self.path)
        if isinstance(data, dict):
            return data.get("releases", [])
        return data
