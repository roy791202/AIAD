#!/usr/bin/env python3
"""VGenAxIs 看板監看小後端。標準函式庫、只綁 127.0.0.1。

GET  /           → PROJECT-BOARD.html（不快取）
GET  /events     → SSE：HTML 檔 mtime/size 一變就推一筆 {sig, mtime, size}
GET  /api/tasks  → 讀 #board-snapshot 工項
POST /api/tasks  → 新增工項並原子寫回 HTML
PATCH/DELETE /api/tasks/<id>
GET  /api/releases
GET  /api/dispatch → 派工器快照（enabled=true 時含 token／lanes）
POST /api/dispatch/lanes[/id/start|stop|remove] ／ unskip
GET  /api/dispatch/lanes/<id>/output ／ /api/dispatch/runs/<id>/output
GET  /agent-log    → docs/AGENT-LOG.html（黑底唯讀 log）
GET  /api/health

正式派工器：依紅>黃>灰啟動 Claude／cursor-agent／Codex／Antigravity CLI。
工項 SSOT 仍是本頁 #board-snapshot。派工狀態在 tools/board/runtime/dispatch.json。
埠不得是 8788（HoneyBadgerCreator mailbox）。
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

_TOOLS_BOARD = Path(__file__).resolve().parents[1] / "tools" / "board"
if str(_TOOLS_BOARD) not in sys.path:
    sys.path.insert(0, str(_TOOLS_BOARD))

from board_core import ports  # noqa: E402
from board_core import snapshot_safe  # noqa: E402  # PD-BOARD-SAFE-01
from board_core.dispatch_config import ConfigError, executable, load_config  # noqa: E402
from board_core.dispatch_store import DispatchStateStore  # noqa: E402
from board_core.dispatcher import Dispatcher, DispatchBadRequest, DispatchBusy  # noqa: E402
from board_core.domain import DomainError, apply_owner_action as domain_apply_owner_action, normalize_decision  # noqa: E402
from board_core.report_inbox import ReportInbox  # noqa: E402
from board_core.subprocess_launcher import SubprocessLauncher, SystemClock, read_log_chunk  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_HTML = HERE / "PROJECT-BOARD.html"
DEFAULT_LOG_HTML = HERE / "AGENT-LOG.html"
DEFAULT_DISPATCH_CONFIG = REPO / "tools" / "board" / "dispatch-agents.json"
DEFAULT_RUNTIME = REPO / "tools" / "board" / "runtime"
DEFAULT_REPORT_INBOX = REPO / "tools" / "board" / "report-inbox"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 28789
RESERVED_FOREIGN_PORTS = frozenset({8788})
DISPATCH_PREFIX = "/api/dispatch"
LANES_PREFIX = "/api/dispatch/lanes/"
RUNS_PREFIX = "/api/dispatch/runs/"
LOG_PAGE_PATHS = ("/agent-log", "/AGENT-LOG.html")
LANE_ACTIONS = ("start", "stop", "remove")
OUTPUT_CHUNK_BYTES = 64 * 1024
APP_ID = "vg-board"
SERVER_VERSION = 2
FEATURES = (
    "tasks",
    "releases",
    "events",
    "health",
    "dispatch",
    "dispatch-unlimited",
    "dispatch-lanes",
    "agent-log-page",
    "agent-detached",
    "report-channels",
)
STALE_LOCK_SECONDS = 30.0
SNAPSHOT_OPEN = '<script type="application/json" id="board-snapshot">'
SNAPSHOT_CLOSE = "</script>"
ZONES = frozenset({"gray", "yellow", "red", "green", "orange"})
ID_RE = re.compile(r"^[A-Za-z0-9_.~:@+-]+$")
EDITABLE = ("title", "ref", "kind", "note", "bdd", "tdd", "decision")
MAX_LOG = 20
MAX_BODY = 256 * 1024
TAIPEI = timezone(timedelta(hours=8))
DISPATCH_DISABLED_REASON = "以 --no-dispatch 啟動，派工器未載入。"


class BoardError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class Forbidden(Exception):
    """Host / Origin / token guard failed (INV-BD-20/21)."""


class FileLock:
    """Cross-process mutex so HTTP and `board.py report` do not clobber the HTML snapshot."""

    def __init__(self, path: str, timeout: float = 5.0, poll: float = 0.05) -> None:
        self.path = path
        self.timeout = timeout
        self.poll = poll
        self._fd = None

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

    def __exit__(self, *exc) -> bool:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        try:
            os.remove(self.path)
        except OSError:
            pass
        return False


def now_iso() -> str:
    return datetime.now(TAIPEI).replace(microsecond=0).isoformat()


def read_stamp(path: Path) -> tuple[int, int]:
    """回傳 (mtime_ns, size)。檔案不存在則 (0, 0)。"""
    try:
        st = path.stat()
    except OSError:
        return (0, 0)
    mtime_ns = getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))
    return (int(mtime_ns), int(st.st_size))


def stamp_sig(stamp: tuple[int, int]) -> str:
    return "%d-%x" % (stamp[1], stamp[0] & 0xFFFFFFFFFFFFFFFF)


def stamp_payload(stamp: tuple[int, int]) -> dict:
    return {"mtime": stamp[0], "size": stamp[1], "sig": stamp_sig(stamp)}


class StampHub:
    """檔案指紋 + 等變動。HTTP 執行緒只 wait，監看執行緒只 set。"""

    def __init__(self) -> None:
        self._cv = threading.Condition()
        self._gen = 0
        self._stamp: tuple[int, int] = (0, 0)

    def snapshot(self) -> tuple[int, tuple[int, int]]:
        with self._cv:
            return self._gen, self._stamp

    def set_stamp(self, stamp: tuple[int, int]) -> bool:
        with self._cv:
            if stamp == self._stamp:
                return False
            self._stamp = stamp
            self._gen += 1
            self._cv.notify_all()
            return True

    def wait(self, last_gen: int, timeout: float) -> tuple[int, tuple[int, int]]:
        with self._cv:
            self._cv.wait_for(lambda: self._gen != last_gen, timeout=timeout)
            return self._gen, self._stamp


def watch_loop(path: Path, hub: StampHub, stop: threading.Event, interval: float = 0.4) -> None:
    while not stop.is_set():
        hub.set_stamp(read_stamp(path))
        stop.wait(interval)


def split_snapshot(html: str) -> tuple[str, str, str]:
    start = html.find(SNAPSHOT_OPEN)
    if start < 0:
        raise BoardError(500, "board-snapshot missing")
    inner = start + len(SNAPSHOT_OPEN)
    end = html.find(SNAPSHOT_CLOSE, inner)
    if end < 0:
        raise BoardError(500, "board-snapshot unclosed")
    return html[:inner], html[inner:end], html[end:]


def load_snapshot_text(json_text: str) -> dict:
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise BoardError(500, "snapshot JSON invalid") from exc
    if not isinstance(data, dict):
        raise BoardError(500, "snapshot is not an object")
    data.setdefault("tasks", [])
    data.setdefault("releases", [])
    if not isinstance(data["tasks"], list):
        raise BoardError(500, "tasks is not a list")
    return data


def dump_snapshot(data: dict) -> str:
    return "\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(str(tmp), str(path))


def _task_id(raw: object, tasks: list) -> str:
    text = str(raw or "").strip()
    if not text:
        text = "T-" + datetime.now(TAIPEI).strftime("%Y%m%d%H%M%S")
    if not ID_RE.match(text):
        raise BoardError(400, "invalid id")
    existing = {str(t.get("id")) for t in tasks if isinstance(t, dict)}
    if text in existing:
        raise BoardError(409, "id already exists")
    return text


def apply_zone(task: dict, zone: str, now: str) -> None:
    if zone not in ZONES:
        raise BoardError(400, "invalid zone")
    prev = task.get("zone")
    if prev == zone:
        return
    task["zone"] = zone
    if zone == "green":
        task["doneAt"] = now
    else:
        task["doneAt"] = None
    if zone == "yellow" and not task.get("startedAt"):
        task["startedAt"] = now
    log = list(task.get("log") or [])
    log.append({"t": now, "zone": zone, "by": task.get("updatedBy") or "user"})
    task["log"] = log[-MAX_LOG:]


def create_task(data: dict, body: dict, now_iso: str) -> dict:
    if not isinstance(body, dict):
        raise BoardError(400, "body must be an object")
    title = str(body.get("title") or "").strip()
    if not title:
        raise BoardError(400, "title is required")
    zone = str(body.get("zone") or "gray")
    if zone not in ZONES:
        raise BoardError(400, "invalid zone")
    try:
        decision = normalize_decision(body.get("decision"), zone)
    except DomainError as exc:
        raise BoardError(400, str(exc)) from exc
    tasks = data.setdefault("tasks", [])
    ident = _task_id(body.get("id") or body.get("ref"), tasks)
    kind = str(body.get("kind") or ("bug" if zone == "red" else "task"))
    created = str(body.get("createdAt") or now_iso)
    task = {
        "id": ident,
        "ref": str(body.get("ref") or ident).strip(),
        "title": title,
        "zone": "gray" if zone == "green" else zone,
        "kind": kind,
        "bdd": str(body.get("bdd") or "").strip(),
        "tdd": str(body.get("tdd") or "").strip(),
        "note": str(body.get("note") or "").strip(),
        "decision": decision,
        "ownerActions": [],
        "createdAt": created,
        "startedAt": now_iso if zone == "yellow" else None,
        "doneAt": None,
        "by": "user",
        "updatedAt": now_iso,
        "updatedBy": "user",
        "version": 1,
        "log": [{"t": created, "zone": "gray" if zone == "green" else zone, "by": "user"}],
    }
    if zone == "yellow":
        apply_zone(task, "yellow", now_iso)
    elif zone == "green":
        apply_zone(task, "green", str(body.get("doneAt") or now_iso))
        if task["doneAt"] and task["createdAt"] > task["doneAt"]:
            task["createdAt"] = task["doneAt"]
    elif zone == "red":
        apply_zone(task, "red", created)
        task["log"] = [{"t": created, "zone": "red", "by": "user"}]
    tasks.insert(0, task)
    data["asOf"] = now_iso
    return task


def _find_task(data: dict, task_id: str) -> dict:
    for task in data.get("tasks") or []:
        if isinstance(task, dict) and task.get("id") == task_id:
            return task
    raise BoardError(404, "task not found")


def patch_task(data: dict, task_id: str, body: dict, now_iso: str) -> dict:
    if not isinstance(body, dict):
        raise BoardError(400, "body must be an object")
    task = _find_task(data, task_id)
    expected = body.get("expected_version")
    current = int(task.get("version") or 1)
    if expected is not None and int(expected) != current:
        raise BoardError(409, "version conflict")
    candidate = dict(task)
    candidate["log"] = list(task.get("log") or [])
    if "zone" in body:
        apply_zone(candidate, str(body["zone"]), now_iso)
    fields = body.get("fields") if isinstance(body.get("fields"), dict) else body
    for key in EDITABLE:
        if key in fields and key != "zone":
            value = fields[key]
            if key == "decision":
                try:
                    candidate[key] = normalize_decision(value, candidate.get("zone"))
                except DomainError as exc:
                    raise BoardError(400, str(exc)) from exc
            else:
                candidate[key] = str(value if value is not None else "").strip()
    try:
        candidate["decision"] = normalize_decision(candidate.get("decision", ""), candidate.get("zone"))
    except DomainError as exc:
        raise BoardError(400, str(exc)) from exc
    candidate["updatedAt"] = now_iso
    candidate["updatedBy"] = "user"
    candidate["version"] = current + 1
    task.clear()
    task.update(candidate)
    data["asOf"] = now_iso
    return task


def owner_action(data: dict, task_id: str, body: dict, now_iso: str) -> dict:
    """Apply an Owner-only action under the snapshot write lock and expected-version CAS."""
    if not isinstance(body, dict):
        raise BoardError(400, "body must be an object")
    extra = set(body) - {"action", "text", "expected_version"}
    if extra:
        raise BoardError(400, "unexpected fields: %s" % ", ".join(sorted(extra)))
    expected = body.get("expected_version")
    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 1:
        raise BoardError(400, "expected_version must be a positive integer")
    task = _find_task(data, task_id)
    current = int(task.get("version") or 1)
    if expected != current:
        raise BoardError(409, "version conflict")
    try:
        candidate = domain_apply_owner_action(
            task, body.get("action"), body.get("text"), by="user", now=now_iso
        )
    except DomainError as exc:
        raise BoardError(400, str(exc)) from exc
    candidate["version"] = current + 1
    task.clear()
    task.update(candidate)
    data["asOf"] = now_iso
    return task


def delete_task(data: dict, task_id: str) -> None:
    tasks = data.get("tasks") or []
    kept = [t for t in tasks if not (isinstance(t, dict) and t.get("id") == task_id)]
    if len(kept) == len(tasks):
        raise BoardError(404, "task not found")
    data["tasks"] = kept


def mutate_html(path: Path, mutator) -> dict:
    """PD-BOARD-SAFE-01: replace only #board-snapshot; preserve DOCTYPE／導覽 shell."""
    try:
        return snapshot_safe.mutate_snapshot_file(path, mutator, lock_factory=FileLock)
    except snapshot_safe.FullOverwriteRejected as exc:
        raise BoardError(500, "full overwrite rejected: %s" % exc) from exc
    except snapshot_safe.ShellCorruptError as exc:
        raise BoardError(500, "board shell corrupt: %s" % exc) from exc


class HtmlSnapshotStore:
    """ITaskStore over PROJECT-BOARD.html #board-snapshot (VGenAxIs SSOT)."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self):
        html = self.path.read_text(encoding="utf-8")
        _prefix, inner, _suffix = split_snapshot(html)
        data = load_snapshot_text(inner)
        return [t for t in (data.get("tasks") or []) if isinstance(t, dict)]

    def get(self, task_id):
        for task in self.load():
            if task.get("id") == task_id:
                return task
        raise ports.NotFound("task not found")

    def create(self, task):
        def mutator(data):
            tasks = data.setdefault("tasks", [])
            if any(isinstance(t, dict) and t.get("id") == task.get("id") for t in tasks):
                raise BoardError(409, "id already exists")
            tasks.insert(0, task)
            data["asOf"] = task.get("updatedAt") or data.get("asOf")
            return task

        try:
            return mutate_html(self.path, mutator)
        except BoardError as exc:
            self._raise_port(exc)

    def update(self, task_id, expected_version, mutate):
        def mutator(data):
            tasks = data.setdefault("tasks", [])
            index = None
            current = None
            for i, task in enumerate(tasks):
                if isinstance(task, dict) and task.get("id") == task_id:
                    index, current = i, task
                    break
            if current is None:
                raise BoardError(404, "task not found")
            version = int(current.get("version") or 1)
            if expected_version is not None and int(expected_version) != version:
                raise BoardError(409, "version conflict")
            try:
                updated = mutate(dict(current))
            except DomainError as exc:
                raise BoardError(400, str(exc)) from exc
            updated["version"] = version + 1
            tasks[index] = updated
            data["asOf"] = updated.get("updatedAt") or data.get("asOf")
            return updated

        try:
            return mutate_html(self.path, mutator)
        except BoardError as exc:
            self._raise_port(exc)

    def remove(self, task_id):
        def mutator(data):
            tasks = data.setdefault("tasks", [])
            kept = [t for t in tasks if not (isinstance(t, dict) and t.get("id") == task_id)]
            if len(kept) == len(tasks):
                raise BoardError(404, "task not found")
            data["tasks"] = kept
            return {"ok": True, "id": task_id}

        try:
            return mutate_html(self.path, mutator)
        except BoardError as exc:
            self._raise_port(exc)

    @staticmethod
    def _raise_port(exc: BoardError):
        if exc.status == 404:
            raise ports.NotFound(exc.message) from exc
        if exc.status == 409:
            raise ports.VersionConflict(exc.message) from exc
        raise exc


def build_handler(
    html_path: Path,
    hub: StampHub,
    dispatcher=None,
    token=None,
    disabled_reason=None,
    log_html_path=None,
):
    write_lock = threading.Lock()
    log_html_path = Path(log_html_path or DEFAULT_LOG_HTML)
    disabled_reason = disabled_reason or DISPATCH_DISABLED_REASON

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args) -> None:
            pass

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path in ("/", "/index.html", "/PROJECT-BOARD.html"):
                return self._serve_html()
            if path == "/events":
                return self._serve_events()
            if path == "/api/tasks":
                return self._api_get_tasks()
            if path == "/api/releases":
                return self._api_get_releases()
            if path == DISPATCH_PREFIX:
                return self._route(self._dispatch_get)
            if path.startswith(LANES_PREFIX) and path.endswith("/output") and path.count("/") == 5:
                lane_id = path[len(LANES_PREFIX) : -len("/output")]
                return self._route(lambda: self._lane_output_get(lane_id))
            if path.startswith(RUNS_PREFIX) and path.endswith("/output") and path.count("/") == 5:
                run_id = unquote(path[len(RUNS_PREFIX) : -len("/output")])
                return self._route(lambda: self._run_output_get(run_id))
            if path in LOG_PAGE_PATHS:
                return self._route(self._serve_log_page)
            if path == "/api/health":
                return self._route(self._health_get)
            return self._send(404, b"not found", "text/plain; charset=utf-8")

        def do_POST(self) -> None:
            path = urlsplit(self.path).path
            if path.startswith(DISPATCH_PREFIX + "/"):
                return self._route(lambda: self._dispatch_post(path))
            task_prefix = "/api/tasks/"
            owner_suffix = "/owner-action"
            if path.startswith(task_prefix) and path.endswith(owner_suffix):
                task_id = unquote(path[len(task_prefix):-len(owner_suffix)]).strip("/")
                if task_id and "/" not in task_id:
                    return self._api_write(lambda data, body: owner_action(data, task_id, body, now_iso()))
                return self._send(404, b"not found", "text/plain; charset=utf-8")
            if path == "/api/tasks":
                return self._api_write(self._create)
            return self._send(404, b"not found", "text/plain; charset=utf-8")

        def do_PATCH(self) -> None:
            task_id = self._task_id_from_path()
            if not task_id:
                return self._send(404, b"not found", "text/plain; charset=utf-8")
            return self._api_write(lambda data, body: patch_task(data, task_id, body, now_iso()))

        def do_DELETE(self) -> None:
            task_id = self._task_id_from_path()
            if not task_id:
                return self._send(404, b"not found", "text/plain; charset=utf-8")

            def _delete(data, _body):
                delete_task(data, task_id)
                return {"ok": True, "id": task_id}

            return self._api_write(_delete)

        def _task_id_from_path(self):
            path = urlsplit(self.path).path
            prefix = "/api/tasks/"
            if not path.startswith(prefix):
                return None
            ident = unquote(path[len(prefix) :]).strip()
            return ident or None

        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _send_json(self, code: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            return self._send(code, body, "application/json; charset=utf-8")

        def _read_json_body(self) -> dict:
            raw_len = self.headers.get("Content-Length", "0")
            try:
                length = int(raw_len)
            except ValueError:
                raise BoardError(400, "bad Content-Length")
            if length < 0 or length > MAX_BODY:
                raise BoardError(400, "body too large")
            raw = self.rfile.read(length) if length else b"{}"
            if not raw:
                return {}
            try:
                body = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise BoardError(400, "invalid JSON") from exc
            if not isinstance(body, dict):
                raise BoardError(400, "body must be an object")
            return body

        def _load_data(self) -> dict:
            html = html_path.read_text(encoding="utf-8")
            _prefix, inner, _suffix = split_snapshot(html)
            return load_snapshot_text(inner)

        def _api_get_tasks(self) -> None:
            try:
                with write_lock:
                    data = self._load_data()
                return self._send_json(200, {"tasks": data.get("tasks") or []})
            except BoardError as exc:
                return self._send_json(exc.status, {"error": exc.message})
            except OSError:
                return self._send_json(500, {"error": "html missing"})

        def _api_get_releases(self) -> None:
            try:
                with write_lock:
                    data = self._load_data()
                return self._send_json(200, {"releases": data.get("releases") or []})
            except BoardError as exc:
                return self._send_json(exc.status, {"error": exc.message})
            except OSError:
                return self._send_json(500, {"error": "html missing"})

        def _create(self, data: dict, body: dict) -> dict:
            return create_task(data, body, now_iso())

        def _api_write(self, mutator) -> None:
            try:
                body = self._read_json_body()
                with write_lock:
                    result = mutate_html(html_path, lambda data: mutator(data, body))
                    hub.set_stamp(read_stamp(html_path))
                return self._send_json(200, result)
            except BoardError as exc:
                return self._send_json(exc.status, {"error": exc.message})
            except OSError:
                return self._send_json(500, {"error": "write failed"})

        def _route(self, handler) -> None:
            try:
                handler()
            except Forbidden as exc:
                self._send_json(403, {"error": str(exc)})
            except (BoardError,) as exc:
                self._send_json(exc.status, {"error": exc.message})
            except (DispatchBadRequest, DomainError) as exc:
                self._send_json(400, {"error": str(exc)})
            except ports.NotFound as exc:
                self._send_json(404, {"error": str(exc)})
            except (ports.VersionConflict, ports.AlreadyExists, DispatchBusy) as exc:
                self._send_json(409, {"error": str(exc)})
            except (ports.LockTimeout, ports.StoreCorrupt) as exc:
                self._send_json(503, {"error": str(exc)})

        def _allowed_hosts(self):
            port = self.server.server_address[1]
            return ("127.0.0.1:%d" % port, "localhost:%d" % port)

        def _check_host(self) -> None:
            if (self.headers.get("Host") or "").lower() not in self._allowed_hosts():
                raise Forbidden("Host header must be 127.0.0.1 or localhost on this port")

        def _check_origin(self) -> None:
            origin = self.headers.get("Origin")
            if origin is not None and origin.lower() not in tuple("http://" + h for h in self._allowed_hosts()):
                raise Forbidden("cross-origin request rejected")

        def _check_post(self) -> None:
            self._check_host()
            self._check_origin()
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ctype != "application/json":
                raise Forbidden("Content-Type must be application/json")
            given = self.headers.get("X-Board-Token") or ""
            if not token or not hmac.compare_digest(given.encode("utf-8"), token.encode("utf-8")):
                raise Forbidden("missing or wrong X-Board-Token")

        def _dispatch_get(self) -> None:
            self._check_host()
            self._check_origin()
            if dispatcher is None:
                return self._send_json(200, {"enabled": False, "reason": disabled_reason})
            self._send_json(200, dict(dispatcher.snapshot(), token=token))

        def _health_get(self) -> None:
            self._check_host()
            info = {"enabled": False, "state": None}
            if dispatcher is not None:
                info = dict(dispatcher.aggregate_state(), enabled=True)
            self._send_json(
                200,
                {
                    "app": APP_ID,
                    "version": SERVER_VERSION,
                    "features": list(FEATURES),
                    "zones": sorted(ZONES),
                    "ownerActionsSupported": True,
                    "pid": os.getpid(),
                    "port": self.server.server_address[1],
                    "dispatch": info,
                },
            )

        @staticmethod
        def _only(body, allowed) -> None:
            extra = set(body) - set(allowed)
            if extra:
                raise BoardError(400, "unexpected fields: %s" % ", ".join(sorted(extra)))

        def _read_only_dispatch(self) -> None:
            self._check_host()
            self._check_origin()
            if dispatcher is None:
                raise ports.NotFound(disabled_reason)

        def _output_payload(self, run, out):
            query = parse_qs(urlsplit(self.path).query)
            offsets = {}
            for stream in ("stdout", "stderr"):
                raw = (query.get(stream) or ["0"])[0]
                if not raw.isdigit():
                    raise BoardError(400, "%s offset must be a non-negative integer" % stream)
                offsets[stream] = int(raw)
            if run is None:
                for stream in offsets:
                    out[stream] = {"offset": 0, "next": 0, "text": "", "truncated": False}
                return out
            out.update(
                runId=run["runId"],
                cardId=run["cardId"],
                running=run["running"],
                detached=bool(run.get("detached")),
            )
            if out["detached"]:
                out["promptFile"] = os.path.join(run["logDir"], "prompt.md")
            out["reportChannel"] = run.get("reportChannel")
            out["reportFile"] = run.get("reportFile")
            out["reportError"] = run.get("reportError")
            for stream, off in offsets.items():
                out[stream] = read_log_chunk(
                    os.path.join(run["logDir"], stream + ".log"), off, OUTPUT_CHUNK_BYTES
                )
            return out

        def _lane_output_get(self, lane_id) -> None:
            self._read_only_dispatch()
            run = dispatcher.lane_run(lane_id)
            self._send_json(
                200,
                self._output_payload(
                    run, {"laneId": lane_id, "runId": None, "cardId": None, "running": False}
                ),
            )

        def _run_output_get(self, run_id) -> None:
            self._read_only_dispatch()
            run = dispatcher.history_run(run_id)
            self._send_json(200, self._output_payload(run, {"laneId": run["laneId"]}))

        def _serve_log_page(self) -> None:
            self._check_host()
            self._check_origin()
            try:
                body = log_html_path.read_bytes()
            except OSError as exc:
                raise ports.NotFound("agent log page missing: %s" % log_html_path) from exc
            self._send(200, body, "text/html; charset=utf-8")

        def _dispatch_post(self, path) -> None:
            self._check_post()
            if dispatcher is None:
                raise Forbidden(disabled_reason)
            body = self._read_json_body()
            if path == DISPATCH_PREFIX + "/lanes":
                self._only(body, ("agent", "maxCards"))
                snap = dispatcher.add_lane(body.get("agent"), body.get("maxCards"))
            elif path == DISPATCH_PREFIX + "/unskip":
                if not isinstance(body.get("id"), str):
                    raise BoardError(400, "id (string) is required")
                snap = dispatcher.unskip(body["id"])
            elif path.startswith(LANES_PREFIX) and path.count("/") == 5 and path.rsplit("/", 1)[1] in LANE_ACTIONS:
                lane_id, action = path[len(LANES_PREFIX) :].split("/")
                if action == "start":
                    self._only(body, ("agent", "maxCards"))
                    snap = dispatcher.start_lane(lane_id, body.get("agent"), body.get("maxCards"))
                elif action == "stop":
                    self._only(body, ("mode",))
                    snap = dispatcher.stop_lane(lane_id, body.get("mode", "after-current"))
                else:
                    self._only(body, ())
                    snap = dispatcher.remove_lane(lane_id)
            else:
                return self._send_json(404, {"error": "not found"})
            self._send_json(200, dict(snap, token=token))

        def _serve_html(self) -> None:
            try:
                body = html_path.read_bytes()
            except OSError:
                return self._send(404, b"html missing", "text/plain; charset=utf-8")
            return self._send(200, body, "text/html; charset=utf-8")

        def _serve_events(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            last = -1
            try:
                while True:
                    gen, stamp = hub.wait(last, timeout=20.0)
                    if gen == last:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                        continue
                    last = gen
                    data = json.dumps(stamp_payload(stamp), separators=(",", ":"))
                    self.wfile.write(("data: %s\n\n" % data).encode("utf-8"))
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                return

    return Handler


def _ticker(dispatcher, stop_event, interval: float) -> None:
    while not stop_event.wait(interval):
        try:
            dispatcher.tick()
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write("[dispatch] tick error: %r\n" % (exc,))
            sys.stderr.flush()


def report_inbox_dir(runtime_dir, explicit=None):
    """The repo inbox for the real runtime; a separate runtime (temp copy, tests) gets its own (INV-BD-46)."""
    if explicit:
        return os.path.abspath(explicit)
    if os.path.normcase(os.path.abspath(str(runtime_dir))) == os.path.normcase(os.path.abspath(str(DEFAULT_RUNTIME))):
        return str(DEFAULT_REPORT_INBOX)
    return os.path.join(str(runtime_dir), "report-inbox")


def build_dispatcher(task_store, tasks_path: str, config_path: Path, runtime_dir: Path, report_inbox=None):
    try:
        config = load_config(str(config_path))
    except ConfigError as exc:
        return None, "派工設定無效:%s" % exc
    runtime_dir.mkdir(parents=True, exist_ok=True)
    state_path = str(runtime_dir / "dispatch.json")
    inbox_dir = report_inbox_dir(runtime_dir, report_inbox)
    dispatcher = Dispatcher(
        task_store,
        DispatchStateStore(state_path),
        SubprocessLauncher(),
        SystemClock(),
        config,
        repo=str(REPO),
        tasks_path=str(tasks_path),
        state_path=state_path,
        log_root=str(runtime_dir / "logs"),
        python=sys.executable,
        default_tasks_path=str(DEFAULT_HTML),
        default_state_path=str(DEFAULT_RUNTIME / "dispatch.json"),
        available=lambda agent: agent["command"][0] == "{python}"
        or shutil.which(executable(agent)) is not None,
        inbox=ReportInbox(inbox_dir, str(runtime_dir / "reports")),
    )
    dispatcher.recover()
    return dispatcher, None


def probe_health(port: int) -> dict | None:
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=1.5)
        conn.request("GET", "/api/health")
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        if resp.status != 200:
            return None
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def is_current_board(port: int) -> bool:
    data = probe_health(port)
    if not data:
        return False
    feats = data.get("features") or []
    return data.get("app") == APP_ID and "dispatch" in feats and "dispatch-lanes" in feats


def listening_pids(port: int) -> list:
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"], text=True, encoding="utf-8", errors="replace"
        )
    except OSError:
        return []
    want = {"127.0.0.1:%d" % port, "[::1]:%d" % port}
    pids = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[3].upper() != "LISTENING":
            continue
        if parts[1] in want:
            try:
                pids.append(int(parts[4]))
            except ValueError:
                continue
    return pids


def process_command_line(pid: int) -> str:
    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_Process -Filter 'ProcessId=%d').CommandLine" % pid,
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
        )
        return (out or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def replace_stale_listener(port: int) -> str:
    """If this port is an old board-watch (no /api/health), kill only that board_watch.py. Never 8788."""
    if port in RESERVED_FOREIGN_PORTS:
        raise BoardError(400, "mailbox port")
    if is_current_board(port):
        return "current"
    pids = listening_pids(port)
    if not pids:
        return "missing"
    killed = False
    for pid in pids:
        cmd = process_command_line(pid).lower()
        if "board_watch.py" not in cmd:
            return "foreign"
        subprocess.check_call(["taskkill", "/PID", str(pid), "/F"])
        killed = True
    if killed:
        for _ in range(30):
            if not listening_pids(port):
                break
            time.sleep(0.1)
        return "replaced"
    return "missing"


def shutdown_dispatcher(dispatcher) -> None:
    if dispatcher is None:
        return
    for cur in dispatcher.shutdown():
        sys.stderr.write(
            "[dispatch] stopping lane %s pid %s card %s (needs-human)\n"
            % (cur.get("laneId"), cur.get("pid"), cur.get("cardId"))
        )


def serve(
    html_path: Path,
    host: str,
    port: int,
    open_browser: bool,
    dispatcher=None,
    disabled_reason=None,
    log_html_path=None,
    tick_seconds: float = 1.0,
) -> None:
    hub = StampHub()
    hub.set_stamp(read_stamp(html_path))
    stop = threading.Event()
    watcher = threading.Thread(
        target=watch_loop, args=(html_path, hub, stop), name="board-watch", daemon=True
    )
    watcher.start()
    token = secrets.token_urlsafe(32) if dispatcher is not None else None
    httpd = ThreadingHTTPServer(
        (host, port),
        build_handler(
            html_path,
            hub,
            dispatcher=dispatcher,
            token=token,
            disabled_reason=disabled_reason,
            log_html_path=log_html_path,
        ),
    )
    httpd.daemon_threads = True
    if dispatcher is not None:
        ticker = threading.Thread(
            target=_ticker,
            args=(dispatcher, stop, tick_seconds),
            daemon=True,
            name="board-dispatch-ticker",
        )
        ticker.start()
    url = "http://%s:%d/" % (host, port)
    sys.stderr.write("board-watch %s  (watching %s)\n" % (url, html_path))
    if dispatcher is not None:
        sys.stderr.write("dispatch: ON  runtime %s  app %s v%d\n" % (DEFAULT_RUNTIME, APP_ID, SERVER_VERSION))
    else:
        sys.stderr.write("dispatch: OFF  %s\n" % (disabled_reason or DISPATCH_DISABLED_REASON))
    sys.stderr.flush()
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        shutdown_dispatcher(dispatcher)
        httpd.shutdown()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="VGenAxIs 看板 HTML 監看小後端")
    ap.add_argument("--html", default=str(DEFAULT_HTML), help="要監看的 HTML 路徑")
    ap.add_argument("--log-html", default=str(DEFAULT_LOG_HTML), help="/agent-log 頁")
    ap.add_argument("--dispatch-config", default=str(DEFAULT_DISPATCH_CONFIG))
    ap.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME))
    ap.add_argument(
        "--report-inbox",
        help="agents' report files (default tools/board/report-inbox for the default runtime, else <runtime>/report-inbox)",
    )
    ap.add_argument("--no-dispatch", action="store_true", help="只提供燈號寫回，不啟動派工器")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument(
        "--replace-stale",
        action="store_true",
        help="kill old board-watch on this port if /api/health is missing; do not serve",
    )
    args = ap.parse_args(argv)
    if args.host not in ("127.0.0.1", "localhost"):
        sys.stderr.write("只允許綁 127.0.0.1 / localhost\n")
        return 2
    if args.port in RESERVED_FOREIGN_PORTS:
        sys.stderr.write("port %s is reserved for HoneyBadgerCreator mailbox; use 28789\n" % args.port)
        return 2
    if args.replace_stale:
        sys.stderr.write("board-watch %s\n" % replace_stale_listener(args.port))
        return 0
    html_path = Path(args.html).resolve()
    dispatcher, reason = (None, DISPATCH_DISABLED_REASON) if args.no_dispatch else build_dispatcher(
        HtmlSnapshotStore(html_path),
        str(html_path),
        Path(args.dispatch_config),
        Path(args.runtime_dir),
        report_inbox=args.report_inbox,
    )
    serve(
        html_path,
        args.host,
        args.port,
        open_browser=not args.no_browser,
        dispatcher=dispatcher,
        disabled_reason=reason,
        log_html_path=Path(args.log_html),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
