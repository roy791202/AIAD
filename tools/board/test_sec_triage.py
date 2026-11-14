"""PD-SEC-TRIAGE-01 — triage note structure + anti-forge phrases."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPORT_MD = REPO / "reports" / "sec-triage-v0.1.md"
REPORT_JSON = REPO / "reports" / "sec-triage-v0.1.json"
SOURCE_SCAN = REPO / "reports" / "sec-scan-20261024T120542.json"

REQUIRED_SECTION_MARKERS = (
    "## 1. Why sec-scan is PARTIAL",
    "## 2. High / critical",
    "## 3. 剩餘風險",
    "## 4. Anti-forge",
    "## 5. Citation map",
    "BDD-PD-SEC-TRIAGE-01",
    "PD-SEC-TRIAGE-01",
    "untriagedHigh",
    "blocksBuildPass",
    "PARTIAL",
)

# Affirmative forged claims (must not appear as facts without ban context).
FORBIDDEN_CLAIM_PATTERNS = (
    r"整體安全\s*PASS",
    r"overall\s+security\s+PASS",
    r"sec(?:urity)?\s*(?:scan\s+)?(?:is|=|:)\s*PASS\b",
    r"已通過安全閘門",
    r"正式安全放行",
)


class TestSecTriageNote(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = REPORT_MD.read_text(encoding="utf-8")
        cls.payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
        cls.scan = json.loads(SOURCE_SCAN.read_text(encoding="utf-8"))

    def test_report_files_exist(self) -> None:
        self.assertTrue(REPORT_MD.is_file(), f"missing {REPORT_MD}")
        self.assertTrue(REPORT_JSON.is_file(), f"missing {REPORT_JSON}")
        self.assertTrue(SOURCE_SCAN.is_file(), f"missing {SOURCE_SCAN}")

    def test_required_structure(self) -> None:
        missing = [m for m in REQUIRED_SECTION_MARKERS if m not in self.text]
        self.assertEqual(missing, [], f"missing markers: {missing}")

    def test_anti_forge_ban_phrase_present(self) -> None:
        self.assertIn("未分流高危不得暗示整體安全 PASS", self.text)
        self.assertTrue(
            "≠" in self.text or "不得" in self.text or "禁止" in self.text,
            "report must carry explicit ban / ≠ language",
        )

    def test_forbids_forged_overall_pass_claims(self) -> None:
        for pat in FORBIDDEN_CLAIM_PATTERNS:
            for m in re.finditer(pat, self.text, flags=re.IGNORECASE):
                line_start = self.text.rfind("\n", 0, m.start()) + 1
                line_end = self.text.find("\n", m.end())
                if line_end < 0:
                    line_end = len(self.text)
                line = self.text[line_start:line_end]
                ban_ctx = (
                    "禁止" in line
                    or "Forbidden" in line
                    or "≠" in line
                    or "不是" in line
                    or "不得" in line
                    or "must not" in line.lower()
                    or "ban" in line.lower()
                    or "Anti-forge" in line
                    or "false" in line.lower()
                )
                self.assertTrue(
                    ban_ctx,
                    f"forged security PASS claim without ban context: {line!r}",
                )

    def test_json_matches_partial_and_gate(self) -> None:
        self.assertEqual(self.payload.get("schema"), "aiad.sec-triage.v0.1")
        self.assertEqual(self.payload.get("status"), "PARTIAL")
        self.assertEqual(self.payload.get("cardId"), "PD-SEC-TRIAGE-01")
        high = self.payload.get("highTriage") or {}
        self.assertEqual(high.get("untriagedHighCount"), 0)
        self.assertIs(high.get("blocksBuildPass"), False)
        self.assertEqual((self.payload.get("legs") or {}).get("overall"), "PARTIAL")
        self.assertTrue((self.payload.get("antiForge") or {}).get("overallIsNotPass"))

    def test_aligned_with_source_scan_gate(self) -> None:
        gate = self.scan.get("gate") or {}
        high = self.payload.get("highTriage") or {}
        self.assertEqual(self.scan.get("status"), "PARTIAL")
        self.assertIn("untriagedHighCount", gate)
        self.assertIn("untriagedHighCount", high)
        self.assertEqual(
            int(gate["untriagedHighCount"]),
            int(high["untriagedHighCount"]),
        )
        self.assertEqual(
            bool(gate.get("blocksBuildPass")),
            bool(high.get("blocksBuildPass")),
        )

    def test_cites_build_result_gonogo(self) -> None:
        lower = self.text.lower()
        self.assertIn("build result", lower)
        self.assertTrue("gonogo" in lower or "go/nogo" in lower or "GoNoGo" in self.text)


if __name__ == "__main__":
    unittest.main()
