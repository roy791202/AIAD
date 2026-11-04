"""PM: move completed yellow cards → red for Codex TDD handoff; yellow remaining impl."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe  # noqa: E402

NOW = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
# insert colon in tz: +0800 -> +08:00 if needed
if len(NOW) >= 5 and NOW[-5] in "+-" and NOW[-3] != ":":
    NOW = NOW[:-2] + ":" + NOW[-2:]

# Completed implementable / verification cards → red handoff for Codex TDD
HANDOFF_RED = [
    "PD-RUST-BASELINE-TEST-01",
    "PD-RUST-BASELINE-CI-01",
    "PD-RUST-XML-PACKET-SKELETON-01",
    "PD-RUST-XML-PACKET-RED-01",
    "PD-RUST-XML-PACKET-IMPL-01",
    "PD-RUST-MCP-NOTRUN-ARCH-01",
    "PD-RUST-MCP-NOTRUN-TDD-01",
    "PD-RUST-MCP-NOTRUN-REVIEW-01",
    "PD-RUST-FS-IMPL-01",
    "PD-RUST-FS-TDD-01",
    "PD-RUST-PROC-IMPL-01",
    "PD-RUST-PROC-TDD-01",
    "PD-RUST-PROC-REVIEW-01",
    "PD-RUST-UI-ACTIVE-RUN-01",
    "PD-RUST-DOCUMENT-CONTRACT-01",
]

# Still need implementer / planner work
DISPATCH_YELLOW = [
    "PD-RUST-WIP-AUDIT-01",
    "PD-RUST-PROC-PLAN-02",
]

HANDOFF_NOTE = (
    f"[{NOW}] 交付 TDD Codex 審查（母對話 PM）。"
    "狀態: zone=red（交付佇列，非 decision）。"
    "請獨立 Codex TDD Agent 親跑／核對測試，寫 reports/dispatch-pd/<ID>-TDD-REVIEW.md，"
    "回報 TDD_PASS／TDD_FAIL。§7.1 禁止自改綠；綠燈僅母對話在 TDD_PASS 後滅。"
)

DISPATCH_NOTE = (
    f"[{NOW}] 黃燈開工：分派實作 subagent（母對話 PM）。"
    "完成後寫 reports/dispatch-pd/<ID>.md 含 READY_FOR_TDD，"
    "母對話改 zone=red 交付 Codex TDD。禁止自改綠／讀整板。"
)


def mutate(data: dict[str, Any]) -> dict[str, Any]:
    tasks = data.get("tasks") or data.get("cards") or []
    by_id = {t.get("id"): t for t in tasks}
    moved, yellowed = [], []

    for tid in HANDOFF_RED:
        t = by_id.get(tid)
        if not t:
            continue
        if (t.get("kind") or "") == "decision":
            continue
        prev = t.get("zone")
        t["zone"] = "red"
        note = (t.get("note") or "").rstrip() + "\n" + HANDOFF_NOTE
        t["note"] = note
        log = t.get("log") or []
        log.append({"t": NOW, "zone": "red", "by": "parent-pm", "note": "handoff Codex TDD"})
        t["log"] = log
        moved.append(f"{tid}({prev}->red)")

    for tid in DISPATCH_YELLOW:
        t = by_id.get(tid)
        if not t:
            continue
        if (t.get("kind") or "") == "decision":
            continue
        t["zone"] = "yellow"
        t["startedAt"] = t.get("startedAt") or NOW
        note = (t.get("note") or "").rstrip() + "\n" + DISPATCH_NOTE
        t["note"] = note
        log = t.get("log") or []
        log.append({"t": NOW, "zone": "yellow", "by": "parent-pm", "note": "dispatch implementer"})
        t["log"] = log
        yellowed.append(tid)

    epic = by_id.get("PD-RUST-IMPROVE-20261025")
    if epic is not None:
        epic["note"] = (
            (epic.get("note") or "").rstrip()
            + f"\n[{NOW}] PM 分派：完成卡→紅燈交付 Codex TDD：{', '.join(HANDOFF_RED)}；"
            f"黃燈開工：{', '.join(DISPATCH_YELLOW)}。"
            "開紅 decision 仍阻塞依賴卡；不自動綠燈。"
        )

    print("moved_red:", ", ".join(moved))
    print("yellow_dispatch:", ", ".join(yellowed))
    return data


def main() -> None:
    path = ROOT / "docs" / "PROJECT-BOARD.html"
    snapshot_safe.mutate_snapshot_file(path, mutate)
    print("OK")


if __name__ == "__main__":
    main()
