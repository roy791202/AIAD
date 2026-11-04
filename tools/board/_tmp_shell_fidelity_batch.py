# -*- coding: utf-8 -*-
"""Gray backlog: desktop shell fidelity to git_workbench_interactive.html."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe
from board_core.pm import new_decision_card

BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
PARENT = "PRODUCT-SHELL-FIDELITY-20261024"
COLLAB = (
    "協作：實作子代理以本卡 BDD 為開發指標；既定 TDD／assertions／fixtures／expected values／skip 不得自行修改。"
    "測試定義、RED/GREEN 驗證與回報交專屬 TDD 子代理。契約矛盾 SPEC_CONFLICT；新 seam REPLAN_REQUIRED。"
    "§7.1 不可自改綠；§7.2 只讀本卡 prompt／報告／允許路徑（禁止讀整板）。"
    "看板寫入：禁止整檔覆寫 HTML 殼；只改 #board-snapshot（優先 snapshot_safe）。"
    "ARCH：UI → Tauri Command → DispatchHost → 領域 → Ports；禁 UI 直撞 adapter。"
)


def gray_task(id_, title, bdd, note):
    return {
        "id": id_,
        "ref": id_,
        "title": title,
        "zone": "gray",
        "kind": "task",
        "createdAt": NOW,
        "doneAt": None,
        "startedAt": None,
        "by": "human",
        "updatedAt": NOW,
        "updatedBy": "human",
        "bdd": bdd,
        "tdd": "PENDING_TDD_PACKET：開工後由專屬 TDD 子代理定義；未建立自動化不宣稱 GREEN。",
        "note": (
            f"母工項: {PARENT}\n里程碑: Shell-Fidelity\n{note.rstrip()}\n{COLLAB}\n"
            f"[{NOW}] 灰燈入板（owner：安裝版與 Workbench HTML 落差大；Workbench=IA SSOT）。"
        ),
        "log": [{"t": NOW, "zone": "gray", "by": "human"}],
        "version": 1,
    }


EPIC = {
    "id": PARENT,
    "ref": PARENT,
    "title": "SGenAxis：安裝版桌機殼對齊 git_workbench_interactive.html（視覺／IA）",
    "zone": "gray",
    "kind": "epic",
    "createdAt": NOW,
    "doneAt": None,
    "startedAt": None,
    "by": "human",
    "updatedAt": NOW,
    "updatedBy": "human",
    "bdd": (
        "BDD-PD-SHELL-FIDELITY-EPIC：apps/sgenaxis-desktop UI 殼（選單／工具列／側欄主路徑／"
        "主區視圖密度／Inspector／狀態列）對齊 git_workbench_interactive.html；"
        "Workbench 為 IA SSOT；Command 路徑不變；≠ 重寫領域、≠ 偽接通 Adapter。"
    ),
    "tdd": "N/A（epic；子卡 TDD_PASS 後母對話滅燈）。",
    "note": (
        "Primary module: UI/HOST\n"
        "問題: 打包 MSI 安裝後體感與 Workbench HTML 落差大（資訊架構／密度／缺視圖）。\n"
        "權威: 1) git_workbench_interactive.html  2) PRODUCT §5  3) 既有 Command 契約。\n"
        "不做: 改回 PySide/Electron；用 ui-design 14 頁覆寫側欄；買證／tag／商店。\n"
        "相關: PRODUCT-UI-DESIGN-ALIGN 僅文件對齊，不解決安裝版外觀。\n"
        f"[{NOW}] 本批已建卡：PD-DEC-SHELL-FIDELITY-GO-01、"
        f"PD-SHELL-AUDIT-01、PD-SHELL-CHROME-01、PD-SHELL-SIDEBAR-01、"
        f"PD-SHELL-BOARD-01、PD-SHELL-UIDESIGN-VIEW-01、PD-SHELL-CSS-01。"
    ),
    "log": [{"t": NOW, "zone": "gray", "by": "human"}],
    "version": 1,
}

TASKS = [
    gray_task(
        "PD-SHELL-AUDIT-01",
        "DOC：Workbench↔桌機落差清單（可勾選）",
        "BDD-PD-SHELL-AUDIT-01：產出對照表（殼區／側欄／六視圖／密度／缺項）；"
        "標 Must／Should／Won't（v0.1）；引用 Workbench 選擇器與 desktop 檔案路徑；"
        "不得暗示 MSI 已視覺對齊完成。",
        "Primary module: DOC/UI\n依賴: 無\n"
        "交付／AC: docs 或 reports 落差清單＋斷言。\n"
        "允許範圍: git_workbench_interactive.html 讀、apps/sgenaxis-desktop/ui 讀、docs、reports、tests。\n"
        "不做: 改產品碼。",
    ),
    gray_task(
        "PD-SHELL-CHROME-01",
        "UI：選單列／工具列／狀態列對齊 Workbench 殼",
        "BDD-PD-SHELL-CHROME-01：menubar＋toolbar＋status 資訊層級／間距／專案列呈現"
        "接近 Workbench（非像素逐點）；既有 data-cmd 保留；空／未綁定態可讀。",
        "Primary module: UI\n依賴: PD-SHELL-AUDIT-01（軟）\n"
        "交付／AC: ui/index.html＋styles＋chrome 測試。\n"
        "允許範圍: apps/sgenaxis-desktop/ui。\n"
        "不做: 新業務 Command；PySide 移植。",
    ),
    gray_task(
        "PD-SHELL-SIDEBAR-01",
        "UI：側欄主路徑對齊 Workbench（Agent→Tasks Status→佈版→架構→UI設計）",
        "BDD-PD-SHELL-SIDEBAR-01：側欄順序與分組貼近 Workbench；Tasks Status 四態篩選"
        "視覺／交互更接近原型；次要項（Git／Spec／Report／Settings／Ports／Listen）"
        "可次層或下部，但不破壞既有 panel 路由。",
        "Primary module: UI\n依賴: PD-SHELL-AUDIT-01（軟）\n"
        "交付／AC: sidebar 結構＋導覽測試。\n"
        "允許範圍: apps/sgenaxis-desktop/ui。\n"
        "不做: 刪除 Ports／Listen（可降級位置）。",
    ),
    gray_task(
        "PD-SHELL-BOARD-01",
        "UI：工項看板表密度／欄位對齊 Workbench 工項表",
        "BDD-PD-SHELL-BOARD-01：board 表格列高、欄位層級、燈號、空態接近 Workbench"
        "viewTaskBoard；資料仍經既有 board Command／投影；禁 UI 直讀檔。",
        "Primary module: UI\n依賴: PD-SHELL-SIDEBAR-01（軟）\n"
        "交付／AC: board 面板樣式／結構＋測試。\n"
        "允許範圍: apps/sgenaxis-desktop/ui。\n"
        "不做: 假造工項資料。",
    ),
    gray_task(
        "PD-SHELL-UIDESIGN-VIEW-01",
        "UI：補 Workbench「UI 設計工具」視圖（嵌入／開啟設計包）",
        "BDD-PD-SHELL-UIDESIGN-VIEW-01：側欄／模組選單可進 UI 設計工具視圖；"
        "內容可為內嵌 docs/ui-design/index.html 或受控開啟本機設計包；"
        "標示設計稿非產品證據；無則空態＋路徑說明；禁當正式驗收 PASS。",
        "Primary module: UI\n依賴: PD-SHELL-SIDEBAR-01（軟）\n"
        "交付／AC: panel-uidesign（或等價）＋測試。\n"
        "允許範圍: apps/sgenaxis-desktop/ui、docs/ui-design 讀、必要 host command（若需開檔）。\n"
        "不做: 重畫 14 張 PNG。",
    ),
    gray_task(
        "PD-SHELL-CSS-01",
        "UI：token／密度／Inspector 對齊 Workbench CSS 變數",
        "BDD-PD-SHELL-CSS-01：styles.css token 與 Workbench :root 對齊（色／字級／側欄寬／"
        "Inspector 寬）；主區與 Inspector 比例接近原型；a11y 焦點保留。",
        "Primary module: UI\n依賴: PD-SHELL-CHROME-01（軟）\n"
        "交付／AC: styles 更新＋視覺／契約測試（可靜態 assert token）。\n"
        "允許範圍: apps/sgenaxis-desktop/ui。\n"
        "不做: 行銷風大改版；破壞對比可讀性。",
    ),
]


def mutate(data):
    existing = {t["id"] for t in data.get("tasks") or []}
    added = []
    go = new_decision_card(
        "PD-DEC-SHELL-FIDELITY-GO-01",
        "決策：核准安裝版殼對齊 Workbench 批（灰燈入板）",
        now=NOW,
        parent=PARENT,
        pending_items=[
            "DEC-1: 核准 AUDIT／CHROME／SIDEBAR／BOARD／UIDESIGN-VIEW／CSS 六卡？",
            "DEC-2: 本批以 Workbench 為視覺／IA 主；不改領域契約；不重產 ui-design 大圖？",
        ],
        bdd="BDD-PD-DEC-SHELL-FIDELITY-GO-01：核准後才可黃燈派本批實作卡。",
    )
    # Owner stated the gap + Workbench-primary → approve backlog entry; keep tasks gray
    go["zone"] = "green"
    go["doneAt"] = NOW
    go["note"] = (go.get("note") or "").replace("- [ ]", "- [x]") + (
        f"\n[{NOW}] owner「安裝版與 Workbench 落差大」+「以 Workbench 為主」→ "
        f"已決：DEC-1=核准六卡入板；DEC-2=Workbench SSOT、不改領域、不重產大圖；"
        f"實作卡維持灰燈待另令派工。"
    )
    go["log"].append({"t": NOW, "zone": "green", "by": "human"})
    go["tdd"] = "N/A（決策卡；owner 陳述落差即核准入板）。"
    go["version"] = 2

    for c in [EPIC, go] + TASKS:
        if c["id"] in existing:
            print("skip", c["id"])
            continue
        data["tasks"].append(c)
        added.append(c["id"])
        print("add", c["id"], c.get("zone"))

    data["asOf"] = NOW
    data["overall"] = "PARTIAL"
    print("added", len(added))
    return [x for x in added if x.startswith("PD-SHELL-")]


if __name__ == "__main__":
    print("ok", snapshot_safe.mutate_snapshot_file(BOARD, mutate))
