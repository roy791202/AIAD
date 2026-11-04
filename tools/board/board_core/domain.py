"""Task rules (pure functions; no file, HTTP, OS or clock access).

Invariants (spec-BOARD-LOCAL-01 §3):
  INV-BL-1  zone in {gray, yellow, red, green}
  INV-BL-2  doneAt != null  <=>  zone == green
  INV-BL-3  startedAt written on first entry to yellow, never cleared or overwritten
  INV-BL-4  every zone change appends {t, zone, by} to log; keep the last 20
  INV-BL-6  by / updatedBy in {user, agent}
  INV-BL-10 fixed field set + version; id chars limited to [A-Za-z0-9_\\-.~:@+]

Times are ISO-8601 strings supplied by the caller. `version` is owned by the store.
"""
import re
from datetime import datetime

ZONES = ("gray", "yellow", "red", "green", "orange")
ACTORS = ("user", "agent")
ID_RE = re.compile(r"^[A-Za-z0-9_\-.~:@+]+$")
MAX_LOG = 20
MAX_OWNER_ACTIONS = 20
MAX_OWNER_ACTION_TEXT = 1000

FIELDS = ("id", "ref", "title", "zone", "kind", "bdd", "tdd", "note", "decision", "ownerActions",
          "createdAt", "doneAt", "startedAt", "by", "updatedAt", "updatedBy",
          "log", "version")
EDITABLE = ("title", "ref", "kind", "bdd", "tdd", "note", "decision")
MAX_DECISION = 200


class DomainError(ValueError):
    """A board invariant was violated."""


def _require_actor(by):
    if by not in ACTORS:
        raise DomainError("by must be user or agent, got %r" % (by,))


def _require_zone(zone):
    if zone not in ZONES:
        raise DomainError("illegal zone %r (allowed: %s)" % (zone, ", ".join(ZONES)))


def _require_id(tid):
    if not isinstance(tid, str) or not ID_RE.match(tid):
        raise DomainError("illegal id %r (allowed chars [A-Za-z0-9_-.~:@+])" % (tid,))


def _text(fields, key, default=""):
    v = fields.get(key)
    if v is None:
        return default
    if not isinstance(v, str):
        raise DomainError("%s must be a string" % key)
    return v.strip()


def normalize_decision(value, zone):
    """Return a trimmed optional decision; orange requires 1..200 characters."""
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise DomainError("decision must be a string")
    decision = value.strip()
    if len(decision) > MAX_DECISION:
        raise DomainError("decision must be at most %d characters" % MAX_DECISION)
    if zone == "orange" and not decision:
        raise DomainError("decision is required when zone == orange")
    return decision


def _parse_iso(s):
    if not isinstance(s, str) or not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def trim_log(log):
    return list(log or [])[-MAX_LOG:]


def _resolve_times(fields, zone, now):
    """createdAt optional (blank = now); doneAt only accepted for green, blank = now, not before createdAt."""
    created_at = fields.get("createdAt") or now
    raw_done = fields.get("doneAt")
    if zone != "green":
        if raw_done:
            raise DomainError("doneAt only allowed when zone == green (zone=%r)" % (zone,))
        return created_at, None
    done_at = raw_done or now
    c, d = _parse_iso(created_at), _parse_iso(done_at)
    if c is not None and d is not None and d < c:
        raise DomainError("doneAt %r is earlier than createdAt %r" % (done_at, created_at))
    return created_at, done_at


def new_task(fields, by, now):
    """Build a new task (version 1). Unknown payload keys are ignored; actor comes from `by`."""
    _require_actor(by)
    tid = fields.get("id")
    _require_id(tid)
    zone = fields.get("zone") or "gray"
    _require_zone(zone)
    created_at, done_at = _resolve_times(fields, zone, now)
    log = [{"t": created_at, "zone": "gray" if zone == "green" else zone, "by": by}]
    if zone == "green":
        log.append({"t": done_at, "zone": "green", "by": by})
    task = {
        "id": tid,
        "ref": _text(fields, "ref") or tid,
        "title": _text(fields, "title"),
        "zone": zone,
        "kind": _text(fields, "kind") or "task",
        "bdd": _text(fields, "bdd"),
        "tdd": _text(fields, "tdd"),
        "note": _text(fields, "note"),
        "decision": normalize_decision(fields.get("decision"), zone),
        "ownerActions": [],
        "createdAt": created_at,
        "doneAt": done_at,
        "startedAt": now if zone == "yellow" else None,
        "by": by,
        "updatedAt": now,
        "updatedBy": by,
        "log": log,
        "version": 1,
    }
    return validate(task)


def apply_zone(task, new_zone, by, now):
    """Change zone; returns a new dict and leaves `version` to the store."""
    _require_actor(by)
    _require_zone(new_zone)
    t = dict(task)
    t["log"] = list(task.get("log") or [])
    if new_zone == task.get("zone"):
        return validate(t)
    t["zone"] = new_zone
    t["updatedAt"] = now
    t["updatedBy"] = by
    t["doneAt"] = now if new_zone == "green" else None
    if new_zone == "yellow" and not t.get("startedAt"):
        t["startedAt"] = now
    t["log"] = trim_log(t["log"] + [{"t": now, "zone": new_zone, "by": by}])
    return validate(t)


def apply_edit(task, patch, by, now):
    """Edit free-text fields only (zone goes through apply_zone)."""
    _require_actor(by)
    t = dict(task)
    t["log"] = list(task.get("log") or [])
    for k in patch:
        if k not in EDITABLE:
            raise DomainError("field %r is not editable (editable: %s)" % (k, ", ".join(EDITABLE)))
        t[k] = _text(patch, k)
    t["updatedAt"] = now
    t["updatedBy"] = by
    return validate(t)


def apply_owner_action(task, action, text, by, now):
    """Apply an explicit human Owner action; this operation cannot be attributed to an agent."""
    if by != "user":
        raise DomainError("owner action must be performed by user")
    validate(task)
    if action not in ("approve", "instruct"):
        raise DomainError("action must be approve or instruct")
    if not isinstance(text, str):
        raise DomainError("text must be a string")
    message = text.strip()
    if not message or len(message) > MAX_OWNER_ACTION_TEXT:
        raise DomainError("text must be 1..%d characters after trimming" % MAX_OWNER_ACTION_TEXT)
    if action == "approve" and (task.get("zone") != "orange" or not task.get("decision", "").strip()):
        raise DomainError("approve requires an orange task with a decision")

    result = dict(task)
    result["log"] = list(task.get("log") or [])
    result["ownerActions"] = list(task.get("ownerActions") or [])
    result["ownerActions"].append({
        "action": action,
        "text": message,
        "decision": task.get("decision", ""),
        "at": now,
        "by": "user",
    })
    result["ownerActions"] = result["ownerActions"][-MAX_OWNER_ACTIONS:]
    if action == "approve":
        result["zone"] = "gray"
        result["doneAt"] = None
        if task.get("zone") != "gray":
            result["log"] = trim_log(result["log"] + [{"t": now, "zone": "gray", "by": "user"}])
    result["updatedAt"] = now
    result["updatedBy"] = "user"
    return validate(result)


def validate(task):
    """Raise DomainError when a stored task breaks an invariant; return the task otherwise."""
    _require_id(task.get("id"))
    _require_zone(task.get("zone"))
    decision = normalize_decision(task.get("decision", ""), task.get("zone"))
    if task.get("decision", "") != decision:
        raise DomainError("decision must be trimmed")
    _require_actor(task.get("by"))
    _require_actor(task.get("updatedBy"))
    if (task.get("zone") == "green") != (task.get("doneAt") is not None):
        raise DomainError("INV-BL-2: doneAt must be set iff zone == green (zone=%r, doneAt=%r)"
                          % (task.get("zone"), task.get("doneAt")))
    if len(task.get("log") or []) > MAX_LOG:
        raise DomainError("INV-BL-4: log longer than %d" % MAX_LOG)
    owner_actions = task.get("ownerActions", [])
    if not isinstance(owner_actions, list) or len(owner_actions) > MAX_OWNER_ACTIONS:
        raise DomainError("ownerActions must be a list of at most %d entries" % MAX_OWNER_ACTIONS)
    return task
