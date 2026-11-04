# -*- coding: utf-8 -*-
"""M2 deepen batch: E2E loop / MCP live smoke / live matrix / git-board sync / M2 val."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe
from board_core.pm import new_decision_card

BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
PARENT = "PRODUCT-M2-DEEPEN-20261024"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
COLLAB = (
    "協作：實作子代理以本卡 BDD 為開發指標；既定 TDD／assertions／fixtures／expected values／skip 不得自行修改。"
    "測試定義、RED/GREEN 驗證與回報交專屬 TDD 子代理。契約矛盾 SPEC_CONFLICT；新 seam REPLAN_REQUIRED。"
    "§7.1 不可自改綠；§7.2 只讀本卡 prompt／報告／允許路徑（禁止讀整板）。"
    "看板寫入：禁止整檔覆寫 HTML 殼；只改 #board-snapshot（優先 snapshot_safe）。"
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
        "tdd": "PENDING_TDD_PACKET：專屬 TDD 子代理定義／核對後回報有效 RED；未建立自動化不宣稱 GREEN。",
        "note": (
            f"母工項: {PARENT}\n里程碑: M2\n{note.rstrip()}\n{COLLAB}\n"
            f"[{NOW}] Cursor subagent 派工開始（母對話授權；§7.1／§7.2）。"
        ),
        "log": [
            {"t": NOW, "zone": "gray", "by": "human"},
            {"t": NOW, "zone": "yellow", "by": "human"},
        ],
        "version": 1,
    }


EPIC = {
    "id": PARENT,
    "ref": PARENT,
    "title": "SGenAxis M2 加深：E2E 閉環／MCP Live 冒煙／矩陣／Git↔看板／驗收",
    "zone": "yellow",
    "kind": "epic",
    "createdAt": NOW,
    "doneAt": None,
    "startedAt": NOW,
    "by": "human",
    "updatedAt": NOW,
    "updatedBy": "human",
    "bdd": (
        "BDD-PD-M2-DEEPEN-EPIC：在已綠 M2 切片上補齊閉環證據；無目標維持 NOT RUN；"
        "禁止把 DryRun 偽造成全 Live PASS。"
    ),
    "tdd": "N/A（epic；子卡 TDD_PASS 後母對話滅燈）。",
    "note": (
        "Primary module: EXEC/HOST/UI/GIT\n"
        "承接: PRODUCT-DEV M2 切片已綠；里程碑 M2 仍 PARTIAL（Live 依環境）。\n"
        "範圍: E2E 閉環測、MCP Live 冒煙、Live 矩陣、Git↔看板同步斷言、M2 驗收報告。\n"
        "不做: DCC／SSH／買證／並行雙 Provider Run（§6.3 後續）。\n"
        f"[{NOW}] owner「把M2工項排入並派工」；PD-DEC-M2-DEEPEN-GO-01 已決。"
    ),
    "log": [
        {"t": NOW, "zone": "gray", "by": "human"},
        {"t": NOW, "zone": "yellow", "by": "human"},
    ],
    "version": 1,
}

TASKS = [
    task(
        "PD-M2-E2E-LOOP-01",
        "EXEC/HOST：M2 閉環整合測（看板＋Git＋Provider DryRun 事件鏈）",
        "BDD-PD-M2-E2E-LOOP-01：可重跑整合測串起 load_board（或等價）＋git summarize＋"
        "Cli｜Mcp DryRun start_run→chunk／exit 事件；缺依賴→明確 skip／NOT RUN；禁止暗示已全 Live PASS。",
        "Primary module: EXEC/HOST\n依賴: PD-BOARD-LIVE-01、PD-GIT-01、PD-EXEC-CLI、PD-EXEC-MCP\n"
        "交付／AC: cargo／pytest 整合測＋報告。\n"
        "允許範圍: apps/sgenaxis-desktop/crates、tests、scripts、reports。\n"
        "不做: 強制真 Live；不開 DCC。",
    ),
    task(
        "PD-MCP-LIVE-SMOKE-01",
        "EXEC：地端 MCP Live 冒煙（無目標→NOT RUN）",
        "BDD-PD-MCP-LIVE-SMOKE-01：核准下對明示本機 MCP 做一次 Live 連線／工具呼叫或串流對帳，"
        "或明確 NOT RUN；秘密不進投影；不得把 DryRun 寫成 Live PASS。",
        "Primary module: EXEC\n依賴: PD-MCP-LIVE-01、PD-LIVE-TARGET-01、PD-DEC-VERIFY-GO-01（軟）\n"
        "交付／AC: 冒煙測／腳本＋報告。\n允許範圍: crates sgenaxis-exec／adapters、tests、scripts、reports。\n"
        "不做: 雲端任意閘道；不強制購買服務。",
    ),
    task(
        "PD-M2-LIVE-MATRIX-01",
        "DOC/EXEC：Live 目標×狀態矩陣（PASS｜NOT RUN｜FAIL）",
        "BDD-PD-M2-LIVE-MATRIX-01：報告列出 CLI／MCP 探測與冒煙結果狀態；缺跑＝NOT RUN；"
        "可被 M2 驗收引用；禁止把未跑升 PASS。",
        "Primary module: DOC/EXEC\n依賴: PD-LIVE-TARGET-01、PD-LIVE-CLI-SMOKE-01、PD-MCP-LIVE-SMOKE-01（軟）\n"
        "交付／AC: reports 矩陣＋測試斷言。\n允許範圍: docs、reports、tools 測試。\n不做: 改 Provider 契約。",
    ),
    task(
        "PD-GIT-BOARD-SYNC-01",
        "GIT/HOST：Git 工作台摘要與看板讀取一致性斷言",
        "BDD-PD-GIT-BOARD-SYNC-01：同一測試夾具下 git status／log 摘要與 board snapshot 讀取互不污染；"
        "唯讀路徑無寫入；失敗分類清楚。",
        "Primary module: GIT/HOST\n依賴: PD-GIT-01、PD-BOARD-LIVE-01、PD-GIT-UI-01\n"
        "交付／AC: 整合／單元測＋報告。\n允許範圍: crates adapters／host、tests、reports。\n"
        "不做: force push；不開寫入新語意。",
    ),
    task(
        "PD-M2-VAL-01",
        "PM：M2 里程碑再驗收報告（誠實 PARTIAL）",
        "BDD-PD-M2-VAL-01：對照 PRODUCT-DEVELOPMENT §8 M2 目標與本批證據；"
        "列出剩餘 NOT RUN；不得宣稱 M2 全 Live 閉環 PASS。",
        "Primary module: PM/DOC\n依賴: PD-M2-E2E-LOOP-01、PD-M2-LIVE-MATRIX-01\n"
        "交付／AC: reports/m2-validation-*.md＋測試。\n允許範圍: docs、reports、tools 測試。\n"
        "不做: 改寫 §8 里程碑定義。",
    ),
]


def mutate(data):
    existing = {t["id"] for t in data.get("tasks") or []}
    added = []

    dec = new_decision_card(
        "PD-DEC-M2-DEEPEN-GO-01",
        "決策：核准 M2 加深批開工",
        now=NOW,
        parent=PARENT,
        pending_items=[
            "DEC-1: 核准 E2E-LOOP／MCP-LIVE-SMOKE／LIVE-MATRIX／GIT-BOARD-SYNC／M2-VAL？",
            "DEC-2: 無 MCP／CLI 目標時冒煙維持 NOT RUN（不偽造 Live PASS）？",
            "DEC-3: 本批不開 DCC／SSH／雙 Provider 並行 Run？",
        ],
        bdd="BDD-PD-DEC-M2-DEEPEN-GO-01：核准後才可派本批實作卡。",
    )
    dec["zone"] = "green"
    dec["doneAt"] = NOW
    dec["note"] = (dec.get("note") or "").replace("- [ ]", "- [x]") + (
        f"\n[{NOW}] owner「把M2工項排入並派工」→ 已決：核准五卡；無目標→NOT RUN；"
        f"不開 DCC／SSH／雙 Provider 並行；禁 DryRun→Live PASS 偽造。"
    )
    dec["log"].append({"t": NOW, "zone": "green", "by": "human"})
    dec["tdd"] = "N/A（決策卡；owner 派工即核准）。"
    dec["version"] = 2

    for c in [EPIC, dec] + TASKS:
        if c["id"] in existing:
            print("skip", c["id"])
            continue
        data["tasks"].append(c)
        added.append(c["id"])
        print("add", c["id"])

    data["asOf"] = NOW
    data["overall"] = "PARTIAL"
    print("added", len(added))
    return [x for x in added if x.startswith("PD-") and not x.startswith("PD-DEC")]


def main():
    ids = snapshot_safe.mutate_snapshot_file(BOARD, mutate)
    assert BOARD.read_text(encoding="utf-8").lstrip().lower().startswith("<!doctype")
    print("dispatch", ids)
    print("OK")


if __name__ == "__main__":
    main()
