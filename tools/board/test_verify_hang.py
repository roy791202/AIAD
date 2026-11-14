"""Unit tests for BDD-PD-VERIFY-HANG-01 (tools/board/verify_hang.py)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import build_result as br
import verify_hang as vh


class TestRefuseForgedPass(unittest.TestCase):
    def test_not_run_cannot_become_pass(self):
        self.assertEqual(vh.refuse_forged_pass("PASS", ["NOT RUN"]), "NOT RUN")
        self.assertEqual(vh.refuse_forged_pass("PASS", ["PARTIAL"]), "PARTIAL")
        self.assertEqual(vh.refuse_forged_pass("PASS", ["FAIL"]), "FAIL")
        self.assertEqual(vh.refuse_forged_pass("PARTIAL", ["NOT RUN"]), "PARTIAL")

    def test_empty_hung_keeps_base(self):
        self.assertEqual(vh.refuse_forged_pass("PASS", []), "PASS")


class TestSummarizeElev(unittest.TestCase):
    def test_missing_payload_is_not_run(self):
        self.assertEqual(vh.summarize_elev(vh.missing_payload("elev")), "NOT RUN")

    def test_dry_run_packaging_json_is_not_run(self):
        payload = {
            "overall": "PARTIAL",
            "elevated_process": False,
            "run_elevated": False,
            "live_executed": False,
            "checks": [
                {"id": "VI-CONTRACT-MSI", "status": "PASS"},
                {"id": "VI-EXIT-INSTALL", "status": "NOT RUN"},
                {"id": "VI-FILE-EXE", "status": "NOT RUN"},
            ],
        }
        self.assertEqual(vh.summarize_elev(payload), "NOT RUN")

    def test_live_fail_rolls_fail(self):
        payload = {
            "overall": "FAIL",
            "live_executed": True,
            "run_elevated": True,
            "checks": [
                {"id": "VI-EXIT-INSTALL", "status": "FAIL"},
                {"id": "VI-EXIT-UNINSTALL", "status": "PASS"},
            ],
        }
        self.assertEqual(vh.summarize_elev(payload), "FAIL")

    def test_live_partial(self):
        payload = {
            "overall": "PARTIAL",
            "elevated": True,
            "checks": [
                {"id": "VI-EXIT-INSTALL", "status": "PASS"},
                {"id": "VI-FILE-EXE", "status": "PARTIAL"},
            ],
        }
        self.assertEqual(vh.summarize_elev(payload), "PARTIAL")


class TestSummarizeLive(unittest.TestCase):
    def test_missing_is_not_run(self):
        self.assertEqual(vh.summarize_live(vh.missing_payload("live")), "NOT RUN")

    def test_fixture_pass_without_execute_refused(self):
        payload = {"overall": "PASS", "live_executed": False, "checks": []}
        self.assertEqual(vh.summarize_live(payload), "NOT RUN")

    def test_executed_fail(self):
        payload = {
            "status": "FAIL",
            "live_executed": True,
            "checks": [{"id": "smoke", "status": "FAIL"}],
        }
        self.assertEqual(vh.summarize_live(payload), "FAIL")


class TestAttach(unittest.TestCase):
    def _pass_result(self) -> dict:
        result = br.build_result(
            version="0.1.0",
            summary="hang test",
            artifacts=[],
            verification=[{"name": "unit", "status": "PASS"}],
            status="PASS",
            signing_status="PASS",
        )
        result["status"] = "PASS"
        return result

    def test_missing_inputs_refuse_pass(self):
        result = self._pass_result()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reports").mkdir()
            (root / "packaging/windows/wix/out").mkdir(parents=True)
            vh.attach_verify_hang(result, repo=root)
            self.assertNotEqual(result["status"], "PASS")
            self.assertEqual(result["status"], "NOT RUN")
            names = {r["name"]: r["status"] for r in result["verification"]}
            self.assertEqual(names[vh.ELEV_ROW], "NOT RUN")
            self.assertEqual(names[vh.LIVE_ROW], "NOT RUN")
            self.assertIn(vh.BDD_ID, result["requirementTraceability"])

    def test_fixture_elev_fail_and_live_not_run(self):
        result = self._pass_result()
        elev = {
            "live_executed": True,
            "run_elevated": True,
            "overall": "FAIL",
            "checks": [{"id": "VI-EXIT-INSTALL", "status": "FAIL"}],
            "evidence": "fixture/elev.json",
            "source": "file",
        }
        live = vh.missing_payload("live", evidence="reports/")
        vh.attach_verify_hang(result, elev=elev, live=live)
        self.assertEqual(result["status"], "FAIL")
        names = {r["name"]: r["status"] for r in result["verification"]}
        self.assertEqual(names[vh.ELEV_ROW], "FAIL")
        self.assertEqual(names[vh.LIVE_ROW], "NOT RUN")

    def test_load_elev_from_packaging_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "packaging/windows/wix/out"
            out.mkdir(parents=True)
            payload = {
                "overall": "PARTIAL",
                "elevated_process": False,
                "run_elevated": False,
                "live_executed": False,
                "checks": [
                    {"id": "VI-CONTRACT-MSI", "status": "PASS"},
                    {"id": "VI-EXIT-INSTALL", "status": "NOT RUN"},
                ],
            }
            (out / "verify-install-result.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            loaded = vh.load_elev_verify(repo=root)
            self.assertEqual(loaded["status"], "NOT RUN")
            self.assertEqual(loaded["source"], "file")

    def test_write_hang_summary(self):
        result = self._pass_result()
        vh.attach_verify_hang(
            result,
            elev=vh.missing_payload("elev"),
            live=vh.missing_payload("live"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = vh.write_hang_summary(result, repo=root)
            self.assertTrue(path.is_file())
            text = path.read_text(encoding="utf-8")
            self.assertIn("NOT RUN must not be written as PASS", text)
            self.assertTrue(path.with_suffix(".json").is_file())


if __name__ == "__main__":
    unittest.main()
