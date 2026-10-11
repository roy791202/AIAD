"""Period statistics from the Beta board (期間統計). Pure; days are local wall-clock days."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sgenaxis.core import timefmt
from sgenaxis.core.board import WorkItem

GRANULARITIES = ("day", "week", "month")
GRANULARITY_LABELS = {"day": "日", "week": "週", "month": "月"}


@dataclass(frozen=True)
class Period:
    label: str
    start: date
    created: int
    done: int
    created_done: int
    cumulative_rate: float

    @property
    def created_done_rate(self) -> float:
        return self.created_done / self.created if self.created else 0.0


def completion_rate(items: list[WorkItem]) -> float:
    if not items:
        return 0.0
    return sum(1 for item in items if item.zone == "green") / len(items)


def periods(items: list[WorkItem], granularity: str, limit: int | None = None) -> list[Period]:
    if granularity not in GRANULARITIES:
        raise ValueError(f"未知的統計單位：{granularity}")
    created = [(day, item) for item in items if (day := _day(item.created)) is not None]
    done = [day for item in items if item.zone == "green" and (day := _day(item.completed)) is not None]
    if not created:
        return []
    first = _bucket(min(day for day, _item in created), granularity)
    last = _bucket(max([day for day, _item in created] + done), granularity)
    rows: list[Period] = []
    start = first
    while start <= last:
        end = _next(start, granularity)
        in_period = [item for day, item in created if start <= day < end]
        created_total = sum(1 for day, _item in created if day < end)
        done_total = sum(1 for day in done if day < end)
        rows.append(
            Period(
                _label(start, granularity),
                start,
                len(in_period),
                sum(1 for day in done if start <= day < end),
                sum(1 for item in in_period if item.zone == "green"),
                done_total / created_total if created_total else 0.0,
            )
        )
        start = end
    return rows[-limit:] if limit else rows


def _day(text: str | None) -> date | None:
    moment = timefmt.parse(text)
    return timefmt.local(moment).date() if moment else None


def _bucket(day: date, granularity: str) -> date:
    if granularity == "week":
        return day - timedelta(days=day.weekday())
    if granularity == "month":
        return day.replace(day=1)
    return day


def _next(start: date, granularity: str) -> date:
    if granularity == "day":
        return start + timedelta(days=1)
    if granularity == "week":
        return start + timedelta(days=7)
    return (start.replace(day=28) + timedelta(days=4)).replace(day=1)


def _label(start: date, granularity: str) -> str:
    if granularity == "month":
        return start.strftime("%Y-%m")
    if granularity == "week":
        return start.strftime("%m-%d") + " 週"
    return start.strftime("%m-%d")
