"""Read-only Beta board snapshot shipped in sgenaxis/data/board-seed (80 tasks + 1 release).

Shown at startup before any project is opened. It is never written back; the
manifest records the source folder and a SHA-256 per file so a changed copy is caught.
"""

from __future__ import annotations

import hashlib
import json
import os

from sgenaxis.core import board_json, release
from sgenaxis.core.board import WorkItem
from sgenaxis.core.ports import StoreError
from sgenaxis.core.release import Release

SEED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "board-seed")


def _read_checked(name: str, seed_dir: str) -> dict | list:
    with open(os.path.join(seed_dir, "manifest.json"), encoding="utf-8") as handle:
        expected = json.load(handle)["files"][name]
    with open(os.path.join(seed_dir, name), "rb") as handle:
        raw = handle.read()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise StoreError(f"示範看板 {name} 與 manifest 的 SHA-256 不符（{actual}）")
    return json.loads(raw.decode("utf-8-sig"))


def available(seed_dir: str = SEED_DIR) -> bool:
    """The snapshot is local data and is not shipped in the public repository."""
    return os.path.isfile(os.path.join(seed_dir, "manifest.json"))


def load_items(seed_dir: str = SEED_DIR) -> list[WorkItem]:
    return board_json.items_from_document(_read_checked("tasks.json", seed_dir))


def load_releases(seed_dir: str = SEED_DIR) -> list[Release]:
    return release.releases_from_document(_read_checked("releases.json", seed_dir))


def source(seed_dir: str = SEED_DIR) -> str:
    with open(os.path.join(seed_dir, "manifest.json"), encoding="utf-8") as handle:
        return json.load(handle)["source"]
