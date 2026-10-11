"""Schedule rules from the Beta board (INV-BD-48/49). Local naive datetimes; no clock."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta

KINDS = ("once", "daily", "window")
KIND_LABELS = {"once": "單次", "daily": "每天", "window": "時段"}
WEEKDAY_LABELS = ("週一", "週二", "週三", "週四", "週五", "週六", "週日")
UNLIMITED = "unlimited"

_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


@dataclass(frozen=True)
class Schedule:
    schedule_id: str
    kind: str
    at: str = ""
    time: str = ""
    start: str = ""
    end: str = ""
    weekdays: tuple[int, ...] = ()
    enabled: bool = True
    max_cards: int | str | None = None
    last_fired: str = ""
    last_result: str = ""


def make(
    schedule_id: str,
    kind: str,
    *,
    now: datetime,
    at: str = "",
    time: str = "",
    start: str = "",
    end: str = "",
    weekdays=(),
    enabled: bool = True,
    max_cards: int | str | None = None,
    require_future: bool = True,
) -> Schedule:
    if kind not in KINDS:
        raise ValueError(f"未知的排程種類：{kind}")
    days = tuple(sorted(set(weekdays)))
    if any(day not in range(7) for day in days):
        raise ValueError("星期只能是 0（週一）到 6（週日）")
    if max_cards not in (None, UNLIMITED) and (not isinstance(max_cards, int) or max_cards < 1):
        raise ValueError("張數必須是正整數或做到無卡為止")
    if kind == "once":
        moment = _parse_at(at)
        if require_future and moment <= now:
            raise ValueError("單次排程的時間已過")
        return Schedule(schedule_id, kind, at=at, enabled=enabled, max_cards=max_cards)
    if kind == "daily":
        _parse_hhmm(time)
        return Schedule(schedule_id, kind, time=time, weekdays=days, enabled=enabled, max_cards=max_cards)
    if _parse_hhmm(start) == _parse_hhmm(end):
        raise ValueError("時段開始與結束不能相同")
    return Schedule(schedule_id, kind, start=start, end=end, weekdays=days, enabled=enabled, max_cards=max_cards)


def events_between(entry: Schedule, after: datetime, until: datetime) -> list[tuple[datetime, str]]:
    """Events with after < t <= until, oldest first. Missed periods are not replayed."""
    if until <= after:
        return []
    if entry.kind == "once":
        moment = _parse_at(entry.at)
        return [(moment, "start")] if after < moment <= until else []
    events: list[tuple[datetime, str]] = []
    day = after.date() - timedelta(days=1)
    while day <= until.date():
        if not entry.weekdays or day.weekday() in entry.weekdays:
            events.extend(_day_events(entry, day))
        day += timedelta(days=1)
    return sorted(event for event in events if after < event[0] <= until)


def next_event(entry: Schedule, now: datetime) -> tuple[datetime, str] | None:
    if not entry.enabled:
        return None
    upcoming = events_between(entry, now, now + timedelta(days=8))
    return upcoming[0] if upcoming else None


def disable(entry: Schedule) -> Schedule:
    return replace(entry, enabled=False)


def describe(entry: Schedule) -> str:
    days = "、".join(WEEKDAY_LABELS[day] for day in entry.weekdays) or "每天"
    if entry.kind == "once":
        text = f"單次 {entry.at.replace('T', ' ')}"
    elif entry.kind == "daily":
        text = f"每天 {entry.time}（{days}）"
    else:
        text = f"時段 {entry.start}–{entry.end}（{days}）"
    if entry.max_cards == UNLIMITED:
        return text + " · 做到無卡為止"
    if entry.max_cards is not None:
        return text + f" · {entry.max_cards} 張"
    return text + " · 跟這條 Agent 的設定"


def _day_events(entry: Schedule, day: date) -> list[tuple[datetime, str]]:
    if entry.kind == "daily":
        return [(datetime.combine(day, _parse_hhmm(entry.time)), "start")]
    start = _parse_hhmm(entry.start)
    end = _parse_hhmm(entry.end)
    end_day = day if end > start else day + timedelta(days=1)
    return [(datetime.combine(day, start), "start"), (datetime.combine(end_day, end), "stop")]


def _parse_hhmm(text: str) -> time:
    match = _HHMM.match(text or "")
    if not match:
        raise ValueError(f"時間格式必須是 HH:MM：{text}")
    return time(int(match.group(1)), int(match.group(2)))


def _parse_at(text: str) -> datetime:
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M")
    except ValueError as exc:
        raise ValueError(f"日期時間格式必須是 YYYY-MM-DDTHH:MM：{text}") from exc
