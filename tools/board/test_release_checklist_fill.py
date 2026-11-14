"""PD-CHECKLIST-FILL-01 — six checklist rows must carry allowed statuses."""

from __future__ import annotations

import unittest
from pathlib import Path

import release_checklist_fill as checklist


class ReleaseChecklistFillTests(unittest.TestCase):
    def test_six_items_have_allowed_nonblank_status(self) -> None:
        rows = checklist.load_and_assert()
        self.assertEqual(set(rows), set(checklist.REQUIRED_ITEMS))
        for name in checklist.REQUIRED_ITEMS:
            status = rows[name]["status"]
            self.assertIn(status, checklist.ALLOWED_STATUSES)
            self.assertTrue(rows[name]["evidence"].strip())

    def test_parser_rejects_blank_status(self) -> None:
        bad = """
| # | 項 | 狀態 | 證據（路徑） |
|---|----|------|--------------|
| 1 | MSI | PASS | a |
| 2 | Elev | PASS | b |
| 3 | Sec | PARTIAL | c |
| 4 | SBOM | PASS | d |
| 5 | 簽章 |  | e |
| 6 | CHANGELOG | PASS | f |
"""
        with self.assertRaises(AssertionError):
            checklist.assert_six_statuses(bad)

    def test_parser_rejects_unknown_status(self) -> None:
        bad = """
| 1 | MSI | PASS | a |
| 2 | Elev | PASS | b |
| 3 | Sec | PARTIAL | c |
| 4 | SBOM | PASS | d |
| 5 | 簽章 | SKIPPED | e |
| 6 | CHANGELOG | PASS | f |
"""
        with self.assertRaises(AssertionError):
            checklist.assert_six_statuses(bad)

    def test_checklist_file_exists(self) -> None:
        path = checklist.default_checklist_path()
        self.assertTrue(path.is_file(), "missing %s" % path)
        self.assertIn("PD-CHECKLIST-FILL-01", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(
        0 if unittest.main(verbosity=2, exit=False).result.wasSuccessful() else 1
    )
