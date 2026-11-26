"""PD-CI-GUARD-CLOSEOUT-01 — AI Dev Guard close-out PRs (``board-closeout`` label).

Runs ``.github/ai-dev-guard/guard.ps1`` with pwsh inside a throwaway git repo:
the base commit holds a minimal board, the head commit applies one scenario,
and the guard sees the same env vars the workflow passes.
"""

from __future__ import annotations

import copy
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
CLOSEOUT_TITLE = f"chore(board): set {TASK} Done (Owner-directed)"

T0 = "2026-11-20T10:00:00+08:00"
T1 = "2026-11-21T10:00:00+08:00"
T2 = "2026-11-25T10:00:00+08:00"


def _task(task_id: str) -> dict:
    return {
        "id": task_id,
        "level": "Task",
        "title": f"task {task_id}",
        "parentId": "PD-E-01",
        "status": "In Review",
        "light": "Green",
        "createdAt": T0,
        "updatedAt": T1,
        "startedAt": T0,
        "role": "dev-agent",
        "hours": 1,
        "tdd": "Green",
        "ci": "Pending",
        "prUrl": "https://github.com/example/repo/pull/1",
        "history": [
            {"at": T0, "from": "new", "to": "In Progress", "by": "dev-agent"},
            {"at": T1, "from": "In Progress", "to": "In Review", "by": "dev-agent"},
        ],
    }


def _base_board() -> dict:
    epic = {
        "id": "PD-E-01",
        "level": "Epic",
        "title": "epic",
        "parentId": None,
        "status": "In Progress",
        "light": "Green",
        "createdAt": T0,
        "updatedAt": T0,
    }
    return {"version": 1, "project": "fixture", "updatedAt": T1, "items": [epic, _task(TASK), _task(OTHER)]}


def _card(board: dict, task_id: str) -> dict:
    return next(it for it in board["items"] if it["id"] == task_id)


def _close(board: dict, task_id: str = TASK) -> dict:
    """Valid In Review -> Done close-out of one card."""
    card = _card(board, task_id)
    card.update(status="Done", light="Blue", ci="Green", updatedAt=T2, completedAt=T2)
    card["history"].append({"at": T2, "from": "In Review", "to": "Done", "by": "Owner"})
    board["updatedAt"] = T2
    return board


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True, encoding="utf-8")
    return out.stdout.strip()


def _write_board(repo: Path, board: dict) -> None:
    (repo / BOARD).write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    _git(r, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "add", "-A")
    _git(r, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "base")
    return r


def _commit_head(repo: Path) -> None:
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "head")


def _run_guard(repo: Path, *, title: str = CLOSEOUT_TITLE, labels: str = "", ref: str = "chore/closeout") -> subprocess.CompletedProcess:
    pwsh = shutil.which("pwsh")
    assert pwsh, "pwsh (PowerShell 7) is required to run the AI Dev Guard tests"
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
        [pwsh, "-NoProfile", "-Command", script],
        cwd=repo, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def _apply(repo: Path, board: dict) -> None:
    _write_board(repo, board)
    _commit_head(repo)


def _out(p: subprocess.CompletedProcess) -> str:
    return p.stdout + p.stderr


# --- without the label: existing rule unchanged -------------------------------------------------

def test_should_pass_when_no_label_and_card_in_review(repo: Path) -> None:
    board = _base_board()
    _card(board, TASK)["notes"] = [{"at": T2, "by": "dev-agent", "text": "progress"}]
    _apply(repo, board)
    p = _run_guard(repo, title=f"feat: work ({TASK})")
    assert p.returncode == 0, _out(p)


def test_should_fail_when_no_label_and_card_done(repo: Path) -> None:
    _apply(repo, _close(_base_board()))
    p = _run_guard(repo)
    assert p.returncode == 1, _out(p)
    assert "必須是 In Review" in _out(p)


# --- with the label: close-out checks -------------------------------------------------------------

def test_should_pass_when_closeout_label_and_valid_closeout(repo: Path) -> None:
    _apply(repo, _close(_base_board()))
    p = _run_guard(repo, labels="board-closeout")
    assert p.returncode == 0, _out(p)


def test_should_pass_when_closeout_label_among_other_labels(repo: Path) -> None:
    _apply(repo, _close(_base_board()))
    p = _run_guard(repo, labels="docs, board-closeout")
    assert p.returncode == 0, _out(p)


def test_should_fail_when_closeout_changes_other_files(repo: Path) -> None:
    (repo / "README.md").write_text("changed\n", encoding="utf-8")
    _apply(repo, _close(_base_board()))
    p = _run_guard(repo, labels="board-closeout")
    assert p.returncode == 1, _out(p)
    assert "README.md" in _out(p)


def test_should_fail_when_closeout_card_was_not_in_review_at_base(repo: Path) -> None:
    base = _base_board()
    _card(base, TASK)["status"] = "In Progress"
    _write_board(repo, base)
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-am", "base2")
    board = copy.deepcopy(base)
    _close(board)
    _card(board, TASK)["history"][-1]["from"] = "In Progress"
    _apply(repo, board)
    p = _run_guard(repo, labels="board-closeout")
    assert p.returncode == 1, _out(p)
    assert "In Review" in _out(p)


def test_should_fail_when_closeout_card_not_done(repo: Path) -> None:
    board = _base_board()
    _card(board, TASK)["notes"] = [{"at": T2, "by": "Owner", "text": "note only"}]
    _apply(repo, board)
    p = _run_guard(repo, labels="board-closeout")
    assert p.returncode == 1, _out(p)
    assert "Done" in _out(p)


@pytest.mark.parametrize(
    ("field", "value"),
    [("ci", "Pending"), ("tdd", "Red"), ("completedAt", None), ("prUrl", None)],
)
def test_should_fail_when_closeout_card_fields_incomplete(repo: Path, field: str, value: object) -> None:
    board = _close(_base_board())
    card = _card(board, TASK)
    if value is None:
        card.pop(field)
    else:
        card[field] = value
    _apply(repo, board)
    p = _run_guard(repo, labels="board-closeout")
    assert p.returncode == 1, _out(p)
    assert field in _out(p)


def test_should_fail_when_closeout_history_last_entry_not_review_to_done(repo: Path) -> None:
    board = _close(_base_board())
    _card(board, TASK)["history"][-1]["from"] = "In Progress"
    _apply(repo, board)
    p = _run_guard(repo, labels="board-closeout")
    assert p.returncode == 1, _out(p)
    assert "history" in _out(p)


def test_should_fail_when_closeout_changes_another_card(repo: Path) -> None:
    board = _close(_base_board())
    _card(board, OTHER)["notes"] = [{"at": T2, "by": "Owner", "text": "sneaky"}]
    _apply(repo, board)
    p = _run_guard(repo, labels="board-closeout")
    assert p.returncode == 1, _out(p)
    assert OTHER in _out(p)


# --- the guard itself is an enforcement file ----------------------------------------------------

def test_should_fail_when_guard_changed_without_guard_change_label(repo: Path) -> None:
    with (repo / GUARD_DIR / "guard.ps1").open("a", encoding="utf-8") as f:
        f.write("\n# touched\n")
    board = _base_board()
    _card(board, TASK)["notes"] = [{"at": T2, "by": "dev-agent", "text": "progress"}]
    _apply(repo, board)
    p = _run_guard(repo, title=f"ci: guard ({TASK})")
    assert p.returncode == 1, _out(p)
    assert "guard-change" in _out(p)


def test_should_pass_when_guard_changed_with_guard_change_label(repo: Path) -> None:
    with (repo / GUARD_DIR / "guard.ps1").open("a", encoding="utf-8") as f:
        f.write("\n# touched\n")
    board = _base_board()
    _card(board, TASK)["notes"] = [{"at": T2, "by": "dev-agent", "text": "progress"}]
    _apply(repo, board)
    p = _run_guard(repo, title=f"ci: guard ({TASK})", labels="guard-change")
    assert p.returncode == 0, _out(p)
