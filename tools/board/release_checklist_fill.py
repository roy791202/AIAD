"""PD-CHECKLIST-FILL-01 — parse RELEASE-CHECKLIST-v0.1.md summary statuses.

Asserts each of the six checklist items has a non-blank status in
{PASS, FAIL, NOT RUN, PARTIAL}. Does not auto-approve release.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

ALLOWED_STATUSES = frozenset({"PASS", "FAIL", "NOT RUN", "PARTIAL"})

REQUIRED_ITEMS: Tuple[str, ...] = (
    "MSI",
    "Elev",
    "Sec",
    "SBOM",
    "簽章",
    "CHANGELOG",
)

# Summary table row: | 1 | MSI | PASS | evidence... |
_SUMMARY_ROW_RE = re.compile(
    r"^\|\s*([1-6])\s*\|\s*(MSI|Elev|Sec|SBOM|簽章|CHANGELOG)\s*\|\s*"
    r"(PASS|FAIL|NOT RUN|PARTIAL)\s*\|\s*(.+?)\s*\|\s*$",
    re.MULTILINE,
)


def default_checklist_path(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[2]
    return root / "docs" / "RELEASE-CHECKLIST-v0.1.md"


def parse_summary_statuses(text: str) -> Dict[str, Dict[str, str]]:
    """Return {item: {status, evidence, index}} from the 彙總 table."""
    found: Dict[str, Dict[str, str]] = {}
    for match in _SUMMARY_ROW_RE.finditer(text or ""):
        index, item, status, evidence = match.groups()
        evidence = evidence.strip()
        if not evidence:
            raise ValueError("blank evidence for item %s" % item)
        found[item] = {
            "index": index,
            "status": status,
            "evidence": evidence,
        }
    return found


def assert_six_statuses(text: str) -> Dict[str, Dict[str, str]]:
    """Raise AssertionError if any of the six items lacks a valid status."""
    found = parse_summary_statuses(text)
    missing = [name for name in REQUIRED_ITEMS if name not in found]
    if missing:
        raise AssertionError(
            "RELEASE-CHECKLIST missing summary rows for: %s" % ", ".join(missing)
        )
    bad: List[str] = []
    for name in REQUIRED_ITEMS:
        status = (found[name].get("status") or "").strip()
        if not status:
            bad.append("%s: blank status" % name)
        elif status not in ALLOWED_STATUSES:
            bad.append("%s: invalid status %r" % (name, status))
        evidence = (found[name].get("evidence") or "").strip()
        if not evidence:
            bad.append("%s: blank evidence" % name)
    if bad:
        raise AssertionError("; ".join(bad))
    return found


def load_and_assert(path: Path | None = None) -> Dict[str, Dict[str, str]]:
    checklist = path or default_checklist_path()
    text = checklist.read_text(encoding="utf-8")
    return assert_six_statuses(text)


if __name__ == "__main__":
    rows = load_and_assert()
    for name in REQUIRED_ITEMS:
        row = rows[name]
        print("%s\t%s\t%s" % (name, row["status"], row["evidence"][:80]))
