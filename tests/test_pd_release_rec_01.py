"""PD-RELEASE-REC-01: append release to snapshot.releases; #release empty-state intact.

Uses tools/board/release_report.py. Writes only #board-snapshot (HTML shell preserved).
Does not touch Firebase; does not force elevated install; does not set zone=green.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BOARD_TOOLS = ROOT / "tools" / "board"
ARTIFACT_ROOT = Path(os.environ.get("SGENAXIS_PACKAGING_TEST_ROOT", str(ROOT))).resolve()
MSI = ARTIFACT_ROOT / "packaging" / "windows" / "wix" / "out" / "SGenAxis-0.1.0-windows-x64.msi"
REPORT_EXAMPLE = ARTIFACT_ROOT / "reports" / "dispatch-pd" / "PD-REL-02.md"
EMPTY_ZONE_MARKER = "還沒有佈版紀錄"
DOCTYPE = "<!DOCTYPE html"
TAB_RELEASE = 'id="tab-release"'
VIEW_RELEASE = 'id="view-release"'
SNAPSHOT_OPEN = '<script type="application/json" id="board-snapshot">'

sys.path.insert(0, str(BOARD_TOOLS))
sys.path.insert(0, str(ROOT / "docs"))

import release_report  # noqa: E402


MINIMAL_BOARD = """<!DOCTYPE html>
<html lang="zh-Hant">
<head><meta charset="utf-8"/><title>board fixture</title></head>
<body>
<nav><button type="button" id="tab-release" data-view="release">最近佈版</button></nav>
<section id="view-release" hidden>
  <div class="rel-body" id="relBody"></div>
</section>
<script type="application/json" id="board-snapshot">
{
  "asOf": "2026-10-24T00:00:00+08:00",
  "version": "0.0.0-test",
  "overall": "PARTIAL",
  "source": "fixture",
  "tasks": [],
  "releases": []
}
</script>
<script>
/* empty-state copy mirrored from PROJECT-BOARD for contract */
var EMPTY = "還沒有佈版紀錄。";
</script>
</body>
</html>
"""


@pytest.fixture()
def board_copy(tmp_path: Path) -> Path:
    path = tmp_path / "PROJECT-BOARD.html"
    path.write_text(MINIMAL_BOARD, encoding="utf-8", newline="\n")
    return path


def _snapshot(path: Path) -> dict:
    html = path.read_text(encoding="utf-8")
    assert SNAPSHOT_OPEN in html
    start = html.find(SNAPSHOT_OPEN) + len(SNAPSHOT_OPEN)
    end = html.find("</script>", start)
    return json.loads(html[start:end])


def test_empty_releases_preserves_empty_state_copy(board_copy: Path):
    html = board_copy.read_text(encoding="utf-8")
    assert EMPTY_ZONE_MARKER in html
    snap = _snapshot(board_copy)
    assert snap["releases"] == []


def test_append_release_version_artifacts_report_path(board_copy: Path):
    assert MSI.is_file(), f"missing example MSI: {MSI}"
    ts = "2026-10-24T02:00:00+08:00"
    art = release_report.build_artifact(MSI, "MSI", ts, ARTIFACT_ROOT)
    release = release_report.build_release(
        version="0.1.0",
        artifacts=[art],
        report_path="reports/dispatch-pd/PD-REL-02.md",
        kind="installer",
        recorded_by="agent",
        released_at=ts,
        embed_report_md=False,
        repo=ARTIFACT_ROOT,
    )
    release_report.append_release(board_copy, release)

    html = board_copy.read_text(encoding="utf-8")
    assert html.lstrip().startswith(DOCTYPE)
    assert TAB_RELEASE in html
    assert VIEW_RELEASE in html
    assert EMPTY_ZONE_MARKER in html  # shell empty-state copy remains

    snap = _snapshot(board_copy)
    assert len(snap["releases"]) == 1
    r = snap["releases"][0]
    assert r["version"] == "0.1.0"
    assert r["reportPath"] == "reports/dispatch-pd/PD-REL-02.md"
    assert r["artifacts"][0]["label"] == "MSI"
    assert r["artifacts"][0]["exists"] is True
    assert "SGenAxis-0.1.0-windows-x64.msi" in r["artifacts"][0]["path"]


def test_append_via_cli_and_list(board_copy: Path, monkeypatch: pytest.MonkeyPatch):
    assert MSI.is_file()
    monkeypatch.setattr(release_report, "REPO", ARTIFACT_ROOT)
    rc = release_report.main(
        [
            "--board",
            str(board_copy),
            "append",
            "--version",
            "0.1.0",
            "--artifact",
            str(MSI.relative_to(ARTIFACT_ROOT)).replace("\\", "/"),
            "--label",
            "MSI",
            "--report-path",
            "reports/dispatch-pd/PD-REL-02.md",
            "--no-embed-report",
            "--released-at",
            "2026-10-24T02:05:00+08:00",
        ]
    )
    assert rc == 0
    rels = release_report.list_releases(board_copy)
    assert len(rels) == 1
    assert rels[0]["version"] == "0.1.0"
    assert rels[0]["reportPath"].endswith("PD-REL-02.md")


def test_append_does_not_destroy_shell_when_board_has_nav(board_copy: Path):
    """Regression: whole-file overwrite would drop DOCTYPE / #release chrome."""
    src = board_copy
    assert src.is_file(), "FIXTURE_SETUP: versioned shell fixture is required"
    # Work on a disposable copy of the isolated shell fixture (read shell markers only).
    # Do not mutate the live board inside unit tests.
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        dest = Path(td) / "PROJECT-BOARD.html"
        shutil.copy2(src, dest)
        before = dest.read_text(encoding="utf-8")
        assert DOCTYPE in before[:64] or before.lstrip().startswith(DOCTYPE)
        assert TAB_RELEASE in before
        assert VIEW_RELEASE in before
        assert EMPTY_ZONE_MARKER in before

        art = release_report.build_artifact(MSI, "MSI", "2026-10-24T02:10:00+08:00", ARTIFACT_ROOT)
        release_report.append_release(
            dest,
            release_report.build_release(
                version="0.1.0-test-fixture",
                artifacts=[art],
                report_path="reports/dispatch-pd/PD-REL-02.md",
                kind="installer",
                recorded_by="agent",
                released_at="2026-10-24T02:10:00+08:00",
                embed_report_md=False,
                repo=ARTIFACT_ROOT,
            ),
        )
        after = dest.read_text(encoding="utf-8")
        assert after.lstrip().startswith(DOCTYPE)
        assert TAB_RELEASE in after
        assert VIEW_RELEASE in after
        assert EMPTY_ZONE_MARKER in after
        snap = _snapshot(dest)
        assert any(r.get("version") == "0.1.0-test-fixture" for r in snap["releases"])


def test_example_msi_and_report_exist_for_demo():
    assert MSI.is_file()
    assert MSI.stat().st_size > 100_000
    assert REPORT_EXAMPLE.is_file()
