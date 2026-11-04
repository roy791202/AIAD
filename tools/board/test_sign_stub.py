"""Unit tests for PD-SIGN-STUB-01 Build Result hang helper."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sign_stub


class SignStubHangTests(unittest.TestCase):
    def test_missing_file_is_not_run(self) -> None:
        missing = Path(tempfile.mkdtemp()) / "absent.json"
        self.assertEqual(sign_stub.load_signing_status(missing), "NOT RUN")

    def test_not_run_json_never_pass(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sign-authenticode-result.json"
            path.write_text(
                json.dumps(
                    {
                        "status": "PASS",  # forged — must be refused
                        "certConfigured": False,
                        "detail": "should not become PASS",
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(sign_stub.load_signing_status(path), "NOT RUN")

    def test_cert_pass_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sign-authenticode-result.json"
            path.write_text(
                json.dumps(
                    {
                        "status": "PASS",
                        "certConfigured": True,
                        "detail": "signed",
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(sign_stub.load_signing_status(path), "PASS")
            row = sign_stub.verification_row(path)
            self.assertEqual(row["name"], "SIGNING")
            self.assertEqual(row["status"], "PASS")


if __name__ == "__main__":
    raise SystemExit(
        0 if unittest.main(verbosity=2, exit=False).result.wasSuccessful() else 1
    )
