#!/usr/bin/env python3
"""Contract assertions for PD-SIGN-STUB-01 (allow-scope: packaging/windows).

Validates:
- Status vocabulary PASS|FAIL|BLOCKED|NOT RUN|PARTIAL
- No cert / unset env → NOT RUN (never PASS)
- refuse_forged_pass blocks NOT RUN→PASS
- Cert configured + dry → PASS/PARTIAL (not forged from empty env)
- Result JSON re-runnable; Build Result signingStatus maps correctly
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import sign_authenticode as stub  # noqa: E402


class SignStubContract(unittest.TestCase):
    def test_valid_status_set(self) -> None:
        self.assertEqual(
            stub.VALID_STATUS,
            frozenset({"PASS", "FAIL", "BLOCKED", "NOT RUN", "PARTIAL"}),
        )

    def test_no_cert_is_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            art = stub.build_result(out_dir=out, environ={}, run_signtool=False)
            self.assertEqual(art["status"], "NOT RUN")
            self.assertFalse(art["certConfigured"])
            self.assertFalse(art["signed"])
            self.assertFalse(art["certPurchaseRequired"])
            self.assertNotEqual(art["status"], "PASS")
            self.assertIn("NOT RUN", art["detail"])
            path = stub.write_result_json(art, out)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["status"], "NOT RUN")
            self.assertEqual(loaded["kind"], "authenticode")
            self.assertEqual(
                stub.signing_status_for_build_result(loaded), "NOT RUN"
            )

    def test_empty_env_strings_are_not_run(self) -> None:
        env = {
            stub.ENV_CERT: "  ",
            stub.ENV_THUMBPRINT: "",
        }
        art = stub.build_result(
            out_dir=Path(tempfile.mkdtemp()), environ=env, run_signtool=False
        )
        self.assertEqual(art["status"], "NOT RUN")
        self.assertNotEqual(art["status"], "PASS")

    def test_refuse_forged_pass_without_cert(self) -> None:
        self.assertEqual(
            stub.refuse_forged_pass("PASS", cert_present=False), "NOT RUN"
        )
        self.assertEqual(
            stub.refuse_forged_pass("NOT RUN", cert_present=False), "NOT RUN"
        )
        self.assertEqual(
            stub.refuse_forged_pass("PASS", cert_present=True), "PASS"
        )

    def test_cert_pfx_dry_partial_without_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fake_pfx = root / "dev.pfx"
            fake_pfx.write_bytes(b"not-a-real-pfx")
            target = root / "artifact.bin"
            target.write_bytes(b"payload")
            env = {stub.ENV_CERT: str(fake_pfx)}
            art = stub.build_result(
                out_dir=root / "out",
                target=target,
                environ=env,
                run_signtool=False,
            )
            self.assertTrue(art["certConfigured"])
            self.assertEqual(art["status"], "PARTIAL")
            self.assertNotEqual(art["status"], "NOT RUN")
            self.assertEqual(
                stub.signing_status_for_build_result(art), "PARTIAL"
            )

    def test_cert_thumbprint_dry_pass_with_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "artifact.bin"
            target.write_bytes(b"payload")
            env = {
                stub.ENV_THUMBPRINT: "AABBCCDDEEFF00112233445566778899AABBCCDD",
                stub.ENV_TIMESTAMP: "http://timestamp.example/rfc3161",
            }
            art = stub.build_result(
                out_dir=root / "out",
                target=target,
                environ=env,
                run_signtool=False,
            )
            self.assertEqual(art["status"], "PASS")
            self.assertEqual(stub.signing_status_for_build_result(art), "PASS")

    def test_missing_target_with_cert_is_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            missing = root / "nope.msi"
            env = {stub.ENV_THUMBPRINT: "DEADBEEF"}
            art = stub.build_result(
                out_dir=root / "out",
                target=missing,
                environ=env,
                run_signtool=True,
            )
            self.assertEqual(art["status"], "FAIL")
            self.assertIn("missing", art["detail"].lower())

    def test_rerun_overwrites_result(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            a1 = stub.build_result(out_dir=out, environ={}, run_signtool=False)
            p1 = stub.write_result_json(a1, out)
            a2 = stub.build_result(out_dir=out, environ={}, run_signtool=False)
            p2 = stub.write_result_json(a2, out)
            self.assertEqual(p1, p2)
            self.assertEqual(
                json.loads(p2.read_text(encoding="utf-8"))["status"],
                "NOT RUN",
            )


if __name__ == "__main__":
    raise SystemExit(
        0 if unittest.main(verbosity=2, exit=False).result.wasSuccessful() else 1
    )
