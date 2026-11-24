"""PD-BOARD-GAPS-POLL-01: poll_next_work.py reads docs/board.json read-only (AC-B1..B6)."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
POLL = REPO / "tools" / "board" / "poll_next_work.py"
EXTINGUISH = REPO / "tools" / "board" / "poll_extinguish.py"
REAL_BOARD = REPO / "docs" / "board.json"

EXIT_OK = 0
EXIT_BOARD_UNREADABLE = 2


def _run(script: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=REPO,
        timeout=60,
    )


def _card(card_id: str, **fields) -> dict:
    card = {
        "id": card_id,
        "level": "Task",
        "title": f"title {card_id}",
        "status": "Todo",
        "light": "Gray",
        "updatedAt": "2026-11-01T00:00:00+08:00",
    }
    card.update(fields)
    return card


def _write_board(tmp_path: Path, items: list[dict]) -> Path:
    board = tmp_path / "board.json"
    board.write_text(
        json.dumps({"version": 1, "items": items}, ensure_ascii=False), encoding="utf-8"
    )
    return board


def _listed_ids(stdout: str) -> list[str]:
    return [line.split("\t")[2] for line in stdout.splitlines() if "\t" in line]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- normal ---------------------------------------------------------------


def test_should_list_open_work_cards_when_board_has_todo_backlog_and_in_progress(tmp_path):
    board = _write_board(
        tmp_path,
        [
            _card("T-TODO", status="Todo"),
            _card("T-BACKLOG", status="Backlog"),
            _card("T-WIP", status="In Progress"),
        ],
    )
    result = _run(POLL, "--board", str(board), "--all")
    assert result.returncode == EXIT_OK, result.stderr
    assert sorted(_listed_ids(result.stdout)) == ["T-BACKLOG", "T-TODO", "T-WIP"]


def test_should_print_light_status_id_title_columns_when_card_listed(tmp_path):
    board = _write_board(
        tmp_path, [_card("T-1", light="Yellow", status="In Progress", title="做某事")]
    )
    result = _run(POLL, "--board", str(board), "--all")
    assert result.returncode == EXIT_OK, result.stderr
    assert result.stdout.splitlines()[0] == "Yellow\tIn Progress\tT-1\t做某事"


def test_should_truncate_title_to_80_chars_when_title_is_long(tmp_path):
    long_title = "x" * 120
    board = _write_board(tmp_path, [_card("T-1", title=long_title)])
    result = _run(POLL, "--board", str(board), "--all")
    assert result.stdout.splitlines()[0].split("\t")[3] == "x" * 80


def test_should_print_only_first_card_when_all_flag_absent(tmp_path):
    board = _write_board(
        tmp_path, [_card("T-A", light="Red"), _card("T-B", light="Gray")]
    )
    result = _run(POLL, "--board", str(board))
    assert result.returncode == EXIT_OK, result.stderr
    assert _listed_ids(result.stdout) == ["T-A"]


# --- AC-B1: exclusions ------------------------------------------------------


def test_should_exclude_closed_statuses_when_card_in_review_or_done(tmp_path):
    board = _write_board(
        tmp_path,
        [
            _card("T-REVIEW", status="In Review"),
            _card("T-DONE", status="Done"),
            _card("T-OPEN", status="Todo"),
        ],
    )
    result = _run(POLL, "--board", str(board), "--all")
    assert _listed_ids(result.stdout) == ["T-OPEN"]


def test_should_exclude_epic_when_include_epic_flag_absent(tmp_path):
    board = _write_board(tmp_path, [_card("E-1", level="Epic"), _card("T-1")])
    result = _run(POLL, "--board", str(board), "--all")
    assert _listed_ids(result.stdout) == ["T-1"]


def test_should_list_epic_when_include_epic_flag_given(tmp_path):
    board = _write_board(tmp_path, [_card("E-1", level="Epic"), _card("T-1")])
    result = _run(POLL, "--board", str(board), "--all", "--include-epic")
    assert sorted(_listed_ids(result.stdout)) == ["E-1", "T-1"]


def test_should_exclude_decision_card_when_red_with_pending_decision_reason(tmp_path):
    board = _write_board(
        tmp_path,
        [
            _card("D-1", light="Red", lightReason="待決策：要不要做 X"),
            _card("T-1"),
        ],
    )
    result = _run(POLL, "--board", str(board), "--all")
    assert _listed_ids(result.stdout) == ["T-1"]


def test_should_list_red_card_when_light_reason_is_not_pending_decision(tmp_path):
    board = _write_board(
        tmp_path, [_card("R-1", light="Red", lightReason="CI 失敗：待決策 之後再說")]
    )
    result = _run(POLL, "--board", str(board), "--all")
    assert _listed_ids(result.stdout) == ["R-1"]


# --- AC-B2: ordering --------------------------------------------------------


def test_should_order_by_light_red_yellow_gray_green_when_lights_differ(tmp_path):
    board = _write_board(
        tmp_path,
        [
            _card("C-GREEN", light="Green"),
            _card("C-GRAY", light="Gray"),
            _card("C-RED", light="Red"),
            _card("C-YELLOW", light="Yellow"),
        ],
    )
    result = _run(POLL, "--board", str(board), "--all")
    assert _listed_ids(result.stdout) == ["C-RED", "C-YELLOW", "C-GRAY", "C-GREEN"]


def test_should_order_oldest_updated_first_when_lights_tie(tmp_path):
    board = _write_board(
        tmp_path,
        [
            _card("C-NEW", updatedAt="2026-11-20T00:00:00+08:00"),
            _card("C-OLD", updatedAt="2026-11-02T00:00:00+08:00"),
        ],
    )
    result = _run(POLL, "--board", str(board), "--all")
    assert _listed_ids(result.stdout) == ["C-OLD", "C-NEW"]


def test_should_order_by_id_when_light_and_updated_at_tie(tmp_path):
    board = _write_board(tmp_path, [_card("C-B"), _card("C-A"), _card("C-C")])
    result = _run(POLL, "--board", str(board), "--all")
    assert _listed_ids(result.stdout) == ["C-A", "C-B", "C-C"]


# --- boundaries -------------------------------------------------------------


def test_should_report_queue_empty_when_board_has_no_items(tmp_path):
    board = _write_board(tmp_path, [])
    result = _run(POLL, "--board", str(board), "--all")
    assert result.returncode == EXIT_OK
    assert "QUEUE_EMPTY" in result.stdout
    assert _listed_ids(result.stdout) == []


def test_should_report_queue_empty_when_every_card_is_excluded(tmp_path):
    board = _write_board(
        tmp_path,
        [
            _card("E-1", level="Epic"),
            _card("D-1", light="Red", lightReason="待決策：A or B"),
            _card("T-DONE", status="Done"),
            _card("T-REVIEW", status="In Review"),
        ],
    )
    result = _run(POLL, "--board", str(board), "--all")
    assert result.returncode == EXIT_OK
    assert "QUEUE_EMPTY" in result.stdout
    assert _listed_ids(result.stdout) == []


# --- AC-B3: invalid input ---------------------------------------------------


def test_should_exit_2_when_board_file_missing(tmp_path):
    result = _run(POLL, "--board", str(tmp_path / "nope.json"))
    assert result.returncode == EXIT_BOARD_UNREADABLE


def test_should_exit_2_when_board_json_is_broken(tmp_path):
    board = tmp_path / "board.json"
    board.write_text('{"items": [ {"id": ', encoding="utf-8")
    result = _run(POLL, "--board", str(board))
    assert result.returncode == EXIT_BOARD_UNREADABLE


# --- AC-B4: read-only --------------------------------------------------------


def test_should_leave_board_bytes_unchanged_when_polling(tmp_path):
    board = _write_board(
        tmp_path, [_card("T-1", light="Red"), _card("E-1", level="Epic")]
    )
    before = _sha256(board)
    _run(POLL, "--board", str(board), "--all", "--include-epic")
    assert _sha256(board) == before


# --- AC-B5: poll_extinguish ---------------------------------------------------


def test_should_refuse_with_exit_2_and_done_rule_when_poll_extinguish_runs():
    result = _run(EXTINGUISH)
    message = result.stdout + result.stderr
    assert result.returncode == EXIT_BOARD_UNREADABLE
    assert "Done" in message
    assert "母對話" not in message


# --- AC-B6: real board --------------------------------------------------------


def test_should_run_against_real_board_without_changing_it():
    before = _sha256(REAL_BOARD)
    result = _run(POLL, "--all")
    assert result.returncode == EXIT_OK, result.stderr
    assert result.stdout.strip(), "expected cards or QUEUE_EMPTY"
    assert _sha256(REAL_BOARD) == before
