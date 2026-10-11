"""Real-launch smoke test: one card, one lane, one real agent CLI, in the sandbox project only.

    python tools/real_agent_smoke.py claude|cursor-agent|codex [--timeout-minutes 10]

Uses the same Dispatcher, ProcessLauncher and board files as the workbench. The card asks the
agent to create one file in the sandbox and report done; the script prints the run's outcome,
the card afterwards, and the tail of the agent output.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sgenaxis.adapters.json_board import FileProjectBoards  # noqa: E402  (needs ROOT on sys.path)
from sgenaxis.adapters.process_launcher import ProcessLauncher  # noqa: E402
from sgenaxis.adapters.system_clock import SystemClock  # noqa: E402
from sgenaxis.core import timefmt  # noqa: E402
from sgenaxis.core.board import WorkItem  # noqa: E402
from sgenaxis.core.dispatch import AGENTS  # noqa: E402
from sgenaxis.core.dispatcher import Dispatcher  # noqa: E402

SANDBOX = os.path.join(ROOT, "_sandbox", "agent-test")
REPORT_COMMAND = f'python "{os.path.join(ROOT, "sgenaxis_report.py")}"'


def _card(agent: str, now: str) -> WorkItem:
    card_id = f"SMOKE-{agent.upper()}"
    return WorkItem(
        card_id,
        card_id,
        f"{agent} 實測：建立 smoke-{agent}.txt",
        "red",
        "manual",
        (f"smoke-{agent}.txt",),
        "檔案存在且內容正確",
        "—",
        now,
        f"在工作目錄建立 UTF-8 檔案 smoke-{agent}.txt，內容只有一行：hello from {agent}。"
        "不要改其他檔案。完成後依 prompt 的回報方式回報 done。",
        kind="task",
        updated=now,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("agent", choices=[name for name in AGENTS if not AGENTS[name].detached])
    parser.add_argument("--timeout-minutes", type=int, default=10)
    args = parser.parse_args()

    boards = FileProjectBoards()
    board = boards.create(SANDBOX)
    clock = SystemClock()
    card = _card(args.agent, timefmt.stamp(clock.now()))
    existing = board.store.get(card.item_id)
    if existing is not None:
        board.store.delete(card.item_id, existing.version)
    board.store.create(card)

    dispatcher = Dispatcher(
        board.store,
        clock,
        ProcessLauncher(),
        inbox=board.inbox,
        state=board.state,
        repo=SANDBOX,
        logs_dir=board.logs_dir,
        report_command=REPORT_COMMAND,
        timeout_minutes=args.timeout_minutes,
        default_agent=args.agent,
    )
    dispatcher.skipped.pop(card.item_id, None)
    lane = dispatcher.lanes[0] if dispatcher.lanes else dispatcher.add_lane(args.agent)
    dispatcher.configure_lane(lane.lane_id, args.agent, 1)
    started = time.monotonic()
    dispatcher.start_lane(lane.lane_id, started_by="smoke")
    run_id = lane.current.run_id if lane.current else "(not started)"
    print(f"started {args.agent} run {run_id}", flush=True)
    while lane.active:
        time.sleep(1.0)
        dispatcher.tick()
    elapsed = time.monotonic() - started

    entry = next((item for item in reversed(dispatcher.history) if item.run_id == run_id), None)
    after = board.store.get(card.item_id)
    target = os.path.join(SANDBOX, f"smoke-{args.agent}.txt")
    print(f"elapsed: {elapsed:.0f}s  lane: {lane.state} {lane.stop_reason} {lane.error}")
    if entry is not None:
        print(f"outcome: {entry.outcome}  channel: {entry.channel or '-'}  note: {entry.note}")
    print(f"card: zone={after.zone}  note tail: {after.note.splitlines()[-1] if after.note else ''}")
    if os.path.isfile(target):
        with open(target, encoding="utf-8") as handle:
            print(f"file: {target} -> {handle.read().strip()!r}")
    else:
        print(f"file: {target} missing")
    print("── output tail ──")
    print((entry.output if entry is not None else "")[-1500:])
    return 0 if entry is not None and entry.outcome == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
