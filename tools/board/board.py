#!/usr/bin/env python3
"""board.py — VGenAxIs board CLI for dispatched agents (BOARD-DISPATCH-01).

  board.py report <id> done|blocked [--note N] [--run RUN_ID]

Writes by=agent into docs/PROJECT-BOARD.html #board-snapshot.
--tasks / --dispatch-state default to $HB_BOARD_TASKS / $HB_BOARD_DISPATCH_STATE.
Exit: 0 ok, 1 rejected, 2 internal.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BOARD_DIR = Path(__file__).resolve().parent
REPO = BOARD_DIR.parents[1]
DOCS = REPO / "docs"
if str(BOARD_DIR) not in sys.path:
    sys.path.insert(0, str(BOARD_DIR))
if str(DOCS) not in sys.path:
    sys.path.insert(0, str(DOCS))

import board_watch  # noqa: E402
from board_core import ports, usecases  # noqa: E402
from board_core.dispatch import REPORT_OUTCOMES  # noqa: E402
from board_core.dispatch_store import DispatchStateStore  # noqa: E402
from board_core.domain import DomainError  # noqa: E402

DEFAULT_TASKS = str(DOCS / "PROJECT-BOARD.html")
DEFAULT_DISPATCH_STATE = str(BOARD_DIR / "runtime" / "dispatch.json")
REJECTED = (
    ports.VersionConflict,
    ports.NotFound,
    ports.AlreadyExists,
    ports.LockTimeout,
    ports.StoreCorrupt,
    DomainError,
    board_watch.BoardError,
    board_watch.snapshot_safe.ShellCorruptError,
    board_watch.snapshot_safe.FullOverwriteRejected,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", default=os.environ.get("HB_BOARD_TASKS") or DEFAULT_TASKS)
    ap.add_argument(
        "--dispatch-state",
        default=os.environ.get("HB_BOARD_DISPATCH_STATE") or DEFAULT_DISPATCH_STATE,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("id")
    r.add_argument("outcome", choices=REPORT_OUTCOMES)
    r.add_argument("--note", default="")
    r.add_argument("--run")
    return ap


def run(args) -> None:
    store = board_watch.HtmlSnapshotStore(Path(args.tasks))
    ts = now_iso()
    task = usecases.report_outcome(store, args.id, args.outcome, args.note, by="agent", now=ts)
    print("reported %s %s -> %s (v%d)" % (task["id"], args.outcome, task["zone"], task["version"]))
    if usecases.record_dispatch_report(
        DispatchStateStore(args.dispatch_state), args.id, args.run, args.outcome, args.note, ts
    ):
        print("dispatch run notified")
    else:
        print("note: no matching dispatch run (card updated only)")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run(args)
        return 0
    except REJECTED as exc:
        print("rejected: %s" % exc, file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print("internal error: %r" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
