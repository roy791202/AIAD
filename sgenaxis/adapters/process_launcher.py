"""Real AgentLauncher: starts the agent CLI as a child process (never through a shell).

- argv[0] gets %VAR% expansion and PATH lookup; a .cmd/.bat shim runs under cmd.exe,
  so every argument (and the shim path) is re-checked against dispatch.SAFE_ARG (INV-BD-39).
- The prompt is always written to the run's prompt file; stdin agents also get it on stdin.
- Captured runs: stdout+stderr go to logs/<runId>/output.log and a bounded in-memory tail.
- Window (detached) runs get no pipes; only a report or the timeout ends them.
- terminate(): normal end of the process tree first, then forced end after `kill_grace`
  seconds, on a worker thread so the UI never waits.
"""

from __future__ import annotations

import codecs
import os
import shutil
import subprocess
import threading

from sgenaxis.core.dispatch import SAFE_ARG
from sgenaxis.core.ports import LaunchFailed, LaunchRequest

OUTPUT_LIMIT = 65536
KILL_GRACE_SECONDS = 5.0
_CHUNK = 4096
_SHIMS = (".cmd", ".bat")
_IS_WINDOWS = os.name == "nt"
_CAPTURED_FLAGS = (subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if _IS_WINDOWS else 0
_DETACHED_FLAGS = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if _IS_WINDOWS else 0
DETACHED_NOTE = "[視窗模式] 輸出不擷取；看板只從回報檔得知結果。\n"


class ProcessLauncher:
    def __init__(self, output_limit: int = OUTPUT_LIMIT, kill_grace: float = KILL_GRACE_SECONDS) -> None:
        self.output_limit = output_limit
        self.kill_grace = kill_grace

    def launch(self, request: LaunchRequest) -> ProcessHandle:
        if not request.cwd or not os.path.isdir(request.cwd):
            raise LaunchFailed(f"工作目錄不存在：{request.cwd or '(未設定)'}")
        if not request.argv:
            raise LaunchFailed("命令列是空的")
        executable = _resolve(request.argv[0])
        argv = [executable, *request.argv[1:]]
        if executable.lower().endswith(_SHIMS):
            for arg in argv:
                if not SAFE_ARG.match(arg):
                    raise LaunchFailed(f"命令列參數含不安全的字元：{arg}")
        log_path = _write_prompt(request)
        env = dict(os.environ)
        env.update(request.env)
        try:
            if request.detached:
                process = subprocess.Popen(
                    argv,
                    cwd=request.cwd,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=_DETACHED_FLAGS,
                )
                return ProcessHandle(process, None, "", self.output_limit, self.kill_grace, DETACHED_NOTE)
            stdin_text = request.prompt if request.prompt_via == "stdin" else None
            process = subprocess.Popen(
                argv,
                cwd=request.cwd,
                env=env,
                stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=_CAPTURED_FLAGS,
            )
        except OSError as exc:
            raise LaunchFailed(f"無法啟動 {request.argv[0]}：{exc}") from exc
        return ProcessHandle(process, stdin_text, log_path, self.output_limit, self.kill_grace)


class ProcessHandle:
    def __init__(
        self,
        process: subprocess.Popen,
        stdin_text: str | None,
        log_path: str,
        output_limit: int,
        kill_grace: float,
        note: str = "",
    ) -> None:
        self.process = process
        self.pid = process.pid
        self._limit = output_limit
        self._kill_grace = kill_grace
        self._text = note
        self._lock = threading.Lock()
        self._stopper: threading.Thread | None = None
        self._reader: threading.Thread | None = None
        if stdin_text is not None:
            threading.Thread(target=self._feed, args=(stdin_text,), daemon=True).start()
        if process.stdout is not None:
            self._reader = threading.Thread(target=self._read, args=(log_path,), daemon=True)
            self._reader.start()

    def poll(self) -> int | None:
        code = self.process.poll()
        if code is not None and self._reader is not None and self._reader.is_alive():
            self._reader.join(1.0)
        return code

    def output(self) -> str:
        with self._lock:
            return self._text[-self._limit:]

    def terminate(self) -> None:
        if self._stopper is not None or self.process.poll() is not None:
            return
        self._stopper = threading.Thread(target=self._stop_tree, name=f"stop-{self.pid}")
        self._stopper.start()

    def _feed(self, text: str) -> None:
        try:
            self.process.stdin.write(text.encode("utf-8"))
            self.process.stdin.close()
        except OSError:
            pass

    def _read(self, log_path: str) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        log = None
        if log_path:
            try:
                log = open(log_path, "a", encoding="utf-8", newline="")
            except OSError:
                log = None
        try:
            while True:
                chunk = self.process.stdout.read1(_CHUNK)
                text = decoder.decode(chunk, final=not chunk)
                if text:
                    self._append(text)
                    if log is not None:
                        log.write(text)
                        log.flush()
                if not chunk:
                    break
        except (OSError, ValueError):
            pass
        finally:
            if log is not None:
                log.close()

    def _append(self, text: str) -> None:
        with self._lock:
            self._text += text
            if len(self._text) > 2 * self._limit:
                self._text = self._text[-self._limit:]

    def _stop_tree(self) -> None:
        if not _IS_WINDOWS:
            self.process.terminate()
            if not _waited(self.process, self._kill_grace):
                self.process.kill()
            return
        _taskkill(self.pid, force=False)
        if not _waited(self.process, self._kill_grace):
            _taskkill(self.pid, force=True)
            _waited(self.process, self._kill_grace)


def _resolve(command: str) -> str:
    expanded = os.path.expandvars(command)
    if os.path.isfile(expanded):
        return os.path.abspath(expanded)
    found = shutil.which(expanded)
    if not found:
        raise LaunchFailed(f"找不到 {command}（PATH 上沒有，請確認已安裝）")
    return found


def _write_prompt(request: LaunchRequest) -> str:
    if not request.prompt_file:
        return ""
    folder = os.path.dirname(request.prompt_file)
    try:
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(request.prompt_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(request.prompt)
    except OSError as exc:
        raise LaunchFailed(f"無法寫入 prompt 檔：{request.prompt_file}：{exc}") from exc
    return os.path.join(folder, "output.log") if folder else ""


def _waited(process: subprocess.Popen, seconds: float) -> bool:
    try:
        process.wait(timeout=seconds)
        return True
    except subprocess.TimeoutExpired:
        return False


def _taskkill(pid: int, force: bool) -> None:
    system = os.environ.get("SystemRoot", r"C:\Windows")
    command = [os.path.join(system, "System32", "taskkill.exe"), "/T", "/PID", str(pid)]
    if force:
        command.insert(1, "/F")
    subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
