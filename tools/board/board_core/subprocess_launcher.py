"""Driven adapters: start agent CLIs as child processes, and the system clock (BOARD-DISPATCH-01).

INV-BD-15 Popen(argv_list) without a shell; the prompt goes to <log>/prompt.md and, for prompt_via=stdin,
          is written to the child's stdin as UTF-8 and closed.
INV-BD-18 Windows: CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW; tree kill via `taskkill /PID <pid> /T /F`.
INV-BD-19 <log>/prompt.md, stdout.log, stderr.log, meta.json.
"""
import json
import os
import shutil
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone

from . import ports

_WIN = os.name == "nt"
_CREATE_NO_WINDOW = 0x08000000
_READ_LIMIT = 256 * 1024


class SystemClock:
    def time(self):
        return time.time()

    def now_iso(self):
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _tail(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - _READ_LIMIT))
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _utf8_complete_end(data):
    """Length of `data` without a trailing partial UTF-8 sequence (the writer may be mid-character)."""
    for back in range(1, min(4, len(data)) + 1):
        b = data[-back]
        if b < 0x80:
            return len(data)
        if b >= 0xC0:
            need = 2 if b < 0xE0 else (3 if b < 0xF0 else 4)
            return len(data) if back >= need else len(data) - back
    return len(data)


def read_log_chunk(path, offset, limit):
    """Incremental read of a run log for the live 啟動視窗 (INV-BD-30).

    offset beyond the file (log replaced) restarts at 0; more than `limit` new bytes skips ahead to the last
    `limit` bytes and sets truncated. `next` is the offset to ask for next time.
    """
    try:
        size = os.path.getsize(path)
    except OSError:
        return {"offset": 0, "next": 0, "text": "", "truncated": False}
    start = offset if 0 <= offset <= size else 0
    truncated = size - start > limit
    if truncated:
        start = size - limit
    try:
        with open(path, "rb") as f:
            f.seek(start)
            data = f.read(size - start)
    except OSError:
        return {"offset": start, "next": start, "text": "", "truncated": truncated}
    end = _utf8_complete_end(data)
    return {"offset": start, "next": start + end, "text": data[:end].decode("utf-8", errors="replace"),
            "truncated": truncated}


class ProcessHandle:
    def __init__(self, proc, stdout_f, stderr_f, log_dir):
        self._proc = proc
        self._files = [stdout_f, stderr_f]
        self.pid = proc.pid
        self.log_dir = log_dir

    def poll(self):
        return self._proc.poll()

    def terminate_tree(self):
        if self._proc.poll() is not None:
            return
        if _WIN:
            subprocess.run(["taskkill", "/PID", str(self.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=_CREATE_NO_WINDOW)
        else:
            try:
                os.killpg(os.getpgid(self.pid), signal.SIGKILL)
            except OSError:
                pass
        try:
            self._proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait(timeout=5)

    def read_output(self):
        for f in self._files:
            if not f.closed:
                f.flush()
        return _tail(os.path.join(self.log_dir, "stdout.log")) + "\n" + _tail(os.path.join(self.log_dir, "stderr.log"))

    def close(self):
        for f in self._files:
            if not f.closed:
                f.close()


def _feed_stdin(stream, data):
    try:
        stream.write(data)
    except OSError:
        pass
    finally:
        try:
            stream.close()
        except OSError:
            pass


class SubprocessLauncher:
    def launch(self, argv, cwd, env, prompt_text, prompt_via, log_dir):
        exe = shutil.which(argv[0])
        if exe is None:
            raise ports.LaunchError("%s not found on PATH" % argv[0])
        os.makedirs(log_dir, exist_ok=True)
        prompt_bytes = prompt_text.encode("utf-8")
        with open(os.path.join(log_dir, "prompt.md"), "wb") as f:
            f.write(prompt_bytes)
        stdout_f = open(os.path.join(log_dir, "stdout.log"), "wb")
        stderr_f = open(os.path.join(log_dir, "stderr.log"), "wb")
        flags = (subprocess.CREATE_NEW_PROCESS_GROUP | _CREATE_NO_WINDOW) if _WIN else 0
        try:
            proc = subprocess.Popen([exe] + list(argv[1:]), cwd=cwd, env=env,
                                    stdin=subprocess.PIPE if prompt_via == "stdin" else subprocess.DEVNULL,
                                    stdout=stdout_f, stderr=stderr_f, creationflags=flags,
                                    start_new_session=not _WIN)
        except OSError as e:
            stdout_f.close()
            stderr_f.close()
            raise ports.LaunchError("cannot start %s: %s" % (argv[0], e))
        if prompt_via == "stdin":
            threading.Thread(target=_feed_stdin, args=(proc.stdin, prompt_bytes), daemon=True).start()
        meta = {"argv": [exe] + list(argv[1:]), "cwd": cwd, "pid": proc.pid, "promptVia": prompt_via,
                "startedAt": SystemClock().now_iso(),
                "env": {k: env[k] for k in sorted(env) if k.startswith("HB_")}}
        with open(os.path.join(log_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=1)
        return ProcessHandle(proc, stdout_f, stderr_f, log_dir)
