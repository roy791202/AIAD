# -*- coding: utf-8 -*-
"""Owner approves all PD-DEC-* red decision cards."""
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

# Owner decisions (user: 紅燈批准 = approve all pending)
APPROVALS = {
    "PD-DEC-M3-CLOSE-01": (
        "已決：核准繼續 M3 閉環 7 卡（EXEC-CANCEL／SINGLE／FLOW-EVID-GATE／UI-RUN／SMOKE／"
        "BUILD-RESULT／LISTEN-RECON）；追認已完成實作與滅燈。"
    ),
    "PD-DEC-V01-GATE-01": (
        "已決：v0.1.0 候選允許 Build Result=PARTIAL；elevated VERIFY-INSTALL 與 Authenticode "
        "簽章非硬閘（維持 NOT RUN／另案）；正式商店上架另議。"
    ),
    "PD-DEC-M4-SCOPE-01": (
        "已決：M3／v0.1.0 候選收尾前不開 M4；macOS／Linux／SSH／DCC 另開 epic 再派，不掛本批黃燈。"
    ),
    "PD-DEC-EPIC-DONE-01": (
        "已決：Epic 綠須 (1) 本 epic 下 kind=task 全綠 (2) 本批 PD-DEC-* 決策結案 "
        "(3) 至少一份 Build Result 存在（允許 PARTIAL）。使用者旅程可演示為加分非唯一條件。"
    ),
}


def mutate(data):
    closed = []
    for t in data.get("tasks") or []:
        tid = t.get("id")
        if tid not in APPROVALS:
            continue
        if t.get("zone") == "green" and "已決：" in (t.get("note") or ""):
            print("already", tid)
            continue
        decision = APPROVALS[tid]
        # mark checkboxes done in pending block
        note = t.get("note") or ""
        note = note.replace("- [ ]", "- [x]")
        note = note.rstrip() + (
            f"\n[{NOW}] owner 紅燈批准。{decision}\n"
            f"狀態: 決策關閉；zone→green（決策結案，非產品發布）。"
        )
        t["note"] = note
        t["zone"] = "green"
        t["doneAt"] = NOW
        t["updatedAt"] = NOW
        t["updatedBy"] = "human"
        t["tdd"] = "N/A（決策卡；owner 批准結案）。"
        log = list(t.get("log") or [])
        log.append({"t": NOW, "zone": "green", "by": "human"})
        t["log"] = log[-20:]
        t["version"] = int(t.get("version") or 1) + 1
        closed.append(tid)
        print("approve", tid)

    for t in data.get("tasks") or []:
        if t.get("id") != "PRODUCT-DEV-20261023":
            continue
        t["note"] = (t.get("note") or "").rstrip() + (
            f"\n[{NOW}] owner 紅燈批准：PD-DEC-M3-CLOSE／V01-GATE／M4-SCOPE／EPIC-DONE 全結案（綠）。"
            "M3 閉環追認；v0.1.0 允許 PARTIAL；M4 另案；Epic 綠條件見 PD-DEC-EPIC-DONE-01。"
        )
        t["updatedAt"] = NOW
        t["updatedBy"] = "human"
        t["version"] = int(t.get("version") or 1) + 1
        break

    data["asOf"] = NOW
    return closed


def main():
    closed = snapshot_safe.mutate_snapshot_file(BOARD, mutate)
    text = BOARD.read_text(encoding="utf-8")
    assert text.lstrip().lower().startswith("<!doctype")
    m = re.search(
        r'<script[^>]*id=["\']board-snapshot["\'][^>]*>(.*?)</script>',
        text,
        re.S,
    )
    snap = json.loads(m.group(1))
    for tid in APPROVALS:
        t = next(x for x in snap["tasks"] if x["id"] == tid)
        print(tid, t["zone"], "已決" in (t.get("note") or ""))
        if t["zone"] != "green":
            raise SystemExit(tid)
    reds = [t["id"] for t in snap["tasks"] if t.get("zone") == "red"]
    print("remaining red:", reds)
    print("closed", closed)
    print("OK")


if __name__ == "__main__":
    main()
