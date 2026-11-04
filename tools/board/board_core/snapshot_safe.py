"""PD-BOARD-SAFE-01 — safe PROJECT-BOARD.html writes.

Any write must replace **only** the JSON inside ``#board-snapshot``.
The HTML shell (DOCTYPE, styles, navigation, runtime ``<script>`` after the
snapshot) is preserved byte-for-byte outside that payload.

Whole-file overwrites (snapshot-only dumps, missing DOCTYPE / nav) are rejected.
Agents must use this helper (or ``board.py`` / ``board_watch.mutate_html`` which
call it) — never rewrite ``docs/PROJECT-BOARD.html`` from a stale full copy.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable, MutableMapping, Tuple

SNAPSHOT_OPEN = '<script type="application/json" id="board-snapshot">'
SNAPSHOT_CLOSE = "</script>"

# Shell landmarks required before and after every write (BDD-PD-BOARD-SAFE-01).
_DOCTYPE_RE = re.compile(r"^\s*<!DOCTYPE\s+html\b", re.IGNORECASE)
# Navigation: CSS `.nav` / `.navbtn`, a `<nav` element, or visible 導覽 copy.
_NAV_MARKERS = (
    "class=\"nav\"",
    "class='nav'",
    ".nav ",
    ".nav{",
    ".navbtn",
    "<nav",
    "導覽",
)


class ShellCorruptError(ValueError):
    """HTML shell missing DOCTYPE, navigation, or #board-snapshot."""


class FullOverwriteRejected(ValueError):
    """Candidate write would replace the whole file / drop the HTML shell."""


def split_snapshot(html: str) -> Tuple[str, str, str]:
    """Return ``(prefix_through_open, json_inner, suffix_from_close)``."""
    start = html.find(SNAPSHOT_OPEN)
    if start < 0:
        raise ShellCorruptError("board-snapshot missing")
    inner = start + len(SNAPSHOT_OPEN)
    end = html.find(SNAPSHOT_CLOSE, inner)
    if end < 0:
        raise ShellCorruptError("board-snapshot unclosed")
    return html[:inner], html[inner:end], html[end:]


def assert_shell_intact(html: str, *, label: str = "html") -> None:
    """FAIL if DOCTYPE, navigation, or #board-snapshot marker is absent."""
    if not _DOCTYPE_RE.match(html or ""):
        raise ShellCorruptError("%s: missing <!DOCTYPE html> shell" % label)
    if SNAPSHOT_OPEN not in html and 'id="board-snapshot"' not in html:
        raise ShellCorruptError("%s: missing #board-snapshot" % label)
    low = html.lower()
    if not any(m.lower() in low if m.isascii() else m in html for m in _NAV_MARKERS):
        raise ShellCorruptError("%s: missing navigation shell (.nav / <nav / 導覽)" % label)


def dump_snapshot_json(data: MutableMapping[str, Any]) -> str:
    return "\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def shell_halves(html: str) -> Tuple[str, str]:
    """Prefix (through open tag) and suffix (from ``</script>``) — the immutable shell."""
    prefix, _inner, suffix = split_snapshot(html)
    return prefix, suffix


def detect_full_overwrite(original: str, candidate: str) -> str | None:
    """Return a reason string if ``candidate`` is a whole-file / shell-destroying overwrite.

    Returns ``None`` when the write is a legitimate snapshot-only replacement
    (shell halves byte-identical to ``original``).
    """
    try:
        assert_shell_intact(original, label="original")
    except ShellCorruptError as exc:
        return "original shell corrupt: %s" % exc
    try:
        assert_shell_intact(candidate, label="candidate")
    except ShellCorruptError as exc:
        return "candidate drops shell: %s" % exc
    try:
        op, osuf = shell_halves(original)
        cp, csuf = shell_halves(candidate)
    except ShellCorruptError as exc:
        return "cannot split snapshot: %s" % exc
    if op != cp:
        return "prefix shell changed (full overwrite or edit outside #board-snapshot)"
    if osuf != csuf:
        return "suffix shell changed (full overwrite or edit outside #board-snapshot)"
    return None


def refuse_if_full_overwrite(original: str, candidate: str) -> None:
    reason = detect_full_overwrite(original, candidate)
    if reason:
        raise FullOverwriteRejected(reason)


def compose_replaced_snapshot(original_html: str, data: MutableMapping[str, Any]) -> str:
    """Build new HTML that only replaces the JSON inside ``#board-snapshot``."""
    assert_shell_intact(original_html, label="before")
    prefix, _inner, suffix = split_snapshot(original_html)
    new_html = prefix + dump_snapshot_json(data) + suffix
    refuse_if_full_overwrite(original_html, new_html)
    assert_shell_intact(new_html, label="after")
    return new_html


def load_snapshot_dict(html: str) -> dict:
    _prefix, inner, _suffix = split_snapshot(html)
    try:
        data = json.loads(inner)
    except json.JSONDecodeError as exc:
        raise ShellCorruptError("snapshot JSON invalid: %s" % exc) from exc
    if not isinstance(data, dict):
        raise ShellCorruptError("snapshot is not an object")
    data.setdefault("tasks", [])
    data.setdefault("releases", [])
    if not isinstance(data["tasks"], list):
        raise ShellCorruptError("tasks is not a list")
    return data


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(str(tmp), str(path))


def mutate_snapshot_file(
    path: Path,
    mutator: Callable[[dict], Any],
    *,
    lock_factory: Callable[[str], Any] | None = None,
) -> Any:
    """Read board HTML, run ``mutator(data)``, write snapshot-only replacement.

    ``lock_factory`` when given is called with ``str(path)+'.lock'`` and used as a
    context manager (same contract as ``board_watch.FileLock``).
    """
    path = Path(path)

    def _run() -> Any:
        html = path.read_text(encoding="utf-8")
        assert_shell_intact(html, label="before-read")
        data = load_snapshot_dict(html)
        result = mutator(data)
        new_html = compose_replaced_snapshot(html, data)
        atomic_write_text(path, new_html)
        return result

    if lock_factory is None:
        return _run()
    with lock_factory(str(path) + ".lock"):
        return _run()
