"""Unit tests for BDD-PD-SEC-SCAN-01 (tools/board/sec_scan.py)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import build_result as br
import sec_scan as ss


class TestTriageAndIds(unittest.TestCase):
    def test_load_triage_list_and_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "triage.json"
            p.write_text(json.dumps(["a", {"id": "b"}]), encoding="utf-8")
            self.assertEqual(ss.load_triage(p), {"a", "b"})
            p.write_text(json.dumps({"waived": [{"id": "c"}, "d"]}), encoding="utf-8")
            self.assertEqual(ss.load_triage(p), {"c", "d"})
            self.assertEqual(ss.load_triage(None), set())


class TestUntriagedHighAndRollup(unittest.TestCase):
    def test_untriaged_high_filters_waived(self):
        findings = [
            {"id": "cve|1", "severity": "HIGH"},
            {"id": "cve|2", "severity": "LOW"},
            {"id": "cve|3", "severity": "CRITICAL"},
        ]
        high = ss.untriaged_high(findings, {"cve|1"})
        self.assertEqual([h["id"] for h in high], ["cve|3"])

    def test_rollup_forces_fail_when_high_untriaged(self):
        legs = [
            {"status": "PASS"},
            {"status": "PASS"},
        ]
        self.assertEqual(ss.rollup_scan_status(legs, high_untriaged=1), "FAIL")
        self.assertEqual(ss.rollup_scan_status(legs, high_untriaged=0), "PASS")
        legs2 = [{"status": "NOT RUN"}, {"status": "PASS"}]
        self.assertEqual(ss.rollup_scan_status(legs2, high_untriaged=0), "NOT RUN")


class TestSecurityGate(unittest.TestCase):
    def test_pass_forged_blocked_when_high(self):
        scan = {
            "status": "FAIL",
            "gate": {"blocksBuildPass": True, "untriagedHighCount": 2},
        }
        self.assertEqual(ss.apply_security_gate("PASS", scan), "FAIL")
        self.assertEqual(ss.apply_security_gate("PARTIAL", scan), "FAIL")
        self.assertEqual(ss.apply_security_gate("NOT RUN", scan), "FAIL")

    def test_missing_scan_downgrades_pass(self):
        self.assertEqual(ss.apply_security_gate("PASS", None), "NOT RUN")
        self.assertEqual(ss.apply_security_gate("FAIL", None), "FAIL")

    def test_clean_scan_allows_pass_rollup(self):
        scan = {
            "status": "PASS",
            "gate": {"blocksBuildPass": False, "untriagedHighCount": 0},
        }
        self.assertEqual(ss.apply_security_gate("PASS", scan), "PASS")
        self.assertEqual(ss.apply_security_gate("PARTIAL", scan), "PARTIAL")


class TestAttachAndWrite(unittest.TestCase):
    def test_attach_refuses_forged_pass(self):
        result = br.build_result(
            version="0.1.0",
            summary="x",
            artifacts=[],
            verification=[{"name": "unit", "status": "PASS"}],
            status="PASS",
            signing_status="PASS",
        )
        result["status"] = "PASS"
        scan = ss.build_scan_result(
            secret_leg={
                "name": "secret-scan",
                "tool": "gitleaks",
                "status": "FAIL",
                "detail": "1 finding",
                "findings": [
                    {
                        "id": "secret|aws|a.py|1",
                        "kind": "secret",
                        "severity": "HIGH",
                        "description": "leak",
                    }
                ],
            },
            cve_leg={
                "name": "cve-scan",
                "tool": "trivy",
                "status": "PASS",
                "detail": "clean",
                "findings": [],
            },
            waived=set(),
            generated_at="2026-10-24T12:00:00+08:00",
            repo_rel_evidence="reports/sec-scan-demo.md",
        )
        self.assertEqual(scan["status"], "FAIL")
        self.assertTrue(scan["gate"]["blocksBuildPass"])
        ss.attach_to_build_result(result, scan)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("PD-SEC-SCAN-01", result["securitySummary"])
        self.assertIn("untriagedHigh", result["securitySummary"])
        names = [r["name"] for r in result["verification"]]
        self.assertIn("secret-scan", names)
        self.assertIn("SEC-GATE", names)

    def test_waived_high_allows_pass(self):
        fid = "secret|aws|a.py|1"
        scan = ss.build_scan_result(
            secret_leg={
                "name": "secret-scan",
                "tool": "gitleaks",
                "status": "FAIL",
                "detail": "1",
                "findings": [{"id": fid, "kind": "secret", "severity": "HIGH"}],
            },
            cve_leg={
                "name": "cve-scan",
                "tool": "trivy",
                "status": "PASS",
                "detail": "clean",
                "findings": [],
            },
            waived={fid},
            generated_at="2026-10-24T12:00:00+08:00",
        )
        self.assertEqual(scan["gate"]["untriagedHighCount"], 0)
        self.assertFalse(scan["gate"]["blocksBuildPass"])
        self.assertEqual(scan["status"], "PASS")
        result = {
            "status": "PASS",
            "verification": [],
            "pending": [],
            "risks": [],
            "requirementTraceability": [],
        }
        ss.attach_to_build_result(result, scan)
        self.assertEqual(result["status"], "PASS")

    def test_write_scan_report(self):
        scan = ss.build_scan_result(
            secret_leg={
                "name": "secret-scan",
                "tool": "gitleaks",
                "status": "PASS",
                "detail": "clean",
                "findings": [],
            },
            cve_leg={
                "name": "cve-scan",
                "tool": "trivy",
                "status": "PASS",
                "detail": "clean",
                "findings": [],
            },
            generated_at="2026-10-24T12:00:00+08:00",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = ss.write_scan_report(scan, repo=root)
            self.assertTrue(path.is_file())
            self.assertTrue(path.with_suffix(".json").is_file())
            md = path.read_text(encoding="utf-8")
            self.assertIn("**Status:** PASS", md)
            self.assertIn("PASS | FAIL | PARTIAL | NOT RUN", md)
            data = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(data["schema"], ss.SCHEMA)
            self.assertEqual(data["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
