"""Print card-local excerpt JSON for one or more IDs (PM dispatch prompts)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe  # noqa: E402

ids = sys.argv[1:]
html = (ROOT / "docs" / "PROJECT-BOARD.html").read_text(encoding="utf-8")
data = snapshot_safe.load_snapshot_dict(html)
by = {t.get("id"): t for t in (data.get("tasks") or [])}
out = []
for i in ids:
    t = by.get(i)
    if not t:
        print(f"MISSING {i}", file=sys.stderr)
        continue
    out.append(
        {
            "id": t.get("id"),
            "ref": t.get("ref"),
            "title": t.get("title"),
            "kind": t.get("kind"),
            "zone": t.get("zone"),
            "bdd": t.get("bdd"),
            "tdd": t.get("tdd"),
            "note": t.get("note"),
        }
    )
print(json.dumps(out, ensure_ascii=False, indent=2))
