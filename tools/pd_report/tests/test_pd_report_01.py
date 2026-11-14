"""TDD for BDD-PD-REPORT-01 — read-only SPEC/EVID → HTML/markdown; never write back specs.

Maps REPORT-001 scenarios:
  TDD-PD-REPORT-01-01  offline HTML + source fingerprint
  TDD-PD-REPORT-01-02  empty evidence → NOT RUN (never forged PASS)
  TDD-PD-REPORT-01-03  HTML special chars escaped (no script injection)
  TDD-PD-REPORT-01-04  SPEC/EVID input files unchanged after project
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from pd_report.project import (  # noqa: E402
    ProjectResult,
    fingerprint_sources,
    project_report,
)

FIXTURES = ROOT / "fixtures"


def _read_bytes(path: Path) -> bytes:
    return path.read_bytes()


class TestPdReport01(unittest.TestCase):
    def test_01_offline_html_with_source_fingerprint(self) -> None:
        """TDD-PD-REPORT-01-01 / BDD-REPORT-001-01"""
        spec = FIXTURES / "happy" / "spec.json"
        evid = FIXTURES / "happy" / "evid.json"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            result = project_report(spec_path=spec, evid_path=evid, out_dir=out)
            self.assertIsInstance(result, ProjectResult)
            html_path = out / "report.html"
            md_path = out / "report.md"
            self.assertTrue(html_path.is_file(), "HTML artifact missing")
            self.assertTrue(md_path.is_file(), "markdown summary missing")
            html = html_path.read_text(encoding="utf-8")
            md = md_path.read_text(encoding="utf-8")
            # offline: no CDN / remote fetch hooks
            self.assertNotIn("http://", html.lower())
            self.assertNotIn("https://", html.lower())
            self.assertNotIn("<script src=", html.lower())
            fp = fingerprint_sources(spec, evid)
            self.assertIn(fp, html)
            self.assertIn(fp, md)
            self.assertIn("MOD-SAMPLE", html)
            self.assertIn("PASS", html)
            self.assertEqual(result.fingerprint, fp)

    def test_02_empty_evidence_shows_not_run(self) -> None:
        """TDD-PD-REPORT-01-02 / BDD-REPORT-001-02 — RED if missing results labeled PASS"""
        spec = FIXTURES / "not_run" / "spec.json"
        evid = FIXTURES / "not_run" / "evid.json"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            project_report(spec_path=spec, evid_path=evid, out_dir=out)
            html = (out / "report.html").read_text(encoding="utf-8")
            md = (out / "report.md").read_text(encoding="utf-8")
            self.assertIn("NOT RUN", html)
            self.assertIn("NOT RUN", md)
            # must not forge approval / PASS when results empty
            self.assertNotRegex(html, r"\bPASS\b")
            self.assertNotRegex(md, r"\bPASS\b")

    def test_03_escapes_html_injection(self) -> None:
        """TDD-PD-REPORT-01-03 / BDD-REPORT-001-03"""
        spec = FIXTURES / "xss" / "spec.json"
        evid = FIXTURES / "xss" / "evid.json"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            project_report(spec_path=spec, evid_path=evid, out_dir=out)
            html = (out / "report.html").read_text(encoding="utf-8")
            # raw script tag from fixture must not appear executable
            self.assertNotIn("<script>alert(1)</script>", html)
            self.assertNotIn("<script>test</script>", html)
            self.assertIn("&lt;script&gt;", html)
            self.assertIn("&amp;", html)

    def test_04_does_not_write_back_specs(self) -> None:
        """TDD-PD-REPORT-01-04 — INV: projection only; SPEC/EVID inputs immutable"""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            spec = base / "spec.json"
            evid = base / "evid.json"
            out = base / "out"
            out.mkdir()
            src_spec = (FIXTURES / "happy" / "spec.json").read_text(encoding="utf-8")
            src_evid = (FIXTURES / "happy" / "evid.json").read_text(encoding="utf-8")
            spec.write_text(src_spec, encoding="utf-8")
            evid.write_text(src_evid, encoding="utf-8")
            before_spec = _read_bytes(spec)
            before_evid = _read_bytes(evid)
            before_spec_hash = hashlib.sha256(before_spec).hexdigest()
            before_evid_hash = hashlib.sha256(before_evid).hexdigest()
            project_report(spec_path=spec, evid_path=evid, out_dir=out)
            self.assertEqual(hashlib.sha256(_read_bytes(spec)).hexdigest(), before_spec_hash)
            self.assertEqual(hashlib.sha256(_read_bytes(evid)).hexdigest(), before_evid_hash)
            self.assertEqual(_read_bytes(spec), before_spec)
            self.assertEqual(_read_bytes(evid), before_evid)
            # outputs only under out_dir
            self.assertTrue((out / "report.html").is_file())
            self.assertEqual(json.loads(spec.read_text(encoding="utf-8"))["id"], "MOD-SAMPLE")


if __name__ == "__main__":
    unittest.main()
