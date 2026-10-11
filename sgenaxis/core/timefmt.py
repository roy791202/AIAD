"""Board timestamps: ISO-8601 strings as in the Beta board (hb-board/1). Pure; no clock."""

from __future__ import annotations

from datetime import datetime, timezone

DISPLAY_FORMAT = "%Y-%m-%d %H:%M"


def stamp(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def parse(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def sort_key(text: str | None) -> tuple[int, float]:
    """Oldest first; a time without zone counts as UTC and an unreadable one sorts last (INV-BD-2)."""
    moment = parse(text)
    if moment is None:
        return (1, 0.0)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return (0, moment.timestamp())


def local(moment: datetime) -> datetime:
    """Wall-clock time without zone, as schedules and day buckets use."""
    return moment.astimezone().replace(tzinfo=None) if moment.tzinfo else moment


def display(text: str | None) -> str:
    moment = parse(text)
    if moment is None:
        return text or "—"
    return local(moment).strftime(DISPLAY_FORMAT)
