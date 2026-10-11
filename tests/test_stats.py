"""Period statistics from the Beta board (期間統計)."""

import pytest

from sgenaxis.core import stats
from sgenaxis.core.board import WorkItem


def _item(item_id: str, created: str, completed: str | None) -> WorkItem:
    return WorkItem(
        item_id=item_id, code=item_id, title=item_id, zone="green" if completed else "gray",
        source="manual", files=(), bdd="", tdd="", created=created, note="", completed=completed,
    )


ITEMS = [
    _item("A", "2026-10-05 09:00", "2026-10-06 10:00"),
    _item("B", "2026-10-06 09:00", None),
    _item("C", "2026-10-12 09:00", "2026-10-12 18:00"),
]


def test_weekly_periods_count_created_done_and_rates():
    rows = stats.periods(ITEMS, "week")
    assert [row.label for row in rows] == ["10-05 週", "10-12 週"]
    first, second = rows
    assert (first.created, first.done, first.created_done) == (2, 1, 1)
    assert first.cumulative_rate == pytest.approx(0.5)
    assert (second.created, second.done, second.cumulative_rate) == (1, 1, pytest.approx(2 / 3))


def test_day_and_month_granularity_and_limit():
    assert [row.label for row in stats.periods(ITEMS, "month")] == ["2026-10"]
    assert len(stats.periods(ITEMS, "day")) == 8
    assert [row.label for row in stats.periods(ITEMS, "day", limit=2)] == ["10-11", "10-12"]
    with pytest.raises(ValueError):
        stats.periods(ITEMS, "year")


def test_completion_rate_is_green_over_all():
    assert stats.completion_rate(ITEMS) == pytest.approx(2 / 3)
    assert stats.completion_rate([]) == 0.0
