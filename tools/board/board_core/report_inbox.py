"""Driven adapter: the report-file inbox (BOARD-DISPATCH-01 §3.11, INV-BD-44/46).

The inbox (default tools/board/report-inbox/) is deliberately NOT gitignored: some agent IDEs (Antigravity's
default "gitignore access" setting) refuse to edit ignored paths. A handled file is moved, never deleted, into
<archive>/processed | ignored | rejected/ under the gitignored runtime directory.
"""
import os

from . import report_channels

ARCHIVE_KINDS = ("processed", "ignored", "rejected")


class ReportInbox:
    def __init__(self, inbox_dir, archive_dir):
        self.inbox_dir = inbox_dir
        self.archive_dir = archive_dir

    def path(self, run_id):
        return os.path.join(self.inbox_dir, run_id + ".json")

    def ensure(self):
        os.makedirs(self.inbox_dir, exist_ok=True)

    def read(self, run_id):
        """Raw bytes of <runId>.json (at most the size cap + 1, so oversize is detectable), or None."""
        try:
            with open(self.path(run_id), "rb") as f:
                return f.read(report_channels.REPORT_FILE_MAX_BYTES + 1)
        except FileNotFoundError:
            return None
        except OSError:
            return None  # still being written / locked by the agent's editor: try again next tick

    def archive(self, run_id, kind):
        """Move the run's file out of the inbox; returns the new path or None (already gone / still locked)."""
        if kind not in ARCHIVE_KINDS:
            raise ValueError("archive kind %r" % (kind,))
        src = self.path(run_id)
        if not os.path.exists(src):
            return None
        dest_dir = os.path.join(self.archive_dir, kind)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, run_id + ".json")
        n = 1
        while os.path.exists(dest):
            n += 1
            dest = os.path.join(dest_dir, "%s.%d.json" % (run_id, n))
        try:
            os.replace(src, dest)
        except OSError:
            return None
        return dest
