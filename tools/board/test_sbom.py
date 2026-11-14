"""Unit tests for BDD-PD-SBOM-01 (tools/board/sbom.py)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import build_result as br
import sbom as sm


class TestRollupAndGate(unittest.TestCase):
    def test_rollup_worst_wins(self):
        self.assertEqual(
            sm.rollup_sbom_status([{"status": "PASS"}, {"status": "NOT RUN"}]),
            "NOT RUN",
        )
        self.assertEqual(
            sm.rollup_sbom_status([{"status": "PASS"}, {"status": "FAIL"}]),
            "FAIL",
        )
        self.assertEqual(sm.rollup_sbom_status([]), "NOT RUN")

    def test_pass_forged_blocked_when_high_from_sec(self):
        payload = sm.build_sbom_result(
            legs=[
                {
                    "name": "sbom-cyclonedx",
                    "tool": "syft",
                    "format": "cyclonedx-json",
                    "status": "PASS",
                    "detail": "ok",
                    "componentCount": 3,
                    "artifact": "reports/sbom-x.cdx.json",
                }
            ],
            sec_gate={"blocksBuildPass": True, "untriagedHighCount": 2},
            generated_at="2026-10-24T13:00:00+08:00",
        )
        self.assertTrue(payload["gate"]["blocksBuildPass"])
        self.assertEqual(payload["gate"]["untriagedHighCount"], 2)
        self.assertEqual(sm.apply_sbom_gate("PASS", payload), "FAIL")
        self.assertEqual(sm.apply_sbom_gate("PARTIAL", payload), "FAIL")
        self.assertEqual(sm.apply_sbom_gate("NOT RUN", payload), "FAIL")

    def test_missing_sbom_downgrades_pass(self):
        self.assertEqual(sm.apply_sbom_gate("PASS", None), "NOT RUN")
        self.assertEqual(sm.apply_sbom_gate("FAIL", None), "FAIL")

    def test_sbom_fail_refuses_pass(self):
        payload = sm.build_sbom_result(
            legs=[
                {
                    "name": "sbom-cyclonedx",
                    "tool": "syft",
                    "format": "cyclonedx-json",
                    "status": "FAIL",
                    "detail": "syft exit 2",
                    "componentCount": 0,
                    "artifact": "",
                }
            ],
            sec_gate=None,
            generated_at="2026-10-24T13:00:00+08:00",
        )
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(sm.apply_sbom_gate("PASS", payload), "FAIL")

    def test_clean_sbom_allows_pass_rollup(self):
        payload = sm.build_sbom_result(
            legs=[
                {
                    "name": "sbom-cyclonedx",
                    "tool": "syft",
                    "format": "cyclonedx-json",
                    "status": "PASS",
                    "detail": "ok",
                    "componentCount": 1,
                    "artifact": "reports/a.cdx.json",
                }
            ],
            sec_gate={"blocksBuildPass": False, "untriagedHighCount": 0},
            generated_at="2026-10-24T13:00:00+08:00",
        )
        self.assertFalse(payload["gate"]["blocksBuildPass"])
        self.assertEqual(sm.apply_sbom_gate("PASS", payload), "PASS")
        self.assertEqual(sm.apply_sbom_gate("PARTIAL", payload), "PARTIAL")


class TestAttachAndWrite(unittest.TestCase):
    def test_attach_refuses_forged_pass_when_high(self):
        result = br.build_result(
            version="0.1.0",
            summary="x",
            artifacts=[],
            verification=[{"name": "unit", "status": "PASS"}],
            status="PASS",
            signing_status="PASS",
        )
        result["status"] = "PASS"
        payload = sm.build_sbom_result(
            legs=[
                {
                    "name": "sbom-cyclonedx",
                    "tool": "syft",
                    "format": "cyclonedx-json",
                    "status": "PASS",
                    "detail": "ok",
                    "componentCount": 2,
                    "artifact": "reports/sbom-demo.cdx.json",
                }
            ],
            sec_gate={"blocksBuildPass": True, "untriagedHighCount": 1, "status": "FAIL"},
            generated_at="2026-10-24T13:00:00+08:00",
            repo_rel_evidence="reports/sbom-demo.md",
        )
        sm.attach_to_build_result(result, payload)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("PD-SBOM-01", result["sbomSummary"])
        self.assertIn("untriagedHigh", result["securitySummary"])
        names = [r["name"] for r in result["verification"]]
        self.assertIn("sbom-cyclonedx", names)
        self.assertIn("SBOM-GATE", names)
        self.assertIn(sm.BDD_ID, result["requirementTraceability"])

    def test_write_sbom_report(self):
        payload = sm.build_sbom_result(
            legs=[
                {
                    "name": "sbom-cyclonedx",
                    "tool": "syft",
                    "format": "cyclonedx-json",
                    "status": "PASS",
                    "detail": "clean",
                    "componentCount": 0,
                    "artifact": "reports/x.cdx.json",
                },
                {
                    "name": "sbom-spdx",
                    "tool": "syft",
                    "format": "spdx-json",
                    "status": "PASS",
                    "detail": "clean",
                    "componentCount": 0,
                    "artifact": "reports/x.spdx.json",
                },
            ],
            formats=["cyclonedx-json", "spdx-json"],
            generated_at="2026-10-24T13:00:00+08:00",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = sm.write_sbom_report(payload, repo=root)
            self.assertTrue(path.is_file())
            self.assertTrue(path.with_suffix(".json").is_file())
            md = path.read_text(encoding="utf-8")
            self.assertIn("**Status:** PASS", md)
            self.assertIn("PASS | FAIL | PARTIAL | NOT RUN", md)
            self.assertIn("cyclonedx-json", md)
            data = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(data["schema"], sm.SCHEMA)
            self.assertEqual(data["status"], "PASS")

    def test_syft_missing_is_not_run_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "apps" / "sgenaxis-desktop").mkdir(parents=True)
            with mock.patch.object(sm, "which", return_value=None):
                leg = sm.run_syft_leg(
                    root,
                    source=root / "apps" / "sgenaxis-desktop",
                    fmt="cyclonedx-json",
                    out_file=root / "reports" / "x.cdx.json",
                )
            self.assertEqual(leg["status"], "NOT RUN")
            self.assertIn("syft not on PATH", leg["detail"])
            payload = sm.build_sbom_result(legs=[leg], generated_at="2026-10-24T13:00:00+08:00")
            self.assertEqual(payload["status"], "NOT RUN")
            self.assertNotEqual(payload["status"], "PASS")


class TestLoadLatest(unittest.TestCase):
    def test_load_latest_skips_raw_cdx(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            (reports / "sbom-20261024T130000.cdx.json").write_text(
                json.dumps({"bomFormat": "CycloneDX", "components": []}),
                encoding="utf-8",
            )
            good = {
                "schema": sm.SCHEMA,
                "status": "PASS",
                "gate": {"blocksBuildPass": False, "untriagedHighCount": 0},
            }
            (reports / "sbom-20261024T130000.json").write_text(
                json.dumps(good), encoding="utf-8"
            )
            loaded = sm.load_latest_sbom(root)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["schema"], sm.SCHEMA)


if __name__ == "__main__":
    unittest.main()
