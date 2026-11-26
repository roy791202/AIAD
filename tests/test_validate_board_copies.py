"""PD-CI-GUARD-HARDEN-01 D3 — the three validate-board.ps1 copies must stay identical.

``.github/ai-dev-guard/`` (CI guard), ``.ai-hooks/`` (agent hooks) and ``.githooks/``
(git pre-commit) each load their own copy; a rule fixed in one copy only would let
the local hooks and CI disagree.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".github" / "ai-dev-guard" / "validate-board.ps1"
COPIES = (ROOT / ".ai-hooks" / "validate-board.ps1", ROOT / ".githooks" / "validate-board.ps1")


def test_should_have_all_validate_board_copies_present() -> None:
    for path in (SOURCE, *COPIES):
        assert path.is_file(), f"missing {path.relative_to(ROOT)}"


def test_should_keep_validate_board_copies_byte_identical() -> None:
    expected = SOURCE.read_bytes()
    differing = [str(p.relative_to(ROOT)) for p in COPIES if p.read_bytes() != expected]
    assert not differing, (
        f"{', '.join(differing)} differ from {SOURCE.relative_to(ROOT)}; "
        "copy .github/ai-dev-guard/validate-board.ps1 over them"
    )
