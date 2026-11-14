# -*- coding: utf-8 -*-
"""建卡：架構／Diagram 近期 UI 變更逐項 VERIFY（灰燈；驗後由母對話改燈）。"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe

BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
PARENT = "PRODUCT-ARCH-UI-VERIFY-20261025"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
COLLAB = (
    "協作：本批為 VERIFY（已實作行為逐卡核對）；母對話跑靜態／pytest／portable 證據。"
    "§7.1 僅 TDD_PASS／母對話可改綠；§7.2 只讀本卡。"
    "看板寫入：只改 #board-snapshot（snapshot_safe）。"
)


def task(id_, title, bdd, note):
    return {
        "id": id_,
        "ref": id_,
        "title": title,
        "zone": "yellow",
        "kind": "task",
        "createdAt": NOW,
        "doneAt": None,
        "startedAt": NOW,
        "by": "human",
        "updatedAt": NOW,
        "updatedBy": "human",
        "bdd": bdd,
        "tdd": "tests/test_pd_arch_ui_verify_01.py（靜態 AC）；失敗不改綠。",
        "note": f"母工項: {PARENT}\n里程碑: ArchUI/Verify\n{note.rstrip()}\n{COLLAB}",
        "log": [
            {"t": NOW, "zone": "gray", "by": "human"},
            {"t": NOW, "zone": "yellow", "by": "human"},
        ],
        "version": 1,
    }


EPIC = {
    "id": PARENT,
    "ref": PARENT,
    "title": "VERIFY：架構／Diagram 近期 UI（Slot／Tabs／Shift／Toolbar／Sidebar）",
    "zone": "yellow",
    "kind": "epic",
    "createdAt": NOW,
    "doneAt": None,
    "startedAt": NOW,
    "by": "human",
    "updatedAt": NOW,
    "updatedBy": "human",
    "bdd": (
        "BDD-PRODUCT-ARCH-UI-VERIFY：owner 要求把近期架構圖 UI 變更開成工項逐個驗證；"
        "每卡須有可觀測 AC＋靜態／pytest 證據；未過不得綠。"
    ),
    "tdd": "子卡 test_pd_arch_ui_verify_01 全過後 epic 可綠。",
    "note": (
        "Primary module: UI\n"
        "承接: portable 2026-10-25 Diagram 側欄刪除後批次核對。\n"
        f"[{NOW}] 建 VERIFY 子卡並黃燈開工核對。\n{COLLAB}"
    ),
    "log": [
        {"t": NOW, "zone": "gray", "by": "human"},
        {"t": NOW, "zone": "yellow", "by": "human"},
    ],
    "version": 1,
}

TASKS = [
    task(
        "PD-ARCH-UI-V-01",
        "VERIFY：Module Slot 拖放高光／放大",
        "BDD-PD-ARCH-UI-V-01：拖入 Module Slot 時目標標 is-drop-target；CSS 有高光＋scale；放開後清除。",
        "允許範圍: apps/sgenaxis-desktop/ui、tests\n"
        "AC: app.js 對 .arch-module-slot 加 is-drop-target；styles 有 scale/box-shadow。",
    ),
    task(
        "PD-ARCH-UI-V-02",
        "VERIFY：頂部分頁 icon＋文字標籤",
        "BDD-PD-ARCH-UI-V-02：工具列分頁 Diagram／Tasks／Git／Setting 同時有 side-tab-icon 與 side-tab-label。",
        "允許範圍: ui/index.html、ui/styles.css、tests\nAC: #side-rail 四主分頁皆含 label＋svg。",
    ),
    task(
        "PD-ARCH-UI-V-03",
        "VERIFY：Shift＋扭開＝遞迴展開／收合",
        "BDD-PD-ARCH-UI-V-03：扭開 click 傳 shiftKey→setArchTreeOpenState(…, deep)；deep 套用子 Layer／Module。",
        "允許範圍: ui/app.js、tests\nAC: setArchTreeOpenState 第三參 deep；twist title 含 Shift。",
    ),
    task(
        "PD-ARCH-UI-V-04",
        "VERIFY：Layer packs 由子推導＋清除；連線可刪",
        "BDD-PD-ARCH-UI-V-04：packsKind 唯讀由子物件；#arch-clear-layer-packs 卸下成員；選取連線可 Delete／清除。",
        "允許範圍: ui、tests\nAC: select#archNodePacksKind disabled；clearArchLayerPacks；deleteArchSelectedEdge。",
    ),
    task(
        "PD-ARCH-UI-V-05",
        "VERIFY：樹＋畫布共用 Panel 工具列（含刪除）",
        "BDD-PD-ARCH-UI-V-05：#arch-panel-chrome 共用工具列含重新整理／編輯／XML／刪除／＋節點；樹與畫布共用。",
        "允許範圍: ui/index.html、tests\nAC: arch-panel-chrome＋arch-delete-node 在 panel-arch。",
    ),
    task(
        "PD-ARCH-UI-V-06",
        "VERIFY：縮放／排列／Grid 僅在節點視窗工具列",
        "BDD-PD-ARCH-UI-V-06：zoom／fit／arrange／Grid 在 .arch-canvas-toolbar，不在共用 panel toolbar。",
        "允許範圍: ui/index.html、tests\nAC: arch-zoom-in／arch-arrange-*／archGridSize 位於 arch-workspace。",
    ),
    task(
        "PD-ARCH-UI-V-07",
        "VERIFY：畫布關鍵字篩選獨立於樹",
        "BDD-PD-ARCH-UI-V-07：archCanvasKeyword 與 archTreeKeyword 分變數；#arch-canvas-filter-q 與 #arch-tree-filter-q 各一。",
        "允許範圍: ui、tests\nAC: 兩 input id 並存；JS 兩變數。",
    ),
    task(
        "PD-ARCH-UI-V-08",
        "VERIFY：icon button 尺寸 token＝24px",
        "BDD-PD-ARCH-UI-V-08：--icon-btn-h: 24px；頂部分頁／arch tool-btn 使用該 token。",
        "允許範圍: ui/styles.css、tests\nAC: CSS 變數與引用存在。",
    ),
    task(
        "PD-ARCH-UI-V-09",
        "VERIFY：Diagram 無左側空抽屜",
        "BDD-PD-ARCH-UI-V-09：無 #side-panel-diagram；arch／diagram 時 drawerless→is-sidebar-collapsed；樹在 #panel-arch。",
        "允許範圍: ui、tests\nAC: HTML 無 side-panel-diagram；syncSideTabs drawerless；body.is-sidebar-collapsed CSS。",
    ),
]


def mutate(data):
    existing = {t.get("id") for t in (data.get("tasks") or [])}
    added = []
    for c in [EPIC] + TASKS:
        if c["id"] in existing:
            print("skip", c["id"])
            continue
        data["tasks"].append(c)
        added.append(c["id"])
        print("add", c["id"], c.get("zone"))
    for t in data.get("tasks") or []:
        if t.get("id") == "PRODUCT-ARCH-DAG-20261024":
            t["note"] = (t.get("note") or "").rstrip() + (
                f"\n[{NOW}] 近期 UI VERIFY 批：{PARENT}（黃燈逐卡核對）。"
            )
            t["updatedAt"] = NOW
            t["updatedBy"] = "human"
            t["version"] = int(t.get("version") or 1) + 1
            break
    data["asOf"] = NOW
    print("added", len(added))
    return added


def main():
    snapshot_safe.mutate_snapshot_file(BOARD, mutate)
    assert BOARD.read_text(encoding="utf-8").lstrip().lower().startswith("<!doctype")
    print("OK — VERIFY cards yellow")


if __name__ == "__main__":
    main()
