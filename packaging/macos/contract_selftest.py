#!/usr/bin/env python3
"""Contract assertions for PD-M4-MAC-STUB-01 (lives in allow-scope packaging/macos).

Validates:
- PackSpec status ∈ PASS|FAIL|BLOCKED|NOT RUN|PARTIAL
- Non-Darwin host path → NOT RUN (never PASS)
- Darwin path → writes stub + PARTIAL (no notarize PASS)
- Result JSON is re-runnable / rewriteable
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_macos_stub as stub  # noqa: E402


class MacosStubContract(unittest.TestCase):
    def test_valid_status_set(self) -> None:
        self.assertEqual(
            stub.VALID_STATUS,
            frozenset({"PASS", "FAIL", "BLOCKED", "NOT RUN", "PARTIAL"}),
        )

    def test_non_darwin_is_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            art = stub.build_result(out_dir=out, system="Windows")
            self.assertEqual(art["status"], "NOT RUN")
            self.assertIsNone(art["path"])
            self.assertIsNone(art["sha256"])
            self.assertNotEqual(art["status"], "PASS")
            self.assertIn("NOT RUN", art["detail"])
            path = stub.write_result_json(art, out)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["status"], "NOT RUN")
            self.assertEqual(loaded["os"], "macos")
            self.assertEqual(loaded["format"], "app-stub")
            self.assertFalse(loaded["notarize"])
            self.assertFalse(loaded["stapling"])

    def test_linux_is_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = stub.build_result(out_dir=Path(td), system="Linux")
            self.assertEqual(art["status"], "NOT RUN")
            self.assertNotEqual(art["status"], "PASS")

    def test_darwin_emits_partial_stub(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            art = stub.build_result(out_dir=out, system="Darwin", version="0.1.0")
            self.assertEqual(art["status"], "PARTIAL")
            self.assertNotEqual(art["status"], "PASS")
            self.assertTrue(art["path"])
            self.assertTrue(art["sha256"])
            self.assertEqual(len(art["sha256"]), 64)
            self.assertTrue(Path(art["path"]).is_file())
            self.assertTrue(str(art["path"]).endswith(".stub"))
            self.assertFalse(art["notarize"])
            self.assertFalse(art["stapling"])

    def test_rerun_overwrites_result(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            a1 = stub.build_result(out_dir=out, system="Windows")
            p1 = stub.write_result_json(a1, out)
            a2 = stub.build_result(out_dir=out, system="Windows")
            p2 = stub.write_result_json(a2, out)
            self.assertEqual(p1, p2)
            self.assertEqual(
                json.loads(p2.read_text(encoding="utf-8"))["status"],
                "NOT RUN",
            )


if __name__ == "__main__":
    raise SystemExit(0 if unittest.main(verbosity=2, exit=False).result.wasSuccessful() else 1)
