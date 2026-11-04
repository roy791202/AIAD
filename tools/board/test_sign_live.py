"""Unit tests for PD-REMAIN-SIGN-LIVE-01 Build Result hang helper."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sign_live


class SignLiveHangTests(unittest.TestCase):
    def test_missing_file_is_not_run(self) -> None:
        missing = Path(tempfile.mkdtemp()) / "absent.json"
        self.assertEqual(sign_live.load_signing_status(missing), "NOT RUN")

    def test_forged_pass_without_cert_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sign-authenticode-result.json"
            path.write_text(
                json.dumps(
                    {
                        "card": "PD-REMAIN-SIGN-LIVE-01",
                        "mode": "live",
                        "status": "PASS",
                        "certConfigured": False,
                        "signed": False,
                        "verified": False,
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(sign_live.load_signing_status(path), "NOT RUN")

    def test_live_pass_without_verified_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sign-authenticode-result.json"
            path.write_text(
                json.dumps(
                    {
                        "card": "PD-REMAIN-SIGN-LIVE-01",
                        "mode": "live",
                        "status": "PASS",
                        "certConfigured": True,
                        "signed": True,
                        "verified": False,
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(sign_live.load_signing_status(path), "FAIL")

    def test_live_pass_with_verify_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sign-authenticode-result.json"
            path.write_text(
                json.dumps(
                    {
                        "card": "PD-REMAIN-SIGN-LIVE-01",
                        "mode": "live",
                        "status": "PASS",
                        "certConfigured": True,
                        "signed": True,
                        "verified": True,
                        "detail": "live ok",
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(sign_live.load_signing_status(path), "PASS")
            row = sign_live.verification_row(path)
            self.assertEqual(row["name"], "SIGNING")
            self.assertEqual(row["status"], "PASS")

    def test_not_run_host_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sign-authenticode-result.json"
            path.write_text(
                json.dumps(
                    {
                        "card": "PD-REMAIN-SIGN-LIVE-01",
                        "mode": "live",
                        "status": "NOT RUN",
                        "certConfigured": False,
                        "signed": False,
                        "verified": False,
                        "certPurchaseRequired": False,
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(sign_live.load_signing_status(path), "NOT RUN")
            self.assertNotEqual(sign_live.load_signing_status(path), "PASS")


if __name__ == "__main__":
    raise SystemExit(
        0 if unittest.main(verbosity=2, exit=False).result.wasSuccessful() else 1
    )
