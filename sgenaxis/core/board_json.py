"""WorkItem <-> hb-board/1 task dict (spec-BOARD-LOCAL-01 INV-BL-10). Pure.

The Beta field set is kept as is so the file stays readable by the board tools;
SGenAxis-only fields (source, files, confirmed, lightMode) are extra keys.
"""

from __future__ import annotations

from sgenaxis.core import board
from sgenaxis.core.board import WorkItem, ZoneChange

SCHEMA = "hb-board/1"


def from_dict(data: dict) -> WorkItem:
    by = data.get("by") or "agent"
    item = WorkItem(
        item_id=data["id"],
        code=data.get("ref") or data["id"],
        title=data.get("title") or "",
        zone=data["zone"],
        source=data.get("source") or ("manual" if by == "user" else "agent"),
        files=tuple(data.get("files") or ()),
        bdd=data.get("bdd") or "",
        tdd=data.get("tdd") or "",
        created=data.get("createdAt") or "",
        note=data.get("note") or "",
        kind=data.get("kind") or "task",
        started=data.get("startedAt"),
        completed=data.get("doneAt"),
        confirmed=bool(data.get("confirmed", False)),
        by=by,
        updated=data.get("updatedAt") or "",
        updated_by=data.get("updatedBy") or by,
        log=tuple(ZoneChange(row["t"], row["zone"], row["by"]) for row in data.get("log") or ()),
        version=int(data.get("version") or 1),
        light_mode=data.get("lightMode") or "set",
    )
    board.check(item)
    return item


def to_dict(item: WorkItem) -> dict:
    return {
        "id": item.item_id,
        "ref": item.code,
        "title": item.title,
        "zone": item.zone,
        "kind": item.kind,
        "bdd": item.bdd,
        "tdd": item.tdd,
        "note": item.note,
        "createdAt": item.created,
        "doneAt": item.completed,
        "startedAt": item.started,
        "by": item.by,
        "updatedAt": item.updated,
        "updatedBy": item.updated_by,
        "log": [{"t": change.at, "zone": change.zone, "by": change.by} for change in item.log],
        "version": item.version,
        "source": item.source,
        "files": list(item.files),
        "confirmed": item.confirmed,
        "lightMode": item.light_mode,
    }


def items_from_document(document: dict | list) -> list[WorkItem]:
    tasks = document if isinstance(document, list) else document.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("看板檔案沒有 tasks 清單")
    return [from_dict(row) for row in tasks]


def document(items: list[WorkItem]) -> dict:
    return {"schema": SCHEMA, "tasks": [to_dict(item) for item in sorted(items, key=lambda row: row.item_id)]}
