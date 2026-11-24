"""Unit tests for BDD-PD-REL-HANG-FINAL-01 (tools/board/rel_hang_final.py)."""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

import rel_hang_final as rhf


def _seed_board_json(root: Path) -> Path:
    """A board file that release tools must never touch (PD-BOARD-GAPS-RELEASE-01)."""
    board = root / "docs" / "board.json"
    board.parent.mkdir(parents=True, exist_ok=True)
    board.write_text('{"items": []}\n', encoding="utf-8", newline="\n")
    return board


def _seed_final_br(root: Path, *, status: str = "PARTIAL", signing: str = "NOT RUN") -> Path:
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    md = reports / "build-0.1.0-final-20261024T120000.md"
    md.write_text(
        "# Build Result — v0.1.0\n\n"
        "- **Status:** %s\n\n## Signing status\n\n%s\n" % (status, signing),
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
                "generatedAt": "2026-10-24T12:00:00+08:00",
                "id": "v0.1.0",
                "kind": "installer",
                "recordedBy": "agent",
                "artifacts": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return md


class TestFindLatestFinalBr(unittest.TestCase):
    def test_picks_newest_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            older = reports / "build-0.1.0-final-20261024T100000.md"
            newer = reports / "build-0.1.0-final-20261024T130000.md"
            older.write_text("# old\n", encoding="utf-8")
            newer.write_text("# new\n", encoding="utf-8")
            # Ensure mtime order.
            older.touch()
            time.sleep(0.05)
            newer.write_text("# new2\n", encoding="utf-8")
            found = rhf.find_latest_final_br(root)
            self.assertIsNotNone(found)
            self.assertEqual(found.name, newer.name)

    def test_ignores_non_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            (reports / "build-0.1.0-br-refresh.md").write_text("# x\n", encoding="utf-8")
            self.assertIsNone(rhf.find_latest_final_br(root))


class TestRefuseSigningForgedPass(unittest.TestCase):
    def test_not_run_stays_not_run(self):
        rel = {"signingStatus": "NOT RUN", "buildResultStatus": "PARTIAL"}
        rhf.refuse_signing_forged_pass(rel)
        self.assertEqual(rel["signingStatus"], "NOT RUN")

    def test_forged_pass_demoted(self):
        rel = {
            "signingStatus": "PASS",
            "buildResultStatus": "PARTIAL",
            "_forgedSigningPass": True,
        }
        rhf.refuse_signing_forged_pass(rel)
        self.assertEqual(rel["signingStatus"], "NOT RUN")

    def test_pass_with_partial_br_demoted(self):
        rel = {"signingStatus": "PASS", "buildResultStatus": "PARTIAL"}
        rhf.refuse_signing_forged_pass(rel)
        self.assertEqual(rel["signingStatus"], "NOT RUN")


class TestCollectKeyArtifacts(unittest.TestCase):
    def test_includes_msi_and_sbom_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            msi = root / rhf.MSI_REL
            msi.parent.mkdir(parents=True)
            msi.write_bytes(b"MZ-fake-msi")
            reports = root / "reports"
            reports.mkdir()
            cdx = reports / "sbom-20261024T110000.cdx.json"
            spdx = reports / "sbom-20261024T110000.spdx.json"
            cdx.write_text('{"bomFormat":"CycloneDX"}', encoding="utf-8")
            spdx.write_text('{"spdxVersion":"SPDX-2.3"}', encoding="utf-8")
            arts = rhf.collect_key_artifacts(repo=root, include_missing=False)
            labels = [a["label"] for a in arts]
            self.assertIn("MSI", labels)
            self.assertIn("SBOM-CycloneDX", labels)
            self.assertIn("SBOM-SPDX", labels)
            self.assertTrue(all(a.get("exists") for a in arts))


class TestHangFinalToRelease(unittest.TestCase):
    def test_updates_report_path_and_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            md = _seed_final_br(root, status="PARTIAL", signing="NOT RUN")
            msi = root / rhf.MSI_REL
            msi.parent.mkdir(parents=True)
            msi.write_bytes(b"MZ")
            reports = root / "reports"
            (reports / "sbom-test.cdx.json").write_text("{}", encoding="utf-8")
            (reports / "sbom-test.spdx.json").write_text("{}", encoding="utf-8")

            board = _seed_board_json(root)
            before = board.read_bytes()

            stored = rhf.hang_final_to_release(
                report_path=md,
                repo=root,
                embed_report_md=False,
                include_missing_artifacts=False,
            )
            self.assertEqual(stored["version"], "0.1.0")
            self.assertEqual(stored["buildResultStatus"], "PARTIAL")
            self.assertEqual(stored["signingStatus"], "NOT RUN")
            self.assertTrue(
                str(stored["reportPath"]).endswith("build-0.1.0-final-20261024T120000.md")
            )
            labels = {a["label"] for a in stored["artifacts"]}
            self.assertIn("MSI", labels)
            self.assertIn("SBOM-CycloneDX", labels)
            self.assertIn("SBOM-SPDX", labels)

            release_json = md.with_name(md.stem + ".release.json")
            self.assertEqual(json.loads(release_json.read_text(encoding="utf-8")), stored)
            self.assertIn("final-", stored["reportPath"])
            self.assertEqual(board.read_bytes(), before)
            self.assertFalse((root / "docs" / "PROJECT-BOARD.html").exists())

    def test_never_writes_signing_pass_from_not_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            md = _seed_final_br(root, status="PARTIAL", signing="NOT RUN")
            stored = rhf.hang_final_to_release(
                report_path=md,
                repo=root,
                embed_report_md=False,
                include_missing_artifacts=False,
            )
            self.assertNotEqual(stored.get("signingStatus"), "PASS")
            self.assertEqual(stored["signingStatus"], "NOT RUN")
            self.assertTrue(md.with_name(md.stem + ".release.json").is_file())
            # Even if someone mutates meta to forge — refuse helper demotes.
            forged = dict(stored)
            forged["signingStatus"] = "PASS"
            forged["_forgedSigningPass"] = True
            rhf.refuse_signing_forged_pass(forged)
            self.assertEqual(forged["signingStatus"], "NOT RUN")

    def test_cli_has_no_board_option(self):
        with self.assertRaises(SystemExit):
            rhf.build_parser().parse_args(["--board", "x.html", "hang"])


if __name__ == "__main__":
    unittest.main()
