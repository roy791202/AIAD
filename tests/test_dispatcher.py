"""Agent dispatch rules ported from the Beta board (spec-BOARD-DISPATCH-01 INV-BD)."""

import json
from datetime import datetime, timedelta

import pytest

from sgenaxis.core import dispatch
from sgenaxis.core.board import WorkItem
from sgenaxis.core.dispatcher import DispatchError, Dispatcher
from sgenaxis.core.in_memory import (
    DryRunLauncher,
    InMemoryDispatchState,
    InMemoryReportInbox,
    InMemoryTaskStore,
    ManualClock,
)

START = datetime(2026, 10, 11, 9, 0)
STAMP = "2026-10-11T09:00:00"


def _item(item_id: str, zone: str, updated: str = "2026-10-10T10:00:00+08:00", kind: str = "task") -> WorkItem:
    return WorkItem(
        item_id=item_id,
        code=item_id,
        title=f"{item_id} 標題",
        zone=zone,
        source="manual",
        files=(),
        bdd="",
        tdd="",
        created="2026-10-10T09:00:00+08:00",
        note="",
        kind=kind,
        started="2026-10-10T09:00:00+08:00" if zone == "yellow" else None,
        completed="2026-10-10T09:00:00+08:00" if zone == "green" else None,
        updated=updated,
        updated_by="agent",
    )


def _setup(items, **options):
    store = InMemoryTaskStore(items)
    clock = ManualClock(START)
    launcher = DryRunLauncher()
    options.setdefault("report_grace_seconds", 0)
    options.setdefault("inbox", InMemoryReportInbox())
    return store, clock, launcher, Dispatcher(store, clock, launcher, **options)


def _report_file(card_id: str, run_id: str, outcome: str = "done", note: str = "ok") -> bytes:
    return json.dumps({"card": card_id, "run": run_id, "outcome": outcome, "note": note}).encode("utf-8")


# ── selection and zones ────────────────────────────────────


def test_select_next_prefers_red_then_yellow_then_gray_and_never_green():
    items = [
        _item("G1", "gray"),
        _item("Y1", "yellow"),
        _item("R2", "red", "2026-10-10T12:00:00+08:00"),
        _item("R1", "red", "2026-10-10T11:00:00+08:00"),
        _item("D1", "green"),
    ]
    order = []
    busy: set[str] = set()
    while (card := dispatch.select_next(items, busy, set())) is not None:
        order.append(card.item_id)
        busy.add(card.item_id)
    assert order == ["R1", "R2", "Y1", "G1"]


def test_select_next_orders_by_real_time_and_puts_unreadable_times_last():
    items = [
        _item("R-BAD", "red", "not-a-time"),
        _item("R-UTC", "red", "2026-10-10T02:30:00Z"),
        _item("R-TPE", "red", "2026-10-10T10:00:00+08:00"),
    ]
    assert dispatch.select_next(items, set(), set()).item_id == "R-TPE"
    assert dispatch.select_next(items, {"R-TPE"}, set()).item_id == "R-UTC"
    assert dispatch.select_next(items, {"R-TPE", "R-UTC"}, set()).item_id == "R-BAD"


def test_select_next_skips_needs_human_and_non_work_kinds():
    items = [_item("R1", "red"), _item("N1", "gray", kind="note"), _item("G1", "gray")]
    assert dispatch.select_next(items, set(), {"R1"}).item_id == "G1"
    assert dispatch.select_next([_item("E1", "gray", kind="epic")], set(), set()) is None


def test_dispatch_moves_gray_to_yellow_and_report_done_turns_green():
    store, clock, launcher, dispatcher = _setup([_item("G1", "gray")])
    lane = dispatcher.add_lane("claude", max_cards=5)
    dispatcher.start_lane(lane.lane_id)
    card = store.get("G1")
    assert (card.zone, card.updated_by, card.started) == ("yellow", "agent", STAMP)
    assert lane.current.card_id == "G1"
    assert launcher.launched[0].card_id == "G1"
    assert "G1" not in " ".join(launcher.launched[0].argv)
    dispatcher.report("G1", "done", "完成")
    card = store.get("G1")
    assert card.zone == "green"
    assert card.note.endswith(f"[派工回報 {STAMP} done] 完成")
    assert (dispatcher.history[0].outcome, dispatcher.history[0].channel) == ("done", "cli")
    assert (lane.state, lane.stop_reason) == ("idle", "no-candidates")


def test_blocked_report_turns_red_and_is_not_redispatched():
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")])
    lane = dispatcher.add_lane("codex", max_cards=None)
    dispatcher.start_lane(lane.lane_id)
    dispatcher.report("R1", "blocked", "缺規格")
    assert store.get("R1").zone == "red"
    assert dispatcher.skipped == {"R1": "agent-blocked"}
    assert lane.stop_reason == "no-candidates"
    dispatcher.unskip("R1")
    assert dispatch.select_next(store.list(), set(), set(dispatcher.skipped)).item_id == "R1"


def test_parallel_lanes_never_take_the_same_card_and_respect_the_lane_limit():
    store, clock, launcher, dispatcher = _setup([_item("R1", "red"), _item("R2", "red")], max_lanes=2)
    first = dispatcher.add_lane("claude", max_cards=1)
    second = dispatcher.add_lane("cursor-agent", max_cards=1)
    dispatcher.start_lane(first.lane_id)
    dispatcher.start_lane(second.lane_id)
    assert {first.current.card_id, second.current.card_id} == {"R1", "R2"}
    with pytest.raises(DispatchError, match="最多 2 個"):
        dispatcher.add_lane("codex")
    with pytest.raises(DispatchError):
        dispatcher.remove_lane(first.lane_id)
    dispatcher.report(first.current.card_id, "done", "ok")
    assert (first.state, first.stop_reason) == ("idle", "limit")


def test_running_lane_cannot_start_twice_and_agent_must_be_known():
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")])
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    with pytest.raises(DispatchError, match="已在執行"):
        dispatcher.start_lane(lane.lane_id)
    with pytest.raises(DispatchError):
        dispatcher.add_lane("gpt-shell")


def test_stop_after_current_finishes_the_card_then_idles():
    store, clock, launcher, dispatcher = _setup([_item("R1", "red"), _item("R2", "red")])
    lane = dispatcher.add_lane("claude", max_cards=None)
    dispatcher.start_lane(lane.lane_id)
    dispatcher.stop_lane(lane.lane_id, "after-current")
    assert lane.state == "stopping"
    dispatcher.report("R1", "done", "ok")
    assert (lane.state, lane.stop_reason, lane.current) == ("idle", "user", None)


def test_stop_now_terminates_and_marks_the_card_needs_human():
    store, clock, launcher, dispatcher = _setup([_item("G1", "gray")])
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    handle = launcher.handles[lane.current.run_id]
    dispatcher.stop_lane(lane.lane_id, "now")
    assert handle.terminated
    card = store.get("G1")
    assert card.zone == "yellow"
    assert f"[派工 needs-human {STAMP}] terminated" in card.note
    assert dispatcher.skipped == {"G1": "terminated"}
    assert (lane.state, lane.stop_reason) == ("idle", "user")


def test_timeout_and_no_report_become_needs_human_without_retry():
    store, clock, launcher, dispatcher = _setup(
        [_item("R1", "red"), _item("R2", "red", "2026-10-10T11:00:00+08:00")],
        timeout_minutes=60,
        exit_report_grace_seconds=0,
    )
    lane = dispatcher.add_lane("claude", max_cards=None)
    dispatcher.start_lane(lane.lane_id)
    clock.advance(timedelta(minutes=61))
    dispatcher.tick()
    assert dispatcher.skipped["R1"] == "timeout"
    assert lane.current.card_id == "R2"
    launcher.handles[lane.current.run_id].finish(0)
    clock.advance(timedelta(minutes=5))
    dispatcher.tick()
    assert dispatcher.skipped["R2"] == "no-report"
    assert lane.stop_reason == "no-candidates"


def test_login_failure_in_output_returns_the_card_to_gray_and_stops_the_lane():
    store, clock, launcher, dispatcher = _setup([_item("G1", "gray")], exit_report_grace_seconds=0)
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    launcher.handles[lane.current.run_id].finish(1, "Not logged in · Please run /login\n")
    dispatcher.tick()
    card = store.get("G1")
    assert card.zone == "gray"
    assert "needs-human" not in card.note
    assert dispatcher.skipped == {}
    assert (lane.state, lane.stop_reason) == ("error", "auth-error")
    assert "/login" in lane.error


def test_quota_message_stops_the_lane_without_needs_human():
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], exit_report_grace_seconds=0)
    lane = dispatcher.add_lane("codex")
    dispatcher.start_lane(lane.lane_id)
    launcher.handles[lane.current.run_id].finish(1, "error: 429 Too Many Requests")
    dispatcher.tick()
    assert (lane.state, lane.stop_reason) == ("error", "quota-error")
    assert store.get("R1").zone == "red"
    assert dispatcher.skipped == {}


def test_a_report_beats_quota_text_in_the_output():
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], exit_report_grace_seconds=0)
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    run_id = lane.current.run_id
    launcher.handles[run_id].finish(0, f"usage limit reached later\nHB-REPORT: done {run_id} 修好了\n")
    dispatcher.tick()
    assert store.get("R1").zone == "green"
    assert (dispatcher.history[0].outcome, dispatcher.history[0].channel) == ("done", "marker")


def test_launch_failure_stops_the_lane_with_an_error():
    store, clock, launcher, dispatcher = _setup([_item("G1", "gray")])
    launcher.fail_next = "找不到 claude 執行檔"
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    assert store.get("G1").zone == "gray"
    assert (lane.state, lane.stop_reason) == ("error", "launch-error")
    assert "找不到 claude" in lane.error


def test_three_fast_failures_stop_the_lane():
    items = [_item(f"R{index}", "red", f"2026-10-10T1{index}:00:00+08:00") for index in range(5)]
    store, clock, launcher, dispatcher = _setup(items, exit_report_grace_seconds=0)
    lane = dispatcher.add_lane("claude", max_cards=None)
    dispatcher.start_lane(lane.lane_id)
    for _ in range(3):
        clock.advance(timedelta(seconds=5))
        launcher.handles[lane.current.run_id].finish(0)
        dispatcher.tick()
    assert (lane.state, lane.stop_reason) == ("error", "fast-fail")
    assert len(dispatcher.skipped) == 3


# ── report channels (INV-BD-43..47) ────────────────────────


def test_report_file_completes_the_run_and_is_archived_as_processed():
    inbox = InMemoryReportInbox()
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], inbox=inbox)
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    run_id = lane.current.run_id
    inbox.put(run_id, b"\xef\xbb\xbf" + _report_file("R1", run_id, note="多行\n說明"))
    dispatcher.tick()
    assert store.get("R1").zone == "green"
    assert store.get("R1").note.endswith("done] 多行 說明")
    assert (dispatcher.history[0].channel, inbox.archived["processed"]) == ("file", [run_id])


def test_invalid_report_file_stays_in_the_inbox_and_is_rejected_when_the_run_ends():
    inbox = InMemoryReportInbox()
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], inbox=inbox, timeout_minutes=60)
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    run_id = lane.current.run_id
    inbox.put(run_id, _report_file("R9", run_id))
    dispatcher.tick()
    assert "應為 'R1'" in lane.current.report_error
    assert run_id in inbox.files
    clock.advance(timedelta(minutes=61))
    dispatcher.tick()
    assert dispatcher.skipped == {"R1": "timeout"}
    assert "回報檔無效" in store.get("R1").note
    assert inbox.archived["rejected"] == [run_id]
    assert dispatcher.history[0].report_error


def test_file_found_with_a_marker_wins_over_the_marker():
    inbox = InMemoryReportInbox()
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], inbox=inbox)
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    run_id = lane.current.run_id
    inbox.put(run_id, _report_file("R1", run_id, "blocked", "缺資料"))
    launcher.handles[run_id].finish(0, f"HB-REPORT: done {run_id} 完成")
    dispatcher.tick()
    assert store.get("R1").zone == "red"
    assert dispatcher.history[0].channel == "file"


def test_first_report_wins_and_later_ones_are_recorded_as_ignored():
    inbox = InMemoryReportInbox()
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], inbox=inbox, report_grace_seconds=120)
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    run_id = lane.current.run_id
    dispatcher.report("R1", "done", "先到")
    inbox.put(run_id, _report_file("R1", run_id, "blocked", "後到"))
    dispatcher.tick()
    assert inbox.archived["ignored"] == [run_id]
    launcher.handles[run_id].finish(0)
    dispatcher.tick()
    entry = dispatcher.history[0]
    assert (entry.outcome, entry.channel, entry.ignored) == ("done", "cli", ("file",))
    assert store.get("R1").zone == "green"


def test_echoed_prompt_marker_template_never_counts_as_a_report():
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], exit_report_grace_seconds=0)
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    run = lane.current
    launcher.handles[run.run_id].finish(0, run.prompt)
    clock.advance(timedelta(minutes=5))
    dispatcher.tick()
    assert dispatcher.skipped == {"R1": "no-report"}


def test_exit_grace_waits_for_a_late_report_file():
    inbox = InMemoryReportInbox()
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], inbox=inbox, exit_report_grace_seconds=20)
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    run_id = lane.current.run_id
    launcher.handles[run_id].finish(0)
    dispatcher.tick()
    assert lane.current is not None
    clock.advance(timedelta(seconds=10))
    inbox.put(run_id, _report_file("R1", run_id))
    dispatcher.tick()
    assert store.get("R1").zone == "green"
    assert dispatcher.history[0].channel == "file"


# ── window (detached) agents (INV-BD-39..42) ───────────────


def test_window_agent_exit_is_not_completion_only_a_report_ends_it():
    inbox = InMemoryReportInbox()
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], inbox=inbox, exit_report_grace_seconds=0)
    lane = dispatcher.add_lane("antigravity")
    dispatcher.start_lane(lane.lane_id)
    run_id = lane.current.run_id
    assert launcher.launched[0].detached
    launcher.handles[run_id].finish(1, "Not logged in")
    clock.advance(timedelta(minutes=10))
    dispatcher.tick()
    assert lane.current is not None and lane.state == "running"
    inbox.put(run_id, _report_file("R1", run_id))
    dispatcher.tick()
    assert store.get("R1").zone == "green"
    assert dispatcher.history[0].detached


def test_window_agent_timeout_never_kills_the_window():
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], timeout_minutes=60)
    lane = dispatcher.add_lane("antigravity")
    dispatcher.start_lane(lane.lane_id)
    handle = launcher.handles[lane.current.run_id]
    clock.advance(timedelta(minutes=61))
    dispatcher.tick()
    assert not handle.terminated
    assert "視窗模式不會自動關閉" in store.get("R1").note
    assert dispatcher.skipped == {"R1": "timeout"}


# ── launch request (INV-BD-15..18) ─────────────────────────


def test_launch_request_carries_env_prompt_file_and_board_path():
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], logs_dir=r"D:\P\.sgenaxis\logs", repo=r"D:\P")
    store.location = r"D:\P\.sgenaxis\tasks.json"
    lane = dispatcher.add_lane("cursor-agent")
    dispatcher.start_lane(lane.lane_id)
    request = launcher.launched[0]
    run_id = request.run_id
    assert request.prompt_file == rf"D:\P\.sgenaxis\logs\{run_id}\prompt.md"
    assert request.prompt_via == "arg" and request.cwd == r"D:\P"
    assert request.env["HB_BOARD_TASKS"] == r"D:\P\.sgenaxis\tasks.json"
    assert request.env["HB_DISPATCH_RUN_ID"] == run_id
    assert request.env["HB_DISPATCH_CARD"] == "R1"
    assert request.env["HB_DISPATCH_REPORT_FILE"].endswith(f"{run_id}.json")
    assert request.env["PYTHONIOENCODING"] == "utf-8"
    assert request.prompt_file in request.argv[-1]
    assert "看板 JSON（必須更新）" in request.prompt
    assert r"D:\P\.sgenaxis\tasks.json" in request.prompt
    assert request.env["HB_DISPATCH_REPORT_FILE"] in request.prompt


def test_unsafe_path_in_argv_refuses_to_launch_and_returns_the_card():
    store, clock, launcher, dispatcher = _setup([_item("G1", "gray")], repo=r"D:\A&B")
    lane = dispatcher.add_lane("codex")
    dispatcher.start_lane(lane.lane_id)
    assert launcher.launched == []
    assert (lane.state, lane.stop_reason) == ("error", "launch-error")
    assert "不安全" in lane.error
    assert store.get("G1").zone == "gray"


def test_agent_specs_never_carry_permission_bypass_flags():
    for spec in dispatch.AGENTS.values():
        dispatch.check_agent_spec(spec)
    bad = dispatch.AgentSpec("x", "X", ("x", "--dangerously-skip-permissions"))
    with pytest.raises(ValueError, match="權限繞過"):
        dispatch.check_agent_spec(bad)
    with pytest.raises(ValueError, match="佔位符"):
        dispatch.check_agent_spec(dispatch.AgentSpec("x", "X", ("x", "{card}")))


def test_second_lane_prompt_lists_the_other_running_lane():
    store, clock, launcher, dispatcher = _setup([_item("R1", "red"), _item("R2", "red")])
    first = dispatcher.add_lane("claude")
    second = dispatcher.add_lane("codex")
    dispatcher.start_lane(first.lane_id)
    dispatcher.start_lane(second.lane_id)
    prompt = launcher.launched[1].prompt
    assert "平行派工" in prompt and "L1" in prompt and first.current.card_id in prompt
    assert "平行派工" not in launcher.launched[0].prompt


def test_prompt_carries_card_and_run_and_forbids_git_and_agent_cli():
    card = _item("FX-55", "red")
    prompt = dispatch.build_prompt(card, "RUN-1", r"D:\AutoCode", report_file=r"D:\inbox\RUN-1.json")
    assert "FX-55" in prompt and "RUN-1" in prompt
    assert "不得執行任何 git 指令" in prompt
    assert "不得呼叫任何 Agent CLI" in prompt
    assert "HB-REPORT: <done-or-blocked> RUN-1" in prompt
    window = dispatch.build_prompt(card, "RUN-1", r"D:\AutoCode", detached=True, agent_label="Antigravity")
    assert "HB-REPORT" not in window and "Antigravity" in window


# ── persistence and recovery (INV-BD-14, INV-BD-25, INV-BD-51) ──


def test_lanes_schedules_and_history_survive_a_restart():
    state = InMemoryDispatchState()
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], state=state)
    lane = dispatcher.add_lane("codex", max_cards=None)
    dispatcher.add_schedule(lane.lane_id, "daily", time="23:30", weekdays=(0, 2))
    dispatcher.start_lane(lane.lane_id)
    dispatcher.report("R1", "done", "ok")
    dispatcher.set_schedules_paused(True)
    again = Dispatcher(store, clock, launcher, state=state, inbox=InMemoryReportInbox())
    restored = again.lane(lane.lane_id)
    assert (restored.agent, restored.max_cards, restored.schedules[0].weekdays) == ("codex", None, (0, 2))
    assert again.history[0].outcome == "done"
    assert again.schedules_paused
    assert again.add_lane("claude").lane_id == "L2"


def test_unfinished_run_after_restart_is_orphaned_and_needs_human():
    state = InMemoryDispatchState()
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], state=state)
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    clock.advance(timedelta(minutes=3))
    again = Dispatcher(store, clock, DryRunLauncher(), state=state, inbox=InMemoryReportInbox())
    restored = again.lane(lane.lane_id)
    assert (restored.state, restored.stop_reason, restored.current) == ("error", "orphaned", None)
    assert again.skipped == {"R1": "orphaned"}
    assert "orphaned" in store.get("R1").note
    assert state.state["lanes"][0]["current"] is None


def test_report_written_while_closed_is_applied_on_restart():
    state, inbox = InMemoryDispatchState(), InMemoryReportInbox()
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], state=state, inbox=inbox)
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    run_id = lane.current.run_id
    inbox.put(run_id, _report_file("R1", run_id))
    again = Dispatcher(store, clock, DryRunLauncher(), state=state, inbox=inbox)
    assert store.get("R1").zone == "green"
    assert again.skipped == {}
    assert (again.lane("L1").state, again.lane("L1").stop_reason) == ("idle", "restart")


def test_window_run_keeps_being_tracked_after_restart():
    state, inbox = InMemoryDispatchState(), InMemoryReportInbox()
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], state=state, inbox=inbox)
    lane = dispatcher.add_lane("antigravity")
    dispatcher.start_lane(lane.lane_id)
    run_id = lane.current.run_id
    dispatcher.shutdown()
    again = Dispatcher(store, clock, DryRunLauncher(), state=state, inbox=inbox, report_grace_seconds=0)
    assert again.lane("L1").current.run_id == run_id
    inbox.put(run_id, _report_file("R1", run_id))
    again.tick()
    assert store.get("R1").zone == "green"


def test_shutdown_stops_captured_runs_as_needs_human():
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")])
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    handle = launcher.handles[lane.current.run_id]
    dispatcher.shutdown()
    assert handle.terminated
    assert dispatcher.skipped == {"R1": "server-shutdown"}
    assert (lane.state, lane.current) == ("idle", None)


def test_history_detail_keeps_prompt_and_output_for_the_log_view():
    store, clock, launcher, dispatcher = _setup([_item("R1", "red")], exit_report_grace_seconds=0)
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    run_id = lane.current.run_id
    launcher.handles[run_id].finish(0, "x" * 20000 + f"\nHB-REPORT: done {run_id} ok")
    dispatcher.tick()
    entry = dispatcher.history[0]
    assert "## 2. 你的卡" in entry.prompt
    assert len(entry.output) == 8 * 1024 and entry.output.endswith("ok")
    assert (entry.agent, entry.started_at, entry.at) == ("claude", STAMP, STAMP)
