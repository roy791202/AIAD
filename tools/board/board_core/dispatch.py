"""Dispatch rules (BOARD-DISPATCH-01; pure functions, no file / process / clock access).

  INV-BD-1  priority red > yellow > gray; green is never selected
  INV-BD-2  within a zone: oldest updatedAt first (parsed ISO; naive = UTC; unparseable last), then id
  INV-BD-3  excluded: running / skipped (needs-human) ids, and non-work kinds
  INV-BD-5  dispatch moves gray -> yellow; red and yellow stay
  INV-BD-6  report done -> green, blocked -> red
  INV-BD-11 stop after the run that reaches maxCards
  INV-BD-23 maxCards "unlimited" (stored as None): no limit; stops only on user stop, no candidates or halt
"""
from datetime import timezone

from .domain import DomainError, _parse_iso

PRIORITY = ("red", "yellow", "gray")
# kind=decision：紅燈決策卡（PM-AGENT.md §2）；自動派工跳過，僅人工／PM 處理
DEFAULT_SKIP_KINDS = ("note", "epic", "milestone", "release", "decision")
REPORT_OUTCOMES = ("done", "blocked")
NEEDS_HUMAN_OUTCOMES = ("no-report", "timeout", "terminated", "server-shutdown", "orphaned")
HALT_OUTCOMES = ("auth-error", "quota-error", "launch-error")
STOP_MODES = ("after-current", "now")
UNLIMITED = "unlimited"
_LAST = float("inf")


def _order_key(task):
    d = _parse_iso(task.get("updatedAt"))
    if d is None:
        return (_LAST, task.get("id", ""))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return (d.timestamp(), task.get("id", ""))


def candidates(tasks, exclude_ids=(), skip_kinds=DEFAULT_SKIP_KINDS):
    """All dispatchable tasks in dispatch order."""
    excluded = set(exclude_ids or ())
    skip = set(skip_kinds or ())
    out = []
    for zone in PRIORITY:
        zs = [t for t in tasks
              if t.get("zone") == zone and t.get("id") not in excluded and (t.get("kind") or "task") not in skip]
        out.extend(sorted(zs, key=_order_key))
    return out


def select_next(tasks, exclude_ids=(), skip_kinds=DEFAULT_SKIP_KINDS):
    c = candidates(tasks, exclude_ids, skip_kinds)
    return c[0] if c else None


def dispatch_zone(zone):
    if zone not in PRIORITY:
        raise DomainError("zone %r is not dispatchable" % (zone,))
    return "yellow" if zone == "gray" else zone


def report_zone(outcome):
    if outcome == "done":
        return "green"
    if outcome == "blocked":
        return "red"
    raise DomainError("report outcome must be done or blocked, got %r" % (outcome,))


def append_note(note, line):
    note = (note or "").rstrip()
    return note + "\n" + line if note else line


def report_line(outcome, note, now):
    text = (note or "").strip()
    return "[派工回報 %s %s] %s" % (now, outcome, text) if text else "[派工回報 %s %s]" % (now, outcome)


def needs_human_line(reason, log_dir, now):
    return "[派工 needs-human %s] %s; log: %s" % (now, reason, log_dir)


def after_run(dispatched, max_cards, stop_requested):
    """What to do after a run ends: 'user' (stop requested), 'limit' (maxCards reached) or 'continue'.

    max_cards None = unlimited (INV-BD-23)."""
    if stop_requested:
        return "user"
    if max_cards is not None and dispatched >= max_cards:
        return "limit"
    return "continue"


def validate_max_cards(value, limit):
    """Integer 1..limit, or the string "unlimited" -> None. A missing / null value is an error, never unlimited."""
    if value == UNLIMITED:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= limit:
        raise DomainError('maxCards must be an integer 1..%d or "%s", got %r' % (limit, UNLIMITED, value))
    return value


def new_lane(lane_id, agent, max_cards):
    """A fresh idle agent lane (INV-BD-25); maxCards None = unlimited."""
    return {"id": lane_id, "agent": agent, "maxCards": max_cards, "state": "idle", "stopReason": None,
            "error": None, "session": None, "current": None, "lastRun": None}
