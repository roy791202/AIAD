"""Classify yellow/gray cards: ready-for-red-tdd vs need-implement vs skip."""
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
tasks = data.get("tasks") or []
red_dec = {
    t["id"]
    for t in tasks
    if (t.get("zone") or "").lower() == "red" and (t.get("kind") or "") == "decision"
}

READY_MARKERS = (
    "READY_FOR_GREEN",
    "READY_FOR_TDD",
    "READY_FOR_AI_IMPLEMENTATION",
    "TDD_PASS",
    "Owner acceptance pending",
    "owner acceptance pending",
    "Proposal delivered",
    "Architecture proposal delivered",
    "Independent RED complete",
    "Read-only audit delivered",
    "final independent gate",
)

SKIP_KIND = {"decision", "epic"}
NOT_READY = ("NOT_READY_FOR_IMPLEMENTATION", "本次不啟動lane", "PLANNING_ONLY")

ready_for_tdd_red = []
need_impl = []
skip = []

for t in tasks:
    z = (t.get("zone") or "").lower()
    if z not in ("gray", "yellow"):
        continue
    kind = (t.get("kind") or "task").lower()
    note = t.get("note") or ""
    blob = "\n".join([note, t.get("bdd") or "", t.get("tdd") or "", t.get("title") or ""])
    row = {
        "id": t.get("id"),
        "zone": z,
        "kind": kind,
        "title": t.get("title"),
        "bdd": t.get("bdd"),
        "tdd": t.get("tdd"),
        "note": note,
        "ref": t.get("ref"),
    }
    if kind in SKIP_KIND:
        skip.append({**row, "why": f"kind={kind}"})
        continue
    if any(d in blob for d in red_dec):
        skip.append({**row, "why": "open red decision dependency"})
        continue
    if any(m in note for m in READY_MARKERS):
        ready_for_tdd_red.append(row)
        continue
    # planning cards that already delivered proposals → red TDD/owner
    if kind == "planning" and ("delivered" in note.lower() or "Proposal" in note):
        ready_for_tdd_red.append(row)
        continue
    if any(m in note for m in NOT_READY) and z == "gray":
        skip.append({**row, "why": "gray PLANNING_ONLY / not start lane"})
        continue
    need_impl.append(row)

out = {
    "ready_for_tdd_red": ready_for_tdd_red,
    "need_impl": need_impl,
    "skip": skip,
}
Path("tools/board/_tmp_ready_batch.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"READY_FOR_TDD_RED ({len(ready_for_tdd_red)}):")
for r in ready_for_tdd_red:
    print(f"  [{r['zone']}] {r['id']} — {(r['title'] or '')[:70]}")
print(f"\nNEED_IMPL ({len(need_impl)}):")
for r in need_impl:
    print(f"  [{r['zone']}] {r['id']} — {(r['title'] or '')[:70]}")
print(f"\nSKIP ({len(skip)})")
