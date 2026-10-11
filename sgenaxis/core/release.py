"""Release records from the board (hb-board/1 releases). Pure, read-only value objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Artifact:
    label: str
    path: str
    exists: bool
    checked_at: str


@dataclass(frozen=True)
class ArtifactCheck:
    """An artifact as found now (`live`) or, without a file probe, as recorded on the board."""

    label: str
    path: str
    exists: bool
    live: bool
    size: int = 0
    files: int = 0
    is_dir: bool = False
    modified: datetime | None = None


@dataclass(frozen=True)
class Commit:
    hash: str
    subject: str
    at: str


@dataclass(frozen=True)
class Release:
    release_id: str
    version: str
    kind: str
    released_at: str
    recorded_at: str
    recorded_by: str
    artifacts: tuple[Artifact, ...] = ()
    commits: tuple[Commit, ...] = ()
    report_md: str = ""
    changelog_md: str = ""
    sources: tuple[tuple[str, str], ...] = ()


def from_dict(data: dict) -> Release:
    version = str(data.get("version") or "")
    return Release(
        release_id=str(data.get("id") or f"v{version}"),
        version=version,
        kind=str(data.get("kind") or ""),
        released_at=str(data.get("releasedAt") or ""),
        recorded_at=str(data.get("recordedAt") or ""),
        recorded_by=str(data.get("recordedBy") or ""),
        artifacts=tuple(
            Artifact(str(row.get("label", "")), str(row.get("path", "")), bool(row.get("exists")), str(row.get("checkedAt", "")))
            for row in data.get("artifacts") or ()
        ),
        commits=tuple(
            Commit(str(row.get("hash", "")), str(row.get("subject", "")), str(row.get("at", "")))
            for row in data.get("commits") or ()
        ),
        report_md=str(data.get("reportMd") or ""),
        changelog_md=str(data.get("changelogMd") or ""),
        sources=tuple((str(row.get("label", "")), str(row.get("path", ""))) for row in data.get("sources") or ()),
    )


def releases_from_document(document: dict | list) -> list[Release]:
    rows = document if isinstance(document, list) else document.get("releases", [])
    if not isinstance(rows, list):
        raise ValueError("佈版檔案沒有 releases 清單")
    releases = [from_dict(row) for row in rows]
    return sorted(releases, key=lambda item: item.released_at or item.recorded_at, reverse=True)
