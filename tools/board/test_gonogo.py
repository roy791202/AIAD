"""Unit tests for BDD-PD-REL-GONOGO-01 (tools/board/gonogo.py)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import gonogo as gg


class TestNeverPromoteNotRun(unittest.TestCase):
    def test_not_run_stays_not_run(self):
        self.assertEqual(gg.never_promote("NOT RUN"), "NOT RUN")
        self.assertEqual(gg.refuse_not_run_as_pass("NOT RUN"), "NOT RUN")
        self.assertEqual(gg.refuse_not_run_as_pass("skipped"), "NOT RUN")

    def test_blank_checklist_is_not_run(self):
        self.assertEqual(gg.normalize_leg_status("________"), "NOT RUN")
        self.assertEqual(gg.normalize_leg_status(""), "NOT RUN")
        self.assertEqual(gg.normalize_leg_status(None), "NOT RUN")

    def test_pass_and_partial_ok(self):
        self.assertEqual(gg.never_promote("PASS"), "PASS")
        self.assertEqual(gg.never_promote("PARTIAL"), "PARTIAL")


class TestVerdictRules(unittest.TestCase):
    def _legs(self, **overrides):
        base = {
            "build_result": "PARTIAL",
            "msi": "PASS",
            "elev": "NOT RUN",
            "sec": "PARTIAL",
            "sbom": "PASS",
            "signing": "NOT RUN",
            "changelog": "PASS",
        }
        base.update(overrides)
        return base

    def test_elev_sign_not_run_yields_go_with_partial(self):
        """V01-GATE: elev/sign NOT RUN → Go-with-PARTIAL (not Go, not forged PASS)."""
        verdict = gg.compute_verdict(self._legs())
        self.assertEqual(verdict, "Go-with-PARTIAL")
        # legs themselves must still report NOT RUN
        legs = self._legs()
        self.assertEqual(legs["elev"], "NOT RUN")
        self.assertEqual(legs["signing"], "NOT RUN")
        self.assertNotEqual(legs["elev"], "PASS")
        self.assertNotEqual(legs["signing"], "PASS")

    def test_all_pass_is_go(self):
        verdict = gg.compute_verdict(
            self._legs(
                build_result="PASS",
                elev="PASS",
                sec="PASS",
                signing="PASS",
                sbom="PASS",
            )
        )
        self.assertEqual(verdict, "Go")

    def test_fail_is_nogo(self):
        self.assertEqual(gg.compute_verdict(self._legs(msi="FAIL")), "NoGo")
        self.assertEqual(gg.compute_verdict(self._legs(sec="FAIL")), "NoGo")
        self.assertEqual(
            gg.compute_verdict(self._legs(build_result="FAIL")), "NoGo"
        )

    def test_blocked_is_nogo(self):
        self.assertEqual(
            gg.compute_verdict(self._legs(build_result="BLOCKED")), "NoGo"
        )

    def test_missing_build_result_is_nogo(self):
        self.assertEqual(
            gg.compute_verdict(self._legs(build_result="NOT RUN")), "NoGo"
        )

    def test_missing_msi_is_nogo(self):
        self.assertEqual(gg.compute_verdict(self._legs(msi="NOT RUN")), "NoGo")

    def test_partial_br_with_elev_pass_still_go_with_partial(self):
        verdict = gg.compute_verdict(
            self._legs(elev="PASS", signing="NOT RUN", build_result="PARTIAL")
        )
        self.assertEqual(verdict, "Go-with-PARTIAL")

    def test_hard_gate_elev_forces_nogo_when_enabled(self):
        verdict = gg.compute_verdict(
            self._legs(elev="NOT RUN"),
            elev_hard_gate=True,
        )
        self.assertEqual(verdict, "NoGo")

    def test_disallow_partial_forces_nogo(self):
        verdict = gg.compute_verdict(self._legs(), allow_partial=False)
        self.assertEqual(verdict, "NoGo")


class TestChecklistParse(unittest.TestCase):
    def test_blank_checklist_unfilled(self):
        text = """
### 1. MSI（Windows 安裝包）
- [ ] **MSI**
  - 狀態：`________`（PASS｜FAIL｜NOT RUN｜PARTIAL）

### 2. Elev（elevated VERIFY-INSTALL）
- [ ] **Elev**
  - 狀態：`________`

| # | 項 | 狀態 | 證據（路徑） |
|---|----|------|--------------|
| 1 | MSI | | |
| 2 | Elev | | |
"""
        st = gg.parse_checklist_statuses(text)
        self.assertIsNone(st["msi"])
        self.assertIsNone(st["elev"])
        self.assertFalse(gg.checklist_is_filled(st))

    def test_filled_summary_and_sections(self):
        text = """
### 1. MSI
  - 狀態：`PASS`

### 5. 簽章
  - 狀態：`NOT RUN`

| # | 項 | 狀態 | 證據（路徑） |
|---|----|------|--------------|
| 1 | MSI | PASS | reports/x |
| 2 | Elev | PARTIAL | elev.json |
| 3 | Sec | PASS | sec.md |
| 4 | SBOM | PASS | sbom.md |
| 5 | 簽章 | NOT RUN | sign.json |
| 6 | CHANGELOG | PASS | CHANGELOG.md |
"""
        st = gg.parse_checklist_statuses(text)
        self.assertTrue(gg.checklist_is_filled(st))
        self.assertEqual(st["msi"], "PASS")
        self.assertEqual(st["elev"], "PARTIAL")
        self.assertEqual(st["signing"], "NOT RUN")
        # Must not promote
        self.assertNotEqual(st["signing"], "PASS")


class TestBuildResultPick(unittest.TestCase):
    def test_prefers_partial_over_newer_not_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp)
            older = reports / "build-0.1.0-br-refresh.json"
            newer = reports / "build-0.1.0-with-sbom.json"
            older.write_text(
                json.dumps({"status": "PARTIAL", "version": "0.1.0"}),
                encoding="utf-8",
            )
            newer.write_text(
                json.dumps({"status": "NOT RUN", "version": "0.1.0"}),
                encoding="utf-8",
            )
            # Make with-sbom appear newer on disk
            import os
            import time

            now = time.time()
            os.utime(older, (now - 100, now - 100))
            os.utime(newer, (now, now))
            picked = gg.find_latest_build_result(reports)
            self.assertEqual(picked, older)


class TestDeriveAndAggregate(unittest.TestCase):
    def test_derive_from_build_result_preserves_not_run(self):
        result = {
            "status": "PARTIAL",
            "signingStatus": "NOT RUN",
            "artifacts": [
                {"label": "MSI", "path": "out/x.msi", "exists": True},
            ],
            "verification": [
                {"name": "MSI-ARTIFACT", "status": "PASS"},
                {"name": "ELEV-VERIFY", "status": "PASS"},
                {"name": "SIGNING", "status": "NOT RUN"},
                {"name": "SEC-GATE", "status": "PARTIAL"},
                {"name": "cve-scan", "status": "PARTIAL"},
            ],
            "securitySummary": "PARTIAL",
        }
        legs = gg.derive_legs_from_build_result(result)
        self.assertEqual(legs["build_result"], "PARTIAL")
        self.assertEqual(legs["msi"], "PASS")
        self.assertEqual(legs["elev"], "PASS")
        self.assertEqual(legs["signing"], "NOT RUN")
        self.assertEqual(legs["sec"], "PARTIAL")
        self.assertNotEqual(legs["signing"], "PASS")

    def test_aggregate_fixture_repo_go_with_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            docs = root / "docs"
            docs.mkdir()
            # Minimal blank checklist
            (docs / "RELEASE-CHECKLIST-v0.1.md").write_text(
                "# checklist\n### 1. MSI\n  - 狀態：`________`\n",
                encoding="utf-8",
            )
            (root / "CHANGELOG.md").write_text("## v0.1.0\n- demo\n", encoding="utf-8")
            br = {
                "schema": "aiad.build-result.v1",
                "version": "0.1.0",
                "status": "PARTIAL",
                "signingStatus": "NOT RUN",
                "artifacts": [
                    {"label": "MSI", "path": "out/x.msi", "exists": True},
                ],
                "verification": [
                    {"name": "MSI-ARTIFACT", "status": "PASS"},
                    {"name": "ELEV-VERIFY", "status": "PASS"},
                    {"name": "SIGNING", "status": "NOT RUN"},
                    {"name": "SEC-GATE", "status": "PARTIAL"},
                    {"name": "cve-scan", "status": "PARTIAL"},
                ],
                "securitySummary": "PARTIAL untriagedHigh=0",
            }
            br_path = reports / "build-0.1.0-fixture.json"
            br_path.write_text(json.dumps(br), encoding="utf-8")
            (reports / "sbom-fixture.md").write_text(
                "# SBOM\n- **Status:** PASS\n", encoding="utf-8"
            )
            sign_dir = root / "packaging" / "windows" / "out"
            sign_dir.mkdir(parents=True)
            sign_path = sign_dir / "sign-authenticode-result.json"
            sign_path.write_text(
                json.dumps(
                    {
                        "status": "NOT RUN",
                        "certConfigured": False,
                        "detail": "no cert",
                    }
                ),
                encoding="utf-8",
            )

            report = gg.aggregate(
                repo=root,
                build_result_path=br_path,
                checklist_path=docs / "RELEASE-CHECKLIST-v0.1.md",
                sign_result_path=sign_path,
                sbom_path=reports / "sbom-fixture.md",
            )
            self.assertEqual(report["verdict"], "Go-with-PARTIAL")
            self.assertEqual(report["legs"]["signing"], "NOT RUN")
            self.assertEqual(report["legs"]["elev"], "PASS")
            self.assertNotEqual(report["legs"]["signing"], "PASS")
            self.assertTrue(
                any("PD-CHECKLIST-FILL-01" in n for n in report["notes"])
            )
            self.assertEqual(report["implementerStatus"], "PARTIAL")
            self.assertTrue(report["readyForGreen"])

            md_path, json_path = gg.write_report(report, out_dir=reports, stamp="TEST")
            self.assertTrue(md_path.is_file())
            self.assertTrue(json_path.is_file())
            md = md_path.read_text(encoding="utf-8")
            self.assertIn("Go-with-PARTIAL", md)
            self.assertIn("NOT RUN", md)
            self.assertNotIn("NOT RUN → PASS", md.replace("never rewrites NOT RUN → PASS", ""))

    def test_fail_leg_aggregate_nogo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            br = {
                "version": "0.1.0",
                "status": "FAIL",
                "signingStatus": "NOT RUN",
                "artifacts": [{"label": "MSI", "path": "x.msi", "exists": True}],
                "verification": [
                    {"name": "MSI-ARTIFACT", "status": "FAIL"},
                    {"name": "ELEV-VERIFY", "status": "NOT RUN"},
                    {"name": "SIGNING", "status": "NOT RUN"},
                ],
            }
            br_path = reports / "build-0.1.0-bad.json"
            br_path.write_text(json.dumps(br), encoding="utf-8")
            report = gg.aggregate(repo=root, build_result_path=br_path)
            self.assertEqual(report["verdict"], "NoGo")
            self.assertEqual(report["implementerStatus"], "FAIL")


class TestRender(unittest.TestCase):
    def test_markdown_contains_verdict_and_legs(self):
        report = gg.build_gonogo_report(
            legs={
                "build_result": "PARTIAL",
                "msi": "PASS",
                "elev": "NOT RUN",
                "sec": "PARTIAL",
                "sbom": "PASS",
                "signing": "NOT RUN",
                "changelog": "PASS",
            },
            verdict="Go-with-PARTIAL",
            sources={"build_result": "reports/build-0.1.0.json"},
            notes=["dep: PD-CHECKLIST-FILL-01"],
        )
        md = gg.render_markdown(report)
        self.assertIn("**Verdict:** Go-with-PARTIAL", md)
        self.assertIn("| elev | NOT RUN |", md)
        self.assertIn("| signing | NOT RUN |", md)
        self.assertIn("PD-DEC-V01-GATE-01", md)


if __name__ == "__main__":
    unittest.main()
