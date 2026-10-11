"""Task rules from the Beta light board (spec-BOARD-LOCAL-01 INV-BL-1..11).

Pure functions over immutable work items. No Qt, no I/O, and no clock:
callers pass the current time as an ISO-8601 string (see timefmt).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

ZONES = ("gray", "yellow", "red", "green")
STATUSES = ZONES + ("accepted",)
KINDS = ("task", "bug", "note", "epic", "milestone", "release")
ACTORS = ("user", "agent")
SOURCES = ("git", "agent", "manual")
EDITABLE = ("title", "bdd", "tdd", "note", "kind", "files")
LOG_LIMIT = 20

_ID = re.compile(r"^[A-Za-z0-9_\-.~:@+]+$")


class VersionConflict(ValueError):
    """The stored task changed after the caller read it."""


@dataclass(frozen=True)
class ZoneChange:
    at: str
    zone: str
    by: str


@dataclass(frozen=True)
class WorkItem:
    item_id: str
    code: str
    title: str
    zone: str
    source: str
    files: tuple[str, ...]
    bdd: str
    tdd: str
    created: str
    note: str
    kind: str = "task"
    started: str | None = None
    completed: str | None = None
    confirmed: bool = False
    by: str = "user"
    updated: str = ""
    updated_by: str = "user"
    log: tuple[ZoneChange, ...] = ()
    version: int = 1
    light_mode: str = "set"

    @property
    def status(self) -> str:
        return "accepted" if self.zone == "green" and self.confirmed else self.zone


def check(item: WorkItem) -> None:
    if not _ID.match(item.item_id):
        raise ValueError(f"工項編號只能用英數與 _-.~:@+：{item.item_id}")
    _require(item.zone, ZONES, "燈號")
    _require(item.kind, KINDS, "類型")
    _require(item.by, ACTORS, "來源")
    _require(item.updated_by, ACTORS, "修改者")
    if (item.completed is not None) != (item.zone == "green"):
        raise ValueError("完成時間只在綠燈時存在")
    if item.confirmed and item.zone != "green":
        raise ValueError("只有綠燈工項可以驗收")
    if len(item.log) > LOG_LIMIT:
        raise ValueError("燈號紀錄最多 20 筆")
    if item.version < 1:
        raise ValueError("版本必須是正整數")


def set_zone(item: WorkItem, zone: str, actor: str, now: str, note_line: str = "") -> WorkItem:
    _require(zone, ZONES, "燈號")
    _require(actor, ACTORS, "來源")
    if zone == item.zone and not note_line:
        return item
    changes: dict = {}
    if zone != item.zone:
        changes.update(
            zone=zone,
            completed=now if zone == "green" else None,
            confirmed=False,
            log=(item.log + (ZoneChange(now, zone, actor),))[-LOG_LIMIT:],
        )
        if zone == "yellow" and item.started is None:
            changes["started"] = now
    if note_line:
        changes["note"] = f"{item.note}\n{note_line}" if item.note else note_line
    return _touch(item, actor, now, **changes)


def set_status(item: WorkItem, status: str, actor: str, now: str) -> WorkItem:
    _require(status, STATUSES, "狀態")
    if status != "accepted":
        if status == "green" and item.confirmed:
            return _touch(item, actor, now, confirmed=False)
        return set_zone(item, status, actor, now)
    if actor != "user":
        raise ValueError("只有使用者可以確認驗收")
    if item.confirmed:
        return item
    green = set_zone(item, "green", actor, now)
    return replace(green, confirmed=True, updated=now, updated_by=actor, version=item.version + 1)


def edit(item: WorkItem, fields: dict, actor: str, now: str) -> WorkItem:
    _require(actor, ACTORS, "來源")
    unknown = set(fields) - set(EDITABLE)
    if unknown:
        raise ValueError(f"不能修改欄位：{', '.join(sorted(unknown))}")
    if "kind" in fields:
        _require(fields["kind"], KINDS, "類型")
    if "files" in fields:
        fields = {**fields, "files": tuple(fields["files"])}
    if all(getattr(item, key) == value for key, value in fields.items()):
        return item
    return _touch(item, actor, now, **fields)


def agent_may_overwrite(item: WorkItem) -> bool:
    return item.updated_by != "user"


def _touch(item: WorkItem, actor: str, now: str, **changes) -> WorkItem:
    return replace(item, updated=now, updated_by=actor, version=item.version + 1, **changes)


def _require(value: str, allowed: tuple[str, ...], label: str) -> None:
    if value not in allowed:
        raise ValueError(f"未知的{label}：{value}")
