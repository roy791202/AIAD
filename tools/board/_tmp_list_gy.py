"""List gray/yellow/red cards from board snapshot (PM dispatch helper)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe  # noqa: E402

html = (ROOT / "docs" / "PROJECT-BOARD.html").read_text(encoding="utf-8")
data = snapshot_safe.load_snapshot_dict(html)
tasks = data.get("tasks") or data.get("cards") or []
by_zone: dict[str, list] = {"gray": [], "yellow": [], "red": [], "green": [], "other": []}
for t in tasks:
    z = (t.get("zone") or "other").lower()
    if z not in by_zone:
        z = "other"
    by_zone[z].append(t)

for zone in ("gray", "yellow", "red"):
    items = by_zone[zone]
    print(f"=== {zone.upper()} ({len(items)}) ===")
    for t in items:
        kind = t.get("kind") or "task"
        tid = t.get("id") or "?"
        title = (t.get("title") or "")[:80]
        print(f"{tid}\t{kind}\t{title}")
    print()

# dump slim JSON for dispatch
out = []
for zone in ("gray", "yellow"):
    for t in by_zone[zone]:
        out.append(
            {
                "id": t.get("id"),
                "ref": t.get("ref"),
                "title": t.get("title"),
                "kind": t.get("kind") or "task",
                "zone": t.get("zone"),
                "bdd": t.get("bdd"),
                "tdd": t.get("tdd"),
                "note": (t.get("note") or "")[-2000:],
            }
        )
Path("tools/board/_tmp_gy_cards.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"wrote tools/board/_tmp_gy_cards.json ({len(out)} cards)")
