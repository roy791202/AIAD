"""How a dispatched agent's report reaches the board (BOARD-DISPATCH-01 §3.11; pure functions, no I/O).

INV-BD-43 three channels, any valid one completes the run: the report file (<inbox>/<runId>.json), the stdout
          marker line, and `board.py report`. The first valid report wins; later ones are ignored (recorded).
INV-BD-44 report file: a JSON object {"card", "run", "outcome", "note"} of at most REPORT_FILE_MAX_BYTES, UTF-8
          (a BOM or UTF-16 from Windows editors / PowerShell is accepted); card and run must equal the running
          round's, outcome done | blocked; the note is flattened to one line and cut at NOTE_MAX_CHARS.
INV-BD-45 marker: a line `HB-REPORT: <done|blocked> <runId> <note>` in the agent's output. The run id must be
          the running round's; leading markdown (`>`, `*`, backquotes) is tolerated. The prompt only ever shows
          the marker with a `<done-or-blocked>` placeholder, so an echoed prompt can never match.
"""
import json
import re

from .dispatch import REPORT_OUTCOMES

CHANNELS = ("file", "marker", "cli")
CHANNEL_LABEL = {"file": "回報檔", "marker": "輸出標記", "cli": "board.py report"}
REPORT_FILE_MAX_BYTES = 16 * 1024
NOTE_MAX_CHARS = 500
MARKER_PREFIX = "HB-REPORT:"
MARKER_RE = re.compile(
    r"^[ \t>*`_]*HB-REPORT:[ \t]*(done|blocked)[ \t]+([A-Za-z0-9_.\-]+)[`*_]*(?:[ \t]+(.*?))?[ \t`*_\r]*$",
    re.MULTILINE,
)


class ReportInvalid(ValueError):
    """The report file exists but cannot be accepted; the message says why (shown to the owner)."""


def one_line(note):
    text = " ".join(str(note or "").split())
    return text[:NOTE_MAX_CHARS]


def _decode(raw):
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8")
    return raw.decode("utf-8")


def parse_report_file(raw, card_id, run_id):
    """-> (outcome, note) or raise ReportInvalid."""
    if len(raw) > REPORT_FILE_MAX_BYTES:
        raise ReportInvalid("回報檔超過 %d KB" % (REPORT_FILE_MAX_BYTES // 1024))
    try:
        doc = json.loads(_decode(raw))
    except (UnicodeDecodeError, ValueError) as e:
        raise ReportInvalid("回報檔不是有效的 UTF-8 JSON:%s" % e)
    if not isinstance(doc, dict):
        raise ReportInvalid("回報檔必須是 JSON 物件")
    if doc.get("card") != card_id:
        raise ReportInvalid("回報檔的 card 是 %r,應為 %r" % (doc.get("card"), card_id))
    if doc.get("run") != run_id:
        raise ReportInvalid("回報檔的 run 是 %r,應為 %r" % (doc.get("run"), run_id))
    outcome = doc.get("outcome")
    if outcome not in REPORT_OUTCOMES:
        raise ReportInvalid("回報檔的 outcome 必須是 done 或 blocked,收到 %r" % (outcome,))
    note = doc.get("note", "")
    if not isinstance(note, str):
        raise ReportInvalid("回報檔的 note 必須是字串")
    return outcome, one_line(note)


def find_marker(text, run_id):
    """The last marker line for this run in `text` -> (outcome, note), else None."""
    found = None
    for m in MARKER_RE.finditer(text or ""):
        if m.group(2) == run_id:
            found = (m.group(1), one_line(m.group(3)))
    return found


def marker_template(run_id):
    """How the prompt shows the marker: the placeholder keeps an echoed prompt from matching (INV-BD-45)."""
    return "%s <done-or-blocked> %s <one-line note>" % (MARKER_PREFIX, run_id)
