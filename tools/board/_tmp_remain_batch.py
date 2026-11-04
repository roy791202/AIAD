# -*- coding: utf-8 -*-
"""Backlog: remaining unfinished desktop/product items — gray cards + red go decision. No dispatch."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe
from board_core.pm import new_decision_card

BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
PARENT = "PRODUCT-REMAIN-20261024"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
COLLAB = (
    "協作：實作子代理以本卡 BDD 為開發指標；既定 TDD／assertions／fixtures／expected values／skip 不得自行修改。"
    "測試定義、RED/GREEN 驗證與回報交專屬 TDD 子代理。契約矛盾 SPEC_CONFLICT；新 seam REPLAN_REQUIRED。"
    "§7.1 不可自改綠；§7.2 只讀本卡 prompt／報告／允許路徑（禁止讀整板）。"
    "看板寫入：禁止整檔覆寫 HTML 殼；只改 #board-snapshot（優先 snapshot_safe）。"
    "ARCH：UI → Tauri Command → DispatchHost → Core／FLOW／EXEC／WORK／EVID → Ports；禁 UI 直撞 adapter。"
)


def task(id_, title, bdd, note, *, milestone="Remain"):
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
        "tdd": "PENDING_TDD_PACKET：專屬 TDD 子代理定義／核對後回報有效 RED；未建立自動化不宣稱 GREEN。",
        "note": f"母工項: {PARENT}\n里程碑: {milestone}\n{note.rstrip()}\n{COLLAB}",
        "log": [{"t": NOW, "zone": "gray", "by": "human"}],
        "version": 1,
    }


EPIC = {
    "id": PARENT,
    "ref": PARENT,
    "title": "SGenAxis 剩餘未作 backlog：桌機未接功能／Live spawn／另案",
    "zone": "gray",
    "kind": "epic",
    "createdAt": NOW,
    "doneAt": None,
    "startedAt": None,
    "by": "human",
    "updatedAt": NOW,
    "updatedBy": "human",
    "bdd": (
        "BDD-PD-REMAIN-EPIC：盤點 Wire-Up 後仍「尚未實作／NOT RUN／PARTIAL」項並建卡；"
        "開工須決策核准；不得把 backlog 存在偽造成已全功能 GA。"
    ),
    "tdd": "N/A（epic；子卡 TDD_PASS 後母對話滅燈）。",
    "note": (
        "Primary module: UI/EXEC/REL/PM\n"
        "承接: PRODUCT-WIRE-20261024 已綠；DESTUB 明示未接項；AGENT Live spawn PARTIAL；"
        "DCC／SSH／買證／實打 tag 另案。\n"
        f"[{NOW}] owner「還有那些未作都排入」→ 建灰燈 backlog＋紅燈開工決策；未派工。"
    ),
    "log": [{"t": NOW, "zone": "gray", "by": "human"}],
    "version": 1,
}

TASKS = [
    task(
        "PD-REMAIN-DESTUB-OPEN-01",
        "UI：OPEN 接通後更新 file.open／project.switch 標籤（去尚未實作）",
        "BDD-PD-REMAIN-DESTUB-OPEN-01：Wire OPEN 已接後，CMD_LABELS／文案不再標 file.open／project.switch 為尚未實作；"
        "仍無路徑者維持 NOT RUN；禁止把未接項改成已完成。",
        "Primary module: UI\n依賴: PD-WIRE-OPEN-01、PD-WIRE-DESTUB-01\n"
        "交付／AC: app.js／測試更新。\n允許範圍: apps/sgenaxis-desktop/ui、tests。",
        milestone="Remain/UI",
    ),
    task(
        "PD-REMAIN-FILE-NEW-01",
        "UI/HOST：新增專案（file.new → Command）",
        "BDD-PD-REMAIN-FILE-NEW-01：新增專案經 Command 建立／綁定 project_root（或明確 NOT RUN）；"
        "禁 UI 直寫 FS；失敗可讀。",
        "Primary module: UI/HOST\n依賴: PD-WIRE-OPEN-01\n"
        "交付／AC: command＋UI＋測試。\n允許範圍: apps/sgenaxis-desktop。\n不做: 雲端範本市集。",
        milestone="Remain/UI",
    ),
    task(
        "PD-REMAIN-FILE-SAVE-01",
        "UI/HOST：儲存（file.save → Command）",
        "BDD-PD-REMAIN-FILE-SAVE-01：儲存經 Command 持久化設定／看板投影狀態（範圍書面化）；"
        "無實作則維持 NOT RUN；禁偷偷寫任意路徑。",
        "Primary module: UI/HOST\n依賴: PD-WIRE-ROOT-01\n"
        "交付／AC: command＋測試。\n允許範圍: apps/sgenaxis-desktop。",
        milestone="Remain/UI",
    ),
    task(
        "PD-REMAIN-FILE-QUIT-01",
        "UI/HOST：結束應用（file.quit → Command）",
        "BDD-PD-REMAIN-FILE-QUIT-01：Tauri 下可經 Command／host_request_shutdown 結束；"
        "瀏覽器模式明示無法關閉殼（NOT RUN）。",
        "Primary module: UI/HOST\n依賴: PD-HOST-01\n"
        "交付／AC: 接線＋測試。\n允許範圍: apps/sgenaxis-desktop。",
        milestone="Remain/UI",
    ),
    task(
        "PD-REMAIN-EDIT-01",
        "UI：編輯選單（undo／redo／selectAll／clear）接通或明示 NOT RUN",
        "BDD-PD-REMAIN-EDIT-01：四項皆經 Command 進領域選取／歷史，或維持尚未實作／NOT RUN；"
        "禁止半接半示意。",
        "Primary module: UI/CORE\n依賴: PD-UI-01\n"
        "交付／AC: 接通子集或文件化 NOT RUN＋測試。\n允許範圍: apps/sgenaxis-desktop。",
        milestone="Remain/UI",
    ),
    task(
        "PD-REMAIN-PORTS-UI-01",
        "UI：Ports 檢視（讀領域／Ports 投影）",
        "BDD-PD-REMAIN-PORTS-UI-01：Ports 檢視經 Command 投影已註冊 Port／adapter 狀態；"
        "無資料→空態；禁 UI 直列 OS。",
        "Primary module: UI/HOST\n依賴: PD-ADAPT-01、PD-CMD-01\n"
        "交付／AC: 面板＋command＋測試。\n允許範圍: apps/sgenaxis-desktop。",
        milestone="Remain/UI",
    ),
    task(
        "PD-REMAIN-ARCH-UI-01",
        "UI：模組架構圖刷新（arch.refresh）",
        "BDD-PD-REMAIN-ARCH-UI-01：架構圖經 Command 取模組／依賴投影並刷新；無圖→空態／NOT RUN；"
        "禁止靜態假圖冒充即時圖。",
        "Primary module: UI\n依賴: PD-SPEC-UI-01\n"
        "交付／AC: 面板＋測試。\n允許範圍: apps/sgenaxis-desktop。",
        milestone="Remain/UI",
    ),
    task(
        "PD-REMAIN-WORK-TAGS-01",
        "UI/WORK：批次 BDD／TDD 標籤",
        "BDD-PD-REMAIN-WORK-TAGS-01：批次標籤經 Command 寫入工項投影／領域；非法→可讀錯誤；"
        "未做則 NOT RUN。",
        "Primary module: UI/WORK\n依賴: PD-WORK-01、PD-BOARD-LIVE-01\n"
        "交付／AC: command＋UI＋測試。\n允許範圍: apps/sgenaxis-desktop。",
        milestone="Remain/UI",
    ),
    task(
        "PD-REMAIN-WIN-RESET-01",
        "UI：重設佈局（win.reset）",
        "BDD-PD-REMAIN-WIN-RESET-01：重設側欄／Inspector／面板佈局經 Command 或本機 chrome 狀態；"
        "可還原預設；失敗可讀。",
        "Primary module: UI\n依賴: PD-UI-NAV-01\n"
        "交付／AC: 實作＋測試。\n允許範圍: apps/sgenaxis-desktop/ui。",
        milestone="Remain/UI",
    ),
    task(
        "PD-REMAIN-LIVE-SPAWN-01",
        "EXEC：DispatchHost Live real-spawn（CLI）",
        "BDD-PD-REMAIN-LIVE-SPAWN-01：核准 Live 且路徑有效時，start_run 經 DispatchHost→EXEC 真起程"
        "（非僅 DryRun compose）；無核准／無 CLI→NOT RUN／可讀拒絕；秘密不進投影。",
        "Primary module: EXEC\n依賴: PD-WIRE-AGENT-01、PD-EXEC-LIVE-01、PD-LIVE-CLI-SMOKE-01\n"
        "交付／AC: DispatchHost 接 StdProcess／real-spawn＋測試。\n"
        "允許範圍: src-tauri dispatch／commands、sgenaxis-exec／adapters。\n"
        "不做: 雲端閘道。",
        milestone="Remain/EXEC",
    ),
    task(
        "PD-REMAIN-LIVE-MCP-01",
        "EXEC：DispatchHost Live MCP（非 DryRun-only）",
        "BDD-PD-REMAIN-LIVE-MCP-01：核准 Live＋有效本機 MCP 端點時經 Command→DispatchHost 真連；"
        "禁 :8788／:8787；無目標→NOT RUN。",
        "Primary module: EXEC\n依賴: PD-REMAIN-LIVE-SPAWN-01、PD-MCP-LIVE-SMOKE-01\n"
        "交付／AC: 接線＋測試。\n允許範圍: src-tauri、sgenaxis-exec。\n不做: 任意雲端 MCP。",
        milestone="Remain/EXEC",
    ),
    task(
        "PD-REMAIN-LISTEN-UI-01",
        "UI/LISTEN：監聽事件投影進桌機（若仍缺面板）",
        "BDD-PD-REMAIN-LISTEN-UI-01：FS／Git／Agent 監聽事件經 Command／橋接投影到 UI；"
        "無事件→空態；禁 UI 自建 notify。",
        "Primary module: UI/LISTEN\n依賴: PD-LISTEN-01、PD-LISTEN-02\n"
        "交付／AC: 投影＋測試或明示已由既有面板覆蓋＋NOT RUN 項。\n"
        "允許範圍: apps/sgenaxis-desktop。",
        milestone="Remain/UI",
    ),
    task(
        "PD-REMAIN-SIGN-LIVE-01",
        "REL：Authenticode 真簽（有憑證）或維持 NOT RUN 文件閘",
        "BDD-PD-REMAIN-SIGN-LIVE-01：有憑證可跑真簽並掛 BR；無憑證→NOT RUN（禁偽 PASS）。",
        "Primary module: REL\n依賴: PD-SIGN-STUB-01、PD-DEC-V01-GATE-01\n"
        "交付／AC: 腳本路徑＋測試；買證另決策。\n允許範圍: packaging、tools、docs。\n"
        "不做: 強制購買憑證。",
        milestone="Remain/REL",
    ),
    task(
        "PD-REMAIN-TAG-APPLY-01",
        "REL：git tag v0.1.0 實打（顯式核准）",
        "BDD-PD-REMAIN-TAG-APPLY-01：僅在 owner 核准＋顯式旗標下 tag_prep --apply；"
        "預設仍 dry-run；禁把 dry-run 當已發布。",
        "Primary module: REL\n依賴: PD-TAG-PREP-01、PD-DEC-NEXT-SCOPE（tag 項）\n"
        "交付／AC: 文件／閘＋測試。\n允許範圍: tools/board、docs。\n不做: 預設自動 push。",
        milestone="Remain/REL",
    ),
    task(
        "PD-REMAIN-DCC-EPIC-01",
        "DOC/PM：DCC 宿主另案開題說明（不實作）",
        "BDD-PD-REMAIN-DCC-EPIC-01：產出 DCC 另案範圍一頁（Mode B／attach／非首版）；"
        "本卡不實作插件；禁止暗示 DCC 已接通。",
        "Primary module: PM/DOC\n依賴: PRODUCT-DEVELOPMENT §6.5\n"
        "交付／AC: docs 一頁＋斷言。\n允許範圍: docs。\n不做: Maya／Houdini 碼。",
        milestone="Remain/另案",
    ),
    task(
        "PD-REMAIN-SSH-EPIC-01",
        "DOC/PM：SSH／遠端另案開題說明（不實作）",
        "BDD-PD-REMAIN-SSH-EPIC-01：產出 SSH／容器遠端另案範圍一頁；本卡不實作連線；"
        "禁止暗示遠端已接通。",
        "Primary module: PM/DOC\n依賴: PRODUCT-DEVELOPMENT §6.5\n"
        "交付／AC: docs 一頁＋斷言。\n允許範圍: docs。\n不做: SSH 客戶端實作。",
        milestone="Remain/另案",
    ),
]


def mutate(data):
    existing = {t["id"] for t in data.get("tasks") or []}
    added = []

    dec = new_decision_card(
        "PD-DEC-REMAIN-GO-01",
        "決策：剩餘未作 backlog 開工優先序",
        now=NOW,
        parent=PARENT,
        pending_items=[
            "DEC-1: 核准灰燈 backlog 哪些先黃燈開工？（建議：DESTUB-OPEN→LIVE-SPAWN→FILE-*→PORTS/ARCH）",
            "DEC-2: Live real-spawn／真簽／實打 tag 是否本波允許？",
            "DEC-3: DCC／SSH 僅文件開題 or 暫緩？",
        ],
        bdd="BDD-PD-DEC-REMAIN-GO-01：未決前不得把本批灰燈改黃派工。",
    )

    for c in [EPIC, dec] + TASKS:
        if c["id"] in existing:
            print("skip", c["id"])
            continue
        data["tasks"].append(c)
        added.append(c["id"])
        print("add", c["id"], c.get("zone"))

    for t in data.get("tasks") or []:
        if t.get("id") == "PRODUCT-WIRE-20261024":
            t["note"] = (t.get("note") or "").rstrip() + (
                f"\n[{NOW}] 剩餘未作已排入 {PARENT}（灰燈＋紅燈決策；未派工）。"
            )
            t["updatedAt"] = NOW
            t["updatedBy"] = "human"
            t["version"] = int(t.get("version") or 1) + 1
            break

    data["asOf"] = NOW
    data["overall"] = "PARTIAL"
    print("added", len(added))
    return added


def main():
    snapshot_safe.mutate_snapshot_file(BOARD, mutate)
    assert BOARD.read_text(encoding="utf-8").lstrip().lower().startswith("<!doctype")
    print("OK — gray backlog; red decision; no dispatch")


if __name__ == "__main__":
    main()
