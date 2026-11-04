# -*- coding: utf-8 -*-
"""Next batch: release candidate harden — sign stub, SBOM, BR refresh. Dispatch-ready."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe
from board_core.pm import new_decision_card

BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
PARENT = "PRODUCT-REL-CANDIDATE-20261024"
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
            f"母工項: {PARENT}\n里程碑: Rel-Candidate\n{note.rstrip()}\n{COLLAB}\n"
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
    "title": "SGenAxis v0.1 候選強化：簽章 stub／SBOM／Build Result 升格",
    "zone": "yellow",
    "kind": "epic",
    "createdAt": NOW,
    "doneAt": None,
    "startedAt": NOW,
    "by": "human",
    "updatedAt": NOW,
    "updatedBy": "human",
    "bdd": "BDD-PD-REL-CAND-EPIC：簽章／SBOM／BR 可重跑掛接；無憑證則 NOT RUN；不得偽造 PASS。",
    "tdd": "N/A（epic；子卡 TDD_PASS 後母對話滅燈）。",
    "note": (
        "Primary module: REL/SEC\n"
        "承接: VERIFY（elev live PASS）、HARDEN、M4 stub、首版 epic。\n"
        "範圍: Authenticode stub、SBOM、Build Result 重產（掛 elev／sec／verify-hang）、發布檢查清單、notarize 文件預留。\n"
        "不做: 強制購買憑證、商店上架、DCC／SSH（另案）。\n"
        f"[{NOW}] 安排並派工；PD-DEC-REL-CAND-GO-01 已決。"
    ),
    "log": [
        {"t": NOW, "zone": "gray", "by": "human"},
        {"t": NOW, "zone": "yellow", "by": "human"},
    ],
    "version": 1,
}

TASKS = [
    task(
        "PD-SIGN-STUB-01",
        "REL：Windows Authenticode 簽章 stub（無憑證→NOT RUN）",
        "BDD-PD-SIGN-STUB-01：提供可重跑簽章入口；無憑證／未設定→NOT RUN；有憑證才嘗試；"
        "不得把 NOT RUN 寫成 PASS；結果可掛 Build Result。",
        "Primary module: REL\n依賴: PD-REL-02、PD-BUILD-RESULT-01\n"
        "交付／AC: packaging／scripts stub＋測試。\n允許範圍: packaging/windows、tools、scripts。\n"
        "不做: 強制購買／匯入憑證。",
    ),
    task(
        "PD-SBOM-01",
        "SEC：產出 SBOM（CycloneDX 或 SPDX）並掛報告",
        "BDD-PD-SBOM-01：可重跑產出 SBOM 檔；失敗明示；可被 sec／Build Result 引用；"
        "高危未分流不得因此偽造成整體 PASS。",
        "Primary module: SEC/REL\n依賴: PD-SEC-SCAN-01、PD-BUILD-RESULT-01\n"
        "交付／AC: 腳本＋reports 範例＋測試。\n允許範圍: tools、scripts、reports。\n"
        "不做: 自動封鎖合併。",
    ),
    task(
        "PD-BR-REFRESH-01",
        "REL：重產 Build Result（掛 elev PASS＋sec＋verify-hang）",
        "BDD-PD-BR-REFRESH-01：以現有 elev／sec／verify-hang 證據重產 Build Result；"
        "狀態依證據聚合（不得把 NOT RUN 變 PASS）；可更新 releases 掛接。",
        "Primary module: REL\n依賴: PD-ELEV-VERIFY-01、PD-SEC-SCAN-01、PD-VERIFY-HANG-01、PD-BUILD-RESULT-01\n"
        "交付／AC: 新 reports/build-*.md＋測試或腳本證明。\n允許範圍: tools/board、reports、packaging 讀。",
    ),
    task(
        "PD-REL-CHECKLIST-01",
        "DOC：v0.1 發布檢查清單（可勾選）",
        "BDD-PD-REL-CHECKLIST-01：文件列出發布前檢查項（MSI／elev／sec／SBOM／簽章／CHANGELOG）；"
        "每項對應狀態語意 PASS｜FAIL｜NOT RUN｜PARTIAL。",
        "Primary module: DOC/REL\n依賴: PD-CHANGELOG-01、PD-BR-REFRESH-01\n"
        "交付／AC: docs 清單＋交叉連結。\n允許範圍: docs、README。",
    ),
    task(
        "PD-NOTARY-PREP-01",
        "DOC：macOS notarize／stapling 預留說明（不實跑）",
        "BDD-PD-NOTARY-PREP-01：文件說明 notarize 步驟與本機限制；標明目前 NOT RUN；"
        "禁止暗示已完成 Apple 公證。",
        "Primary module: DOC/REL\n依賴: PD-M4-MAC-STUB-01、PD-M4-DOC-01\n"
        "交付／AC: docs 章節。\n允許範圍: docs、packaging/macos README。\n不做: 真機公證。",
    ),
]


def mutate(data):
    existing = {t["id"] for t in data.get("tasks") or []}
    added = []

    dec = new_decision_card(
        "PD-DEC-REL-CAND-GO-01",
        "決策：核准 v0.1 候選強化批開工",
        now=NOW,
        parent=PARENT,
        pending_items=[
            "DEC-1: 核准 SIGN-STUB／SBOM／BR-REFRESH／CHECKLIST／NOTARY-PREP？",
            "DEC-2: 無憑證時簽章維持 NOT RUN（不強制買證）？",
        ],
        bdd="BDD-PD-DEC-REL-CAND-GO-01：核准後才可派本批實作卡。",
    )
    dec["zone"] = "green"
    dec["doneAt"] = NOW
    dec["note"] = (dec.get("note") or "").replace("- [ ]", "- [x]") + (
        f"\n[{NOW}] owner「安排下一批次並派工」→ 已決：核准五卡；無憑證→簽章 NOT RUN；禁偽造 PASS。"
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
        if t.get("id") == "PRODUCT-VERIFY-20261024":
            t["note"] = (t.get("note") or "").rstrip() + (
                f"\n[{NOW}] 下一批已開 {PARENT}（候選強化）並派工。"
            )
            t["updatedAt"] = NOW
            t["updatedBy"] = "human"
            t["version"] = int(t.get("version") or 1) + 1
            break

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
