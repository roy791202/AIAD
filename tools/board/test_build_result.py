"""Unit tests for BDD-PD-BUILD-RESULT-01 (tools/board/build_result.py)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import build_result as br
import release_report


class TestStatusVocabulary(unittest.TestCase):
    def test_allowed_statuses(self):
        for s in ("PASS", "FAIL", "BLOCKED", "NOT RUN", "PARTIAL"):
            self.assertEqual(br.normalize_status(s), s)

    def test_aliases(self):
        self.assertEqual(br.normalize_status("not_run"), "NOT RUN")
        self.assertEqual(br.normalize_status("skipped"), "NOT RUN")
        self.assertEqual(br.normalize_status("failed"), "FAIL")

    def test_reject_unknown(self):
        with self.assertRaises(br.BuildResultError):
            br.normalize_status("GREEN")
        with self.assertRaises(br.BuildResultError):
            br.normalize_status("success")

    def test_rollup_worst_wins(self):
        self.assertEqual(br.rollup_status(["PASS", "NOT RUN"]), "NOT RUN")
        self.assertEqual(br.rollup_status(["PASS", "PARTIAL", "NOT RUN"]), "PARTIAL")
        self.assertEqual(br.rollup_status(["PARTIAL", "FAIL"]), "FAIL")
        self.assertEqual(br.rollup_status(["PASS", "BLOCKED"]), "BLOCKED")
        self.assertEqual(br.rollup_status([]), "NOT RUN")


class TestBuildResultShape(unittest.TestCase):
    def test_required_fields_and_status(self):
        result = br.build_result(
            version="0.1.0",
            summary="demo",
            artifacts=[{"label": "MSI", "path": "out/x.msi", "exists": True}],
            verification=[
                {"name": "unit", "status": "PASS"},
                {"name": "install", "status": "NOT RUN"},
            ],
        )
        self.assertEqual(result["status"], "NOT RUN")
        self.assertIn("summary", result)
        self.assertIn("artifacts", result)
        self.assertIn("verification", result)
        self.assertEqual(result["signingStatus"], "NOT RUN")
        md = br.render_markdown(result)
        self.assertIn("## Summary", md)
        self.assertIn("## Artifacts", md)
        self.assertIn("## Verification", md)
        self.assertIn("**Status:** NOT RUN", md)
        for s in br.VALID_STATUSES:
            # vocabulary documented by presence of at least Status line using one of them
            self.assertTrue(isinstance(s, str))

    def test_explicit_status_override(self):
        result = br.build_result(
            version="v0.1.0",
            summary="demo",
            artifacts=[],
            verification=[{"name": "a", "status": "PASS"}],
            status="PARTIAL",
            signing_status="NOT RUN",
        )
        self.assertEqual(result["version"], "0.1.0")
        self.assertEqual(result["status"], "PARTIAL")


class TestSecurityHang(unittest.TestCase):
    def test_attach_security_missing_scan_refuses_pass(self):
        result = br.build_result(
            version="0.1.0",
            summary="sec hang",
            artifacts=[],
            verification=[{"name": "t", "status": "PASS"}],
            status="PASS",
            signing_status="PASS",
        )
        result["status"] = "PASS"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reports").mkdir()
            br.attach_security_scan(result, repo=root)
            self.assertEqual(result["status"], "NOT RUN")
            self.assertIn("PD-SEC-SCAN-01 NOT RUN", result["securitySummary"])


class TestSbomHang(unittest.TestCase):
    def test_attach_sbom_missing_refuses_pass(self):
        result = br.build_result(
            version="0.1.0",
            summary="sbom hang",
            artifacts=[],
            verification=[{"name": "t", "status": "PASS"}],
            status="PASS",
            signing_status="PASS",
        )
        result["status"] = "PASS"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reports").mkdir()
            br.attach_sbom(result, repo=root)
            self.assertEqual(result["status"], "NOT RUN")
            self.assertIn("PD-SBOM-01 NOT RUN", result["sbomSummary"])


class TestWriteAndHang(unittest.TestCase):
    def test_write_reports_and_releases(self):
        result = br.build_result(
            version="0.1.0",
            summary="write test",
            artifacts=[],
            verification=[{"name": "t", "status": "PARTIAL"}],
            status="PARTIAL",
            generated_at="2026-10-24T02:00:00+08:00",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for dest in ("reports", "releases"):
                path = br.default_report_path(
                    "0.1.0",
                    generated_at=result["generatedAt"],
                    dest=dest,
                    repo=root,
                )
                written = br.write_report(result, path, also_json=True, repo=root)
                self.assertTrue(written.is_file())
                self.assertTrue(written.with_suffix(".json").is_file())
                self.assertIn(dest, str(written).replace("\\", "/"))
                data = json.loads(written.with_suffix(".json").read_text(encoding="utf-8"))
                self.assertEqual(data["status"], "PARTIAL")
                self.assertEqual(data["schema"], "aiad.build-result.v1")

    def test_hang_to_release_uses_release_report(self):
        """Hang Build Result into snapshot.releases via release_report (fake board)."""
        # Minimal board HTML shell + snapshot (matches snapshot_safe landmarks).
        snap = {
            "asOf": "2026-10-24T00:00:00+08:00",
            "tasks": [],
            "releases": [],
        }
        html = (
            "<!DOCTYPE html>\n<html><head><title>t</title></head>"
            '<body><div class="nav">導覽</div>'
            '<script type="application/json" id="board-snapshot">\n'
            + json.dumps(snap, ensure_ascii=False, indent=2)
            + "\n</script>\n<script>/* runtime */</script></body></html>\n"
        )
        result = br.build_result(
            version="0.1.0",
            summary="hang",
            artifacts=[
                release_report.build_artifact(
                    Path("missing.msi"), "MSI", "2026-10-24T02:00:00+08:00", Path(".")
                )
            ],
            verification=[{"name": "t", "status": "PARTIAL"}],
            status="PARTIAL",
            generated_at="2026-10-24T02:00:00+08:00",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            board = root / "PROJECT-BOARD.html"
            board.write_text(html, encoding="utf-8", newline="\n")
            report = root / "reports" / "build-0.1.0-test.md"
            report.parent.mkdir(parents=True)
            br.write_report(result, report, also_json=False, repo=root)
            stored = br.hang_to_release(board, result, report, repo=root)
            self.assertEqual(stored.get("version"), "0.1.0")
            self.assertEqual(stored.get("buildResultStatus"), "PARTIAL")
            self.assertTrue(str(stored.get("reportPath") or "").endswith("build-0.1.0-test.md"))
            rels = release_report.list_releases(board)
            self.assertEqual(len(rels), 1)
            self.assertEqual(rels[0]["buildResultStatus"], "PARTIAL")


if __name__ == "__main__":
    unittest.main()
