"""PM auto next-round: handoff completed yellow→red TDD; yellow-dispatch ready gray/yellow work."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe  # noqa: E402
from board_core.json_store import FileLock  # noqa: E402

NOW = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
if len(NOW) >= 5 and NOW[-5] in "+-" and NOW[-3] != ":":
    NOW = NOW[:-2] + ":" + NOW[-2:]

# Completed proposal / READY_FOR_GREEN → red TDD handoff
HANDOFF_RED = [
    "PD-RUST-FS-PLAN-02",
    "PD-RUST-XML-PACKET-ARCH-01",
    "PD-RUST-DISPATCH-MODES-PLAN-01",
    "PD-RUST-REPORT-INGRESS-PLAN-01",
]

# Start implement/plan work (not blocked by open red decision ids in deps)
DISPATCH_YELLOW = [
    "PD-RUST-EMBEDDED-AGENT-PLAN-01",
    "PD-RUST-NATIVE-UI-VERIFY-01",
    "PD-RUST-MODULE-HTML-01",
    "PD-RUST-SYSTEM-REGRESSION-01",
]

HANDOFF_NOTE = (
    f"[{NOW}] 自動輪次：完成卡→紅燈交付 TDD。"
    "寫 reports/dispatch-pd/<ID>-TDD-REVIEW.md；禁止自改綠。"
)
DISPATCH_NOTE = (
    f"[{NOW}] 自動輪次：黃燈開工分派 subagent。"
    "完成後 reports/dispatch-pd/<ID>.md 含 READY_FOR_TDD；母對話改紅交 TDD。"
    "禁止自改綠／讀整板。"
)


def mut(data: dict) -> dict:
    by = {t.get("id"): t for t in (data.get("tasks") or [])}
    moved, yellowed = [], []
    for tid in HANDOFF_RED:
        t = by.get(tid)
        if not t or (t.get("kind") or "") == "decision":
            continue
        t["zone"] = "red"
        t["note"] = (t.get("note") or "").rstrip() + "\n" + HANDOFF_NOTE
        t.setdefault("log", []).append(
            {"t": NOW, "zone": "red", "by": "parent-pm", "note": "auto handoff TDD"}
        )
        moved.append(tid)
    for tid in DISPATCH_YELLOW:
        t = by.get(tid)
        if not t or (t.get("kind") or "") == "decision":
            continue
        t["zone"] = "yellow"
        t["startedAt"] = t.get("startedAt") or NOW
        t["note"] = (t.get("note") or "").rstrip() + "\n" + DISPATCH_NOTE
        t.setdefault("log", []).append(
            {"t": NOW, "zone": "yellow", "by": "parent-pm", "note": "auto dispatch"}
        )
        yellowed.append(tid)
    epic = by.get("PD-RUST-IMPROVE-20261025")
    if epic is not None:
        epic["note"] = (
            (epic.get("note") or "").rstrip()
            + f"\n[{NOW}] 自動輪次：handoff-red={moved}; dispatch-yellow={yellowed}。"
            "仍阻塞於開紅 decision：EXEC/DISPATCH-MODES/GUARD/DOCUMENT/UI-OWNERSHIP/"
            "MCP-TRANSPORT/EMBEDDED-AGENT/MCP-NOTRUN-ACCEPT。"
        )
    print("handoff_red", moved)
    print("dispatch_yellow", yellowed)
    return data


def main() -> None:
    path = ROOT / "docs" / "PROJECT-BOARD.html"
    snapshot_safe.mutate_snapshot_file(path, mut, lock_factory=FileLock)
    # excerpts
    html = path.read_text(encoding="utf-8")
    data = snapshot_safe.load_snapshot_dict(html)
    out = Path("tools/board/_tmp_card_excerpts")
    out.mkdir(exist_ok=True)
    ids = HANDOFF_RED + DISPATCH_YELLOW
    by = {t.get("id"): t for t in (data.get("tasks") or [])}
    for tid in ids:
        t = by.get(tid)
        if not t:
            continue
        (out / f"{tid}.json").write_text(
            json.dumps(
                {k: t.get(k) for k in ("id", "ref", "title", "kind", "zone", "bdd", "tdd", "note")},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    print("OK")


if __name__ == "__main__":
    main()
