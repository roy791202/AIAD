# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe

BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
EPIC = "PRODUCT-DEV-20261023"


def mutate(data):
    tasks = data.get("tasks") or []
    bad = [t["id"] for t in tasks if t.get("kind") == "task" and t.get("zone") != "green"]
    if bad:
        raise RuntimeError("tasks not all green: %s" % bad)
    dec_open = [
        t["id"]
        for t in tasks
        if str(t.get("id", "")).startswith("PD-DEC-") and t.get("zone") != "green"
    ]
    if dec_open:
        raise RuntimeError("decisions open: %s" % dec_open)
    if not (data.get("releases") or []):
        raise RuntimeError("no releases / build result hang")

    for t in tasks:
        if t.get("id") != EPIC:
            continue
        if t.get("zone") == "green":
            return {"status": "already"}
        t["zone"] = "green"
        t["doneAt"] = NOW
        t["updatedAt"] = NOW
        t["updatedBy"] = "human"
        t["version"] = int(t.get("version") or 1) + 1
        t["tdd"] = "N/A（epic；依 PD-DEC-EPIC-DONE-01 owner 批准條件結案）。"
        log = list(t.get("log") or [])
        log.append({"t": NOW, "zone": "green", "by": "human"})
        t["log"] = log[-20:]
        t["note"] = (t.get("note") or "").rstrip() + (
            f"\n[{NOW}] Epic 滅燈：owner 紅燈批准後滿足 PD-DEC-EPIC-DONE-01"
            "（task 全綠＋DEC 結案＋releases/Build Result 存在）。首版切片完成≠商店發布。"
        )
        data["overall"] = "PASS"
        data["asOf"] = NOW
        print("epic green")
        return {"status": "greened"}
    raise KeyError(EPIC)


def main():
    snapshot_safe.mutate_snapshot_file(BOARD, mutate)
    text = BOARD.read_text(encoding="utf-8")
    assert text.lstrip().lower().startswith("<!doctype")
    snap = json.loads(
        re.search(r'<script[^>]*id=["\']board-snapshot["\'][^>]*>(.*?)</script>', text, re.S).group(1)
    )
    epic = next(t for t in snap["tasks"] if t["id"] == EPIC)
    print(epic["zone"], epic.get("doneAt"))
    assert epic["zone"] == "green"
    print("OK")


if __name__ == "__main__":
    main()
