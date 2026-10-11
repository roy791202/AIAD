"""How a dispatched agent's report reaches the board (spec-BOARD-DISPATCH-01 §3.11). Pure.

INV-BD-43 any valid channel completes the run; the first valid report wins, later ones are recorded as ignored.
INV-BD-44 report file {"card", "run", "outcome", "note"}: at most 16 KB, UTF-8 (BOM or UTF-16 accepted),
          card and run must match the running round, outcome done | blocked, note flattened to one line.
INV-BD-45 marker line `HB-REPORT: <done|blocked> <runId> <note>` in captured output; the prompt only shows a
          `<done-or-blocked>` placeholder, so an echoed prompt never matches.
"""

from __future__ import annotations

import json
import re

CHANNELS = ("file", "marker", "cli", "ui")
CHANNEL_LABELS = {"file": "回報檔", "marker": "輸出標記", "cli": "回報指令", "ui": "介面模擬"}
REPORT_FILE_MAX_BYTES = 16 * 1024
NOTE_MAX_CHARS = 500
MARKER_PREFIX = "HB-REPORT:"
OUTCOMES = ("done", "blocked")
_MARKER = re.compile(
    r"^[ \t>*`_]*HB-REPORT:[ \t]*(done|blocked)[ \t]+([A-Za-z0-9_.\-]+)[`*_]*(?:[ \t]+(.*?))?[ \t`*_\r]*$",
    re.MULTILINE,
)


class ReportInvalid(ValueError):
    """The report file exists but cannot be accepted; the message says why."""


def one_line(note: object) -> str:
    return " ".join(str(note or "").split())[:NOTE_MAX_CHARS]


def encode_report(card_id: str, run_id: str, outcome: str, note: str, via: str = "file") -> bytes:
    """The report file body; the report command writes it with via="cli"."""
    if outcome not in OUTCOMES:
        raise ReportInvalid(f"outcome 必須是 done 或 blocked，收到 {outcome!r}")
    doc = {"card": card_id, "run": run_id, "outcome": outcome, "note": one_line(note), "via": via}
    raw = json.dumps(doc, ensure_ascii=False).encode("utf-8")
    if len(raw) > REPORT_FILE_MAX_BYTES:
        raise ReportInvalid(f"回報超過 {REPORT_FILE_MAX_BYTES // 1024} KB")
    return raw


def parse_report_file(raw: bytes, card_id: str, run_id: str) -> tuple[str, str, str]:
    """Returns (outcome, note, channel); channel is "cli" when the report command wrote the file."""
    if len(raw) > REPORT_FILE_MAX_BYTES:
        raise ReportInvalid(f"回報檔超過 {REPORT_FILE_MAX_BYTES // 1024} KB")
    try:
        doc = json.loads(_decode(raw))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ReportInvalid(f"回報檔不是有效的 UTF-8 JSON：{exc}") from exc
    if not isinstance(doc, dict):
        raise ReportInvalid("回報檔必須是 JSON 物件")
    if doc.get("card") != card_id:
        raise ReportInvalid(f"回報檔的 card 是 {doc.get('card')!r}，應為 {card_id!r}")
    if doc.get("run") != run_id:
        raise ReportInvalid(f"回報檔的 run 是 {doc.get('run')!r}，應為 {run_id!r}")
    if doc.get("outcome") not in OUTCOMES:
        raise ReportInvalid(f"回報檔的 outcome 必須是 done 或 blocked，收到 {doc.get('outcome')!r}")
    note = doc.get("note", "")
    if not isinstance(note, str):
        raise ReportInvalid("回報檔的 note 必須是字串")
    return doc["outcome"], one_line(note), "cli" if doc.get("via") == "cli" else "file"


def find_marker(text: str, run_id: str) -> tuple[str, str] | None:
    found = None
    for match in _MARKER.finditer(text or ""):
        if match.group(2) == run_id:
            found = (match.group(1), one_line(match.group(3)))
    return found


def marker_template(run_id: str) -> str:
    return f"{MARKER_PREFIX} <done-or-blocked> {run_id} <one-line note>"


def _decode(raw: bytes) -> str:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8")
    return raw.decode("utf-8")
