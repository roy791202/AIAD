"""Read-only file checks for release artifacts and the project's dist folder."""

from __future__ import annotations

import os
import stat
from datetime import datetime

from sgenaxis.core.ports import FileInfo

WALK_LIMIT = 20000


class LocalFileProbe:
    """Folder sizes stop counting after `walk_limit` entries so a huge tree cannot stall the UI."""

    def __init__(self, walk_limit: int = WALK_LIMIT) -> None:
        self.walk_limit = walk_limit

    def stat(self, path: str) -> FileInfo | None:
        try:
            info = os.stat(path)
        except OSError:
            return None
        is_dir = stat.S_ISDIR(info.st_mode)
        size, files = self._tree(path) if is_dir else (info.st_size, 0)
        modified = datetime.fromtimestamp(info.st_mtime).astimezone()
        return FileInfo(path, os.path.basename(path.rstrip("\\/")), is_dir, size, modified, files)

    def entries(self, folder: str) -> list[FileInfo]:
        try:
            with os.scandir(folder) as found:
                paths = sorted(entry.path for entry in found)
        except OSError:
            return []
        return [info for info in (self.stat(path) for path in paths) if info is not None]

    def _tree(self, folder: str) -> tuple[int, int]:
        size = files = seen = 0
        pending = [folder]
        while pending and seen < self.walk_limit:
            try:
                with os.scandir(pending.pop()) as found:
                    for entry in found:
                        seen += 1
                        if entry.is_dir(follow_symlinks=False):
                            pending.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            files += 1
                            size += entry.stat(follow_symlinks=False).st_size
            except OSError:
                continue
        return size, files
