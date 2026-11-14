"""PD-MILESTONE-VAL-01 — milestone validation report structure + anti-forge."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPORT = REPO / "reports" / "milestone-validation-v0.1.md"

# Headings / section markers the validation report must expose.
REQUIRED_SECTION_MARKERS = (
    "## 2. M0",
    "## 3. M1",
    "## 4. M2",
    "## 5. M3",
    "## 6. M4",
    "## 7. Rel-Candidate",
    "## 8. Rel-Freeze",
    "SSH",
    "DCC",
    "Out of scope",
)

# Phrases that would falsely claim a finished multi-OS product release.
FORBIDDEN_CLAIM_PATTERNS = (
    r"已完整跨平台發行",
    r"完整跨平台發行\s*(完成|PASS|已完成)",
    r"full cross-platform release (complete|done|PASS)",
    r"三平台.*(?:皆|全部|已經).*(?:PASS|完成|發行)",
)


class TestMilestoneValidationReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = REPORT.read_text(encoding="utf-8")

    def test_report_exists(self) -> None:
        self.assertTrue(REPORT.is_file(), f"missing {REPORT}")

    def test_required_sections_present(self) -> None:
        missing = [m for m in REQUIRED_SECTION_MARKERS if m not in self.text]
        self.assertEqual(missing, [], f"missing section markers: {missing}")

    def test_ssh_dcc_out_of_scope(self) -> None:
        lower = self.text.lower()
        self.assertIn("out of scope", lower)
        self.assertRegex(self.text, r"SSH")
        self.assertRegex(self.text, r"DCC")
        self.assertTrue(
            "未做另案" in self.text or "out of scope" in lower,
            "SSH/DCC must be deferred / out of scope",
        )

    def test_forbids_full_cross_platform_release_claim(self) -> None:
        """Report may mention the ban; must not assert release-complete as fact."""
        # Positive: anti-forge language present.
        self.assertTrue(
            "≠ 已完整跨平台發行" in self.text
            or "不是**完整跨平台發行" in self.text
            or "not a completed cross-platform" in self.text.lower()
            or "Forbidden / false" in self.text,
            "report must explicitly reject full cross-platform release claim",
        )
        # Negative: no affirmative forged claim lines.
        for pat in FORBIDDEN_CLAIM_PATTERNS:
            for m in re.finditer(pat, self.text, flags=re.IGNORECASE):
                # Allow lines that are bans / forbidden tables / ≠ statements.
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
                    or "must not" in line.lower()
                    or "false" in line.lower()
                    or "Anti-forge" in line
                    or "不得" in line
                )
                self.assertTrue(
                    ban_ctx,
                    f"forged cross-platform claim without ban context: {line!r}",
                )

    def test_m4_not_equated_to_full_release(self) -> None:
        # M4 section must carry PARTIAL and anti-complete language nearby.
        idx = self.text.find("## 6. M4")
        self.assertGreaterEqual(idx, 0)
        chunk = self.text[idx : idx + 1200]
        self.assertIn("PARTIAL", chunk)
        self.assertTrue(
            "完整跨平台" in chunk or "cross-platform" in chunk.lower(),
            "M4 section must discuss cross-platform boundary",
        )


if __name__ == "__main__":
    unittest.main()
