# -*- coding: utf-8 -*-
"""M4 first-cut: epic + tasks (yellow) + DEC closed; ready to dispatch."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe
from board_core.pm import new_decision_card

BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
PARENT = "PRODUCT-M4-20261024"
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
            f"母工項: {PARENT}\n里程碑: M4\n{note.rstrip()}\n{COLLAB}\n"
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
    "title": "SGenAxis M4 首切：macOS／Linux 包裝契約＋stub＋文件（非完整發行）",
    "zone": "yellow",
    "kind": "epic",
    "createdAt": NOW,
    "doneAt": None,
    "startedAt": NOW,
    "by": "human",
    "updatedAt": NOW,
    "updatedBy": "human",
    "bdd": "BDD-PD-M4-EPIC：跨平台包裝契約與可重跑 stub／文件到位；真機 notarize／商店上架另案。",
    "tdd": "N/A（epic；子卡 TDD_PASS 後母對話滅燈）。",
    "note": (
        "Primary module: REL/HOST\n"
        "承接: PRODUCT-DEV-20261023、PRODUCT-HARDEN-20261024（已綠）。\n"
        "範圍: PackSpec、mac／linux stub 腳本、CI 矩陣占位、文件；允許 Win 上 NOT RUN。\n"
        "不做: 完整 notarize／App Store／真機 elevated 全綠偽造；SSH／DCC 另案。\n"
        f"[{NOW}] 建 epic＋黃燈開工（owner 安排並派工）；決策見 PD-DEC-M4-GO-01 已決。"
    ),
    "log": [
        {"t": NOW, "zone": "gray", "by": "human"},
        {"t": NOW, "zone": "yellow", "by": "human"},
    ],
    "version": 1,
}

TASKS = [
    task(
        "PD-M4-PACK-SPEC-01",
        "REL：跨平台 PackSpec／產物契約（mac｜linux｜win）",
        "BDD-PD-M4-PACK-SPEC-01：定義產物欄位（os／arch／path／sha256／status）；"
        "status∈PASS｜FAIL｜BLOCKED｜NOT RUN｜PARTIAL；與 Build Result／releases 可掛接。",
        "Primary module: REL\n依賴: PD-BUILD-RESULT-01、PD-RELEASE-REC-01\n"
        "交付／AC: 契約模組或 JSON schema＋單元測試。\n"
        "允許範圍: tools/board、packaging/、reports。\n不做: 真機打包必過。",
    ),
    task(
        "PD-M4-MAC-STUB-01",
        "REL：macOS 包裝 stub（可重跑；無 Mac 則 NOT RUN）",
        "BDD-PD-M4-MAC-STUB-01：提供 mac 包裝入口腳本／文件；非 Darwin 主機明確 NOT RUN；"
        "不得偽造 PASS。",
        "Primary module: REL\n依賴: PD-M4-PACK-SPEC-01\n"
        "交付／AC: packaging/macos/（或等價）stub＋測試或契約斷言。\n"
        "允許範圍: packaging/macos、docs。\n不做: notarize／stapling 必過。",
    ),
    task(
        "PD-M4-LINUX-STUB-01",
        "REL：Linux 包裝 stub（可重跑；非 Linux 則 NOT RUN）",
        "BDD-PD-M4-LINUX-STUB-01：提供 linux 包裝入口（AppImage／deb 擇一 stub）；"
        "非 Linux 主機明確 NOT RUN；不得偽造 PASS。",
        "Primary module: REL\n依賴: PD-M4-PACK-SPEC-01\n"
        "交付／AC: packaging/linux/（或等價）stub＋測試或契約斷言。\n"
        "允許範圍: packaging/linux、docs。\n不做: 發行版商店上架。",
    ),
    task(
        "PD-M4-CI-MATRIX-01",
        "HOST/CI：多 OS 矩陣占位（文件＋workflow stub）",
        "BDD-PD-M4-CI-MATRIX-01：CI 或文件列出 windows／macos／linux job 占位；"
        "缺 runner 標 NOT RUN；與 PD-CI-01 本機命令可對照。",
        "Primary module: HOST/CI\n依賴: PD-CI-01、PD-M4-PACK-SPEC-01\n"
        "交付／AC: .github workflow 擴充或 docs 矩陣表＋可選 dry script。\n"
        "允許範圍: .github、docs、scripts。\n不做: 付費 mac runner 必買。",
    ),
    task(
        "PD-M4-DOC-01",
        "DOC：M4 包裝／限制說明寫入產品文件",
        "BDD-PD-M4-DOC-01：PRODUCT-DEVELOPMENT／desktop README 說明 M4 範圍、NOT RUN 語意、"
        "與 Windows WiX 邊界；禁止暗示已完整跨平台發行。",
        "Primary module: DOC/REL\n依賴: PD-M4-PACK-SPEC-01\n"
        "交付／AC: md＋html 或 README 章節。\n允許範圍: docs、apps/sgenaxis-desktop/README。\n"
        "不做: 行銷頁。",
    ),
]


def mutate(data):
    existing = {t["id"] for t in data.get("tasks") or []}
    added = []

    # decision: create already-approved (green) — owner said 安排並派工
    dec = new_decision_card(
        "PD-DEC-M4-GO-01",
        "決策：核准 M4 首切（stub＋契約＋文件；非完整發行）",
        now=NOW,
        parent=PARENT,
        pending_items=[
            "DEC-1: 核准 M4 首切五卡？",
            "DEC-2: 範圍限 stub／契約／CI 占位／文件（無 notarize 硬閘）？",
        ],
        note_prefix="里程碑: M4",
        bdd="BDD-PD-DEC-M4-GO-01：核准後才可派 M4 實作卡。",
    )
    # flip to approved green immediately
    dec["zone"] = "green"
    dec["doneAt"] = NOW
    dec["note"] = (dec.get("note") or "").replace("- [ ]", "- [x]") + (
        f"\n[{NOW}] owner「安排下一批次並派工」→ 已決：核准 M4 首切五卡；"
        "stub／契約／CI 占位／文件；禁止偽造跨平台 PASS；notarize／商店另案。"
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

    for t in data.get("tasks") or []:
        if t.get("id") == "PRODUCT-HARDEN-20261024":
            t["note"] = (t.get("note") or "").rstrip() + (
                f"\n[{NOW}] 下一批已開 {PARENT}（M4 首切）並派工。"
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
    print("OK")


if __name__ == "__main__":
    main()
