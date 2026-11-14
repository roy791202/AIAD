"""Unit tests for BDD-PD-BR-FINAL-01 hang rules (SBOM / Rel-Freeze / GoNoGo)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import build_result as br


def _base_pass_result(**kwargs):
    result = br.build_result(
        version="0.1.0",
        summary="final hang base",
        artifacts=[],
        verification=[{"name": "unit", "status": "PASS"}],
        status="PASS",
        signing_status="PASS",
        **kwargs,
    )
    result["status"] = "PASS"
    result["signingStatus"] = "PASS"
    return result


class TestRefuseHangForgedPass(unittest.TestCase):
    def test_signing_not_run_blocks_forged_pass(self):
        result = _base_pass_result()
        result["signingStatus"] = "NOT RUN"
        result["verification"] = [
            br.build_verification_row("unit", "PASS"),
            br.build_verification_row("SIGNING", "NOT RUN"),
        ]
        br.refuse_hang_forged_pass(result)
        self.assertNotEqual(result["status"], "PASS")
        self.assertEqual(result["signingStatus"], "NOT RUN")

    def test_does_not_promote_not_run_to_pass(self):
        result = br.build_result(
            version="0.1.0",
            summary="x",
            artifacts=[],
            verification=[{"name": "t", "status": "NOT RUN"}],
            status="NOT RUN",
            signing_status="NOT RUN",
        )
        # Even if someone injects only PASS rows without updating status first:
        result["verification"] = [br.build_verification_row("fake", "PASS")]
        result["signingStatus"] = "NOT RUN"
        br.refuse_hang_forged_pass(result)
        self.assertNotEqual(result["status"], "PASS")
        self.assertEqual(result["signingStatus"], "NOT RUN")


class TestAttachRelFreeze(unittest.TestCase):
    def test_missing_freeze_refuses_pass(self):
        result = _base_pass_result()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reports").mkdir()
            br.attach_rel_freeze(result, repo=root)
            self.assertNotEqual(result["status"], "PASS")
            names = [r["name"] for r in result["verification"]]
            self.assertIn("REL-FREEZE", names)
            freeze = next(r for r in result["verification"] if r["name"] == "REL-FREEZE")
            self.assertEqual(freeze["status"], "NOT RUN")

    def test_partial_freeze_keeps_partial(self):
        result = _base_pass_result()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            md = reports / "milestone-validation-v0.1.md"
            md.write_text(
                "# Milestone\n\n## 8. Rel-Freeze\n\n"
                "| Field | Value |\n|-------|--------|\n"
                "| Status | **PARTIAL** |\n",
                encoding="utf-8",
            )
            br.attach_rel_freeze(result, freeze_path=md, repo=root)
            self.assertEqual(result["status"], "PARTIAL")
            freeze = next(r for r in result["verification"] if r["name"] == "REL-FREEZE")
            self.assertEqual(freeze["status"], "PARTIAL")


class TestAttachGonogo(unittest.TestCase):
    def test_missing_gonogo_refuses_pass(self):
        result = _base_pass_result()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reports").mkdir()
            br.attach_gonogo(result, repo=root)
            self.assertNotEqual(result["status"], "PASS")
            self.assertIn("PD-REL-GONOGO-01 NOT RUN", result["gonogoSummary"])

    def test_go_with_partial_keeps_signing_not_run(self):
        result = _base_pass_result()
        payload = {
            "schema": "aiad.gonogo.v1",
            "verdict": "Go-with-PARTIAL",
            "gateRef": "PD-DEC-V01-GATE-01",
            "legs": {
                "build_result": "PARTIAL",
                "signing": "NOT RUN",
                "sbom": "PASS",
            },
            "sources": {"signing": "packaging/windows/out/sign-authenticode-result.json"},
            "readyForGreen": True,
        }
        br.attach_gonogo(result, payload, repo=Path("."))
        self.assertEqual(result["signingStatus"], "NOT RUN")
        self.assertEqual(result["status"], "PARTIAL")
        self.assertNotEqual(result["status"], "PASS")
        g = next(r for r in result["verification"] if r["name"] == "GONOGO")
        self.assertEqual(g["status"], "PARTIAL")
        gs = next(r for r in result["verification"] if r["name"] == "GONOGO-SIGNING")
        self.assertEqual(gs["status"], "NOT RUN")

    def test_hang_must_not_force_signing_pass(self):
        """BDD: 不做強制簽章 PASS — gonogo cannot rewrite signing NOT RUN → PASS."""
        result = br.build_result(
            version="0.1.0",
            summary="x",
            artifacts=[],
            verification=[{"name": "t", "status": "PARTIAL"}],
            status="PARTIAL",
            signing_status="NOT RUN",
        )
        payload = {
            "verdict": "Go",
            "legs": {"signing": "PASS", "build_result": "PASS"},
            "sources": {},
            "readyForGreen": True,
        }
        br.attach_gonogo(result, payload)
        self.assertEqual(result["signingStatus"], "NOT RUN")
        self.assertNotEqual(result["status"], "PASS")


class TestAttachSbomWithFinalGate(unittest.TestCase):
    def test_sbom_hang_plus_signing_not_run_not_pass(self):
        result = _base_pass_result()
        result["signingStatus"] = "NOT RUN"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            sbom = {
                "schema": "aiad.sbom.v1",
                "cardId": "PD-SBOM-01",
                "bdd": "BDD-PD-SBOM-01",
                "status": "PASS",
                "summary": "ok",
                "legs": [
                    {
                        "name": "sbom-cyclonedx",
                        "status": "PASS",
                        "detail": "ok",
                        "artifact": "reports/sbom.cdx.json",
                    }
                ],
                "artifacts": ["reports/sbom.cdx.json"],
                "evidence": "reports/sbom.md",
                "gate": {"blocksBuildPass": False, "untriagedHighCount": 0},
            }
            (reports / "sbom-test.json").write_text(
                json.dumps(sbom), encoding="utf-8"
            )
            br.attach_sbom(result, sbom, repo=root)
            result["verification"].append(
                br.build_verification_row("SIGNING", "NOT RUN")
            )
            br.refuse_hang_forged_pass(result)
            self.assertNotEqual(result["status"], "PASS")


class TestFinalPath(unittest.TestCase):
    def test_final_report_path_name(self):
        p = br.final_report_path(
            "0.1.0",
            generated_at="2026-10-24T13:30:00+08:00",
            repo=Path("D:/AIAD"),
        )
        self.assertTrue(p.name.startswith("build-0.1.0-final-"))
        self.assertTrue(p.name.endswith(".md"))

    def test_parse_rel_freeze_status(self):
        text = (
            "## 8. Rel-Freeze\n\n| Field | Value |\n|---|---|\n"
            "| Status | **PARTIAL** |\n"
        )
        self.assertEqual(br.parse_rel_freeze_status(text), "PARTIAL")
        self.assertEqual(br.parse_rel_freeze_status(""), "NOT RUN")


if __name__ == "__main__":
    unittest.main()
