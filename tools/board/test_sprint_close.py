"""PD-SPRINT-CLOSE-01 — sprint close report structure + anti-forge."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPORT = REPO / "reports" / "sprint-close-v0.1.md"

# Headings / section markers the sprint-close report must expose.
REQUIRED_SECTION_MARKERS = (
    "## 1. Green epic chain",
    "## 2. Go-with-PARTIAL",
    "## 3. 未做另案",
    "DEV",
    "HARDEN",
    "M4",
    "VERIFY",
    "REL-CAND",
    "FREEZE",
    "Go-with-PARTIAL",
    "DCC",
    "SSH",
    "買證",
)

# Phrases that would falsely claim a formal external / store release.
FORBIDDEN_CLAIM_PATTERNS = (
    r"已正式對外發布",
    r"已正式商店發布",
    r"v0\.1\s*GA\s*已上線",
    r"formally released externally",
    r"formal (external|store) release (complete|done|PASS)",
)


class TestSprintCloseReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = REPORT.read_text(encoding="utf-8")

    def test_report_exists(self) -> None:
        self.assertTrue(REPORT.is_file(), f"missing {REPORT}")

    def test_required_sections_present(self) -> None:
        missing = [m for m in REQUIRED_SECTION_MARKERS if m not in self.text]
        self.assertEqual(missing, [], f"missing section markers: {missing}")

    def test_epic_chain_order_mentioned(self) -> None:
        # BDD chain label must appear as the ordered path.
        self.assertRegex(
            self.text,
            r"DEV\s*[→\-].*HARDEN\s*[→\-].*M4\s*[→\-].*VERIFY\s*[→\-].*REL-CAND\s*[→\-].*FREEZE",
        )

    def test_deferred_dcc_ssh_cert(self) -> None:
        self.assertIn("未做另案", self.text)
        for token in ("DCC", "SSH", "買證"):
            self.assertIn(token, self.text)
        # Must not claim these were opened / purchased as done.
        self.assertNotRegex(
            self.text,
            r"(?<!不)(?<!未)(?<!禁)開\s*DCC.*epic.*完成",
        )

    def test_go_with_partial_not_full_go(self) -> None:
        self.assertIn("Go-with-PARTIAL", self.text)
        # Closing verdict must not be a bare formal "Go" without PARTIAL context
        # as the sprint-close release posture.
        idx = self.text.find("## 2. Go-with-PARTIAL")
        self.assertGreaterEqual(idx, 0)
        chunk = self.text[idx : idx + 1500]
        self.assertIn("Go-with-PARTIAL", chunk)
        self.assertIn("NOT RUN", chunk)

    def test_forbids_formal_external_release_claim(self) -> None:
        """Report may mention the ban; must not assert formal release as fact."""
        self.assertTrue(
            "禁止" in self.text
            and (
                "已正式對外發布" in self.text
                or "正式對外發布" in self.text
                or "formally released externally" in self.text.lower()
            ),
            "report must explicitly reject formal external release claim",
        )
        self.assertTrue(
            "Forbidden / false" in self.text
            or "Anti-forge" in self.text
            or "禁止寫成已正式對外發布" in self.text,
            "report must carry anti-forge framing",
        )
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
                    or "must not" in line.lower()
                    or "false" in line.lower()
                    or "Anti-forge" in line
                    or "不得" in line
                    or "Is not" in line
                    or "不" in line
                )
                self.assertTrue(
                    ban_ctx,
                    f"forged formal-release claim without ban context: {line!r}",
                )


if __name__ == "__main__":
    unittest.main()
