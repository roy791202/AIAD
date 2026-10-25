"""TDD for BDD-PD-REPORT-UI-01 — UI call boundary into pd_report.

  TDD-PD-REPORT-UI-01-01  call boundary projects HTML／MD (triggerable)
  TDD-PD-REPORT-UI-01-02  empty evid → NOT RUN (never forged PASS)
  TDD-PD-REPORT-UI-01-03  SPEC／EVID unchanged after call (no write-back)
  TDD-PD-REPORT-UI-01-04  DTO write_back is always False
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from pd_report.ui_call import project_for_ui  # noqa: E402

FIXTURES = ROOT / "fixtures"


class TestPdReportUi01(unittest.TestCase):
    def test_01_call_boundary_projects_artifacts(self) -> None:
        """TDD-PD-REPORT-UI-01-01 — trigger／open projection via call boundary."""
        spec = FIXTURES / "happy" / "spec.json"
        evid = FIXTURES / "happy" / "evid.json"
        with tempfile.TemporaryDirectory() as tmp:
            dto = project_for_ui(spec_path=spec, evid_path=evid, out_dir=tmp)
            self.assertTrue(Path(dto["html_path"]).is_file())
            self.assertTrue(Path(dto["md_path"]).is_file())
            self.assertIn("PASS", dto["evidence_status"])
            self.assertIn("<!DOCTYPE html>", dto["html_body"])

    def test_02_empty_evid_not_run(self) -> None:
        """TDD-PD-REPORT-UI-01-02 — empty evid → NOT RUN."""
        spec = FIXTURES / "not_run" / "spec.json"
        evid = FIXTURES / "not_run" / "evid.json"
        with tempfile.TemporaryDirectory() as tmp:
            dto = project_for_ui(spec_path=spec, evid_path=evid, out_dir=tmp)
            self.assertEqual(dto["evidence_status"], "NOT RUN")
            self.assertIn("NOT RUN", dto["html_body"])
            self.assertIn("NOT RUN", dto["md_body"])
            self.assertNotRegex(dto["html_body"], r"\bPASS\b")
            self.assertNotRegex(dto["md_body"], r"\bPASS\b")

    def test_03_no_spec_write_back(self) -> None:
        """TDD-PD-REPORT-UI-01-03 — SPEC／EVID bytes unchanged."""
        spec = FIXTURES / "not_run" / "spec.json"
        evid = FIXTURES / "not_run" / "evid.json"
        spec_before = spec.read_bytes()
        evid_before = evid.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            project_for_ui(spec_path=spec, evid_path=evid, out_dir=tmp)
        self.assertEqual(spec.read_bytes(), spec_before)
        self.assertEqual(evid.read_bytes(), evid_before)

    def test_04_write_back_flag_false(self) -> None:
        """TDD-PD-REPORT-UI-01-04 — DTO always write_back=false."""
        spec = FIXTURES / "happy" / "spec.json"
        evid = FIXTURES / "happy" / "evid.json"
        with tempfile.TemporaryDirectory() as tmp:
            dto = project_for_ui(spec_path=spec, evid_path=evid, out_dir=tmp)
            self.assertIs(dto["write_back"], False)
            # JSON round-trip preserves false
            roundtrip = json.loads(json.dumps(dto))
            self.assertFalse(roundtrip["write_back"])


if __name__ == "__main__":
    unittest.main()
