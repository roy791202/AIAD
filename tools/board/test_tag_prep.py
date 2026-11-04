"""Unit tests for PD-REMAIN-TAG-APPLY-01 / PD-TAG-PREP-01 SemVer tag prep."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tag_prep


CHANGELOG_V010 = """# Changelog

## [0.1.0] — 2026-10-24

Release id `v0.1.0` candidate.
"""


class TagPrepDryRunTests(unittest.TestCase):
    def test_planned_tag_default_v010(self) -> None:
        self.assertEqual(tag_prep.planned_tag_name("0.1.0"), "v0.1.0")
        self.assertEqual(tag_prep.planned_tag_name("v0.1.0"), "v0.1.0")

    def test_dry_run_default_prints_plan_not_published(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            clog = Path(td) / "CHANGELOG.md"
            clog.write_text(CHANGELOG_V010, encoding="utf-8")
            plan = tag_prep.plan_tag(
                version="0.1.0",
                changelog_path=clog,
                apply=False,
            )
            self.assertEqual(plan.mode, tag_prep.MODE_DRY_RUN)
            self.assertEqual(plan.planned_tag, "v0.1.0")
            self.assertTrue(plan.changelog.present)
            self.assertTrue(plan.changelog.has_version_section)
            self.assertTrue(plan.changelog.has_release_id)
            self.assertEqual(plan.tag_status, tag_prep.STATUS_PLANNED)
            self.assertFalse(plan.published)
            self.assertEqual(plan.gate_status, tag_prep.GATE_N_A)
            self.assertFalse(plan.push)
            text = tag_prep.format_plan(plan)
            self.assertIn("planned_tag=v0.1.0", text)
            self.assertIn("published=no", text)
            self.assertIn("push=no", text)
            self.assertIn("dry-run is a plan only", text)
            self.assertIn("not a publish claim", text)
            self.assertNotIn("published=yes", text)
            self.assertNotIn("tag_status=TAGGED", text)

    def test_dry_run_missing_changelog(self) -> None:
        missing = Path(tempfile.mkdtemp()) / "no-CHANGELOG.md"
        plan = tag_prep.plan_tag(changelog_path=missing, apply=False)
        self.assertFalse(plan.changelog.present)
        self.assertFalse(plan.published)
        self.assertEqual(plan.tag_status, tag_prep.STATUS_PLANNED)

    def test_apply_without_owner_gate_blocked_no_tagger(self) -> None:
        calls: list[tuple[str, Path]] = []

        def fake_tagger(tag: str, repo: Path) -> str:
            calls.append((tag, repo))
            return tag_prep.STATUS_NOT_RUN

        with tempfile.TemporaryDirectory() as td:
            clog = Path(td) / "CHANGELOG.md"
            clog.write_text(CHANGELOG_V010, encoding="utf-8")
            plan = tag_prep.plan_tag(
                version="0.1.0",
                changelog_path=clog,
                repo=Path(td),
                apply=True,
                owner_approved=False,
                tagger=fake_tagger,
            )
            self.assertEqual(plan.mode, tag_prep.MODE_APPLY)
            self.assertEqual(plan.tag_status, tag_prep.STATUS_GATE_BLOCKED)
            self.assertEqual(plan.gate_status, tag_prep.GATE_BLOCKED)
            self.assertFalse(plan.published)
            self.assertFalse(plan.owner_approved)
            self.assertFalse(plan.push)
            self.assertEqual(calls, [])
            text = tag_prep.format_plan(plan)
            self.assertIn("gate_status=BLOCKED", text)
            self.assertIn("published=no", text)
            self.assertIn("--owner-approved", text)

    def test_apply_with_owner_gate_stub_not_run(self) -> None:
        calls: list[tuple[str, Path]] = []

        def fake_tagger(tag: str, repo: Path) -> str:
            calls.append((tag, repo))
            return tag_prep.STATUS_NOT_RUN

        with tempfile.TemporaryDirectory() as td:
            clog = Path(td) / "CHANGELOG.md"
            clog.write_text(CHANGELOG_V010, encoding="utf-8")
            plan = tag_prep.plan_tag(
                version="0.1.0",
                changelog_path=clog,
                repo=Path(td),
                apply=True,
                owner_approved=True,
                tagger=fake_tagger,
            )
            self.assertEqual(plan.mode, tag_prep.MODE_APPLY)
            self.assertEqual(plan.tag_status, tag_prep.STATUS_NOT_RUN)
            self.assertEqual(plan.gate_status, tag_prep.GATE_OPEN)
            self.assertTrue(plan.owner_approved)
            self.assertFalse(plan.published)
            self.assertFalse(plan.push)
            self.assertEqual(calls, [("v0.1.0", Path(td))])

    def test_default_stub_tagger_never_tags(self) -> None:
        self.assertEqual(
            tag_prep.stub_tagger("v0.1.0", Path(".")),
            tag_prep.STATUS_NOT_RUN,
        )

    def test_cli_default_is_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            clog = Path(td) / "CHANGELOG.md"
            clog.write_text(CHANGELOG_V010, encoding="utf-8")
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                rc = tag_prep.main(
                    ["--version", "0.1.0", "--changelog", str(clog)]
                )
            self.assertEqual(rc, 0)
            out = buf.getvalue()
            self.assertIn("mode=dry-run", out)
            self.assertIn("planned_tag=v0.1.0", out)
            self.assertIn("published=no", out)
            self.assertIn("push=no", out)

    def test_cli_apply_alone_gate_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            clog = Path(td) / "CHANGELOG.md"
            clog.write_text(CHANGELOG_V010, encoding="utf-8")
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                rc = tag_prep.main(
                    [
                        "--apply",
                        "--version",
                        "0.1.0",
                        "--changelog",
                        str(clog),
                        "--repo",
                        td,
                    ]
                )
            self.assertEqual(rc, 3)
            out = buf.getvalue()
            self.assertIn("tag_status=GATE_BLOCKED", out)
            self.assertIn("published=no", out)
            self.assertNotIn("published=yes", out)

    def test_cli_apply_with_owner_approved_stub(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            clog = Path(td) / "CHANGELOG.md"
            clog.write_text(CHANGELOG_V010, encoding="utf-8")
            plan = tag_prep.plan_from_argv(
                [
                    "--apply",
                    "--owner-approved",
                    "--version",
                    "0.1.0",
                    "--changelog",
                    str(clog),
                    "--repo",
                    td,
                ],
                tagger=tag_prep.stub_tagger,
            )
            self.assertEqual(plan.tag_status, tag_prep.STATUS_NOT_RUN)
            self.assertEqual(plan.gate_status, tag_prep.GATE_OPEN)
            self.assertFalse(plan.published)
            self.assertFalse(plan.push)

    def test_cli_push_rejected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            tag_prep.plan_from_argv(["--push"])
        self.assertIn("push is not implemented", str(ctx.exception))

    def test_cli_owner_approved_without_apply_rejected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            tag_prep.plan_from_argv(["--owner-approved"])
        self.assertIn("--owner-approved only valid with --apply", str(ctx.exception))

    def test_rerunnable_same_plan(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            clog = Path(td) / "CHANGELOG.md"
            clog.write_text(CHANGELOG_V010, encoding="utf-8")
            a = tag_prep.plan_tag(changelog_path=clog, apply=False)
            b = tag_prep.plan_tag(changelog_path=clog, apply=False)
            self.assertEqual(a.to_dict(), b.to_dict())


if __name__ == "__main__":
    raise SystemExit(
        0 if unittest.main(verbosity=2, exit=False).result.wasSuccessful() else 1
    )
