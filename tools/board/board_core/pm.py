"""PM Agent helpers (PRODUCT-DEVELOPMENT §7.3 / tools/board/PM-AGENT.md).

Decision cards: kind=decision, zone=red, note carries 待決策事項.
Auto-dispatch skips kind=decision (see dispatch.DEFAULT_SKIP_KINDS).
"""
from __future__ import annotations

from typing import Iterable, Sequence


PENDING_HEADER = "待決策事項:"


def format_pending_decisions(items: Sequence[str]) -> str:
    """Render a 待決策事項 block (unchecked bullets)."""
    lines = [PENDING_HEADER]
    for raw in items:
        text = (raw or "").strip()
        if not text:
            continue
        if text.startswith("-"):
            lines.append(text)
        else:
            lines.append("- [ ] %s" % text)
    lines.append("狀態: 紅燈阻塞實作派工直至 owner 回覆。")
    return "\n".join(lines)


def ensure_decision_card_fields(task: dict, *, now: str, pending_items: Iterable[str], by: str = "human") -> dict:
    """Force kind=decision, zone=red, append pending list; mutate in place and return task."""
    items = [str(x).strip() for x in pending_items if str(x).strip()]
    task["kind"] = "decision"
    task["zone"] = "red"
    task["doneAt"] = None
    task["updatedAt"] = now
    task["updatedBy"] = by
    if not task.get("startedAt"):
        task["startedAt"] = now
    block = format_pending_decisions(items)
    note = (task.get("note") or "").rstrip()
    if PENDING_HEADER in note:
        # replace trailing pending block if re-recording
        head, _, _ = note.partition(PENDING_HEADER)
        note = head.rstrip()
    task["note"] = (note + "\n\n" + block).strip() if note else block
    log = list(task.get("log") or [])
    if not log or log[-1].get("zone") != "red":
        log.append({"t": now, "zone": "red", "by": by})
        task["log"] = log[-20:]
    task["version"] = int(task.get("version") or 1) + 1
    return task


def new_decision_card(
    id_: str,
    title: str,
    *,
    now: str,
    pending_items: Sequence[str],
    bdd: str = "",
    note_prefix: str = "",
    parent: str = "PRODUCT-DEV-20261023",
    by: str = "human",
) -> dict:
    """Create a new red decision card dict."""
    body = (note_prefix.rstrip() + "\n") if note_prefix else ""
    body += "母工項: %s\nPrimary module: PM/決策\n" % parent
    task = {
        "id": id_,
        "ref": id_,
        "title": title,
        "zone": "red",
        "kind": "decision",
        "createdAt": now,
        "doneAt": None,
        "startedAt": now,
        "by": by,
        "updatedAt": now,
        "updatedBy": by,
        "bdd": bdd or ("BDD-%s：待決策事項關閉前不得派依賴實作卡。" % id_),
        "tdd": "N/A（決策卡；owner 拍板後結案，非 TDD 滅燈對象）。",
        "note": body.strip(),
        "log": [{"t": now, "zone": "red", "by": by}],
        "version": 1,
    }
    return ensure_decision_card_fields(task, now=now, pending_items=pending_items, by=by)
