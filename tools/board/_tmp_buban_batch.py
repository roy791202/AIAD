# -*- coding: utf-8 -*-
"""Next main line: 佈版 first — hang final evidence to #release; no DCC/SSH/tag/cert."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe
from board_core.pm import new_decision_card

BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
PARENT = "PRODUCT-BU-BAN-20261024"
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
            f"母工項: {PARENT}\n里程碑: 佈版\n{note.rstrip()}\n{COLLAB}\n"
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
    "title": "SGenAxis v0.1 佈版：#release 掛最終證據／佈版說明／產物清單",
    "zone": "yellow",
    "kind": "epic",
    "createdAt": NOW,
    "doneAt": None,
    "startedAt": NOW,
    "by": "human",
    "updatedAt": NOW,
    "updatedBy": "human",
    "bdd": (
        "BDD-PD-BU-BAN-EPIC：看板 #release／releases 掛接最終 Build Result 與關鍵產物；"
        "狀態語意誠實（允許 PARTIAL／NOT RUN）；≠ 商店上架或正式對外 GA。"
    ),
    "tdd": "N/A（epic；子卡 TDD_PASS 後母對話滅燈）。",
    "note": (
        "Primary module: REL\n"
        "承接: Post-Freeze 已綠；owner「先佈版」→ PD-DEC-NEXT-SCOPE-01 已決。\n"
        "範圍: releases 掛最終 BR／產物、佈版說明、產物清單、#release 空態／最近列可驗。\n"
        "不做: DCC／SSH／買證／商店／預設 git tag。\n"
        f"[{NOW}] 安排並派工。"
    ),
    "log": [
        {"t": NOW, "zone": "gray", "by": "human"},
        {"t": NOW, "zone": "yellow", "by": "human"},
    ],
    "version": 1,
}

TASKS = [
    task(
        "PD-REL-HANG-FINAL-01",
        "REL：#release 掛最終 Build Result＋關鍵產物",
        "BDD-PD-REL-HANG-FINAL-01：snapshot.releases 追加／更新一筆 v0.1.0（或等價），"
        "reportPath 指向最終 BR；artifacts 含 MSI／SBOM（若存在）路徑；不得把 NOT RUN 簽章寫成 PASS。",
        "Primary module: REL\n依賴: PD-BR-FINAL-01、PD-RELEASE-REC-01\n"
        "交付／AC: release_report 掛接＋測試。\n允許範圍: tools/board、reports 讀、PROJECT-BOARD snapshot.releases。\n"
        "不做: git tag；商店上架。",
    ),
    task(
        "PD-REL-NOTES-01",
        "DOC：v0.1 佈版說明（Go-with-PARTIAL）",
        "BDD-PD-REL-NOTES-01：短文說明本佈版範圍、Go-with-PARTIAL、簽章 NOT RUN、未做另案；"
        "禁止寫成已正式商店／對外 GA。",
        "Primary module: DOC/REL\n依賴: PD-REL-GONOGO-01、PD-SPRINT-CLOSE-01\n"
        "交付／AC: docs 或 reports 佈版說明＋斷言測試。\n允許範圍: docs、reports、tools 測試。\n"
        "不做: 行銷網站。",
    ),
    task(
        "PD-REL-ARTIFACTS-01",
        "REL：佈版產物清單（路徑／sha／狀態）",
        "BDD-PD-REL-ARTIFACTS-01：列出 MSI／SBOM／最終 BR／gonogo 等路徑與狀態語意；缺項標 NOT RUN／缺檔；"
        "不得暗示未簽章已 PASS。",
        "Primary module: REL\n依賴: PD-BR-FINAL-01、PD-REPORTS-INDEX-01\n"
        "交付／AC: reports 或 docs 清單＋測試。\n允許範圍: docs、reports、packaging 讀、tools 測試。\n"
        "不做: 重打包 MSI。",
    ),
    task(
        "PD-REL-UI-SMOKE-01",
        "REL：#release 最近佈版列／空態可驗（腳本）",
        "BDD-PD-REL-UI-SMOKE-01：以腳本／測試讀 snapshot.releases：非空時最近一筆 version／reportPath 可解析；"
        "清空假設下空態契約仍成立（不破壞殼）。禁止整檔覆寫 HTML。",
        "Primary module: REL\n依賴: PD-REL-HANG-FINAL-01、PD-BOARD-SAFE-01\n"
        "交付／AC: 測試讀 releases＋殼 intact。\n允許範圍: tools/board、docs/PROJECT-BOARD.html（snapshot only）。\n"
        "不做: 改 UI 視覺大改版。",
    ),
]


def mutate(data):
    existing = {t["id"] for t in data.get("tasks") or []}
    added = []

    # Close next-scope red
    for t in data.get("tasks") or []:
        if t.get("id") == "PD-DEC-NEXT-SCOPE-01":
            t["zone"] = "green"
            t["doneAt"] = NOW
            t["updatedAt"] = NOW
            t["updatedBy"] = "human"
            note = (t.get("note") or "").replace("- [ ]", "- [x]")
            t["note"] = note.rstrip() + (
                f"\n[{NOW}] owner「先佈版」→ 已決：DEC-1=佈版優先（非 A/B/C/D 大另案）；"
                f"DCC／SSH／買證暫緩；DEC-2=暫不實打 git tag（另令）；"
                f"開 PRODUCT-BU-BAN-20261024 並派工。"
            )
            log = list(t.get("log") or [])
            log.append({"t": NOW, "zone": "green", "by": "human"})
            t["log"] = log[-20:]
            t["tdd"] = "N/A（決策卡；owner 拍板結案）。"
            t["version"] = int(t.get("version") or 1) + 1
            print("close PD-DEC-NEXT-SCOPE-01")
            break

    go = new_decision_card(
        "PD-DEC-BU-BAN-GO-01",
        "決策：核准 v0.1 佈版批開工",
        now=NOW,
        parent=PARENT,
        pending_items=[
            "DEC-1: 核准 REL-HANG-FINAL／REL-NOTES／REL-ARTIFACTS／REL-UI-SMOKE？",
            "DEC-2: 本批不打 git tag、不開 DCC／SSH、不買證？",
        ],
        bdd="BDD-PD-DEC-BU-BAN-GO-01：核准後才可派本批實作卡。",
    )
    go["zone"] = "green"
    go["doneAt"] = NOW
    go["note"] = (go.get("note") or "").replace("- [ ]", "- [x]") + (
        f"\n[{NOW}] owner「先佈版」→ 已決：核准四卡；不 tag／不 DCC-SSH／不買證；禁偽造 GA。"
    )
    go["log"].append({"t": NOW, "zone": "green", "by": "human"})
    go["tdd"] = "N/A（決策卡；owner 派工即核准）。"
    go["version"] = 2

    for c in [EPIC, go] + TASKS:
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
