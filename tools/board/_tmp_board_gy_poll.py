"""Poll gray/yellow cards; always surface actionable work (not only fingerprint deltas).

Usage:
  python tools/board/_tmp_board_gy_poll.py           # scan only
  python tools/board/_tmp_board_gy_poll.py --dispatch # also write recommended dispatch JSON
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_core import snapshot_safe  # noqa: E402

STATE = Path("tools/board/_tmp_gy_poll_state.json")
SKIP_KINDS = {"decision", "epic"}
DEP_RE = re.compile(r"(?im)^\s*Dependencies:\s*(.+)$")


def now() -> str:
    s = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    if len(s) >= 5 and s[-5] in "+-" and s[-3] != ":":
        s = s[:-2] + ":" + s[-2:]
    return s


def dep_ids(note: str) -> set[str]:
    found: set[str] = set()
    for m in DEP_RE.finditer(note or ""):
        for part in re.split(r"[,;，、]", m.group(1)):
            tok = part.strip().rstrip(".")
            if tok.startswith("PD-"):
                # trim trailing junk after id
                tok = tok.split()[0].strip()
                found.add(tok)
    return found


def main() -> None:
    html = (ROOT / "docs" / "PROJECT-BOARD.html").read_text(encoding="utf-8")
    data = snapshot_safe.load_snapshot_dict(html)
    tasks = data.get("tasks") or []
    by_id = {t.get("id"): t for t in tasks}
    red_dec = {
        t.get("id")
        for t in tasks
        if (t.get("zone") or "").lower() == "red" and (t.get("kind") or "") == "decision"
    }
    gy = []
    for t in tasks:
        z = (t.get("zone") or "").lower()
        if z not in ("gray", "yellow"):
            continue
        kind = (t.get("kind") or "task").lower()
        note = str(t.get("note") or "")
        deps = dep_ids(note)
        dec_hits = sorted(deps & red_dec)
        # Owner 2026-10-26: open red DECs do NOT skip gray/yellow task work
        # (still dispatch PLANNING_ONLY packets). Only decision/epic kinds skip.
        blocked = kind in SKIP_KINDS
        planning_only = (
            "PLANNING_ONLY" in note or "NOT_READY_FOR_IMPLEMENTATION" in note
        )
        # Only treat as handoff-ready when a log line reports status, not when
        # dispatch instructions merely mention the token (e.g. "含 READY_FOR_TDD").
        tail = note[-1600:]
        ready_tdd = bool(
            re.search(
                r"(?m)^(?:\[.*?\]\s*(?:Status:\s*)?|\*\*Status:\s*|Status:\s*)"
                r"(READY_FOR_TDD|READY_FOR_GREEN)\b",
                tail,
            )
        ) or bool(
            re.search(
                r"(?m)^\[.*?\]\s*.*\b(READY_FOR_TDD|READY_FOR_GREEN)\s*"
                r"(yellow|→|->|handoff)",
                tail,
            )
        )
        gy.append(
            {
                "id": t.get("id"),
                "zone": z,
                "kind": kind,
                "title": t.get("title"),
                "blocked": blocked,
                "block_decs": dec_hits,
                "dec_open_note": bool(dec_hits),
                "planning_only": planning_only,
                "ready_tdd": ready_tdd,
                "deps": sorted(deps),
            }
        )
    gy.sort(key=lambda r: (r["zone"], r["id"] or ""))
    fp = {r["id"]: f"{r['zone']}|{r['kind']}" for r in gy}

    prev = {}
    if STATE.is_file():
        try:
            prev = json.loads(STATE.read_text(encoding="utf-8")).get("fp") or {}
        except Exception:
            prev = {}

    new_ids = [i for i in fp if i not in prev]
    changed = [i for i in fp if i in prev and prev[i] != fp[i]]
    removed = [i for i in prev if i not in fp]

    dispatchable = [r for r in gy if not r["blocked"] and r["kind"] not in SKIP_KINDS]
    need_start = [r for r in dispatchable if r["zone"] == "gray"]
    need_tdd = [r for r in dispatchable if r["zone"] == "yellow" and r["ready_tdd"]]
    in_progress = [r for r in dispatchable if r["zone"] == "yellow" and not r["ready_tdd"]]
    # Owner rule: GY work is actionable every tick even if fingerprint unchanged.
    action_required = bool(need_start or need_tdd or in_progress)

    print(f"[{now()}] gray+yellow={len(gy)} red_decisions={len(red_dec)}")
    print(f"  new={new_ids}")
    print(f"  changed={changed}")
    print(f"  removed={removed}")
    print(f"  action_required={action_required} (ignore empty new/changed)")
    print(f"  need_start_gray={ [r['id'] for r in need_start] }")
    print(f"  need_tdd_handoff={ [r['id'] for r in need_tdd] }")
    print(f"  yellow_in_progress={ [r['id'] for r in in_progress] }")
    print(f"  dispatchable_unblocked={ [r['id'] for r in dispatchable] }")
    for r in gy:
        flag = "SKIP" if r["blocked"] else "OK"
        extra = ""
        if r.get("block_decs"):
            extra += f" open_dec={r['block_decs']}"
        if r.get("planning_only"):
            extra += " PLANNING"
        if r.get("ready_tdd"):
            extra += " READY_TDD"
        print(f"  [{r['zone']}] {r['id']} ({r['kind']}) {flag}{extra} — {(r['title'] or '')[:50]}")

    STATE.write_text(
        json.dumps(
            {
                "t": now(),
                "fp": fp,
                "dispatchable": dispatchable,
                "need_start": need_start,
                "need_tdd": need_tdd,
                "in_progress": in_progress,
                "action_required": action_required,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if "--dispatch" in sys.argv:
        out = {
            "action_required": action_required,
            "new": new_ids,
            "changed": changed,
            "need_start": need_start,
            "need_tdd": need_tdd,
            "in_progress": in_progress,
            "dispatchable": dispatchable,
            "red_decisions": sorted(red_dec),
        }
        Path("tools/board/_tmp_gy_poll_dispatch.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("wrote tools/board/_tmp_gy_poll_dispatch.json")


if __name__ == "__main__":
    main()
