"""PD-M2-LIVE-MATRIX-01 — vocabulary + anti-forge assertions."""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

import m2_live_matrix as mx

REPO = Path(__file__).resolve().parents[2]
REPORT_MD = REPO / "reports" / "m2-live-matrix.md"
REPORT_JSON = REPO / "reports" / "m2-live-matrix.json"

FORBIDDEN_CLAIM_PATTERNS = (
    r"全\s*Live\s*閉環\s*PASS",
    r"M2\s*全\s*Live\s*PASS",
    r"promote\s+unrun\s+to\s+PASS",
    r"缺跑\s*=\s*PASS",
    r"缺跑＝PASS",
)


class TestM2LiveMatrixVocabAndAntiForge(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = REPORT_MD.read_text(encoding="utf-8")
        cls.payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))

    def test_report_files_exist(self) -> None:
        self.assertTrue(REPORT_MD.is_file(), f"missing {REPORT_MD}")
        self.assertTrue(REPORT_JSON.is_file(), f"missing {REPORT_JSON}")

    def test_vocabulary_in_md_and_json(self) -> None:
        for token in ("PASS", "NOT RUN", "FAIL"):
            self.assertIn(token, self.text)
        vocab = set(self.payload.get("vocabulary") or [])
        self.assertEqual(vocab, set(mx.CELL_VOCAB))
        for cell in self.payload.get("cells") or []:
            self.assertIn(cell["status"], mx.CELL_VOCAB, cell)

    def test_required_cells_present(self) -> None:
        keys = {c["key"] for c in (self.payload.get("cells") or [])}
        self.assertEqual(keys, set(mx.CELL_ORDER))
        for key in mx.CELL_ORDER:
            self.assertIn(key, self.text)

    def test_anti_forge_ban_present(self) -> None:
        self.assertIn(mx.ANTI_FORGE_BAN, self.text)
        self.assertIn(mx.ANTI_FORGE_BAN, json.dumps(self.payload, ensure_ascii=False))
        self.assertIn("Anti-forge", self.text)
        self.assertTrue(
            "不得" in self.text or "禁止" in self.text or "≠" in self.text,
            "report must carry ban / ≠ language",
        )

    def test_forbids_forged_full_live_pass_claims(self) -> None:
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
                )
                self.assertTrue(ban_ctx, f"forged Live PASS without ban context: {line!r}")

    def test_overall_not_pass_while_any_not_run(self) -> None:
        cells = self.payload.get("cells") or []
        statuses = [c["status"] for c in cells]
        overall = self.payload.get("status")
        if any(s == "NOT RUN" for s in statuses):
            self.assertNotEqual(
                overall,
                "PASS",
                "anti-forge: overall must not be PASS while any cell is NOT RUN",
            )

    def test_citable_by_m2_val(self) -> None:
        self.assertIn("PD-M2-VAL-01", self.text)
        cite = self.payload.get("citeFor") or []
        self.assertTrue(any("M2" in str(x) or "VAL" in str(x) for x in cite))

    def test_schema_and_card(self) -> None:
        self.assertEqual(self.payload.get("schema"), mx.SCHEMA)
        self.assertEqual(self.payload.get("cardId"), mx.CARD_ID)
        self.assertEqual(self.payload.get("bdd"), mx.BDD_ID)


class TestM2LiveMatrixRefuseForge(unittest.TestCase):
    def test_missing_evidence_cannot_be_pass(self) -> None:
        self.assertEqual(
            mx.refuse_forge_pass(evidence_exists=False, claimed="PASS"),
            "NOT RUN",
        )
        self.assertEqual(
            mx.refuse_forge_pass(evidence_exists=False, claimed="FAIL"),
            "NOT RUN",
        )

    def test_present_evidence_keeps_claimed(self) -> None:
        self.assertEqual(
            mx.refuse_forge_pass(evidence_exists=True, claimed="PASS"),
            "PASS",
        )
        self.assertEqual(
            mx.refuse_forge_pass(evidence_exists=True, claimed="FAIL"),
            "FAIL",
        )

    def test_empty_repo_all_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reports").mkdir()
            payload = mx.build_matrix(root)
            self.assertEqual(payload["status"], "NOT RUN")
            for cell in payload["cells"]:
                self.assertEqual(cell["status"], "NOT RUN", cell)
                self.assertFalse(cell["ran"], cell)

    def test_cli_probe_pass_does_not_forge_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            (reports / "live-cli-target-result.json").write_text(
                json.dumps(
                    {
                        "status": "PASS",
                        "targets": [{"tool": "claude", "path": "x", "source": "path"}],
                        "detail": "1 CLI",
                        "settings": {
                            "mcp_server_name": "",
                            "mcp_endpoint": "",
                        },
                    }
                ),
                encoding="utf-8",
            )
            payload = mx.build_matrix(root)
            by_key = {c["key"]: c for c in payload["cells"]}
            self.assertEqual(by_key["cli_probe"]["status"], "PASS")
            self.assertEqual(by_key["cli_smoke"]["status"], "NOT RUN")
            self.assertEqual(by_key["mcp_probe"]["status"], "NOT RUN")
            self.assertEqual(by_key["mcp_smoke"]["status"], "NOT RUN")
            self.assertNotEqual(payload["status"], "PASS")

    def test_empty_targets_demote_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = root / "reports"
            reports.mkdir()
            (reports / "live-cli-target-result.json").write_text(
                json.dumps({"status": "PASS", "targets": [], "detail": "forged empty"}),
                encoding="utf-8",
            )
            cell = mx.resolve_cell(root, "cli_probe")
            self.assertEqual(cell.status, "NOT RUN")


if __name__ == "__main__":
    unittest.main()
