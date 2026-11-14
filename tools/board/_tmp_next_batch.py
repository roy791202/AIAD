# -*- coding: utf-8 -*-
"""Next batch: v0.1 harden epic + gray tasks + red decisions. No dispatch."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from board_core import snapshot_safe
from board_core.pm import new_decision_card

BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
PARENT = "PRODUCT-HARDEN-20261024"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
COLLAB = (
    "協作：實作子代理以本卡 BDD 為開發指標；既定 TDD／assertions／fixtures／expected values／skip 不得自行修改。"
    "測試定義、RED/GREEN 驗證與回報交專屬 TDD 子代理。契約矛盾 SPEC_CONFLICT；新 seam REPLAN_REQUIRED。"
    "§7.1 不可自改綠；§7.2 只讀本卡 prompt／報告／允許路徑（禁止讀整板）。"
    "看板寫入：禁止整檔覆寫 HTML 殼；只改 #board-snapshot（優先 snapshot_safe）。"
)


def task(id_, title, bdd, note, *, milestone="Harden"):
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
    "title": "SGenAxis v0.1 硬化：CI／文件／安全掃描／回歸（非 M4）",
    "zone": "yellow",
    "kind": "epic",
    "createdAt": NOW,
    "doneAt": None,
    "startedAt": NOW,
    "by": "human",
    "updatedAt": NOW,
    "updatedBy": "human",
    "bdd": "BDD-PD-HARDEN-EPIC：首版 epic 已綠後，工程衛生與可重跑驗證到位；不開 M4 包。",
    "tdd": "N/A（epic；子卡 TDD_PASS＋產出後由母對話滅燈）。",
    "note": (
        f"Primary module: HOST/REL/VERIFY\n"
        f"承接: PRODUCT-DEV-20261023（已綠）。\n"
        f"範圍: CI、CHANGELOG、App README、依存／秘密掃描、回歸矩陣；可選 elevated／Live 視紅燈決策。\n"
        f"不做: M4 macOS／Linux／SSH／DCC（見已決 PD-DEC-M4-SCOPE-01）。\n"
        f"看板埠: 28789。寫入走 snapshot_safe。\n"
        f"[{NOW}] 建 epic＋灰燈子卡＋紅燈決策；未派工（§7.3）。"
    ),
    "log": [
        {"t": NOW, "zone": "gray", "by": "human"},
        {"t": NOW, "zone": "yellow", "by": "human"},
    ],
    "version": 1,
}

TASKS = [
    task(
        "PD-CI-01",
        "HOST/CI：PR 閘門（lint＋測試子集）",
        "BDD-PD-CI-01：PR 可跑固定指令（lint／單元或 smoke 子集）；失敗不可視為綠；文件寫明本機等價命令。",
        "Primary module: HOST/CI\n依賴: PD-SMOKE-01（建議）\n"
        "交付／AC: CI 設定（GitHub Actions 或等價）＋README 片段；不強制全量 cargo。\n"
        "允許範圍: .github／scripts／docs；可讀 tests。\n不做: 雲端付費專屬 runner。",
    ),
    task(
        "PD-CHANGELOG-01",
        "REL：CHANGELOG＋SemVer 紀錄（v0.1.0）",
        "BDD-PD-CHANGELOG-01：倉庫有 CHANGELOG（或等價）記載 v0.1.0 摘要；與 Build Result／releases 可對照。",
        "Primary module: REL\n依賴: PD-BUILD-RESULT-01、PD-RELEASE-REC-01\n"
        "交付／AC: CHANGELOG.md（或 docs）＋版本對照。\n允許範圍: 根目錄／docs／reports 讀。\n不做: 自動打 git tag（可文件說明）。",
    ),
    task(
        "PD-README-APP-01",
        "DOC：桌機 App 使用說明（開專案／DryRun／設定）",
        "BDD-PD-README-APP-01：新使用者依文件可啟動桌機／開專案／跑 DryRun；埠 28789 與 :8788 禁區寫清。",
        "Primary module: DOC/UI\n依賴: PD-UI-01、PD-SET-UI-01\n"
        "交付／AC: apps/sgenaxis-desktop/README 或 docs 使用章節。\n允許範圍: docs＋desktop README。\n不做: 行銷網站。",
    ),
    task(
        "PD-SEC-SCAN-01",
        "VERIFY：依存 CVE＋秘密掃描（記錄於報告）",
        "BDD-PD-SEC-SCAN-01：可重跑掃描產出報告；高危未分流前 Build Result 不得偽造成 PASS；狀態 PASS｜FAIL｜PARTIAL｜NOT RUN 明示。",
        "Primary module: VERIFY/SEC\n依賴: PD-BUILD-RESULT-01\n"
        "交付／AC: 腳本＋reports 範例；可掛 build_result。\n允許範圍: tools／scripts／reports。\n不做: 自動封鎖合併（可建議 CI 下一步）。",
    ),
    task(
        "PD-REGRESS-01",
        "VERIFY：回歸矩陣（smoke＋關鍵 crate 一鍵）",
        "BDD-PD-REGRESS-01：單一入口跑 smoke＋約定 crate／pytest 子集；輸出摘要；失敗非零退出。",
        "Primary module: VERIFY\n依賴: PD-SMOKE-01\n"
        "交付／AC: scripts/pd_regress.py（或等價）＋文件。\n允許範圍: scripts／tests／desktop crates 測試指令。\n不做: elevated MSI。",
    ),
    task(
        "PD-CARGO-WORKSPACE-01",
        "HOST：desktop Cargo workspace 根可 cargo test -p …",
        "BDD-PD-CARGO-WORKSPACE-01：自 apps/sgenaxis-desktop（或文件指定根）可 `cargo test -p sgenaxis-*`；缺 workspace 則補齊；文件路徑正確。",
        "Primary module: HOST\n依賴: PD-ADAPT-01\n"
        "交付／AC: workspace Cargo.toml 或 README 明確 manifest-path。\n允許範圍: apps/sgenaxis-desktop。\n不做: 改業務邏輯。",
    ),
    task(
        "PD-ELEV-VERIFY-01",
        "REL：elevated VERIFY-INSTALL（可選·決策後）",
        "BDD-PD-ELEV-VERIFY-01：在核准下以提升權限跑靜默裝／卸驗證；結果寫入 verify-install-result；不得偽造 PASS。",
        "Primary module: REL\n依賴: PD-REL-03、PD-DEC-ELEV-01（紅燈核准後才黃燈）\n"
        "交付／AC: 實跑或明確 BLOCKED／NOT RUN 原因。\n允許範圍: packaging/windows/wix。\n"
        "阻塞: 決策未准前保持灰燈。",
        milestone="Harden/optional",
    ),
    task(
        "PD-LIVE-CLI-SMOKE-01",
        "EXEC：真 CLI Live 冒煙（可選·決策後）",
        "BDD-PD-LIVE-CLI-SMOKE-01：在核准下對明示本機 CLI 做一次 Live start→chunk→exit 或明確跳過原因；秘密不進投影。",
        "Primary module: EXEC\n依賴: PD-EXEC-LIVE-01、PD-DEC-LIVE-CLI-01（紅燈核准後才黃燈）\n"
        "交付／AC: 測試或腳本＋報告；失敗分類。\n允許範圍: exec／adapters／tests。\n"
        "阻塞: 決策未准前保持灰燈。\n不做: 雲端任意閘道。",
        milestone="Harden/optional",
    ),
]

DECISIONS = [
    new_decision_card(
        "PD-DEC-ELEV-01",
        "決策：本批是否跑 elevated VERIFY-INSTALL",
        now=NOW,
        parent=PARENT,
        pending_items=[
            "DEC-1: 核准在本機以系統管理員跑靜默裝／卸？（需 UAC／admin）",
            "DEC-2: 若否，PD-ELEV-VERIFY-01 維持灰／標 NOT RUN 結案？",
            "影響: PD-ELEV-VERIFY-01；Build Result PARTIAL→可能升 PASS。",
            "建議: 若無簽章／發行壓力可先否，保持 PARTIAL。",
        ],
        note_prefix="里程碑: Harden\n承接已決 PD-DEC-V01-GATE-01（elevated 非硬閘）。",
        bdd="BDD-PD-DEC-ELEV-01：未批准前不得黃燈派 PD-ELEV-VERIFY-01。",
    ),
    new_decision_card(
        "PD-DEC-LIVE-CLI-01",
        "決策：本批是否做真 CLI Live 冒煙",
        now=NOW,
        parent=PARENT,
        pending_items=[
            "DEC-1: 核准對本機已安裝 Agent CLI 做 Live 冒煙？（非 DryRun）",
            "DEC-2: 目標 CLI 為何（claude／cursor-agent／codex／其他）？路徑？",
            "DEC-3: 若否，PD-LIVE-CLI-SMOKE-01 灰燈擱置或取消？",
            "影響: PD-LIVE-CLI-SMOKE-01。",
            "建議: 無穩定本機 CLI 則先否。",
        ],
        note_prefix="里程碑: Harden",
        bdd="BDD-PD-DEC-LIVE-CLI-01：未批准前不得黃燈派 PD-LIVE-CLI-SMOKE-01。",
    ),
    new_decision_card(
        "PD-DEC-HARDEN-GO-01",
        "決策：核准 v0.1 硬化批開工（非可選卡）",
        now=NOW,
        parent=PARENT,
        pending_items=[
            "DEC-1: 核准灰燈核心卡開工？PD-CI-01／CHANGELOG-01／README-APP-01／SEC-SCAN-01／REGRESS-01／CARGO-WORKSPACE-01",
            "DEC-2: 新 epic PRODUCT-HARDEN-20261024 範圍是否 OK（明確排除 M4）？",
            "影響: 上列 6 卡；不含 ELEV／LIVE（另紅燈）。",
        ],
        note_prefix="里程碑: Harden\n§7.3：決策清後才可黃燈派 subagent。",
        bdd="BDD-PD-DEC-HARDEN-GO-01：owner 核准前不得派核心硬化實作卡。",
    ),
]


def mutate(data):
    existing = {t["id"] for t in data.get("tasks") or []}
    added = []
    for c in [EPIC] + TASKS + DECISIONS:
        if c["id"] in existing:
            print("skip", c["id"])
            continue
        data["tasks"].append(c)
        added.append(c["id"])
        print("add", c["id"])

    # note on old epic
    for t in data.get("tasks") or []:
        if t.get("id") != "PRODUCT-DEV-20261023":
            continue
        t["note"] = (t.get("note") or "").rstrip() + (
            f"\n[{NOW}] 下一批已開新 epic {PARENT}（v0.1 硬化；非 M4）。詳該 epic／紅燈決策。"
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
    text = BOARD.read_text(encoding="utf-8")
    assert text.lstrip().lower().startswith("<!doctype")
    print("OK")


if __name__ == "__main__":
    main()
