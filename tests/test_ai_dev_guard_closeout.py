"""PD-CI-GUARD-CLOSEOUT-01 — AI Dev Guard close-out PRs (``board-closeout`` label).

Each case builds a throwaway git repo with a base board and a head board, runs
``.github/ai-dev-guard/guard.ps1`` under pwsh with the env vars the workflow
passes, and checks the exit code and the reported errors.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUARD_DIR = Path(".github") / "ai-dev-guard"
BOARD = Path("docs") / "board.json"
TASK = "PD-T-01"
OTHER = "PD-T-02"
STORY = "PD-S-01"
CLOSEOUT_TITLE = "chore(board): close out cards (Owner)"

T0 = "2026-11-20T10:00:00+08:00"
T1 = "2026-11-21T10:00:00+08:00"
T2 = "2026-11-25T10:00:00+08:00"

PWSH = shutil.which("pwsh")
if PWSH is None:
    pytest.skip("pwsh (PowerShell 7) not installed: AI Dev Guard tests NOT RUN", allow_module_level=True)  # ci:allow-test-disable: pwsh presence guard (CI ubuntu has pwsh)

GIT_ID = ("-c", "user.name=t", "-c", "user.email=t@example.invalid")


def _task(task_id: str, level: str = "Task") -> dict:
    card = {
        "id": task_id,
        "level": level,
        "title": f"{level} {task_id}",
        "parentId": "PD-E-01",
        "status": "In Review",
        "light": "Green",
        "createdAt": T0,
        "updatedAt": T1,
        "startedAt": T0,
        "role": "dev-agent",
        "tdd": "Green",
        "ci": "Pending",
        "prUrl": "https://github.com/example/repo/pull/1",
        "notes": [{"at": T1, "by": "dev-agent", "text": "READY_FOR_TDD"}],
        "history": [
            {"at": T0, "from": "new", "to": "In Progress", "by": "dev-agent"},
            {"at": T1, "from": "In Progress", "to": "In Review", "by": "dev-agent"},
        ],
    }
    if level == "Story":
        card["bdd"] = [{"id": "S-01-B01", "title": "scenario", "status": "Green"}]
    else:
        card["hours"] = 1
    return card


def _epic() -> dict:
    return {
        "id": "PD-E-01",
        "level": "Epic",
        "title": "epic",
        "parentId": None,
        "status": "In Review",
        "light": "Green",
        "createdAt": T0,
        "updatedAt": T1,
        "tdd": "Green",
        "history": [{"at": T1, "from": "In Progress", "to": "In Review", "by": "Owner"}],
    }


def _base_board() -> dict:
    return {
        "version": 1,
        "project": "fixture",
        "updatedAt": T1,
        "items": [_epic(), _task(TASK), _task(OTHER), _task(STORY, "Story")],
    }


def _card(board: dict, card_id: str) -> dict:
    return next(it for it in board["items"] if it["id"] == card_id)


def _close(board: dict, card_id: str = TASK) -> dict:
    """Valid In Review -> Done close-out of one card."""
    card = _card(board, card_id)
    card.update(status="Done", light="Blue", ci="Green", updatedAt=T2, completedAt=T2)
    card["notes"].append({"at": T2, "by": "Owner", "text": "TDD_PASS and PR merged"})
    card["history"].append({"at": T2, "from": "In Review", "to": "Done", "by": "Owner"})
    board["updatedAt"] = T2
    return board


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8")
    return out.stdout.strip()


def _write_board(repo: Path, board: dict) -> None:
    (repo / BOARD).write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _commit(repo: Path, message: str) -> None:
    _git(repo, *GIT_ID, "add", "-A")
    _git(repo, *GIT_ID, "commit", "-q", "--allow-empty", "-m", message)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    (r / GUARD_DIR).mkdir(parents=True)
    (r / "docs").mkdir()
    (r / "scripts").mkdir()
    for name in ("guard.ps1", "validate-board.ps1"):
        shutil.copy2(ROOT / GUARD_DIR / name, r / GUARD_DIR / name)
    shutil.copy2(ROOT / "scripts" / "check_added_test_disables.py", r / "scripts" / "check_added_test_disables.py")
    (r / "README.md").write_text("fixture\n", encoding="utf-8")
    _write_board(r, _base_board())
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "core.autocrlf", "false")
    _commit(r, "base")
    return r


def _head(repo: Path, board: dict) -> None:
    _write_board(repo, board)
    _commit(repo, "head")


def _rebase_fixture(repo: Path, board: dict) -> None:
    """Replace the base commit's board (for cases that need a different base state)."""
    _write_board(repo, board)
    _commit(repo, "base2")


def _run_guard(repo: Path, *, title: str = CLOSEOUT_TITLE, labels: str = "board-closeout",
               ref: str = "chore/closeout") -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(
        BOARD_PATH=str(BOARD).replace("\\", "/"),
        BASE_SHA=_git(repo, "rev-parse", "HEAD~1"),
        PR_TITLE=title,
        HEAD_REF=ref,
        PR_LABELS=labels,
    )
    guard = str(repo / GUARD_DIR / "guard.ps1").replace("'", "''")
    script = f"[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false); & '{guard}'; exit $LASTEXITCODE"
    return subprocess.run(
        [PWSH, "-NoProfile", "-Command", script],
        cwd=repo, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def _out(p: subprocess.CompletedProcess) -> str:
    return p.stdout + p.stderr


# --- normal mode (no label) is unchanged ----------------------------------------------------------

def test_should_pass_when_no_label_and_card_in_review(repo: Path) -> None:
    board = _base_board()
    _card(board, TASK)["notes"].append({"at": T2, "by": "dev-agent", "text": "progress"})
    _head(repo, board)
    p = _run_guard(repo, title=f"feat: work ({TASK})", labels="")
    assert p.returncode == 0, _out(p)


def test_should_fail_when_no_label_and_card_done(repo: Path) -> None:
    _head(repo, _close(_base_board()))
    p = _run_guard(repo, title=f"chore(board): set {TASK} Done", labels="")
    assert p.returncode == 1, _out(p)
    assert "必須是 In Review" in _out(p)


# --- close-out mode -----------------------------------------------------------------------------

def test_should_pass_when_closeout_of_single_card(repo: Path) -> None:
    _head(repo, _close(_base_board()))
    p = _run_guard(repo)
    assert p.returncode == 0, _out(p)
    assert "PR 沒有對應的 Task 卡片" not in _out(p)


def test_should_pass_when_closeout_label_among_other_labels(repo: Path) -> None:
    _head(repo, _close(_base_board()))
    p = _run_guard(repo, labels="docs, board-closeout")
    assert p.returncode == 0, _out(p)


def test_should_pass_when_closeout_of_multiple_cards(repo: Path) -> None:
    board = _close(_base_board())
    _close(board, OTHER)
    _close(board, STORY)
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 0, _out(p)


def test_should_fail_when_closeout_label_and_other_file_changed(repo: Path) -> None:
    (repo / "README.md").write_text("changed\n", encoding="utf-8")
    _head(repo, _close(_base_board()))
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert "board-closeout PR 只能修改 docs/board.json（另改了：README.md）" in _out(p)
    assert "必須是 In Review" not in _out(p), "must not fall back to normal mode"


def test_should_fail_when_closeout_base_status_not_in_review(repo: Path) -> None:
    base = _base_board()
    _card(base, TASK)["status"] = "In Progress"
    _rebase_fixture(repo, base)
    board = json.loads(json.dumps(base))
    _close(board)
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert f"{TASK}: " in _out(p) and "In Review" in _out(p)


def test_should_fail_when_closeout_base_tdd_not_green(repo: Path) -> None:
    base = _base_board()
    _card(base, TASK)["tdd"] = "Red"
    _rebase_fixture(repo, base)
    board = json.loads(json.dumps(base))
    _close(board)
    _card(board, TASK)["tdd"] = "Green"
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert f"{TASK}: " in _out(p) and "tdd" in _out(p)


def test_should_fail_when_closeout_head_not_done(repo: Path) -> None:
    board = _base_board()
    _card(board, TASK).update(ci="Green", updatedAt=T2)
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert f"{TASK}: " in _out(p) and "Done" in _out(p)


def test_should_fail_when_closeout_missing_completed_at(repo: Path) -> None:
    board = _close(_base_board())
    _card(board, TASK).pop("completedAt")
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert f"{TASK}: " in _out(p) and "completedAt" in _out(p)


@pytest.mark.parametrize(("field", "value"), [("title", "renamed"), ("prUrl", "https://example.invalid/2"), ("hours", 9)])
def test_should_fail_when_closeout_changes_disallowed_field(repo: Path, field: str, value: object) -> None:
    board = _close(_base_board())
    _card(board, TASK)[field] = value
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert f"{TASK}: 結案時不可修改欄位 {field}" in _out(p)


def test_should_pass_when_closeout_changes_allowed_fields(repo: Path) -> None:
    board = _close(_base_board())
    _card(board, TASK).update(approvedBy="Owner", lightReason="closed")
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 0, _out(p)


def test_should_fail_when_closeout_rewrites_old_note(repo: Path) -> None:
    board = _close(_base_board())
    _card(board, TASK)["notes"][0]["text"] = "rewritten"
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert f"{TASK}: " in _out(p) and "notes" in _out(p)


def test_should_fail_when_closeout_drops_old_history(repo: Path) -> None:
    board = _close(_base_board())
    del _card(board, TASK)["history"][0]
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert f"{TASK}: " in _out(p) and "history" in _out(p)


def test_should_fail_when_closeout_level_is_epic(repo: Path) -> None:
    board = _base_board()
    epic = _card(board, "PD-E-01")
    epic.update(status="Done", light="Blue", updatedAt=T2, completedAt=T2)
    epic["history"].append({"at": T2, "from": "In Review", "to": "Done", "by": "Owner"})
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert "PD-E-01: " in _out(p)


def test_should_fail_when_closeout_adds_card(repo: Path) -> None:
    board = _close(_base_board())
    board["items"].append(_task("PD-T-99"))
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert "PD-T-99: " in _out(p)


def test_should_fail_when_closeout_removes_card(repo: Path) -> None:
    board = _close(_base_board())
    board["items"] = [it for it in board["items"] if it["id"] != OTHER]
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert f"{OTHER}: " in _out(p)


@pytest.mark.parametrize(("field", "value"), [
    ("project", "renamed"),
    ("version", 2),
    ("migration", {"source": "x"}),
])
def test_should_fail_when_closeout_changes_top_level_field(repo: Path, field: str, value: object) -> None:
    board = _close(_base_board())
    board[field] = value
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert f"board-closeout 不可修改看板最上層欄位：{field}" in _out(p)


def test_should_fail_when_closeout_removes_top_level_field(repo: Path) -> None:
    base = _base_board()
    base["migration"] = {"source": "x"}
    _rebase_fixture(repo, base)
    board = _close(json.loads(json.dumps(base)))
    del board["migration"]
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert "board-closeout 不可修改看板最上層欄位：migration" in _out(p)


def test_should_pass_when_closeout_changes_only_top_level_updated_at(repo: Path) -> None:
    board = _close(_base_board())
    assert board["updatedAt"] == T2
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 0, _out(p)
    assert "最上層欄位" not in _out(p)


def test_should_fail_when_closeout_label_and_no_card_changed(repo: Path) -> None:
    board = _base_board()
    board["updatedAt"] = T2
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert "board-closeout PR 沒有結案任何卡片" in _out(p)


# --- the guard itself is an enforcement path ------------------------------------------------------

def _touch_guard_and_progress(repo: Path) -> None:
    with (repo / GUARD_DIR / "guard.ps1").open("a", encoding="utf-8") as f:
        f.write("\n# touched\n")
    board = _base_board()
    _card(board, TASK)["notes"].append({"at": T2, "by": "dev-agent", "text": "progress"})
    _head(repo, board)


def test_should_fail_when_guard_changed_without_guard_change_label(repo: Path) -> None:
    _touch_guard_and_progress(repo)
    p = _run_guard(repo, title=f"ci: guard ({TASK})", labels="")
    assert p.returncode == 1, _out(p)
    assert "guard-change" in _out(p)


def test_should_pass_when_guard_changed_with_guard_change_label(repo: Path) -> None:
    _touch_guard_and_progress(repo)
    p = _run_guard(repo, title=f"ci: guard ({TASK})", labels="guard-change")
    assert p.returncode == 0, _out(p)


# --- PD-CI-GUARD-HARDEN-01 D4: approvedBy must be non-empty and not a dev agent ------------------

@pytest.mark.parametrize("value", ["dev-agent", "開發代理 (Claude)", "", "   ", 123])
def test_should_fail_when_closeout_sets_invalid_approved_by(repo: Path, value: object) -> None:
    board = _close(_base_board())
    _card(board, TASK)["approvedBy"] = value
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert f"{TASK}: 結案時 approvedBy 必須是非空字串，且不可以是開發代理" in _out(p)


def test_should_fail_when_closeout_removes_approved_by(repo: Path) -> None:
    base = _base_board()
    _card(base, TASK)["approvedBy"] = "Owner"
    _rebase_fixture(repo, base)
    board = _close(json.loads(json.dumps(base)))
    del _card(board, TASK)["approvedBy"]
    _head(repo, board)
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert f"{TASK}: 結案時 approvedBy 必須是非空字串，且不可以是開發代理" in _out(p)


def test_should_pass_when_closeout_keeps_unchanged_approved_by(repo: Path) -> None:
    base = _base_board()
    _card(base, TASK)["approvedBy"] = "Owner"
    _rebase_fixture(repo, base)
    _head(repo, _close(json.loads(json.dumps(base))))
    p = _run_guard(repo)
    assert p.returncode == 0, _out(p)
