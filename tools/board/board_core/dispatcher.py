"""Application service: board dispatcher with parallel agent lanes (BOARD-DISPATCH-01 §3.3, §3.8).

Each lane runs one agent at a time and follows the same machine as the original single dispatcher:
idle --start--> running(card) --report + exit--> running(next) | idle(limit | no-candidates | user)
running --stop(after-current)--> stopping --run ends--> idle(user)
running|stopping --stop(now)--> kill tree, card needs-human, idle(user)
running --auth/quota/launch failure | repeated fast no-report--> error

INV-BD-25 lanes (id, agent, maxCards) persist in the dispatch state store and survive server restarts.
INV-BD-26 at most config max_lanes lanes (default 3, hard cap 6); add beyond that -> DispatchBusy (409).
INV-BD-27 card claims happen under one dispatcher lock and exclude every lane's running card, so two
          lanes never get the same card.
INV-BD-28 a report (board.py report, another process) lands on the lane whose current run is that card.
INV-BD-33 an unreported exit whose output matches the agent's limit_error_patterns (usage / session limit)
          halts the lane like auth-error: the card is reverted, not marked needs-human.
INV-BD-34 fast_fail_limit consecutive unreported exits each under fast_fail_seconds halt the lane (fast-fail),
          so an unknown CLI failure cannot sweep the whole board; a report or a slower run resets the count.
INV-BD-37 history_run(run_id) resolves a running or recorded run (history only) to its log dir; ids are a strict
          [A-Za-z0-9_.-] token so a request cannot name an arbitrary path.
INV-BD-40 a detached (GUI window) agent's launcher exits at once: its exit is never completion, never no-report,
          never auth/quota/fast-fail. The run ends only by a report or the timeout.
INV-BD-41 a detached run is never killed (the IDE may host other windows): timeout / stop-now stop tracking and
          mark it needs-human; server shutdown leaves it running and recover() keeps tracking it.
INV-BD-43..46 (report channels, see report_channels.py): every tick polls <inbox>/<runId>.json for each running
          round (detached too) and applies a valid file like `board.py report` (by=agent); on a process exit
          without a report the output marker is tried next; a still-unreported exit waits
          exit_report_grace_seconds (re-reading the file) before no-report. An invalid file stays in the inbox
          (lane shows the error, the agent may fix it) until the round ends, then moves to rejected/.
          History and lastRun record reportChannel (file | marker | cli).

Works only through ports: ITaskStore (via use cases), IDispatchStateStore, IAgentLauncher, IClock, ReportInbox.
tick() is the listener: it notices reports, process exits and timeouts for every lane.
"""
import os
import re
import threading

from . import dispatch, dispatch_config, ports, report_channels, usecases
from .dispatch import new_lane
from .domain import DomainError
from .report_inbox import ReportInbox

HISTORY_MAX = 50
RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,160}$")
STOP_LABEL = {"limit": "已達上限", "no-candidates": "沒有可派的工項", "user": "使用者停止",
              "auth-error": "Agent 未登入", "quota-error": "CLI 額度用完", "fast-fail": "連續快速失敗",
              "launch-error": "Agent 無法啟動", "server-shutdown": "伺服器關閉"}
WINDOW_LEFT_OPEN = ";Agent 視窗不會被自動關閉,請到該視窗確認並手動停止 / 關閉"


class DispatchBusy(Exception):
    """Lane already active, lane cap reached, or removing a busy lane (INV-BD-10/26) -> HTTP 409."""


class DispatchBadRequest(ValueError):
    """Unknown agent, bad maxCards or stop mode -> HTTP 400."""


def _run_stamp(now_iso):
    digits = re.sub(r"\D", "", now_iso)[:14]
    return "%s-%s" % (digits[:8], digits[8:14])


def _safe_id(card_id):
    return re.sub(r"[^A-Za-z0-9_.\-]", "_", card_id)


def _find(st, lane_id):
    for lane in st.get("lanes") or []:
        if lane["id"] == lane_id:
            return lane
    raise ports.NotFound("no agent lane %r" % (lane_id,))


def _last_line(text):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines[-1][:300] if lines else ""


def _busy(lane):
    return lane["state"] in ("running", "stopping") or bool(lane.get("current"))


class Dispatcher:
    def __init__(self, task_store, state_store, launcher, clock, config, repo, tasks_path, state_path, log_root,
                 python="python", default_tasks_path=None, default_state_path=None, available=None, inbox=None):
        self.tasks = task_store
        self.state = state_store
        self.launcher = launcher
        self.clock = clock
        self.config = config
        self.repo = repo
        self.tasks_path = tasks_path
        self.state_path = state_path
        self.log_root = log_root
        self.python = python
        self.default_tasks_path = default_tasks_path or tasks_path
        self.default_state_path = default_state_path or state_path
        self._available = available or (lambda agent: True)
        self._agents = {a["id"]: a for a in config["agents"]}
        self._mu = threading.RLock()
        runtime = os.path.dirname(log_root)
        self.inbox = inbox or ReportInbox(os.path.join(runtime, "report-inbox"), os.path.join(runtime, "reports"))
        self._handles = {}
        self._report_seen_at = {}
        self._exit_seen_at = {}

    # ---------- queries ----------
    def _skip_kinds(self):
        return self.config.get("skip_kinds", dispatch.DEFAULT_SKIP_KINDS)

    def _max_lanes(self):
        return self.config.get("max_lanes", dispatch_config.DEFAULTS["max_lanes"])

    @staticmethod
    def _excluded(st):
        ids = set(st.get("skipped") or {})
        for lane in st.get("lanes") or []:
            if lane.get("current"):
                ids.add(lane["current"]["cardId"])
        return ids

    def _lane_view(self, lane):
        cur = lane.get("current")
        if cur:
            cur = dict(cur, elapsedSec=int(self.clock.time() - cur.get("startedEpoch", self.clock.time())))
        return dict(lane, current=cur, stopLabel=STOP_LABEL.get(lane.get("stopReason")))

    def snapshot(self):
        with self._mu:
            st = self.state.load()
            nxt = dispatch.select_next(usecases.list_tasks(self.tasks), self._excluded(st), self._skip_kinds())
            lanes = [self._lane_view(ln) for ln in st.get("lanes") or []]
            return {
                "enabled": True,
                "lanes": lanes,
                "active": sum(1 for ln in lanes if _busy(ln)),
                "limits": {"maxLanes": self._max_lanes(), "hardCap": dispatch_config.LANES_HARD_CAP},
                "history": st.get("history") or [],
                "skipped": st.get("skipped") or {},
                "next": ({"id": nxt["id"], "title": nxt.get("title", ""), "zone": nxt.get("zone")} if nxt else None),
                "agents": [{"id": a["id"], "label": a["label"], "available": bool(self._available(a))}
                           for a in self.config["agents"]],
                "defaults": {"maxCards": self.config["max_cards_default"],
                             "maxCardsLimit": self.config["max_cards_limit"],
                             "unlimited": True,
                             "timeoutMinutes": self.config["timeout_minutes"]},
            }

    def aggregate_state(self):
        """For /api/health: running if any lane runs, else stopping if any stops, else idle."""
        with self._mu:
            lanes = self.state.load().get("lanes") or []
            states = [ln["state"] for ln in lanes]
            state = "running" if "running" in states else ("stopping" if "stopping" in states else "idle")
            return {"state": state, "lanes": len(lanes), "active": sum(1 for ln in lanes if _busy(ln))}

    def lane_run(self, lane_id):
        """The run whose output the lane's 啟動視窗 shows: the current one, else the last one (INV-BD-30)."""
        with self._mu:
            lane = _find(self.state.load(), lane_id)
            cur = lane.get("current")
            if cur:
                return self._run_info(cur, True)
            last = lane.get("lastRun")
            if last:
                return self._run_info(last, False)
            return None

    def _run_info(self, run, running, lane_id=None):
        report = run.get("report") or {}
        info = {"runId": run["runId"], "cardId": run["cardId"], "logDir": run["logDir"], "running": running,
                "detached": bool(run.get("detached")),
                "reportChannel": run.get("reportChannel") or (report.get("channel", "cli") if report else None),
                "reportFile": self.inbox.path(run["runId"]), "reportError": run.get("reportError")}
        if lane_id is not None:
            info["laneId"] = lane_id
        return info

    def history_run(self, run_id):
        """A running or recorded run by id, for the log page's past-run view (INV-BD-37)."""
        if not isinstance(run_id, str) or not RUN_ID_RE.match(run_id):
            raise DispatchBadRequest("bad run id %r" % (run_id,))
        with self._mu:
            st = self.state.load()
            for lane in st.get("lanes") or []:
                cur = lane.get("current")
                if cur and cur["runId"] == run_id:
                    return self._run_info(cur, True, lane["id"])
            for h in st.get("history") or []:
                if h.get("runId") == run_id and h.get("logDir"):
                    return self._run_info(h, False, h.get("laneId"))
        raise ports.NotFound("no recorded run %s" % run_id)

    # ---------- validation ----------
    def _agent(self, agent_id, need_available):
        agent = self._agents.get(agent_id) if isinstance(agent_id, str) else None
        if agent is None:
            raise DispatchBadRequest("unknown agent %r (configured: %s)" % (agent_id, ", ".join(self._agents)))
        if need_available and not self._available(agent):
            raise DispatchBadRequest("agent %s: executable %s not found" % (agent_id, agent["command"][0]))
        return agent

    def _max_cards(self, value):
        try:
            return dispatch.validate_max_cards(value, self.config["max_cards_limit"])
        except DomainError as e:
            raise DispatchBadRequest(str(e))

    # ---------- lane commands ----------
    def add_lane(self, agent_id=None, max_cards=None):
        with self._mu:
            if agent_id is None:
                ready = [a for a in self.config["agents"] if self._available(a)]
                agent_id = (ready or self.config["agents"])[0]["id"]
            self._agent(agent_id, need_available=False)
            max_cards = self._max_cards(self.config["max_cards_default"] if max_cards is None else max_cards)
            cap = self._max_lanes()
            if len(self.state.load().get("lanes") or []) >= cap:
                raise DispatchBusy("已達上限:最多 %d 個 Agent 同時派工(max_lanes=%d)" % (cap, cap))

            def mutate(s):
                seq = int(s.get("laneSeq") or 0) + 1
                return dict(s, laneSeq=seq, lanes=list(s.get("lanes") or []) + [new_lane("L%d" % seq, agent_id, max_cards)])
            self.state.update(mutate)
            return self.snapshot()

    def remove_lane(self, lane_id):
        with self._mu:
            lane = _find(self.state.load(), lane_id)
            if _busy(lane):
                raise DispatchBusy("agent lane %s is running; stop it before removing" % lane_id)
            self.state.update(lambda s: dict(s, lanes=[ln for ln in s.get("lanes") or [] if ln["id"] != lane_id]))
            self._handles.pop(lane_id, None)
            self._report_seen_at.pop(lane_id, None)
            return self.snapshot()

    def start_lane(self, lane_id, agent_id, max_cards):
        with self._mu:
            self._agent(agent_id, need_available=True)
            max_cards = self._max_cards(max_cards)
            st = self.state.load()
            lane = _find(st, lane_id)
            if _busy(lane):
                raise DispatchBusy("agent lane %s already running (%s)" % (lane_id, (lane.get("current") or {}).get("cardId")))
            active = sum(1 for ln in st.get("lanes") or [] if _busy(ln))
            if active >= self._max_lanes():
                raise DispatchBusy("已達上限:最多 %d 個 Agent 同時執行" % self._max_lanes())
            session = {"agent": agent_id, "maxCards": max_cards, "dispatched": 0,
                       "startedAt": self.clock.now_iso(), "stopRequested": False}
            self._update_lane(lane_id, lambda ln: dict(ln, agent=agent_id, maxCards=max_cards, state="running",
                                                       stopReason=None, error=None, session=session))
            self._dispatch_next(lane_id)
            return self.snapshot()

    def stop_lane(self, lane_id, mode):
        with self._mu:
            if mode not in dispatch.STOP_MODES:
                raise DispatchBadRequest("stop mode must be after-current or now, got %r" % (mode,))
            lane = _find(self.state.load(), lane_id)
            if not lane.get("current"):
                self._update_lane(lane_id, lambda ln: dict(
                    ln, state="idle", stopReason="user" if ln["state"] != "error" else ln.get("stopReason")))
                return self.snapshot()
            if mode == "now":
                cur = lane["current"]
                handle = self._handles.get(lane_id)
                if handle is not None and not cur.get("detached"):
                    handle.terminate_tree()
                note = "使用者按下立即終止" + (WINDOW_LEFT_OPEN if cur.get("detached") else "")
                self._finish(lane_id, cur, "terminated", note, self._exit_code(lane_id))
                self._settle(lane_id, "user")
            else:
                self._update_lane(lane_id, lambda ln: dict(ln, state="stopping",
                                                           session=dict(ln.get("session") or {}, stopRequested=True)))
            return self.snapshot()

    def unskip(self, card_id):
        with self._mu:
            if card_id not in (self.state.load().get("skipped") or {}):
                raise ports.NotFound("card %s is not on the needs-human list" % card_id)

            def mutate(s):
                sk = dict(s.get("skipped") or {})
                sk.pop(card_id, None)
                return dict(s, skipped=sk)
            self.state.update(mutate)
            return self.snapshot()

    # ---------- listener ----------
    def tick(self):
        with self._mu:
            for lane in self.state.load().get("lanes") or []:
                self._tick_lane(lane["id"])

    def _tick_lane(self, lane_id):
        try:
            lane = _find(self.state.load(), lane_id)
        except ports.NotFound:
            return
        cur = lane.get("current")
        if cur is None:
            if lane["state"] == "running":
                self._dispatch_next(lane_id)
            return
        cur = self._poll_report_file(lane_id, cur)
        if cur.get("detached"):
            self._tick_detached(lane_id, cur)
            return
        handle = self._handles.get(lane_id)
        if handle is None:
            return
        now = self.clock.time()
        code = handle.poll()
        report = cur.get("report")
        if code is None:
            if report:
                seen = self._report_seen_at.setdefault(lane_id, now)
                if now - seen >= self.config["report_grace_seconds"]:
                    handle.terminate_tree()
                    self._finish(lane_id, cur, report["outcome"], report.get("note", ""), self._exit_code(lane_id))
                    self._after_run(lane_id)
                return
            if now >= cur["deadlineEpoch"]:
                handle.terminate_tree()
                self._finish(lane_id, cur, "timeout", self._unreported("超過 %d 分鐘" % cur["timeoutMinutes"], cur),
                             self._exit_code(lane_id))
                self._after_run(lane_id)
            return
        if report:
            self._finish(lane_id, cur, report["outcome"], report.get("note", ""), code)
            self._after_run(lane_id)
            return
        agent = self._agents.get(cur["agent"]) or {}
        raw_output = handle.read_output()
        marker = report_channels.find_marker(raw_output, cur["runId"])
        if marker:
            cur = self._accept_report(lane_id, cur, marker[0], marker[1], "marker")
            if cur.get("report"):
                self._finish(lane_id, cur, marker[0], cur["report"]["note"], code)
                self._after_run(lane_id)
            return  # store busy: try again next tick
        output = raw_output.lower()
        if any(p.lower() in output for p in agent.get("auth_error_patterns", []) if p):
            self._finish(lane_id, cur, "auth-error", agent.get("login_hint", ""), code)
            self._halt(lane_id, "auth-error", "%s(輸出含登入錯誤;日誌 %s)" % (agent.get("login_hint") or "Agent 未登入", cur["logDir"]))
            return
        if any(p.lower() in output for p in agent.get("limit_error_patterns", []) if p):
            tail = _last_line(raw_output)
            self._finish(lane_id, cur, "quota-error", tail, code)
            self._halt(lane_id, "quota-error", "%s 額度已用完或被限流,已停止派工:%s(日誌 %s)"
                       % (agent.get("label") or cur["agent"], tail, cur["logDir"]))
            return
        exited = self._exit_seen_at.setdefault(lane_id, now)
        if now - exited < self._cfg("exit_report_grace_seconds"):
            return  # the agent may still be flushing its report file (INV-BD-46)
        fast = exited - cur.get("startedEpoch", exited) < self._cfg("fast_fail_seconds")
        self._finish(lane_id, cur, "no-report", self._unreported("行程結束(exit %s)但沒有回報" % code, cur), code)
        self._after_run(lane_id, fast_fail=fast, log_dir=cur["logDir"], tail=_last_line(raw_output))

    def _tick_detached(self, lane_id, cur):
        """INV-BD-40/41: the launcher's exit and output mean nothing; only a report or the deadline ends the run."""
        report = cur.get("report")
        if report:
            self._finish(lane_id, cur, report["outcome"], report.get("note", ""), self._exit_code(lane_id))
            self._after_run(lane_id)
        elif self.clock.time() >= cur["deadlineEpoch"]:
            note = self._unreported("超過 %d 分鐘沒有回報" % cur["timeoutMinutes"], cur) + WINDOW_LEFT_OPEN
            self._finish(lane_id, cur, "timeout", note, self._exit_code(lane_id))
            self._after_run(lane_id)

    def _set_current(self, lane_id, cur, **fields):
        new = dict(cur, **fields)
        self._update_lane(lane_id, lambda ln: dict(ln, current=new)
                          if ln.get("current") and ln["current"]["runId"] == cur["runId"] else ln)
        return new

    def _accept_report(self, lane_id, cur, outcome, note, channel):
        """Apply a file / marker report like `board.py report` does; returns cur (with report unless the store was busy)."""
        now = self.clock.now_iso()
        try:
            usecases.report_outcome(self.tasks, cur["cardId"], outcome, note, by="agent", now=now)
        except ports.LockTimeout:
            return cur
        except (ports.NotFound, ports.VersionConflict, ports.StoreCorrupt, DomainError):
            pass  # the card is gone or unreadable; the round still ends with the agent's outcome
        return self._set_current(lane_id, cur, reportError=None,
                                 report={"outcome": outcome, "note": note, "at": now, "channel": channel})

    def _poll_report_file(self, lane_id, cur):
        raw = self.inbox.read(cur["runId"])
        if raw is None:
            return cur
        if cur.get("report"):
            self.inbox.archive(cur["runId"], "ignored")
            return self._set_current(lane_id, cur, ignoredReports=list(cur.get("ignoredReports") or []) + ["file"])
        try:
            outcome, note = report_channels.parse_report_file(raw, cur["cardId"], cur["runId"])
        except report_channels.ReportInvalid as e:
            return cur if cur.get("reportError") == str(e) else self._set_current(lane_id, cur, reportError=str(e))
        cur = self._accept_report(lane_id, cur, outcome, note, "file")
        if cur.get("report"):
            self.inbox.archive(cur["runId"], "processed")
        return cur

    @staticmethod
    def _unreported(note, cur):
        return note + (";回報檔無效:%s" % cur["reportError"] if cur.get("reportError") else "")

    def recover(self):
        """Server boot: a persisted lane `current` means the previous server died mid-run (INV-BD-14)."""
        with self._mu:
            for lane in self.state.load().get("lanes") or []:
                lane_id, cur = lane["id"], lane.get("current")
                if cur is None:
                    if lane["state"] in ("running", "stopping"):
                        self._update_lane(lane_id, lambda ln: dict(ln, state="idle", stopReason="server-shutdown"))
                    continue
                if cur.get("detached"):
                    continue  # the window agent never depended on this process; keep waiting for its report
                cur = self._poll_report_file(lane_id, cur)
                if cur.get("report"):
                    self._finish(lane_id, cur, cur["report"]["outcome"], cur["report"].get("note", ""), None)
                    self._update_lane(lane_id, lambda ln: dict(ln, state="idle", stopReason="server-shutdown"))
                    continue
                self._finish(lane_id, cur, "orphaned", "伺服器重啟時發現未結束的輪次(pid %s)" % cur.get("pid"), None)
                msg = ("上次派工 %s(卡 %s,pid %s)在伺服器停止時未正常結束;該行程可能仍在執行,請在工作管理員確認。"
                       "該卡已列入需人工。" % (cur["runId"], cur["cardId"], cur.get("pid")))
                self._update_lane(lane_id, lambda ln, m=msg: dict(ln, state="error", stopReason="server-shutdown", error=m))

    def shutdown(self):
        """Server shutdown: never leave an agent running silently (INV-BD-14). Returns the terminated runs."""
        with self._mu:
            stopped = []
            for lane in self.state.load().get("lanes") or []:
                lane_id, cur = lane["id"], lane.get("current")
                handle = self._handles.get(lane_id)
                if cur is None or handle is None or cur.get("detached"):
                    continue
                handle.terminate_tree()
                self._finish(lane_id, cur, "server-shutdown", "伺服器關閉時終止 Agent 行程", self._exit_code(lane_id))
                self._update_lane(lane_id, lambda ln: dict(ln, state="idle", stopReason="server-shutdown"))
                stopped.append(dict(cur, laneId=lane_id))
            return stopped

    # ---------- internals ----------
    def _update_lane(self, lane_id, fn):
        self.state.update(lambda s: dict(s, lanes=[fn(ln) if ln["id"] == lane_id else ln for ln in s.get("lanes") or []]))

    def _exit_code(self, lane_id):
        handle = self._handles.get(lane_id)
        return handle.poll() if handle is not None else None

    def _dispatch_next(self, lane_id):
        st = self.state.load()
        lane = _find(st, lane_id)
        session = lane.get("session") or {}
        agent = self._agents.get(session.get("agent"))
        if agent is None:
            self._settle(lane_id, "user")
            return
        card = dispatch.select_next(usecases.list_tasks(self.tasks), self._excluded(st), self._skip_kinds())
        if card is None:
            self._settle(lane_id, "no-candidates")
            return
        zone_before = card["zone"]
        zone_now = dispatch.dispatch_zone(zone_before)
        try:
            if zone_now != zone_before:
                usecases.set_zone(self.tasks, card["id"], zone_now, by="agent", now=self.clock.now_iso(),
                                  expected_version=card.get("version"))
        except (ports.VersionConflict, ports.LockTimeout):
            return  # someone edited the card meanwhile; reselect on the next tick
        now_iso = self.clock.now_iso()
        run_id = "%s-%s-%02d-%s" % (_run_stamp(now_iso), lane_id, session.get("dispatched", 0) + 1, _safe_id(card["id"]))
        log_dir = os.path.join(self.log_root, run_id)
        prompt_file = os.path.join(log_dir, "prompt.md")
        others = [{"laneId": ln["id"], "agent": ln["current"].get("agent"), "cardId": ln["current"]["cardId"],
                   "title": ln["current"].get("cardTitle", "")}
                  for ln in st.get("lanes") or [] if ln["id"] != lane_id and ln.get("current")]
        detached = bool(agent.get("detached"))
        report_file = self.inbox.path(run_id)
        prompt = dispatch_config.build_prompt(card, run_id, self.repo, self.tasks_path, self.state_path,
                                              self.default_tasks_path, self.default_state_path,
                                              others=others, lane_id=lane_id, detached=detached,
                                              agent_label=agent["label"], report_file=report_file)
        env = dict(os.environ)
        env.update({"HB_BOARD_TASKS": self.tasks_path, "HB_BOARD_DISPATCH_STATE": self.state_path,
                    "HB_DISPATCH_RUN_ID": run_id, "HB_DISPATCH_CARD": card["id"], "HB_DISPATCH_LANE": lane_id,
                    "HB_DISPATCH_REPORT_FILE": report_file, "PYTHONIOENCODING": "utf-8"})
        timeout_min = agent.get("timeout_minutes", self.config["timeout_minutes"])
        started = self.clock.time()
        cur = {"runId": run_id, "cardId": card["id"], "cardTitle": card.get("title", ""), "zoneBefore": zone_before,
               "zoneMoved": zone_now != zone_before, "agent": agent["id"], "pid": None, "startedAt": now_iso,
               "startedEpoch": started, "timeoutMinutes": timeout_min, "deadlineEpoch": started + timeout_min * 60,
               "logDir": log_dir, "report": None, "detached": detached}
        try:
            self.inbox.ensure()
            argv = dispatch_config.resolve_argv(agent, self.repo, self.python, prompt_file)
            handle = self.launcher.launch(argv, self.repo, env, prompt, agent["prompt_via"], log_dir)
        except (ports.LaunchError, dispatch_config.ConfigError, OSError) as e:
            self._revert_zone(cur)
            self._append_history(lane_id, cur, "launch-error", str(e), None)
            self._halt(lane_id, "launch-error", "%s 無法啟動:%s" % (agent["label"], e))
            return
        self._handles[lane_id] = handle
        self._report_seen_at.pop(lane_id, None)
        self._exit_seen_at.pop(lane_id, None)
        cur["pid"] = handle.pid
        self._update_lane(lane_id, lambda ln: dict(ln, current=cur, session=dict(
            ln.get("session") or {}, dispatched=(ln.get("session") or {}).get("dispatched", 0) + 1)))

    def _revert_zone(self, cur):
        if not cur.get("zoneMoved"):
            return
        try:
            t = usecases.get_task(self.tasks, cur["cardId"])
            if t["zone"] == dispatch.dispatch_zone(cur["zoneBefore"]):
                usecases.set_zone(self.tasks, cur["cardId"], cur["zoneBefore"], by="agent", now=self.clock.now_iso())
        except (ports.NotFound, ports.VersionConflict, ports.LockTimeout, DomainError):
            pass

    def _append_history(self, lane_id, cur, outcome, note, exit_code):
        report = cur.get("report") or {}
        channel = (report.get("channel") or "cli") if report and outcome in dispatch.REPORT_OUTCOMES else None
        entry = {"runId": cur["runId"], "laneId": lane_id, "cardId": cur["cardId"], "title": cur.get("cardTitle", ""),
                 "agent": cur["agent"], "outcome": outcome, "note": note or "", "exitCode": exit_code,
                 "startedAt": cur.get("startedAt"), "endedAt": self.clock.now_iso(),
                 "durationSec": int(self.clock.time() - cur.get("startedEpoch", self.clock.time())),
                 "logDir": cur.get("logDir"), "detached": bool(cur.get("detached")), "reportChannel": channel,
                 "ignoredReports": list(cur.get("ignoredReports") or []), "reportError": cur.get("reportError")}
        last = {"runId": cur["runId"], "cardId": cur["cardId"], "cardTitle": cur.get("cardTitle", ""),
                "agent": cur["agent"], "logDir": cur.get("logDir"), "outcome": outcome,
                "detached": bool(cur.get("detached")), "reportChannel": channel, "reportError": cur.get("reportError")}

        def mutate(s):
            lanes = [dict(ln, current=None, lastRun=last) if ln["id"] == lane_id else ln for ln in s.get("lanes") or []]
            return dict(s, lanes=lanes, history=([entry] + list(s.get("history") or []))[:HISTORY_MAX])
        self.state.update(mutate)

    def _skip(self, card_id, reason, run_id):
        at = self.clock.now_iso()

        def mutate(s):
            sk = dict(s.get("skipped") or {})
            sk[card_id] = {"reason": reason, "at": at, "runId": run_id}
            return dict(s, skipped=sk)
        self.state.update(mutate)

    def _finish(self, lane_id, cur, outcome, note, exit_code):
        if outcome in dispatch.NEEDS_HUMAN_OUTCOMES:
            line = dispatch.needs_human_line("%s: %s" % (outcome, note), cur.get("logDir"), self.clock.now_iso())
            try:
                usecases.append_task_note(self.tasks, cur["cardId"], line, by="agent", now=self.clock.now_iso())
            except (ports.NotFound, ports.LockTimeout, ports.StoreCorrupt):
                pass
            self._skip(cur["cardId"], outcome, cur["runId"])
        elif outcome == "blocked":
            self._skip(cur["cardId"], "agent-blocked", cur["runId"])
        elif outcome in dispatch.HALT_OUTCOMES:
            self._revert_zone(cur)
        self._append_history(lane_id, cur, outcome, note, exit_code)
        self.inbox.archive(cur["runId"], "rejected" if cur.get("reportError") else "ignored")
        handle = self._handles.pop(lane_id, None)
        if handle is not None:
            handle.close()
        self._report_seen_at.pop(lane_id, None)
        self._exit_seen_at.pop(lane_id, None)

    def _cfg(self, key):
        return self.config.get(key, dispatch_config.DEFAULTS[key])

    def _after_run(self, lane_id, fast_fail=False, log_dir=None, tail=""):
        lane = _find(self.state.load(), lane_id)
        s = lane.get("session") or {}
        fails = s.get("fastFails", 0) + 1 if fast_fail else 0
        if fails != s.get("fastFails", 0):
            self._update_lane(lane_id, lambda ln: dict(ln, session=dict(ln.get("session") or {}, fastFails=fails)))
        if fails >= self._cfg("fast_fail_limit"):
            self._halt(lane_id, "fast-fail",
                       "連續 %d 張在 %d 秒內結束且沒有回報,已停止派工(可能是 CLI 額度用完、未登入或設定錯誤)。"
                       "最後輸出:%s(日誌 %s)" % (fails, self._cfg("fast_fail_seconds"), tail or "(無)", log_dir))
            return
        decision = dispatch.after_run(s.get("dispatched", 0), s.get("maxCards", 0),
                                      bool(s.get("stopRequested")) or lane["state"] == "stopping")
        if decision == "continue":
            self._dispatch_next(lane_id)
        else:
            self._settle(lane_id, decision)

    def _settle(self, lane_id, reason):
        self._update_lane(lane_id, lambda ln: dict(ln, state="idle", stopReason=reason))

    def _halt(self, lane_id, reason, message):
        self._update_lane(lane_id, lambda ln: dict(ln, state="error", stopReason=reason, error=message))
