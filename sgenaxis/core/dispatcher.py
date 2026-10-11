"""Agent dispatcher: lanes, one card per lane, red > yellow > gray (spec-BOARD-DISPATCH-01).

Application layer. It acts only through the TaskStore, DispatchStateStore, ReportInbox,
Clock, and AgentLauncher ports, and is driven by explicit calls plus a periodic tick()
on the UI thread. Every public call that changes lanes, runs, or schedules saves the
dispatch state, so a restart recovers it (INV-BD-14, INV-BD-25, INV-BD-51).
"""

from __future__ import annotations

import functools
import os
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta

from sgenaxis.core import board, dispatch, report_channels, schedule, timefmt
from sgenaxis.core.board import VersionConflict, WorkItem
from sgenaxis.core.in_memory import InMemoryReportInbox
from sgenaxis.core.ports import (
    AgentLauncher,
    Clock,
    DispatchStateStore,
    LaunchFailed,
    LaunchRequest,
    ReportInbox,
    RunHandle,
    TaskStore,
)
from sgenaxis.core.schedule import Schedule

STATE_SCHEMA = "sgenaxis-dispatch/1"
MAX_LANES_HARD = 6
HISTORY_LIMIT = 50
OUTPUT_LIMIT = 8 * 1024
SCHEDULE_FIELDS = ("kind", "at", "time", "start", "end", "weekdays", "enabled", "max_cards")
_FOLLOW_LANE = object()


class DispatchError(ValueError):
    def __init__(self, message: str, code: int = 400) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class Run:
    run_id: str
    lane_id: str
    agent: str
    card_id: str
    title: str
    from_zone: str
    started_at: datetime
    handle: RunHandle | None
    started_by: str | None = None
    detached: bool = False
    prompt: str = ""
    report: tuple[str, str, str] | None = None
    reported_at: datetime | None = None
    exited_at: datetime | None = None
    report_error: str = ""
    ignored: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HistoryEntry:
    run_id: str
    lane_id: str
    agent: str
    card_id: str
    title: str
    outcome: str
    channel: str
    started_at: str
    at: str
    note: str
    started_by: str | None
    detached: bool = False
    report_error: str = ""
    ignored: tuple[str, ...] = ()
    prompt: str = ""
    output: str = ""


@dataclass(frozen=True)
class ScheduleEvent:
    at: str
    lane_id: str
    schedule_id: str
    action: str
    result: str


@dataclass
class Lane:
    lane_id: str
    agent: str
    max_cards: int | None = 5
    state: str = "idle"
    stop_reason: str = ""
    error: str = ""
    dispatched: int = 0
    limit: int | None = 5
    current: Run | None = None
    started_by: str | None = None
    fast_fails: int = 0
    schedules: list[Schedule] = field(default_factory=list)
    schedule_seq: int = 0

    @property
    def active(self) -> bool:
        return self.state in ("running", "stopping")


def _persisting(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        finally:
            self._persist()

    return wrapper


class Dispatcher:
    def __init__(
        self,
        store: TaskStore,
        clock: Clock,
        launcher: AgentLauncher,
        *,
        inbox: ReportInbox | None = None,
        state: DispatchStateStore | None = None,
        repo: str = r"D:\AutoCode",
        logs_dir: str = "",
        report_command: str = "",
        max_lanes: int = 3,
        max_cards_limit: int = 50,
        timeout_minutes: int = 60,
        report_grace_seconds: int = 120,
        exit_report_grace_seconds: int = 20,
        fast_fail_seconds: int = 60,
        fast_fail_limit: int = 3,
        max_schedules: int = 10,
        schedule_max_gap_seconds: int = 10,
        default_agent: str | None = None,
    ) -> None:
        if not 1 <= max_lanes <= MAX_LANES_HARD:
            raise ValueError(f"Agent 條數上限必須在 1 到 {MAX_LANES_HARD} 之間")
        self.store = store
        self.clock = clock
        self.launcher = launcher
        self.inbox = inbox if inbox is not None else InMemoryReportInbox()
        self.state_store = state
        self.repo = repo
        self.logs_dir = logs_dir
        self.report_command = report_command
        self.max_lanes = max_lanes
        self.max_cards_limit = max_cards_limit
        self.timeout = timedelta(minutes=timeout_minutes)
        self.report_grace = timedelta(seconds=report_grace_seconds)
        self.exit_report_grace = timedelta(seconds=exit_report_grace_seconds)
        self.fast_fail = timedelta(seconds=fast_fail_seconds)
        self.fast_fail_limit = fast_fail_limit
        self.max_schedules = max_schedules
        self.schedule_max_gap = timedelta(seconds=schedule_max_gap_seconds)
        self.lanes: list[Lane] = []
        self.history: list[HistoryEntry] = []
        self.skipped: dict[str, str] = {}
        self.schedules_paused = False
        self.schedule_history: list[ScheduleEvent] = []
        self._lane_seq = 0
        self._run_seq = 0
        self._last_check: datetime | None = None
        self._saved: dict | None = None
        saved = state.load() if state is not None else None
        if saved:
            self._restore(saved)
            self._saved = self._snapshot()
            self._recover()
        elif default_agent is not None:
            self._check_agent(default_agent)
            self._lane_seq = 1
            self.lanes.append(Lane("L1", default_agent, 5, limit=5))
            self._saved = self._snapshot()

    # ── lanes ──────────────────────────────────────────────

    @_persisting
    def add_lane(self, agent: str = "claude", max_cards: int | None = 5) -> Lane:
        self._check_agent(agent)
        self._check_max_cards(max_cards)
        if len(self.lanes) >= self.max_lanes:
            raise DispatchError(f"已達上限：最多 {self.max_lanes} 個 Agent 同時派工", 409)
        self._lane_seq += 1
        lane = Lane(f"L{self._lane_seq}", agent, max_cards, limit=max_cards)
        self.lanes.append(lane)
        return lane

    @_persisting
    def configure_lane(self, lane_id: str, agent: str, max_cards: int | None) -> None:
        lane = self.lane(lane_id)
        if lane.active:
            raise DispatchError("執行中的 Agent 不能改設定", 409)
        self._check_agent(agent)
        self._check_max_cards(max_cards)
        lane.agent = agent
        lane.max_cards = max_cards

    @_persisting
    def remove_lane(self, lane_id: str) -> None:
        lane = self.lane(lane_id)
        if lane.active:
            raise DispatchError("執行中的 Agent 不能移除，請先停止", 409)
        self.lanes.remove(lane)

    def lane(self, lane_id: str) -> Lane:
        for lane in self.lanes:
            if lane.lane_id == lane_id:
                return lane
        raise DispatchError(f"找不到 Agent {lane_id}", 404)

    @_persisting
    def start_lane(self, lane_id: str, started_by: str | None = None, max_cards=_FOLLOW_LANE) -> None:
        lane = self.lane(lane_id)
        if lane.active:
            raise DispatchError(f"Agent {lane_id} 已在執行", 409)
        limit = lane.max_cards if max_cards is _FOLLOW_LANE else max_cards
        self._check_max_cards(limit)
        lane.state = "running"
        lane.stop_reason = ""
        lane.error = ""
        lane.dispatched = 0
        lane.limit = limit
        lane.started_by = started_by
        lane.fast_fails = 0
        self._dispatch_next(lane)

    @_persisting
    def stop_lane(self, lane_id: str, mode: str = "after-current") -> None:
        if mode not in dispatch.STOP_MODES:
            raise DispatchError(f"未知的停止方式：{mode}")
        lane = self.lane(lane_id)
        if not lane.active:
            return
        if lane.current is None:
            self._idle(lane, "user")
        elif mode == "now":
            run = lane.current
            if run.handle is not None and not run.detached:
                run.handle.terminate()
            self._finish(lane, "terminated")
        else:
            lane.state = "stopping"

    @_persisting
    def shutdown(self) -> None:
        """App closing (INV-BD-14/41): stop captured runs as needs-human; window agents keep their run for recovery."""
        for lane in self.lanes:
            run = lane.current
            if run is None:
                if lane.active:
                    self._idle(lane, "user")
                continue
            if run.detached:
                continue
            if run.handle is not None:
                run.handle.terminate()
            self._finish(lane, "server-shutdown", proceed=False)
            self._idle(lane, "user")

    def running_count(self) -> int:
        return sum(1 for lane in self.lanes if lane.active)

    def use_launcher(self, launcher: AgentLauncher, report_grace_seconds: int) -> None:
        if self.running_count():
            raise DispatchError("Agent 派工中，請先全部停止再切換啟動方式", 409)
        self.launcher = launcher
        self.report_grace = timedelta(seconds=report_grace_seconds)

    def busy_cards(self) -> set[str]:
        return {lane.current.card_id for lane in self.lanes if lane.current is not None}

    def next_card(self) -> WorkItem | None:
        return dispatch.select_next(self.store.list(), self.busy_cards(), set(self.skipped))

    @_persisting
    def unskip(self, card_id: str) -> None:
        if card_id not in self.skipped:
            raise DispatchError(f"{card_id} 不在需人工清單", 404)
        del self.skipped[card_id]

    # ── reports ────────────────────────────────────────────

    @_persisting
    def report(self, card_id: str, outcome: str, note: str, channel: str = "cli") -> str | None:
        """Report from the CLI or the UI. Like board.py report it always writes the card (INV-BD-43)."""
        if channel not in report_channels.CHANNELS:
            raise DispatchError(f"未知的回報管道：{channel}")
        now = self.clock.now()
        lane = next((lane for lane in self.lanes if lane.current and lane.current.card_id == card_id), None)
        if lane is not None and lane.current.report is None:
            self._take_report(lane, outcome, note, channel, now)
            self._check_run(lane, now)
            return lane.lane_id
        self._write_card(card_id, dispatch.report_zone(outcome), dispatch.report_note(timefmt.stamp(now), outcome, note))
        if lane is not None:
            lane.current.ignored.append(channel)
        return None

    def _take_report(self, lane: Lane, outcome: str, note: str, channel: str, now: datetime) -> None:
        run = lane.current
        try:
            self._write_card(run.card_id, dispatch.report_zone(outcome), dispatch.report_note(timefmt.stamp(now), outcome, note))
        except DispatchError:
            pass
        run.report = (outcome, report_channels.one_line(note), channel)
        run.reported_at = now
        if outcome == "blocked":
            self.skipped[run.card_id] = "agent-blocked"

    def _poll_inbox(self, lane: Lane, now: datetime) -> None:
        run = lane.current
        raw = self.inbox.read(run.run_id)
        if raw is None:
            return
        if run.report is not None:
            self.inbox.archive(run.run_id, "ignored")
            run.ignored.append("file")
            return
        try:
            outcome, note, channel = report_channels.parse_report_file(raw, run.card_id, run.run_id)
        except report_channels.ReportInvalid as exc:
            run.report_error = str(exc)
            return
        run.report_error = ""
        self._take_report(lane, outcome, note, channel, now)
        self.inbox.archive(run.run_id, "processed")

    # ── tick ───────────────────────────────────────────────

    @_persisting
    def tick(self) -> None:
        now = self.clock.now()
        for lane in list(self.lanes):
            if lane.current is not None:
                self._poll_inbox(lane, now)
                self._check_run(lane, now)
            elif lane.state == "running":
                self._dispatch_next(lane)
        self._run_schedules(timefmt.local(now))

    def _check_run(self, lane: Lane, now: datetime) -> None:
        run = lane.current
        if run is None:
            return
        if run.handle is not None and run.exited_at is None and run.handle.poll() is not None:
            run.exited_at = now
        if run.report is not None:
            if not run.detached:
                if run.exited_at is None and now - run.reported_at < self.report_grace:
                    return
                if run.exited_at is None and run.handle is not None:
                    run.handle.terminate()
            lane.fast_fails = 0
            outcome, note, channel = run.report
            self._finish(lane, outcome, channel, note)
            return
        if run.exited_at is not None and not run.detached:
            output = run.handle.output() if run.handle is not None else ""
            marker = report_channels.find_marker(output, run.run_id)
            if marker is not None:
                self._take_report(lane, marker[0], marker[1], "marker", now)
                self._check_run(lane, now)
                return
            if now - run.exited_at < self.exit_report_grace:
                return
            failure = dispatch.classify_exit(run.agent, output)
            if failure is not None:
                spec = dispatch.AGENTS[run.agent]
                hint = spec.login_hint if failure == "auth-error" else f"{spec.label} 額度或次數用完，請等重置後再開始。"
                self._fail_lane(lane, failure, f"{hint}（最後輸出：{_last_line(output)}）")
                return
            fast = run.exited_at - run.started_at < self.fast_fail
            lane.fast_fails = lane.fast_fails + 1 if fast else 0
            if lane.fast_fails < self.fast_fail_limit:
                self._finish(lane, "no-report")
                return
            self._finish(lane, "no-report", proceed=False)
            self._set_error(lane, "fast-fail", f"連續 {lane.fast_fails} 輪在 {self.fast_fail.seconds} 秒內結束且沒有回報")
            return
        if now - run.started_at >= self.timeout:
            if run.handle is not None and not run.detached:
                run.handle.terminate()
            self._finish(lane, "timeout")

    # ── dispatch internals ─────────────────────────────────

    def _dispatch_next(self, lane: Lane) -> None:
        if lane.limit is not None and lane.dispatched >= lane.limit:
            self._idle(lane, "limit")
            return
        card = dispatch.select_next(self.store.list(), self.busy_cards(), set(self.skipped))
        if card is None:
            self._idle(lane, "no-candidates")
            return
        now = self.clock.now()
        zone = dispatch.dispatch_zone(card.zone)
        if zone != card.zone:
            try:
                self.store.commit(board.set_zone(card, zone, "agent", timefmt.stamp(now)), card.version)
            except VersionConflict:
                return
        spec = dispatch.AGENTS[lane.agent]
        self._run_seq += 1
        run_id = f"{now:%Y%m%d-%H%M%S}-{lane.lane_id}-{self._run_seq:02d}-{card.item_id}"
        prompt_file = os.path.join(self.logs_dir, run_id, "prompt.md") if self.logs_dir else f"{run_id}.prompt.md"
        report_file = self.inbox.path(run_id)
        tasks_path = self.store.location or ""
        others = tuple(
            dispatch.OtherRun(other.lane_id, other.agent, other.current.card_id, other.current.title)
            for other in self.lanes
            if other is not lane and other.current is not None
        )
        prompt = dispatch.build_prompt(
            card,
            run_id,
            self.repo,
            tasks_path=tasks_path,
            report_file=report_file,
            lane_id=lane.lane_id,
            others=others,
            detached=spec.detached,
            agent_label=spec.label,
            report_command=self.report_command,
        )
        run = Run(
            run_id, lane.lane_id, lane.agent, card.item_id, card.title, card.zone, now, None, lane.started_by, spec.detached, prompt
        )
        lane.current = run
        lane.dispatched += 1
        try:
            argv = dispatch.resolve_argv(lane.agent, self.repo, prompt_file)
            request = LaunchRequest(
                run_id,
                lane.lane_id,
                lane.agent,
                card.item_id,
                argv,
                prompt,
                spec.prompt_via,
                prompt_file,
                self.repo,
                spec.detached,
                dispatch.run_env(tasks_path, run_id, card.item_id, report_file),
            )
            run.handle = self.launcher.launch(request)
        except (LaunchFailed, ValueError) as exc:
            self._fail_lane(lane, "launch-error", f"無法啟動 {spec.label}：{exc}")

    def _finish(self, lane: Lane, outcome: str, channel: str = "", note: str = "", proceed: bool = True) -> None:
        run = lane.current
        lane.current = None
        now = self.clock.now()
        if outcome in dispatch.NEEDS_HUMAN:
            reason = outcome
            if run.detached and outcome in ("timeout", "terminated"):
                reason += "；視窗模式不會自動關閉 Agent 視窗，請自行檢查"
            if run.report_error:
                reason += f"；回報檔無效：{run.report_error}"
                self.inbox.archive(run.run_id, "rejected")
            if self.store.get(run.card_id) is not None:
                self._write_card(run.card_id, None, dispatch.needs_human_note(timefmt.stamp(now), reason))
            self.skipped[run.card_id] = outcome
        self._record(run, outcome, channel, note, now)
        if not proceed:
            return
        if outcome == "terminated" or lane.state == "stopping":
            self._idle(lane, "user")
        else:
            self._dispatch_next(lane)

    def _fail_lane(self, lane: Lane, kind: str, message: str) -> None:
        run = lane.current
        lane.current = None
        now = self.clock.now()
        if run.from_zone == "gray":
            card = self.store.get(run.card_id)
            if card is not None and card.zone == "yellow":
                self.store.commit(board.set_zone(card, "gray", "agent", timefmt.stamp(now)), card.version)
        self._record(run, kind, "", message, now)
        self._set_error(lane, kind, message)

    def _set_error(self, lane: Lane, kind: str, message: str) -> None:
        lane.state = "error"
        lane.stop_reason = kind
        lane.error = message
        lane.started_by = None

    def _idle(self, lane: Lane, reason: str) -> None:
        lane.state = "idle"
        lane.stop_reason = reason
        lane.started_by = None

    def _record(self, run: Run, outcome: str, channel: str, note: str, now: datetime) -> None:
        output = run.handle.output() if run.handle is not None else ""
        entry = HistoryEntry(
            run.run_id,
            run.lane_id,
            run.agent,
            run.card_id,
            run.title,
            outcome,
            channel,
            timefmt.stamp(run.started_at),
            timefmt.stamp(now),
            note,
            run.started_by,
            run.detached,
            run.report_error,
            tuple(run.ignored),
            run.prompt,
            output[-OUTPUT_LIMIT:],
        )
        self.history = [entry] + self.history[: HISTORY_LIMIT - 1]

    def _write_card(self, card_id: str, zone: str | None, note_line: str) -> None:
        card = self.store.get(card_id)
        if card is None:
            raise DispatchError(f"找不到工項 {card_id}", 404)
        changed = board.set_zone(card, zone or card.zone, "agent", timefmt.stamp(self.clock.now()), note_line)
        self.store.commit(changed, card.version)

    def _check_agent(self, agent: str) -> None:
        if agent not in dispatch.AGENTS:
            raise DispatchError(f"未知的 Agent：{agent}")

    def _check_max_cards(self, max_cards) -> None:
        if max_cards is None:
            return
        if not isinstance(max_cards, int) or not 1 <= max_cards <= self.max_cards_limit:
            raise DispatchError(f"張數必須在 1 到 {self.max_cards_limit} 之間，或做到無卡為止")

    # ── schedules ──────────────────────────────────────────

    @_persisting
    def add_schedule(self, lane_id: str, kind: str, **fields) -> Schedule:
        lane = self.lane(lane_id)
        _check_schedule_fields(fields)
        if len(lane.schedules) >= self.max_schedules:
            raise DispatchError(f"每條 Agent 最多 {self.max_schedules} 筆排程", 409)
        try:
            entry = schedule.make(f"S{lane.schedule_seq + 1}", kind, now=timefmt.local(self.clock.now()), **fields)
        except ValueError as exc:
            raise DispatchError(str(exc)) from exc
        lane.schedule_seq += 1
        lane.schedules.append(entry)
        return entry

    @_persisting
    def update_schedule(self, lane_id: str, schedule_id: str, **fields) -> Schedule:
        """Partial update; a fired once-schedule can only be re-enabled together with a new future time."""
        lane = self.lane(lane_id)
        _check_schedule_fields(fields)
        current = self._schedule(lane, schedule_id)
        merged = {name: getattr(current, name) for name in SCHEDULE_FIELDS} | fields
        kind = merged.pop("kind")
        try:
            entry = schedule.make(
                schedule_id, kind, now=timefmt.local(self.clock.now()), require_future=bool(merged["enabled"]), **merged
            )
        except ValueError as exc:
            raise DispatchError(str(exc)) from exc
        entry = replace(entry, last_fired=current.last_fired, last_result=current.last_result)
        self._replace_schedule(lane, entry)
        return entry

    def set_schedule_enabled(self, lane_id: str, schedule_id: str, enabled: bool) -> None:
        try:
            self.update_schedule(lane_id, schedule_id, enabled=enabled)
        except DispatchError as exc:
            if "已過" in str(exc):
                raise DispatchError("單次排程的時間已過，請改成新的未來時間") from exc
            raise

    @_persisting
    def delete_schedule(self, lane_id: str, schedule_id: str) -> None:
        lane = self.lane(lane_id)
        lane.schedules.remove(self._schedule(lane, schedule_id))

    @_persisting
    def set_schedules_paused(self, paused: bool) -> None:
        self.schedules_paused = paused

    def next_run(self, entry: Schedule) -> tuple[datetime, str] | None:
        if self.schedules_paused:
            return None
        return schedule.next_event(entry, timefmt.local(self.clock.now()))

    def _run_schedules(self, now: datetime) -> None:
        last, self._last_check = self._last_check, now
        if last is None or now <= last or now - last > self.schedule_max_gap:
            return
        for lane in list(self.lanes):
            for entry in list(lane.schedules):
                if not entry.enabled:
                    continue
                for moment, action in schedule.events_between(entry, last, now):
                    self._fire(lane, entry, action, moment)

    def _fire(self, lane: Lane, entry: Schedule, action: str, moment: datetime) -> None:
        if action == "start":
            result = self._fire_start(lane, entry)
        elif lane.state == "running" and lane.started_by == entry.schedule_id:
            self.stop_lane(lane.lane_id, "after-current")
            result = "stop-requested"
        elif lane.active:
            result = "not-started-by-schedule"
        else:
            result = "idle"
        current = self._schedule(lane, entry.schedule_id)
        updated = replace(current, last_fired=timefmt.stamp(moment), last_result=result)
        if entry.kind == "once":
            updated = schedule.disable(updated)
        self._replace_schedule(lane, updated)
        event = ScheduleEvent(timefmt.stamp(moment), lane.lane_id, entry.schedule_id, action, result)
        self.schedule_history = [event] + self.schedule_history[: HISTORY_LIMIT - 1]

    def _fire_start(self, lane: Lane, entry: Schedule) -> str:
        if self.schedules_paused:
            return "skipped-paused"
        if lane.active:
            return "skipped-busy"
        limit = _FOLLOW_LANE if entry.max_cards is None else (None if entry.max_cards == schedule.UNLIMITED else entry.max_cards)
        try:
            self.start_lane(lane.lane_id, started_by=entry.schedule_id, max_cards=limit)
        except DispatchError as exc:
            return f"error: {exc}"
        return "started" if lane.active else lane.stop_reason or "idle"

    def _schedule(self, lane: Lane, schedule_id: str) -> Schedule:
        for entry in lane.schedules:
            if entry.schedule_id == schedule_id:
                return entry
        raise DispatchError(f"找不到排程 {schedule_id}", 404)

    def _replace_schedule(self, lane: Lane, entry: Schedule) -> None:
        lane.schedules = [entry if item.schedule_id == entry.schedule_id else item for item in lane.schedules]

    # ── persistence ────────────────────────────────────────

    def _persist(self) -> None:
        if self.state_store is None:
            return
        snapshot = self._snapshot()
        if snapshot != self._saved:
            self.state_store.save(snapshot)
            self._saved = snapshot

    def _snapshot(self) -> dict:
        return {
            "schema": STATE_SCHEMA,
            "laneSeq": self._lane_seq,
            "runSeq": self._run_seq,
            "lanes": [_lane_to_dict(lane) for lane in self.lanes],
            "history": [asdict(entry) for entry in self.history],
            "skipped": dict(self.skipped),
            "schedulePaused": self.schedules_paused,
            "scheduleHistory": [asdict(event) for event in self.schedule_history],
        }

    def _restore(self, saved: dict) -> None:
        if saved.get("schema") != STATE_SCHEMA:
            raise ValueError(f"派工狀態檔格式不符：{saved.get('schema')}")
        self._lane_seq = int(saved.get("laneSeq", 0))
        self._run_seq = int(saved.get("runSeq", 0))
        self.lanes = [_lane_from_dict(row) for row in saved.get("lanes", ())]
        self.history = [HistoryEntry(**{**row, "ignored": tuple(row.get("ignored", ()))}) for row in saved.get("history", ())]
        self.skipped = dict(saved.get("skipped", {}))
        self.schedules_paused = bool(saved.get("schedulePaused", False))
        self.schedule_history = [ScheduleEvent(**row) for row in saved.get("scheduleHistory", ())]

    @_persisting
    def _recover(self) -> None:
        """After a restart (INV-BD-14/41/46): apply reports written while closed, keep tracking window
        agents, and mark any other unfinished run orphaned without touching unknown processes."""
        now = self.clock.now()
        for lane in self.lanes:
            run = lane.current
            if run is None:
                if lane.active:
                    self._idle(lane, "restart")
                continue
            self._poll_inbox(lane, now)
            if run.report is not None:
                outcome, note, channel = run.report
                self._finish(lane, outcome, channel, note, proceed=False)
                self._idle(lane, "restart")
            elif run.detached:
                continue
            else:
                self._finish(lane, "orphaned", proceed=False)
                self._set_error(lane, "orphaned", f"上次執行中斷：{run.card_id} 已列入需人工，請確認 Agent 是否仍在執行。")


def _check_schedule_fields(fields: dict) -> None:
    unknown = set(fields) - set(SCHEDULE_FIELDS)
    if unknown:
        raise DispatchError(f"排程不支援這些欄位：{', '.join(sorted(unknown))}")


def _last_line(text: str) -> str:
    lines = [line for line in (text or "").splitlines() if line.strip()]
    return lines[-1].strip()[:200] if lines else "（沒有輸出）"


def _lane_to_dict(lane: Lane) -> dict:
    run = lane.current
    return {
        "laneId": lane.lane_id,
        "agent": lane.agent,
        "maxCards": lane.max_cards,
        "state": lane.state,
        "stopReason": lane.stop_reason,
        "error": lane.error,
        "dispatched": lane.dispatched,
        "limit": lane.limit,
        "startedBy": lane.started_by,
        "fastFails": lane.fast_fails,
        "scheduleSeq": lane.schedule_seq,
        "schedules": [{**asdict(entry), "weekdays": list(entry.weekdays)} for entry in lane.schedules],
        "current": None
        if run is None
        else {
            "runId": run.run_id,
            "agent": run.agent,
            "cardId": run.card_id,
            "title": run.title,
            "fromZone": run.from_zone,
            "startedAt": timefmt.stamp(run.started_at),
            "startedBy": run.started_by,
            "detached": run.detached,
            "prompt": run.prompt,
            "reportError": run.report_error,
        },
    }


def _lane_from_dict(row: dict) -> Lane:
    current = row.get("current")
    run = None
    if current:
        run = Run(
            current["runId"],
            row["laneId"],
            current["agent"],
            current["cardId"],
            current.get("title", ""),
            current.get("fromZone", "gray"),
            timefmt.parse(current["startedAt"]),
            None,
            current.get("startedBy"),
            bool(current.get("detached", False)),
            current.get("prompt", ""),
            report_error=current.get("reportError", ""),
        )
    return Lane(
        row["laneId"],
        row["agent"],
        row.get("maxCards"),
        row.get("state", "idle"),
        row.get("stopReason", ""),
        row.get("error", ""),
        row.get("dispatched", 0),
        row.get("limit"),
        run,
        row.get("startedBy"),
        row.get("fastFails", 0),
        [Schedule(**{**entry, "weekdays": tuple(entry.get("weekdays", ()))}) for entry in row.get("schedules", ())],
        row.get("scheduleSeq", 0),
    )
