"""Report command for dispatched agents (spec-BOARD-DISPATCH-01 §3.11, the CLI channel).

    python <SGenAxis>\\sgenaxis_report.py --outcome done --note "..." [--card ID] [--run RUN] [--file PATH]

It writes the run's report file with via="cli"; the running workbench picks it up on its
next tick, or on restart. Card, run and file default to HB_DISPATCH_CARD, HB_DISPATCH_RUN_ID
and HB_DISPATCH_REPORT_FILE. An existing report file is never overwritten: the first report wins.
Standard library and core only, so it runs under any Python 3.10+ without PySide6.

Exit codes: 0 written, 1 refused or I/O error, 2 bad arguments.
"""

from __future__ import annotations

import argparse
import os
import sys

from sgenaxis.core import report_channels

ENV_CARD = "HB_DISPATCH_CARD"
ENV_RUN = "HB_DISPATCH_RUN_ID"
ENV_FILE = "HB_DISPATCH_REPORT_FILE"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sgenaxis report", description="回報一張派工卡的結果（done 或 blocked）。")
    parser.add_argument("--outcome", required=True, choices=report_channels.OUTCOMES)
    parser.add_argument("--note", default="", help="一行說明")
    parser.add_argument("--card", default=None, help=f"卡號（預設 {ENV_CARD}）")
    parser.add_argument("--run", default=None, help=f"派工編號（預設 {ENV_RUN}）")
    parser.add_argument("--file", default=None, help=f"回報檔路徑（預設 {ENV_FILE}）")
    return parser


def write_report(path: str, raw: bytes) -> None:
    """Create `path` atomically and only if absent (hard link of a finished temp file)."""
    folder = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"回報資料夾不存在：{folder}")
    if os.path.exists(path):
        raise FileExistsError(f"已經有回報檔，第一個回報才算數：{path}")
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(tmp, path)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def report_main(argv: list[str] | None = None, env: dict[str, str] | None = None) -> int:
    env = os.environ if env is None else env
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    card = args.card or env.get(ENV_CARD, "")
    run = args.run or env.get(ENV_RUN, "")
    path = args.file or env.get(ENV_FILE, "")
    missing = [name for name, value in (("--card", card), ("--run", run), ("--file", path)) if not value]
    if missing:
        print(f"缺少 {'、'.join(missing)}（也可由環境變數帶入）", file=sys.stderr)
        return 2
    try:
        raw = report_channels.encode_report(card, run, args.outcome, args.note, via="cli")
        write_report(path, raw)
    except (report_channels.ReportInvalid, OSError) as exc:
        print(f"未回報：{exc}", file=sys.stderr)
        return 1
    print(f"已回報 {card} {args.outcome}（{run}）→ {path}")
    return 0
