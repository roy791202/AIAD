# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
html = (ROOT / "docs" / "PROJECT-BOARD.html").read_text(encoding="utf-8")
m = re.search(r'id="board-snapshot"[^>]*>(.*?)</script>', html, re.S)
if not m:
    raise SystemExit("no snapshot")
data = json.loads(m.group(1).strip())
by_zone: dict[str, list] = {}
for c in data.get("cards", []):
    by_zone.setdefault(c.get("zone") or "?", []).append(c)
for z, items in sorted(by_zone.items()):
    print(f"{z}: {len(items)}")

# Also search yellow-like in notes / accepted
yellowish = [
    c
    for c in data["cards"]
    if c.get("zone") == "yellow"
    or "yellow" in str(c.get("zone", "")).lower()
]
print("yellowish", len(yellowish))

# Live board said next card is PD-ARCH-UI-V-01VERIFY — find ARCH-UI-V cards
for c in data["cards"]:
    cid = c.get("id") or ""
    if "ARCH-UI-V" in cid or "VERIFY" in cid:
        print(
            "HIT",
            c.get("zone"),
            cid,
            "|",
            (c.get("title") or "")[:80],
        )
