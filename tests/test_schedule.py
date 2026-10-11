"""Schedule rules ported from the Beta board (INV-BD-48..51)."""

from datetime import datetime, timedelta

import pytest

from sgenaxis.core import schedule
from sgenaxis.core.board import WorkItem
from sgenaxis.core.dispatcher import DispatchError, Dispatcher
from sgenaxis.core.in_memory import DryRunLauncher, InMemoryTaskStore, ManualClock

NOW = datetime(2026, 10, 10, 22, 0)  # Saturday


def test_once_must_be_in_the_future_and_fires_once():
    with pytest.raises(ValueError, match="已過"):
        schedule.make("S1", "once", now=NOW, at="2026-10-10T21:00")
    entry = schedule.make("S1", "once", now=NOW, at="2026-10-10T23:00")
    assert schedule.events_between(entry, NOW, NOW + timedelta(hours=2)) == [(datetime(2026, 10, 10, 23, 0), "start")]
    assert schedule.events_between(entry, datetime(2026, 10, 10, 23, 0), NOW + timedelta(hours=2)) == []


def test_daily_respects_weekdays():
    entry = schedule.make("S1", "daily", now=NOW, time="09:00", weekdays=(0, 2))
    events = schedule.events_between(entry, NOW, NOW + timedelta(days=7))
    assert [moment.weekday() for moment, _action in events] == [0, 2]


def test_window_crosses_midnight_and_filters_on_the_start_day():
    entry = schedule.make("S1", "window", now=NOW, start="23:00", end="07:00", weekdays=(5,))
    events = schedule.events_between(entry, NOW, NOW + timedelta(days=1))
    assert events == [(datetime(2026, 10, 10, 23, 0), "start"), (datetime(2026, 10, 11, 7, 0), "stop")]
    with pytest.raises(ValueError, match="不能相同"):
        schedule.make("S2", "window", now=NOW, start="08:00", end="08:00")


def test_unknown_kind_and_bad_time_are_rejected():
    with pytest.raises(ValueError):
        schedule.make("S1", "hourly", now=NOW)
    with pytest.raises(ValueError):
        schedule.make("S1", "daily", now=NOW, time="25:00")


def _dispatcher():
    item = WorkItem(
        item_id="R1", code="R1", title="R1", zone="red", source="manual", files=(), bdd="", tdd="",
        created="2026-10-10 09:00", note="", updated="2026-10-10 09:00", updated_by="agent",
    )
    clock = ManualClock(NOW)
    dispatcher = Dispatcher(InMemoryTaskStore([item]), clock, DryRunLauncher(), report_grace_seconds=0)
    return clock, dispatcher


def _run(clock: ManualClock, dispatcher: Dispatcher, seconds: int) -> None:
    for _ in range(seconds // 5):
        clock.advance(timedelta(seconds=5))
        dispatcher.tick()


def test_schedule_starts_the_lane_and_window_end_stops_only_its_own_session():
    clock, dispatcher = _dispatcher()
    lane = dispatcher.add_lane("claude", max_cards=None)
    dispatcher.add_schedule(lane.lane_id, "window", start="22:01", end="22:03")
    dispatcher.tick()
    _run(clock, dispatcher, 60)
    assert lane.state == "running"
    assert dispatcher.schedule_history[0].result == "started"
    _run(clock, dispatcher, 120)
    assert lane.state == "stopping"
    assert dispatcher.schedule_history[0].result == "stop-requested"


def test_window_end_never_stops_a_manual_session():
    clock, dispatcher = _dispatcher()
    lane = dispatcher.add_lane("claude", max_cards=None)
    dispatcher.add_schedule(lane.lane_id, "window", start="21:00", end="22:01")
    dispatcher.start_lane(lane.lane_id)
    dispatcher.tick()
    _run(clock, dispatcher, 60)
    assert lane.state == "running"
    assert dispatcher.schedule_history[0].result == "not-started-by-schedule"


def test_missed_schedules_are_never_caught_up():
    clock, dispatcher = _dispatcher()
    lane = dispatcher.add_lane("claude")
    dispatcher.add_schedule(lane.lane_id, "once", at="2026-10-10T22:05")
    dispatcher.tick()
    clock.advance(timedelta(minutes=30))
    dispatcher.tick()
    assert lane.state == "idle"
    assert dispatcher.schedule_history == []


def test_paused_schedules_record_skipped_paused_and_once_disables():
    clock, dispatcher = _dispatcher()
    lane = dispatcher.add_lane("claude")
    entry = dispatcher.add_schedule(lane.lane_id, "once", at="2026-10-10T22:01")
    assert entry.schedule_id == "S1"
    dispatcher.set_schedules_paused(True)
    dispatcher.tick()
    _run(clock, dispatcher, 60)
    assert lane.state == "idle"
    assert dispatcher.schedule_history[0].result == "skipped-paused"
    assert not lane.schedules[0].enabled


def test_fired_once_schedule_needs_a_new_future_time_to_be_enabled_again():
    clock, dispatcher = _dispatcher()
    lane = dispatcher.add_lane("claude")
    dispatcher.add_schedule(lane.lane_id, "once", at="2026-10-10T22:01")
    dispatcher.set_schedules_paused(True)
    dispatcher.tick()
    _run(clock, dispatcher, 60)
    with pytest.raises(DispatchError, match="時間已過"):
        dispatcher.set_schedule_enabled(lane.lane_id, "S1", True)
    edited = dispatcher.update_schedule(lane.lane_id, "S1", max_cards=2)
    assert (edited.enabled, edited.max_cards, edited.last_result) == (False, 2, "skipped-paused")
    again = dispatcher.update_schedule(lane.lane_id, "S1", at="2026-10-11T08:00", enabled=True)
    assert (again.enabled, again.at) == (True, "2026-10-11T08:00")


def test_unknown_schedule_fields_are_rejected():
    clock, dispatcher = _dispatcher()
    lane = dispatcher.add_lane("claude")
    with pytest.raises(DispatchError, match="不支援"):
        dispatcher.add_schedule(lane.lane_id, "daily", time="09:00", repeat=3)
    entry = dispatcher.add_schedule(lane.lane_id, "daily", time="09:00")
    with pytest.raises(DispatchError, match="不支援"):
        dispatcher.update_schedule(lane.lane_id, entry.schedule_id, last_fired="2026-10-10T09:00")


def test_next_run_is_reported_and_hidden_while_paused():
    clock, dispatcher = _dispatcher()
    lane = dispatcher.add_lane("claude")
    entry = dispatcher.add_schedule(lane.lane_id, "daily", time="23:30")
    assert dispatcher.next_run(entry) == (datetime(2026, 10, 10, 23, 30), "start")
    dispatcher.set_schedules_paused(True)
    assert dispatcher.next_run(entry) is None
