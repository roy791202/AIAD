# -*- coding: utf-8 -*-
"""Final-2026-10-25 缺口：決策紅燈＋未阻塞屬性卡黃燈。"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from board_core import snapshot_safe
from board_core.json_store import FileLock

BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
PARENT = "PRODUCT-ARCH-FINAL-GAP-20261025"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
COLLAB = (
    "協作：實作子代理以本卡 BDD 為開發指標；§7.1 不可自改綠；§7.2 只讀本卡／"
    "reports/dispatch-pd/<ID>.md／允許路徑。\n"
    "看板寫入：禁止整檔覆寫 HTML 殼；禁止 board.py report done（會改綠）。"
    "只可 snapshot_safe 追加本卡 note，zone 維持原燈。"
)
ALLOW_ATTR = (
    "允許: apps/sgenaxis-desktop/ui/app.js、apps/sgenaxis-desktop/ui/index.html、"
    "apps/sgenaxis-desktop/ui/styles.css、tests/test_pd_arch_dag_shell_01.py、"
    "reports/dispatch-pd/PD-ARCH-COMMON-ATTR-01.md。\n"
    "保護: 不新增 ARCH_NODE_KINDS；不改 UI_NODE_TYPES；"
    "workflowStatus／testStatus 仍只在 WorkItem；不改 Module Slot 模型。"
)


def base(id_, kind, zone, title, bdd, tdd, note):
    return {
        "id": id_,
        "ref": id_,
        "kind": kind,
        "zone": zone,
        "title": title,
        "bdd": bdd,
        "tdd": tdd,
        "note": note.rstrip() + "\n" + COLLAB,
        "createdAt": NOW,
        "updatedAt": NOW,
        "updatedBy": "parent-pm",
        "startedAt": NOW if zone in ("yellow", "red") else None,
        "doneAt": None,
        "by": "parent-pm",
        "log": [{"t": NOW, "zone": zone, "by": "parent-pm"}],
        "version": 1,
    }


CARDS = [
    base(
        PARENT,
        "epic",
        "yellow",
        "Final-2026-10-25：補齊節點屬性；類別擴充待決",
        "BDD-ARCH-FINAL-GAP：既有節點補上規格共用欄位、Port 結構與 UI Layer 缺項；"
        "新節點類別與 UI 全目錄在決策紅燈關閉前不派工。",
        "子卡 TDD_PASS 後才滅燈。",
        "母工項: PRODUCT-ARCH-DAG-20261024\n里程碑: Arch-DAG\n"
        "SSOT: docs/Final-2026-10-25/\n"
        "本批已建卡: PD-DEC-ARCH-FINAL-GAP-01（紅）、"
        "PD-ARCH-COMMON-ATTR-01（黃）、"
        "PD-ARCH-EXTRA-KINDS-01（灰，阻塞）、"
        "PD-UI-BHV-CATALOG-01（灰，阻塞）。\n"
        f"[{NOW}] 黃燈開工：PD-ARCH-COMMON-ATTR-01。",
    ),
    base(
        "PD-DEC-ARCH-FINAL-GAP-01",
        "decision",
        "red",
        "決策：Final 缺口裡哪些類別要進畫布",
        "BDD-DEC-ARCH-FINAL-GAP：未勾選前，不得新增節點 kind，不得擴充 UI 元件目錄。",
        "N/A（文件決策；關閉前不派實作）",
        "母工項: PRODUCT-ARCH-FINAL-GAP-20261025\n"
        "待決策事項:\n"
        "- [ ] DEC-1: Module/Feature 要不要變成新畫布節點？"
        " A 維持 Module Slot（建議，已對齊 Layer PDF）。"
        " B 另增 Module 節點。影響 PD-ARCH-EXTRA-KINDS-01。\n"
        "- [ ] DEC-2: workflowStatus／testStatus 要不要加到每一種節點？"
        " A 只留 Work Item（建議）。 B 全部節點。\n"
        "- [ ] DEC-3: UI 工具視窗要不要一次補上 UI-bhv §7 全部元件與專屬屬性？"
        " A 維持現有 9 種。 B 全量登記。影響 PD-UI-BHV-CATALOG-01。\n"
        "- [ ] DEC-4: 是否把 Code File、Test、Build、AI Task 加入 ARCH_NODE_KINDS"
        "（擴充已決 10 類；Module 仍用 Slot）？"
        " A 加入這四類。 B 不加。影響 PD-ARCH-EXTRA-KINDS-01。\n"
        "狀態: 紅燈阻塞 EXTRA-KINDS 與 UI-BHV-CATALOG，直到 owner 回覆。"
        "不阻塞 PD-ARCH-COMMON-ATTR-01。",
    ),
    base(
        "PD-ARCH-COMMON-ATTR-01",
        "task",
        "yellow",
        "ARCH：補齊既有節點的共用屬性、Port 結構、UI Layer 缺項",
        "BDD-PD-ARCH-COMMON-ATTR-01：既有架構節點可讀寫並寫入 XML："
        "createdAt、updatedAt、contentHash、schemaVersion、"
        "dependencies[]（target、dependencyType、required）、bddSpecs[]、tddSpecs[]。"
        "每個 Port 可讀寫 dataType、schemaRef、required、cardinality、constraints、"
        "defaultValue、errorTypeRefs、description。"
        "UI Layer 另有 rootNodeId、assetRefs。"
        "節點可存 width／height；meta.viewports 記住各層 zoom 與捲動。",
        "tests/test_pd_arch_dag_shell_01.py::test_arch_common_attrs_and_port_schema",
        "里程碑: Arch-DAG\n" + ALLOW_ATTR + "\n"
        "AC: 新建節點有 createdAt；編輯後 updatedAt 更新；"
        "XML 往返保留上述欄位；Inspector 可改；"
        "不新增 kind、不改 UI 元件目錄、不把 workflow 狀態加到非 WorkItem。\n"
        "證據: reports/dispatch-pd/PD-ARCH-COMMON-ATTR-01.md 含 READY_FOR_TDD。\n"
        f"[{NOW}] 黃燈開工。",
    ),
    base(
        "PD-ARCH-EXTRA-KINDS-01",
        "task",
        "gray",
        "ARCH：依決策補 Code File／Test／Build／AI Task",
        "BDD-PD-ARCH-EXTRA-KINDS-01：僅在 PD-DEC-ARCH-FINAL-GAP-01 的 DEC-4 選 A 後，"
        "ARCH_NODE_KINDS 增加 CodeFile、Test、Build、AITask，並各有文件所列專屬屬性。",
        "決策關閉後另定。",
        "里程碑: Arch-DAG\n"
        "阻塞: PD-DEC-ARCH-FINAL-GAP-01 DEC-1／DEC-4 未決。禁止黃燈。\n"
        "不做: 在決策前改 ARCH_NODE_KINDS。",
    ),
    base(
        "PD-UI-BHV-CATALOG-01",
        "task",
        "gray",
        "UI：依決策補 UI-bhv §7 元件目錄",
        "BDD-PD-UI-BHV-CATALOG-01：僅在 DEC-3 選 B 後，UI 工具視窗登記 UI-bhv §7 元件種類與專屬屬性。",
        "決策關閉後另定。",
        "里程碑: Arch-DAG\n"
        "阻塞: PD-DEC-ARCH-FINAL-GAP-01 DEC-3 未決。禁止黃燈。\n"
        "不做: 在決策前擴充 UI_NODE_TYPES。",
    ),
]


def mutate(data):
    existing = {t.get("id") for t in data.get("tasks") or []}
    added = []
    for card in CARDS:
        if card["id"] in existing:
            print("skip", card["id"])
            continue
        data.setdefault("tasks", []).append(card)
        added.append(card["id"])
        print("add", card["zone"], card["id"])
    for t in data.get("tasks") or []:
        if t.get("id") == "PRODUCT-ARCH-DAG-20261024":
            line = f"[{NOW}] 後續缺口見 {PARENT}。"
            if line not in (t.get("note") or ""):
                t["note"] = (t.get("note") or "").rstrip() + "\n" + line
                t["updatedAt"] = NOW
                t["updatedBy"] = "parent-pm"
                t["version"] = int(t.get("version") or 1) + 1
            break
    data["asOf"] = NOW
    return added


def main():
    added = snapshot_safe.mutate_snapshot_file(BOARD, mutate, lock_factory=FileLock)
    print("added", added)


if __name__ == "__main__":
    main()
