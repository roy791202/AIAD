"""PD-RELEASE-REC-01 (PD-BOARD-GAPS-RELEASE-01): release record JSON, no board writes.

Uses tools/board/release_report.py. The board's single source of truth is
docs/board.json; release tools never write any board file. ``build`` emits one
release record JSON to stdout or ``--out``.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BOARD_TOOLS = ROOT / "tools" / "board"
ARTIFACT_ROOT = Path(os.environ.get("SGENAXIS_PACKAGING_TEST_ROOT", str(ROOT))).resolve()
MSI = ARTIFACT_ROOT / "packaging" / "windows" / "wix" / "out" / "SGenAxis-0.1.0-windows-x64.msi"
REPORT_EXAMPLE = ARTIFACT_ROOT / "reports" / "dispatch-pd" / "PD-REL-02.md"
REPORT_REL = "reports/dispatch-pd/PD-REL-02.md"
RELEASED_AT = "2026-10-24T02:05:00+08:00"
RELEASE_TOOLS = ("release_report.py", "build_result.py", "rel_hang_final.py", "rel_hang_post.py")
LEGACY_BOARD_MARKERS = ("board_watch", "PROJECT-BOARD")

sys.path.insert(0, str(BOARD_TOOLS))

import release_report  # noqa: E402


def _msi_rel() -> str:
    return str(MSI.relative_to(ARTIFACT_ROOT)).replace("\\", "/")


def _build_argv(*extra: str) -> list[str]:
    return [
        "build",
        "--version",
        "0.1.0",
        "--artifact",
        _msi_rel(),
        "--label",
        "MSI",
        "--report-path",
        REPORT_REL,
        "--no-embed-report",
        "--released-at",
        RELEASED_AT,
        *extra,
    ]


def _expected_release() -> dict:
    art = release_report.build_artifact(Path(_msi_rel()), "MSI", RELEASED_AT, ARTIFACT_ROOT)
    return release_report.build_release(
        version="0.1.0",
        artifacts=[art],
        report_path=REPORT_REL,
        kind="installer",
        recorded_by="agent",
        released_at=RELEASED_AT,
        embed_report_md=False,
        repo=ARTIFACT_ROOT,
    )


@pytest.fixture()
def repo_at_artifacts(monkeypatch: pytest.MonkeyPatch) -> Path:
    assert MSI.is_file(), f"missing example MSI: {MSI}"
    monkeypatch.setattr(release_report, "REPO", ARTIFACT_ROOT)
    return ARTIFACT_ROOT


def test_should_print_release_json_to_stdout_when_build_without_out(
    repo_at_artifacts: Path, capsys: pytest.CaptureFixture[str]
):
    rc = release_report.main(_build_argv())
    assert rc == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed == _expected_release()
    assert printed["version"] == "0.1.0"
    assert printed["reportPath"] == REPORT_REL
    assert printed["artifacts"][0]["label"] == "MSI"
    assert printed["artifacts"][0]["exists"] is True
    assert "SGenAxis-0.1.0-windows-x64.msi" in printed["artifacts"][0]["path"]


def test_should_write_release_json_file_when_build_with_out(repo_at_artifacts: Path, tmp_path: Path):
    out = tmp_path / "nested" / "v0.1.0.release.json"
    rc = release_report.main(_build_argv("--out", str(out)))
    assert rc == 0
    assert json.loads(out.read_text(encoding="utf-8")) == _expected_release()


def test_should_leave_board_files_untouched_when_build(
    repo_at_artifacts: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    board = tmp_path / "board.json"
    board.write_text('{"items": []}\n', encoding="utf-8", newline="\n")
    before = board.read_bytes()
    monkeypatch.chdir(tmp_path)
    rc = release_report.main(_build_argv("--out", str(tmp_path / "r.release.json")))
    assert rc == 0
    assert board.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["board.json", "r.release.json"]


def test_should_reject_board_option_and_board_writers():
    with pytest.raises(SystemExit):
        release_report.build_parser().parse_args(["--board", "x.html", *_build_argv()])
    for legacy in ("append_release", "list_releases", "_mutate_snapshot"):
        assert not hasattr(release_report, legacy), legacy


def test_should_reject_build_without_artifact(capsys: pytest.CaptureFixture[str]):
    rc = release_report.main(["build", "--version", "0.1.0"])
    assert rc == 1
    assert "artifact" in capsys.readouterr().err


def test_should_derive_release_json_path_next_to_report():
    report = Path("reports") / "build-0.1.0-final-20261024T120000.md"
    assert release_report.release_json_path(report) == (
        Path("reports") / "build-0.1.0-final-20261024T120000.release.json"
    )


def test_should_not_reference_legacy_board_in_release_tools():
    for name in RELEASE_TOOLS:
        text = (BOARD_TOOLS / name).read_text(encoding="utf-8")
        for marker in LEGACY_BOARD_MARKERS:
            assert marker not in text, f"{name} still references {marker}"


def test_example_msi_and_report_exist_for_demo():
    assert MSI.is_file()
    assert MSI.stat().st_size > 100_000
    assert REPORT_EXAMPLE.is_file()
