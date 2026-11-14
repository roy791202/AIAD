# -*- coding: utf-8 -*-
"""補派工：Arch DAG 殼＋PDF 10 類節點（§7.3 snapshot_safe）。

工作已於對話落地；本腳本建 epic／已決決策／實作卡（黃→綠需 TDD_PASS 後由母對話滅燈）。
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from board_core import snapshot_safe

BOARD = ROOT / "docs" / "PROJECT-BOARD.html"
PARENT = "PRODUCT-ARCH-DAG-20261024"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
COLLAB = (
    "協作：實作子代理以本卡 BDD 為開發指標；§7.1 不可自改綠；§7.2 只讀本卡／reports/dispatch-pd/<ID>.md／允許路徑。\n"
    "看板寫入：禁止整檔覆寫 HTML 殼；只改 #board-snapshot（snapshot_safe／board.py report）。"
)

ALLOW = (
    "允許: apps/sgenaxis-desktop/ui、apps/sgenaxis-desktop/src-tauri/permissions、"
    "tests/test_pd_arch_dag_shell_01.py、tests/test_pd_remain_arch_ui_01_chrome.py、"
    "reports/dispatch-pd、docs/節點類型定義整理.pdf（唯讀）。\n"
    "保護: 不改 UI Designer Form 語意；不靜態假圖冒充 live。"
)


def task(id_, title, bdd, tdd, note, *, zone="yellow"):
    return {
        "id": id_,
        "ref": id_,
        "title": title,
        "zone": zone,
        "kind": "task",
        "createdAt": NOW,
        "doneAt": None,
        "startedAt": NOW if zone == "yellow" else None,
        "by": "parent-pm",
        "updatedAt": NOW,
        "updatedBy": "parent-pm",
        "bdd": bdd,
        "tdd": tdd,
        "note": (
            f"母工項: {PARENT}\n里程碑: Arch-DAG\n{ALLOW}\n{note.rstrip()}\n{COLLAB}\n"
            f"[{NOW}] 補派工：對話已落地→黃燈待 TDD Gate。"
        ),
        "log": [
            {"t": NOW, "zone": "gray", "by": "parent-pm"},
            {"t": NOW, "zone": zone, "by": "parent-pm"},
        ],
        "version": 1,
    }


CARDS = [
    {
        "id": PARENT,
        "ref": PARENT,
        "kind": "epic",
        "zone": "yellow",
        "title": "模組架構圖：產品殼嵌節點 DAG＋PDF 10 類 Node",
        "bdd": (
            "BDD-ARCH-DAG-EPIC：#panel-arch 為節點 DAG（收合／左 in 右 out）；"
            "kind∈PDF 01–10；草稿常駐；arch_get_projection 僅 live 疊加；禁假 live。"
        ),
        "tdd": "子卡 TDD_PASS 後滅燈。",
        "note": (
            "Primary: UI/ARCH\n"
            "SSOT: docs/節點類型定義整理.pdf\n"
            "承接: PD-REMAIN-ARCH-UI-01（列表投影）→ 本 epic 升級為 DAG 工作區。\n"
            "不做: Workbench HTML 全量同步；UI Designer 改節點圖；Schema Registry／Validation Engine 全量（後續卡）。\n"
            f"[{NOW}] 補派工建 epic＋決策（已決）＋三實作卡黃燈。\n"
            f"本批已建卡: PD-DEC-ARCH-KINDS-01（綠已決）、"
            f"PD-ARCH-DAG-SHELL-01、PD-ARCH-NODE-IO-01、PD-ARCH-ACL-LIVE-01（黃）。"
        ),
        "createdAt": NOW,
        "updatedAt": NOW,
        "updatedBy": "parent-pm",
        "startedAt": NOW,
        "doneAt": None,
        "by": "parent-pm",
        "log": [
            {"t": NOW, "zone": "gray", "by": "parent-pm"},
            {"t": NOW, "zone": "yellow", "by": "parent-pm"},
        ],
        "version": 1,
    },
    {
        "id": "PD-DEC-ARCH-KINDS-01",
        "ref": "PD-DEC-ARCH-KINDS-01",
        "kind": "decision",
        "zone": "green",
        "title": "決策：Node 類別 SSOT＝節點類型定義整理.pdf（10 類）",
        "bdd": "BDD-DEC-ARCH-KINDS：核准 10 類順序 API→…→Custom；型別先於連線；規格／驗證／執行分離。",
        "tdd": "N/A（文件決策）",
        "note": (
            f"母工項: {PARENT}\n"
            "待決策事項:\n"
            "- [x] DEC-1: SSOT 是否採 docs/節點類型定義整理.pdf？\n"
            "- [x] DEC-2: 類別名 Api→API？\n"
            "- [x] DEC-3: 產品殼 #panel-arch 嵌 DAG（非僅 Workbench）？\n"
            f"[{NOW}] 已決: 全是（owner 提供 PDF＋確認嵌產品殼）。zone=green；不阻塞實作卡。"
        ),
        "createdAt": NOW,
        "updatedAt": NOW,
        "updatedBy": "parent-pm",
        "startedAt": NOW,
        "doneAt": NOW,
        "by": "parent-pm",
        "log": [
            {"t": NOW, "zone": "red", "by": "parent-pm"},
            {"t": NOW, "zone": "green", "by": "parent-pm"},
        ],
        "version": 1,
    },
    task(
        "PD-ARCH-DAG-SHELL-01",
        "UI：#panel-arch 嵌 DAG 畫布（量尺／Grid／版面／SVG 邊／拖曳）",
        "BDD-PD-ARCH-DAG-SHELL-01：#archStage／#archEdgesSvg／#archNodes；編輯草稿；適合視窗／縮放；"
        "Grid／版面可調；收合＝一條線；展開左 in／右 out；草稿常駐。",
        "tests/test_pd_arch_dag_shell_01.py（canvas／collapse／ports）",
        "交付: index.html panel-arch＋app.js wireArchUi／renderArchDag＋styles。\n"
        "證據: reports/dispatch-pd/PD-ARCH-DAG-SHELL-01.md",
    ),
    task(
        "PD-ARCH-NODE-IO-01",
        "ARCH：嚴格 10 類 Node＋預設 I/O 埠（對齊 PDF）＋Inspector",
        "BDD-PD-ARCH-NODE-IO-01：ARCH_NODE_KINDS＝API|Contract|UI|Command|Query|Application|"
        "Domain|Infrastructure|ACL|Custom；拒絕枚舉外 kind；ARCH_KIND_IO 預設埠；#inspector-arch。",
        "tests/test_pd_arch_dag_shell_01.py::test_strict_arch_node_kinds",
        "SSOT: docs/節點類型定義整理.pdf\n"
        "證據: reports/dispatch-pd/PD-ARCH-NODE-IO-01.md",
    ),
    task(
        "PD-ARCH-ACL-LIVE-01",
        "HOST/UI：arch_get_projection ACL＋live 疊加不冒充",
        "BDD-PD-ARCH-ACL-LIVE-01：allow-arch-get-projection 進 dispatch-default；"
        "僅 live=true 標 live；失敗／無 IPC 草稿仍可用；禁靜態假圖冒充即時圖。",
        "tests/test_pd_arch_dag_shell_01.py::test_arch_get_projection_acl＋"
        "test_no_fake_live；tests/test_pd_remain_arch_ui_01_chrome.py",
        "允許另含: apps/sgenaxis-desktop/src-tauri/permissions/dispatch.toml\n"
        "證據: reports/dispatch-pd/PD-ARCH-ACL-LIVE-01.md",
    ),
]


def mutate(data):
    existing = {t["id"] for t in data.get("tasks") or []}
    added = []
    for c in CARDS:
        if c["id"] in existing:
            print("skip", c["id"])
            continue
        data.setdefault("tasks", []).append(c)
        added.append(c["id"])
        print("add", c["id"], c["zone"])

    for t in data.get("tasks") or []:
        if t.get("id") == "PD-REMAIN-ARCH-UI-01":
            t["note"] = (t.get("note") or "").rstrip() + (
                f"\n[{NOW}] 後續升級見 {PARENT}（DAG 工作區；本卡列表投影仍有效）。"
            )
            t["updatedAt"] = NOW
            t["updatedBy"] = "parent-pm"
            t["version"] = int(t.get("version") or 1) + 1
            break

    data["asOf"] = NOW
    if data.get("overall") == "PASS":
        data["overall"] = "PARTIAL"
    print("added", len(added))
    return added


def main():
    snapshot_safe.mutate_snapshot_file(BOARD, mutate)
    text = BOARD.read_text(encoding="utf-8")
    assert text.lstrip().lower().startswith("<!doctype")
    for cid in (
        PARENT,
        "PD-DEC-ARCH-KINDS-01",
        "PD-ARCH-DAG-SHELL-01",
        "PD-ARCH-NODE-IO-01",
        "PD-ARCH-ACL-LIVE-01",
    ):
        assert cid in text, cid
    print("OK")


if __name__ == "__main__":
    main()
