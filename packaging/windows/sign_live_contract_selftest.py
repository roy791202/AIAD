#!/usr/bin/env python3
"""Contract assertions for PD-REMAIN-SIGN-LIVE-01 (allow-scope: packaging/windows).

Validates:
- No cert → NOT RUN (never PASS); certPurchaseRequired=false
- Live refuses dry-cert → BLOCKED (never forged PASS)
- refuse_forged_pass blocks unsigned PASS
- PASS requires signed+verified evidence
- Result JSON re-runnable; Build Result signingStatus maps correctly
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import sign_live as live  # noqa: E402
import sign_authenticode as stub  # noqa: E402


class SignLiveContract(unittest.TestCase):
    def test_card_and_mode(self) -> None:
        self.assertEqual(live.CARD_ID, "PD-REMAIN-SIGN-LIVE-01")
        self.assertEqual(live.BDD_ID, "BDD-PD-REMAIN-SIGN-LIVE-01")
        self.assertEqual(live.MODE, "live")

    def test_no_cert_is_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            art = live.build_live_result(out_dir=out, environ={}, run_signtool=True)
            self.assertEqual(art["status"], "NOT RUN")
            self.assertEqual(art["card"], live.CARD_ID)
            self.assertEqual(art["mode"], "live")
            self.assertFalse(art["certConfigured"])
            self.assertFalse(art["signed"])
            self.assertFalse(art["verified"])
            self.assertFalse(art["certPurchaseRequired"])
            self.assertNotEqual(art["status"], "PASS")
            path = live.write_result_json(art, out)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["status"], "NOT RUN")
            self.assertEqual(live.signing_status_for_build_result(loaded), "NOT RUN")

    def test_dry_cert_with_cert_is_blocked_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fake_pfx = root / "dev.pfx"
            fake_pfx.write_bytes(b"not-a-real-pfx")
            target = root / "artifact.bin"
            target.write_bytes(b"payload")
            env = {stub.ENV_CERT: str(fake_pfx)}
            art = live.build_live_result(
                out_dir=root / "out",
                target=target,
                environ=env,
                run_signtool=False,
            )
            self.assertTrue(art["certConfigured"])
            self.assertEqual(art["status"], "BLOCKED")
            self.assertNotEqual(art["status"], "PASS")
            self.assertFalse(art["signed"])
            self.assertIn("dry-cert", art["detail"].lower())

    def test_refuse_forged_pass_unsigned(self) -> None:
        self.assertEqual(
            live.refuse_forged_pass("PASS", cert_present=False, signed=False),
            "NOT RUN",
        )
        self.assertEqual(
            live.refuse_forged_pass("PASS", cert_present=True, signed=False),
            "FAIL",
        )
        self.assertEqual(
            live.refuse_forged_pass("PASS", cert_present=True, signed=True),
            "PASS",
        )

    def test_missing_target_with_cert_is_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            missing = root / "nope.msi"
            env = {stub.ENV_THUMBPRINT: "DEADBEEF"}
            art = live.build_live_result(
                out_dir=root / "out",
                target=missing,
                environ=env,
                run_signtool=True,
            )
            self.assertEqual(art["status"], "FAIL")
            self.assertIn("missing", art["detail"].lower())

    def test_live_sign_then_verify_pass(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "artifact.bin"
            target.write_bytes(b"payload")
            env = {
                stub.ENV_THUMBPRINT: "AABBCCDDEEFF00112233445566778899AABBCCDD",
                stub.ENV_TIMESTAMP: "http://timestamp.example/rfc3161",
            }

            def fake_run(cmd, capture_output=True, text=True, check=False):  # noqa: ARG001
                if len(cmd) > 1 and cmd[1] == "sign":
                    return mock.Mock(returncode=0, stdout="Sign success", stderr="")
                if len(cmd) > 1 and cmd[1] == "verify":
                    return mock.Mock(returncode=0, stdout="Successfully verified", stderr="")
                return mock.Mock(returncode=1, stdout="", stderr="unexpected")

            with mock.patch.object(stub, "_find_signtool", return_value="signtool.exe"):
                with mock.patch.object(stub.subprocess, "run", side_effect=fake_run):
                    with mock.patch.object(live.subprocess, "run", side_effect=fake_run):
                        art = live.build_live_result(
                            out_dir=root / "out",
                            target=target,
                            environ=env,
                            run_signtool=True,
                        )
            self.assertEqual(art["status"], "PASS")
            self.assertTrue(art["signed"])
            self.assertTrue(art["verified"])
            self.assertEqual(live.signing_status_for_build_result(art), "PASS")

    def test_live_sign_verify_fail_is_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "artifact.bin"
            target.write_bytes(b"payload")
            env = {
                stub.ENV_THUMBPRINT: "AABBCCDDEEFF00112233445566778899AABBCCDD",
                stub.ENV_TIMESTAMP: "http://timestamp.example/rfc3161",
            }

            def fake_run(cmd, capture_output=True, text=True, check=False):  # noqa: ARG001
                if len(cmd) > 1 and cmd[1] == "sign":
                    return mock.Mock(returncode=0, stdout="Sign success", stderr="")
                if len(cmd) > 1 and cmd[1] == "verify":
                    return mock.Mock(returncode=1, stdout="", stderr="verify boom")
                return mock.Mock(returncode=1, stdout="", stderr="unexpected")

            with mock.patch.object(stub, "_find_signtool", return_value="signtool.exe"):
                with mock.patch.object(stub.subprocess, "run", side_effect=fake_run):
                    with mock.patch.object(live.subprocess, "run", side_effect=fake_run):
                        art = live.build_live_result(
                            out_dir=root / "out",
                            target=target,
                            environ=env,
                            run_signtool=True,
                        )
            self.assertEqual(art["status"], "FAIL")
            self.assertTrue(art["signed"])
            self.assertFalse(art["verified"])

    def test_rerun_overwrites_result(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            a1 = live.build_live_result(out_dir=out, environ={}, run_signtool=True)
            p1 = live.write_result_json(a1, out)
            a2 = live.build_live_result(out_dir=out, environ={}, run_signtool=True)
            p2 = live.write_result_json(a2, out)
            self.assertEqual(p1, p2)
            self.assertEqual(
                json.loads(p2.read_text(encoding="utf-8"))["card"], live.CARD_ID
            )


if __name__ == "__main__":
    raise SystemExit(
        0 if unittest.main(verbosity=2, exit=False).result.wasSuccessful() else 1
    )
