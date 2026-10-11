"""Report command (CLI channel, INV-BD-43): writes the run's report file, first report wins."""

import json
import os
import subprocess
import sys
from datetime import datetime

from sgenaxis.adapters.json_board import FileProjectBoards
from sgenaxis.core import dispatch
from sgenaxis.core.board import WorkItem
from sgenaxis.core.dispatcher import Dispatcher
from sgenaxis.core.in_memory import DryRunLauncher, ManualClock
from sgenaxis.report_cli import report_main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T0 = "2026-10-10T09:00:00+08:00"


def _card(item_id: str = "R1") -> WorkItem:
    return WorkItem(
        item_id=item_id, code=item_id, title="標題", zone="red", source="manual", files=(), bdd="", tdd="",
        created=T0, note="", updated=T0, updated_by="agent",
    )


def test_report_command_writes_a_cli_report_file(tmp_path):
    path = tmp_path / "RUN-1.json"
    code = report_main(["--card", "R1", "--run", "RUN-1", "--file", str(path), "--outcome", "done", "--note", "修好\n了"], env={})
    assert code == 0
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "card": "R1", "run": "RUN-1", "outcome": "done", "note": "修好 了", "via": "cli",
    }
    assert [name.name for name in tmp_path.iterdir()] == ["RUN-1.json"]


def test_report_command_takes_card_run_and_file_from_the_environment(tmp_path):
    path = tmp_path / "RUN-2.json"
    env = {"HB_DISPATCH_CARD": "R2", "HB_DISPATCH_RUN_ID": "RUN-2", "HB_DISPATCH_REPORT_FILE": str(path)}
    assert report_main(["--outcome", "blocked", "--note", "缺規格"], env=env) == 0
    assert json.loads(path.read_text(encoding="utf-8"))["outcome"] == "blocked"


def test_report_command_never_overwrites_the_first_report(tmp_path, capsys):
    path = tmp_path / "RUN-1.json"
    path.write_bytes(b'{"first": true}')
    code = report_main(["--card", "R1", "--run", "RUN-1", "--file", str(path), "--outcome", "done"], env={})
    assert code == 1
    assert path.read_bytes() == b'{"first": true}'
    assert "第一個回報才算數" in capsys.readouterr().err


def test_report_command_rejects_missing_values_and_bad_outcomes(tmp_path):
    assert report_main(["--outcome", "done"], env={}) == 2
    assert report_main(["--card", "R1", "--run", "X", "--file", str(tmp_path / "x.json"), "--outcome", "maybe"], env={}) == 2
    assert report_main(["--card", "R1", "--run", "X", "--file", str(tmp_path / "no" / "x.json"), "--outcome", "done"], env={}) == 1


def test_running_workbench_records_the_cli_channel(tmp_path):
    project = FileProjectBoards().create(str(tmp_path / "P"))
    project.store.create(_card())
    dispatcher = Dispatcher(
        project.store, ManualClock(datetime(2026, 10, 11, 9, 0)), DryRunLauncher(),
        inbox=project.inbox, state=project.state, report_grace_seconds=0, report_command="python sgenaxis_report.py",
    )
    lane = dispatcher.add_lane("claude")
    dispatcher.start_lane(lane.lane_id)
    run = lane.current
    assert f"--card R1 --run {run.run_id}" in run.prompt
    report_file = project.inbox.path(run.run_id)
    assert report_main(["--file", report_file, "--outcome", "done", "--note", "ok"],
                       env={"HB_DISPATCH_CARD": "R1", "HB_DISPATCH_RUN_ID": run.run_id}) == 0
    dispatcher.tick()
    assert project.store.get("R1").zone == "green"
    assert dispatcher.history[0].channel == "cli"
    assert os.path.isfile(os.path.join(str(tmp_path / "P"), ".sgenaxis", "reports", "processed", f"{run.run_id}.json"))


def test_prompt_without_a_report_command_has_no_option_c():
    prompt = dispatch.build_prompt(_card(), "RUN-1", r"D:\P", report_file=r"D:\P\x.json")
    assert "C. " not in prompt


def test_report_script_runs_from_another_folder_without_qt(tmp_path):
    path = tmp_path / "RUN-9.json"
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "sgenaxis_report.py"), "--card", "R9", "--run", "RUN-9",
         "--file", str(path), "--outcome", "done", "--note", "ok"],
        cwd=str(tmp_path), capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(path.read_text(encoding="utf-8"))["via"] == "cli"
    probe = subprocess.run(
        [sys.executable, "-c", "import sys, runpy; sys.argv=['x','--help']; "
         f"sys.path.insert(0, {ROOT!r}); import sgenaxis.report_cli; print('PySide6' in sys.modules)"],
        capture_output=True, text=True, timeout=60,
    )
    assert probe.stdout.strip() == "False"
