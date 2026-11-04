# -*- coding: utf-8 -*-
"""Note V-09 regression: sidebar display:none broke main; CSS fixed to visibility."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe

BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
NOTE = (
    f"\n[{NOW}] REGRESSION：is-sidebar-collapsed 對 #sidebar 用 display:none → "
    f"#main 掉進 0 寬欄、畫面只剩 Inspector。已改 visibility:hidden 保 grid 槽位。"
    f" pytest test_pd_arch_ui_verify_01 重跑。"
)


def mutate(data):
    for tid in ("PD-ARCH-UI-V-09", "PRODUCT-ARCH-UI-VERIFY-20261025"):
        for t in data.get("tasks") or []:
            if t.get("id") == tid:
                t["note"] = (t.get("note") or "").rstrip() + NOTE
                t["updatedAt"] = NOW
                t["updatedBy"] = "human"
                t["version"] = int(t.get("version") or 1) + 1
                print("noted", tid)
                break
    data["asOf"] = NOW


def main():
    snapshot_safe.mutate_snapshot_file(BOARD, mutate)
    print("OK")


if __name__ == "__main__":
    main()
