"""PD-BOARD-SAFE-01 — regression: snapshot-only writes; whole-file overwrite FAIL."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BOARD_DIR = Path(__file__).resolve().parent
if str(BOARD_DIR) not in sys.path:
    sys.path.insert(0, str(BOARD_DIR))

from board_core import snapshot_safe  # noqa: E402

MINI_SHELL = """<!DOCTYPE html>
<html lang="zh-Hant">
<head><meta charset="utf-8"><title>board</title>
<style>.nav { display:flex; } .navbtn { padding:4px; }</style>
</head>
<body>
<aside class="nav" aria-label="導覽">
  <button type="button" class="navbtn">工項</button>
</aside>
<main>
<script type="application/json" id="board-snapshot">
{
  "asOf": "2026-10-24T00:00:00+08:00",
  "tasks": [
    {"id": "PD-BOARD-SAFE-01", "title": "safe write", "zone": "yellow", "note": "seed", "version": 1}
  ],
  "releases": []
}
</script>
<script>
(function () { 'use strict'; /* runtime shell */ })();
</script>
</main>
</body>
</html>
"""

SNAPSHOT_ONLY = """<script type="application/json" id="board-snapshot">
{"tasks": [{"id": "X", "zone": "green"}], "releases": []}
</script>
"""


def test_assert_shell_intact_accepts_doctype_and_nav():
    snapshot_safe.assert_shell_intact(MINI_SHELL)


def test_assert_shell_intact_rejects_snapshot_only():
    with pytest.raises(snapshot_safe.ShellCorruptError, match="DOCTYPE"):
        snapshot_safe.assert_shell_intact(SNAPSHOT_ONLY)


def test_compose_replaces_only_snapshot_json():
    data = snapshot_safe.load_snapshot_dict(MINI_SHELL)
    data["tasks"][0]["note"] = "seed\n[updated]"
    out = snapshot_safe.compose_replaced_snapshot(MINI_SHELL, data)
    prefix_a, _i, suffix_a = snapshot_safe.split_snapshot(MINI_SHELL)
    prefix_b, inner_b, suffix_b = snapshot_safe.split_snapshot(out)
    assert prefix_a == prefix_b
    assert suffix_a == suffix_b
    assert "<!DOCTYPE html>" in out
    assert "導覽" in out or "class=\"nav\"" in out
    assert "(function ()" in out
    loaded = json.loads(inner_b)
    assert loaded["tasks"][0]["note"].endswith("[updated]")


def test_detect_full_overwrite_snapshot_only_is_fail():
    reason = snapshot_safe.detect_full_overwrite(MINI_SHELL, SNAPSHOT_ONLY)
    assert reason is not None
    assert "shell" in reason.lower() or "doctype" in reason.lower()


def test_refuse_full_overwrite_raises():
    with pytest.raises(snapshot_safe.FullOverwriteRejected):
        snapshot_safe.refuse_if_full_overwrite(MINI_SHELL, SNAPSHOT_ONLY)


def test_detect_accepts_legitimate_snapshot_replace():
    data = snapshot_safe.load_snapshot_dict(MINI_SHELL)
    data["asOf"] = "2026-10-24T01:00:00+08:00"
    candidate = snapshot_safe.compose_replaced_snapshot(MINI_SHELL, data)
    assert snapshot_safe.detect_full_overwrite(MINI_SHELL, candidate) is None


def test_mutate_snapshot_file_preserves_shell(tmp_path: Path):
    path = tmp_path / "PROJECT-BOARD.html"
    path.write_text(MINI_SHELL, encoding="utf-8", newline="\n")
    before = path.read_text(encoding="utf-8")
    prefix_b, _, suffix_b = snapshot_safe.split_snapshot(before)

    def bump(data):
        data["tasks"][0]["note"] = "seed\nmutated"
        return data["tasks"][0]

    task = snapshot_safe.mutate_snapshot_file(path, bump)
    after = path.read_text(encoding="utf-8")
    prefix_a, inner, suffix_a = snapshot_safe.split_snapshot(after)
    assert prefix_a == prefix_b
    assert suffix_a == suffix_b
    assert "<!DOCTYPE html>" in after
    assert "navbtn" in after
    assert json.loads(inner)["tasks"][0]["note"] == "seed\nmutated"
    assert task["id"] == "PD-BOARD-SAFE-01"


def test_whole_file_write_of_snapshot_only_fails_detection(tmp_path: Path):
    """If an agent wrote SNAPSHOT_ONLY over the board, detection must FAIL (not silent)."""
    path = tmp_path / "PROJECT-BOARD.html"
    path.write_text(MINI_SHELL, encoding="utf-8", newline="\n")
    original = path.read_text(encoding="utf-8")
    # Simulate forbidden whole-file overwrite
    path.write_text(SNAPSHOT_ONLY, encoding="utf-8", newline="\n")
    corrupted = path.read_text(encoding="utf-8")
    reason = snapshot_safe.detect_full_overwrite(original, corrupted)
    assert reason is not None
    with pytest.raises(snapshot_safe.ShellCorruptError):
        snapshot_safe.assert_shell_intact(corrupted)
