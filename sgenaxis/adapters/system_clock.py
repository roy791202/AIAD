"""Clock port backed by the local system time."""

from __future__ import annotations

from datetime import datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now().astimezone().replace(microsecond=0)
