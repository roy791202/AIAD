"""PD-M2-VAL-01 — M2 validation report structure + anti-forge (no full Live PASS)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPORT = REPO / "reports" / "m2-validation-v0.1.md"

REQUIRED_MARKERS = (
    "PD-M2-VAL-01",
    "BDD-PD-M2-VAL-01",
    "§8",
    "M2",
    "NOT RUN",
    "PARTIAL",
    "PD-M2-E2E-LOOP-01",
    "PD-M2-LIVE-MATRIX-01",
    "Anti-forge",
)

# Affirmative forged claims — allowed only inside ban / forbidden / ≠ context.
FORBIDDEN_FULL_LIVE_PATTERNS = (
    r"M2\s*全\s*Live\s*閉環\s*PASS",
    r"全\s*Live\s*閉環\s*(?:已完成|完成|PASS)",
    r"full\s+Live\s+loop\s+PASS",
    r"M2\s+full\s+Live\s+(?:loop\s+)?(?:PASS|complete)",
)


def _line_at(text: str, pos: int) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    if end < 0:
        end = len(text)
    return text[start:end]


def _is_ban_context(line: str) -> bool:
    lower = line.lower()
    return (
        "禁止" in line
        or "不得" in line
        or "Forbidden" in line
        or "≠" in line
        or "不是" in line
        or "must not" in lower
        or ("may claim" in lower and "no" in lower)
        or "Anti-forge" in line
        or "false" in lower
        or "拒絕" in line
        or "blocks claiming" in lower
        or "blocks " in lower
    )


class TestM2ValidationReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = REPORT.read_text(encoding="utf-8")

    def test_report_exists(self) -> None:
        self.assertTrue(REPORT.is_file(), f"missing {REPORT}")

    def test_required_markers_present(self) -> None:
        missing = [m for m in REQUIRED_MARKERS if m not in self.text]
        self.assertEqual(missing, [], f"missing markers: {missing}")

    def test_overall_is_partial(self) -> None:
        self.assertRegex(
            self.text,
            r"Overall[^\n]*\*\*PARTIAL\*\*",
            "overall must be PARTIAL",
        )

    def test_lists_remaining_not_run(self) -> None:
        self.assertIn("## 3. Remaining NOT RUN", self.text)
        # Soft deps called out as NOT RUN / skeleton.
        chunk_idx = self.text.find("## 3. Remaining NOT RUN")
        chunk = self.text[chunk_idx : chunk_idx + 2000]
        self.assertIn("PD-M2-E2E-LOOP-01", chunk)
        self.assertIn("PD-M2-LIVE-MATRIX-01", chunk)
        self.assertIn("NOT RUN", chunk)

    def test_cites_soft_dep_expected_paths(self) -> None:
        self.assertIn("reports/dispatch-pd/PD-M2-E2E-LOOP-01.md", self.text)
        self.assertIn("reports/dispatch-pd/PD-M2-LIVE-MATRIX-01.md", self.text)

    def test_does_not_rewrite_section_8_definition(self) -> None:
        """Report may quote §8; must state it does not rewrite the definition."""
        refuses = (
            "不**改寫 §8" in self.text
            or "不改寫 §8" in self.text
            or ("不改寫" in self.text and "§8" in self.text)
        )
        self.assertTrue(refuses, "must explicitly refuse rewriting §8")

    def test_forbids_full_live_loop_pass_claim(self) -> None:
        # Positive: anti-forge language present.
        self.assertTrue(
            "不得宣稱" in self.text
            or "禁止" in self.text
            and "全 Live" in self.text,
            "report must reject full Live loop PASS claim",
        )
        self.assertIn("全 Live 閉環 PASS", self.text)

        for pat in FORBIDDEN_FULL_LIVE_PATTERNS:
            for m in re.finditer(pat, self.text, flags=re.IGNORECASE):
                line = _line_at(self.text, m.start())
                self.assertTrue(
                    _is_ban_context(line),
                    f"forged full-Live claim without ban context: {line!r}",
                )

    def test_dryrun_not_equated_to_live_pass(self) -> None:
        self.assertTrue(
            "DryRun ≠ Live" in self.text or "DryRun ≠" in self.text,
            "must distinguish DryRun from Live",
        )


if __name__ == "__main__":
    unittest.main()
