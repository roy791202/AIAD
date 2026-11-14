"""Unit tests for BDD-PD-REL-HANG-POST-01 (tools/board/rel_hang_post.py)."""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

import rel_hang_post as rhp
import release_report


def _mini_board(releases: list | None = None) -> str:
    snap = {
        "asOf": "2026-10-24T00:00:00+08:00",
        "tasks": [],
        "releases": list(releases or []),
    }
    return (
        "<!DOCTYPE html>\n<html><head><title>t</title></head>"
        '<body><div class="nav">導覽</div>'
        '<script type="application/json" id="board-snapshot">\n'
        + json.dumps(snap, ensure_ascii=False, indent=2)
        + "\n</script>\n<script>/* runtime */</script></body></html>\n"
    )


def _seed_br(
    root: Path,
    name: str,
    *,
    card_id: str,
    status: str = "PARTIAL",
    signing: str = "NOT RUN",
) -> Path:
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    md = reports / name
    md.write_text(
        "# Build Result — v0.1.0\n\n"
        "- **Status:** %s\n"
        "- **Card:** %s\n\n## Signing status\n\n%s\n" % (status, card_id, signing),
        encoding="utf-8",
    )
    side = md.with_suffix(".json")
    side.write_text(
        json.dumps(
            {
                "schema": "aiad.build-result.v1",
                "version": "0.1.0",
                "status": status,
                "signingStatus": signing,
                "generatedAt": "2026-10-24T14:46:26+08:00",
                "id": "v0.1.0",
                "kind": "installer",
                "recordedBy": "agent",
                "cardId": card_id,
                "artifacts": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return md


class TestFindPostRemainBr(unittest.TestCase):
    def test_prefers_soft_dep_card_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            older = _seed_br(
                root,
                "build-0.1.0-final-20261024T120000.md",
                card_id="PD-BR-FINAL-01",
            )
            post = _seed_br(
                root,
                "build-0.1.0-post-remain.md",
                card_id=rhp.SOFT_DEP_CARD,
            )
            older.touch()
            time.sleep(0.05)
            post.write_text(post.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            found = rhp.find_post_remain_br(root)
            self.assertIsNotNone(found)
            self.assertEqual(found.name, "build-0.1.0-post-remain.md")

    def test_fallback_best_available_when_no_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_br(
                root,
                "build-0.1.0-final-20261024T120000.md",
                card_id="PD-BR-FINAL-01",
            )
            self.assertIsNone(rhp.find_post_remain_br(root))
            best = rhp.find_best_available_br(root)
            self.assertIsNotNone(best)
            self.assertIn("final-", best.name)


class TestHangPostToRelease(unittest.TestCase):
    def test_hangs_post_remain_and_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            md = _seed_br(
                root,
                "build-0.1.0-post-remain.md",
                card_id=rhp.SOFT_DEP_CARD,
                status="PARTIAL",
                signing="NOT RUN",
            )
            msi = root / rhp.rhf.MSI_REL
            msi.parent.mkdir(parents=True)
            msi.write_bytes(b"MZ")
            reports = root / "reports"
            (reports / "sbom-test.cdx.json").write_text("{}", encoding="utf-8")
            (reports / "sbom-test.spdx.json").write_text("{}", encoding="utf-8")

            board = root / "PROJECT-BOARD.html"
            board.write_text(
                _mini_board(
                    [
                        {
                            "id": "v0.1.0",
                            "version": "0.1.0",
                            "reportPath": "reports/build-0.1.0-final-old.md",
                            "artifacts": [],
                            "buildResultStatus": "PARTIAL",
                            "cardId": "PD-REL-HANG-FINAL-01",
                        }
                    ]
                ),
                encoding="utf-8",
                newline="\n",
            )
            before = board.read_text(encoding="utf-8")
            self.assertTrue(before.lstrip().startswith("<!DOCTYPE"))

            stored = rhp.hang_post_to_release(
                board,
                report_path=md,
                repo=root,
                embed_report_md=False,
                include_missing_artifacts=False,
            )
            self.assertEqual(stored["version"], "0.1.0")
            self.assertEqual(stored["buildResultStatus"], "PARTIAL")
            self.assertEqual(stored["signingStatus"], "NOT RUN")
            self.assertEqual(stored["cardId"], rhp.CARD_ID)
            self.assertEqual(stored["bdd"], rhp.BDD_ID)
            self.assertEqual(stored["hangSource"], "post-remain")
            self.assertTrue(str(stored["reportPath"]).endswith("post-remain.md"))
            labels = {a["label"] for a in stored["artifacts"]}
            self.assertIn("MSI", labels)
            self.assertIn("SBOM-CycloneDX", labels)
            self.assertIn("SBOM-SPDX", labels)

            after = board.read_text(encoding="utf-8")
            self.assertTrue(after.lstrip().startswith("<!DOCTYPE"))
            self.assertIn('class="nav"', after)
            rels = release_report.list_releases(board)
            self.assertEqual(len(rels), 1)
            self.assertIn("post-remain", rels[0]["reportPath"])

    def test_best_available_stays_partial_no_forged_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            md = _seed_br(
                root,
                "build-0.1.0-final-20261024T120000.md",
                card_id="PD-BR-FINAL-01",
                status="PASS",
                signing="NOT RUN",
            )
            board = root / "PROJECT-BOARD.html"
            board.write_text(_mini_board(), encoding="utf-8", newline="\n")
            stored = rhp.hang_post_to_release(
                board,
                report_path=md,
                repo=root,
                embed_report_md=False,
                include_missing_artifacts=False,
            )
            self.assertEqual(stored["hangSource"], "best-available")
            self.assertEqual(stored["signingStatus"], "NOT RUN")
            self.assertNotEqual(stored["signingStatus"], "PASS")
            # Best-available + signing NOT RUN must not claim overall PASS.
            self.assertEqual(stored["buildResultStatus"], "PARTIAL")

    def test_refuse_forged_signing_pass(self):
        rel = {
            "signingStatus": "PASS",
            "buildResultStatus": "PARTIAL",
            "_forgedSigningPass": True,
        }
        rhp.refuse_signing_forged_pass(rel)
        self.assertEqual(rel["signingStatus"], "NOT RUN")


if __name__ == "__main__":
    unittest.main()
