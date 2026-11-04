"""PD-REL-UI-SMOKE-01 — #release recent row / empty-state smoke (script).

BDD-PD-REL-UI-SMOKE-01:
  - Read snapshot.releases via release_report.list / snapshot_safe.
  - Non-empty: latest version + reportPath are parseable.
  - Empty assumption: empty-state contract still holds; DOCTYPE + nav intact.
  - Never whole-file overwrite HTML; no UI visual redesign.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

BOARD_DIR = Path(__file__).resolve().parent
REPO = BOARD_DIR.parents[1]
if str(BOARD_DIR) not in sys.path:
    sys.path.insert(0, str(BOARD_DIR))

import release_report  # noqa: E402
from board_core import snapshot_safe  # noqa: E402

EMPTY_ZONE_MARKER = "還沒有佈版紀錄"
DOCTYPE = "<!DOCTYPE html"
LIVE_BOARD = REPO / "docs" / "PROJECT-BOARD.html"

MINI_SHELL = """<!DOCTYPE html>
<html lang="zh-Hant">
<head><meta charset="utf-8"><title>rel-ui-smoke</title>
<style>.nav { display:flex; } .navbtn { padding:4px; }</style>
</head>
<body>
<aside class="nav" aria-label="導覽">
  <button type="button" class="navbtn" id="tab-release" data-view="release">最近佈版</button>
</aside>
<main>
<section id="view-release">
  <div class="rel-body" id="relBody"></div>
</section>
<script type="application/json" id="board-snapshot">
{
  "asOf": "2026-10-24T00:00:00+08:00",
  "tasks": [],
  "releases": []
}
</script>
<script>
(function () {
  'use strict';
  /* empty-state contract mirrored from PROJECT-BOARD #release */
  function renderRelease(rels) {
    if (!rels || !rels.length) {
      return '<div class="empty-zone"><b>還沒有佈版紀錄。</b></div>';
    }
    var sorted = rels.slice().sort(function (a, b) {
      return String(b.releasedAt || '').localeCompare(String(a.releasedAt || ''));
    });
    return 'v' + sorted[0].version + '|' + (sorted[0].reportPath || '');
  }
  window.__relSmoke = { renderRelease: renderRelease };
})();
</script>
</main>
</body>
</html>
"""


def _latest_release(rels: list) -> dict | None:
    """Match board UI: sort by releasedAt descending; first is 最近."""
    if not rels:
        return None
    return sorted(
        [r for r in rels if isinstance(r, dict)],
        key=lambda r: str(r.get("releasedAt") or ""),
        reverse=True,
    )[0]


def _assert_shell_contract(html: str) -> None:
    snapshot_safe.assert_shell_intact(html)
    assert DOCTYPE in html[:80] or html.lstrip().startswith(DOCTYPE)
    assert EMPTY_ZONE_MARKER in html
    assert 'id="tab-release"' in html or 'id="view-release"' in html


@pytest.fixture()
def board_path(tmp_path: Path) -> Path:
    path = tmp_path / "PROJECT-BOARD.html"
    path.write_text(MINI_SHELL, encoding="utf-8", newline="\n")
    return path


def test_empty_releases_empty_state_contract_shell_intact(board_path: Path):
    html = board_path.read_text(encoding="utf-8")
    _assert_shell_contract(html)
    data = snapshot_safe.load_snapshot_dict(html)
    assert data["releases"] == []
    rels = release_report.list_releases(board_path)
    assert rels == []
    assert _latest_release(rels) is None


def test_nonempty_latest_version_and_report_path_parseable(board_path: Path):
    ts_old = "2026-10-24T10:00:00+08:00"
    ts_new = "2026-10-24T12:00:00+08:00"
    art = release_report.build_artifact(
        Path("missing-fixture.msi"), "MSI", ts_new, REPO
    )
    older = release_report.build_release(
        version="0.0.9",
        artifacts=[art],
        report_path="reports/dispatch-pd/old.md",
        kind="installer",
        recorded_by="agent",
        released_at=ts_old,
        embed_report_md=False,
        repo=REPO,
    )
    newer = release_report.build_release(
        version="0.1.0",
        artifacts=[art],
        report_path="reports/dispatch-pd/PD-REL-UI-SMOKE-01.md",
        kind="installer",
        recorded_by="agent",
        released_at=ts_new,
        embed_report_md=False,
        repo=REPO,
    )
    release_report.append_release(board_path, older)
    release_report.append_release(board_path, newer)

    after = board_path.read_text(encoding="utf-8")
    _assert_shell_contract(after)
    prefix_b, _, suffix_b = snapshot_safe.split_snapshot(MINI_SHELL)
    prefix_a, _, suffix_a = snapshot_safe.split_snapshot(after)
    assert prefix_a == prefix_b
    assert suffix_a == suffix_b

    rels = release_report.list_releases(board_path)
    assert len(rels) == 2
    latest = _latest_release(rels)
    assert latest is not None
    assert latest["version"] == "0.1.0"
    report = latest.get("reportPath") or ""
    assert report.endswith("PD-REL-UI-SMOKE-01.md")
    # Parseable path / semver-ish version
    assert "/" in report or report.startswith("reports")
    assert datetime.fromisoformat(str(latest["releasedAt"]))


def test_clear_releases_via_snapshot_safe_keeps_shell(board_path: Path):
    art = release_report.build_artifact(
        Path("x.msi"), "MSI", "2026-10-24T11:00:00+08:00", REPO
    )
    release_report.append_release(
        board_path,
        release_report.build_release(
            version="0.1.0",
            artifacts=[art],
            report_path="reports/tmp.md",
            kind="installer",
            recorded_by="agent",
            released_at="2026-10-24T11:00:00+08:00",
            embed_report_md=False,
            repo=REPO,
        ),
    )
    before = board_path.read_text(encoding="utf-8")
    prefix_b, _, suffix_b = snapshot_safe.split_snapshot(before)

    def clear(data: dict):
        data["releases"] = []
        return data["releases"]

    snapshot_safe.mutate_snapshot_file(board_path, clear)
    after = board_path.read_text(encoding="utf-8")
    _assert_shell_contract(after)
    prefix_a, inner, suffix_a = snapshot_safe.split_snapshot(after)
    assert prefix_a == prefix_b
    assert suffix_a == suffix_b
    assert json.loads(inner)["releases"] == []
    assert release_report.list_releases(board_path) == []


def test_full_overwrite_rejected_keeps_smoke_contract(board_path: Path):
    original = board_path.read_text(encoding="utf-8")
    snapshot_only = (
        '<script type="application/json" id="board-snapshot">\n'
        '{"tasks":[],"releases":[]}\n</script>\n'
    )
    reason = snapshot_safe.detect_full_overwrite(original, snapshot_only)
    assert reason is not None
    with pytest.raises(snapshot_safe.FullOverwriteRejected):
        snapshot_safe.refuse_if_full_overwrite(original, snapshot_only)
    # Fixture board unchanged; empty-state shell still valid
    _assert_shell_contract(board_path.read_text(encoding="utf-8"))


def test_live_board_releases_list_smoke_readonly():
    """Read-only: if live snapshot.releases non-empty, latest version/reportPath parse."""
    if not LIVE_BOARD.is_file():
        pytest.skip("live board missing")
    html = LIVE_BOARD.read_text(encoding="utf-8")
    snapshot_safe.assert_shell_intact(html)
    assert DOCTYPE in html[:80] or html.lstrip().startswith(DOCTYPE)
    # Empty-state copy must remain in shell even when releases are populated.
    assert EMPTY_ZONE_MARKER in html

    rels = release_report.list_releases(LIVE_BOARD)
    assert isinstance(rels, list)
    if not rels:
        data = snapshot_safe.load_snapshot_dict(html)
        assert data.get("releases") == [] or data.get("releases") is None
        return

    latest = _latest_release(rels)
    assert latest is not None
    ver = str(latest.get("version") or "").strip()
    assert ver, "latest release missing version"
    # reportPath optional historically; when present must be non-empty path-like
    rp = latest.get("reportPath")
    if rp is not None:
        assert str(rp).strip(), "reportPath present but empty"
        assert not str(rp).startswith("<")
    if latest.get("releasedAt"):
        datetime.fromisoformat(str(latest["releasedAt"]))
