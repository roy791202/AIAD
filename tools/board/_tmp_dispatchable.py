"""Filter gray/yellow cards that can be dispatched (skip decisions + blocked deps)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe  # noqa: E402

html = (ROOT / "docs" / "PROJECT-BOARD.html").read_text(encoding="utf-8")
data = snapshot_safe.load_snapshot_dict(html)
tasks = data.get("tasks") or data.get("cards") or []
by_id = {t.get("id"): t for t in tasks if t.get("id")}

red_decisions = [
    t
    for t in tasks
    if (t.get("zone") or "").lower() == "red"
    and (t.get("kind") or "") == "decision"
]
red_ids = {t.get("id") for t in red_decisions}
print("OPEN RED DECISIONS:")
for t in red_decisions:
    print(f"  {t.get('id')}: {(t.get('title') or '')[:90]}")

SKIP_KINDS = {"decision", "epic"}
# planning/verification may still be dispatchable if not decision-blocked

blocked_markers = (
    "阻塞",
    "待決策",
    "等決策",
    "等 DEC",
    "blocked by",
    "BLOCKED",
    "決策未決",
    "紅燈阻塞",
)


def mentions_open_dec(text: str) -> list[str]:
    hits = []
    for did in red_ids:
        if did and did in (text or ""):
            hits.append(did)
    return hits


def is_blocked(t: dict) -> tuple[bool, str]:
    kind = (t.get("kind") or "task").lower()
    if kind in SKIP_KINDS:
        return True, f"skip kind={kind}"
    blob = "\n".join(
        [
            str(t.get("note") or ""),
            str(t.get("bdd") or ""),
            str(t.get("tdd") or ""),
            str(t.get("title") or ""),
            str(t.get("ref") or ""),
        ]
    )
    hits = mentions_open_dec(blob)
    if hits:
        return True, f"mentions open decision {hits}"
    for m in blocked_markers:
        if m in blob and ("決策" in blob or "DEC" in blob or "blocked" in blob.lower()):
            # soft: only if also mentions a red decision id or 待決策
            if "待決策" in blob or hits:
                return True, f"marker {m}"
    return False, ""


dispatchable = []
blocked = []
for t in tasks:
    z = (t.get("zone") or "").lower()
    if z not in ("gray", "yellow"):
        continue
    kind = (t.get("kind") or "task").lower()
    blocked_flag, reason = is_blocked(t)
    row = {
        "id": t.get("id"),
        "zone": z,
        "kind": kind,
        "title": t.get("title"),
        "ref": t.get("ref"),
        "bdd": t.get("bdd"),
        "tdd": t.get("tdd"),
        "note": t.get("note") or "",
        "reason": reason,
    }
    if blocked_flag:
        blocked.append(row)
    else:
        dispatchable.append(row)

print(f"\nDISPATCHABLE ({len(dispatchable)}):")
for r in dispatchable:
    print(f"  [{r['zone']}] {r['id']} ({r['kind']}) {(r['title'] or '')[:70]}")

print(f"\nBLOCKED/SKIP ({len(blocked)}):")
for r in blocked[:40]:
    print(f"  [{r['zone']}] {r['id']} — {r['reason'][:80]}")

Path("tools/board/_tmp_dispatchable.json").write_text(
    json.dumps(
        {"dispatchable": dispatchable, "blocked": blocked, "red_decisions": list(red_ids)},
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print("\nwrote tools/board/_tmp_dispatchable.json")
