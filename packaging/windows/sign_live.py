#!/usr/bin/env python3
"""PD-REMAIN-SIGN-LIVE-01 — live Windows Authenticode (or honest NOT RUN).

BDD-PD-REMAIN-SIGN-LIVE-01:
  - Certificate configured → real signtool sign + verify; hang status on Build Result.
  - No certificate → NOT RUN (exit 0; never forge PASS).
  - Does **not** purchase or require buying a code-signing certificate.

Reuses packaging/windows/sign_authenticode helpers (PD-SIGN-STUB-01). Live mode
refuses ``--dry-cert`` PASS/PARTIAL claims — only a real signtool success with
verify may be PASS/PARTIAL.

Usage (repo root or this directory)::

    python packaging/windows/sign_live.py
    python packaging/windows/sign-live.py
    .\\packaging\\windows\\sign-live.ps1

Env (any one enables the live attempt; none → NOT RUN)::

    AIAD_AUTHENTICODE_CERT       path to .pfx / .p12
    AIAD_AUTHENTICODE_PASSWORD   optional PFX password
    AIAD_AUTHENTICODE_THUMBPRINT cert store thumbprint (CurrentUser/My)
    AIAD_AUTHENTICODE_TIMESTAMP  optional RFC3161 URL (else PARTIAL if signed+verified)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import sign_authenticode as stub

CARD_ID = "PD-REMAIN-SIGN-LIVE-01"
BDD_ID = "BDD-PD-REMAIN-SIGN-LIVE-01"
MODE = "live"

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = stub.DEFAULT_OUT
DEFAULT_MSI = stub.DEFAULT_MSI
VALID_STATUS = stub.VALID_STATUS


def refuse_forged_pass(status: str, *, cert_present: bool, signed: bool = False) -> str:
    """Never map missing-cert / unsigned into PASS."""
    st = stub.refuse_forged_pass(status, cert_present=cert_present)
    if st == "PASS" and not signed:
        return "NOT RUN" if not cert_present else "FAIL"
    return st


def _verify_signature(signtool: str, target: Path) -> tuple[bool, str]:
    """Run ``signtool verify /pa``. Returns (ok, detail)."""
    cmd = [signtool, "verify", "/pa", str(target)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()[:500]
    if proc.returncode != 0:
        return False, f"signtool verify failed (exit {proc.returncode}): {out or 'no output'}"
    return True, "signtool verify /pa ok"


def attempt_live_sign(
    target: Path,
    *,
    environ: dict[str, str] | None = None,
    run_signtool: bool = True,
) -> dict:
    """Live Authenticode: real signtool only. Dry harness → BLOCKED (not PASS)."""
    env = environ if environ is not None else dict(os.environ)

    if not run_signtool:
        return {
            "status": "BLOCKED",
            "detail": (
                "live mode refuses dry-cert / harness skip — "
                "run without --dry-cert when a cert is configured "
                "(never forge PASS)"
            ),
            "signtool": None,
            "signed": False,
            "verified": False,
        }

    attempt = stub.attempt_sign(target, environ=env, run_signtool=True)
    if not attempt.get("signed"):
        return {
            **attempt,
            "verified": False,
        }

    tool = attempt.get("signtool")
    if not tool:
        return {
            "status": "FAIL",
            "detail": "signed claimed but signtool path missing",
            "signtool": None,
            "signed": False,
            "verified": False,
        }

    ok, verify_detail = _verify_signature(str(tool), target)
    if not ok:
        return {
            "status": "FAIL",
            "detail": f"sign appeared to succeed but verify failed: {verify_detail}",
            "signtool": tool,
            "signed": True,
            "verified": False,
            "command": attempt.get("command"),
        }

    timestamp = (env.get(stub.ENV_TIMESTAMP) or "").strip()
    if not timestamp:
        return {
            "status": "PARTIAL",
            "detail": (
                "live Authenticode sign+verify ok but no timestamp URL "
                f"(set {stub.ENV_TIMESTAMP})"
            ),
            "signtool": tool,
            "signed": True,
            "verified": True,
            "command": attempt.get("command"),
        }
    return {
        "status": "PASS",
        "detail": f"live Authenticode sign + timestamp + verify succeeded ({verify_detail})",
        "signtool": tool,
        "signed": True,
        "verified": True,
        "command": attempt.get("command"),
    }


def build_live_result(
    *,
    out_dir: Path,
    target: Path | None = None,
    environ: dict[str, str] | None = None,
    run_signtool: bool = True,
) -> dict:
    """Return live signing result. Missing cert → NOT RUN (never PASS)."""
    env = environ if environ is not None else dict(os.environ)
    present = stub.cert_configured(env)
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    artifact_path = target if target is not None else DEFAULT_MSI

    base = {
        "card": CARD_ID,
        "bdd": BDD_ID,
        "kind": "authenticode",
        "mode": MODE,
        "os": "windows",
        "target": str(artifact_path.as_posix()) if artifact_path else None,
        "generatedAt": ts,
        "certConfigured": present,
        "certPurchaseRequired": False,
        "envHints": [
            stub.ENV_CERT,
            stub.ENV_THUMBPRINT,
            stub.ENV_PASSWORD,
            stub.ENV_TIMESTAMP,
        ],
    }

    if not present:
        artifact = {
            **base,
            "status": "NOT RUN",
            "detail": (
                f"no certificate configured ({stub.ENV_CERT} / {stub.ENV_THUMBPRINT} unset) - "
                "live Authenticode NOT RUN (never forged PASS; cert purchase not required; "
                "buy-cert is a separate owner decision)"
            ),
            "signed": False,
            "verified": False,
            "signtool": None,
        }
    else:
        attempt = attempt_live_sign(
            artifact_path, environ=env, run_signtool=run_signtool
        )
        artifact = {
            **base,
            "status": attempt["status"],
            "detail": attempt["detail"],
            "signed": bool(attempt.get("signed")),
            "verified": bool(attempt.get("verified")),
            "signtool": attempt.get("signtool"),
        }
        if "command" in attempt:
            artifact["command"] = attempt["command"]

    signed_ok = bool(artifact.get("signed")) and bool(artifact.get("verified"))
    raw = str(artifact["status"])
    if raw == "PASS":
        artifact["status"] = refuse_forged_pass(
            raw, cert_present=present, signed=signed_ok
        )
    else:
        artifact["status"] = stub.refuse_forged_pass(raw, cert_present=present)

    if artifact["status"] not in VALID_STATUS:
        raise RuntimeError(f"invalid signing status {artifact['status']!r}")
    if not present and artifact["status"] == "PASS":
        raise RuntimeError("refusing forged PASS without certificate")
    if artifact["status"] == "PASS" and not signed_ok:
        raise RuntimeError("refusing PASS without signed+verified live evidence")
    return artifact


def write_result_json(artifact: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "sign-authenticode-result.json"
    result_path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result_path


def signing_status_for_build_result(artifact: dict) -> str:
    """Map live result → Build Result ``signingStatus`` (never forge PASS)."""
    present = bool(artifact.get("certConfigured"))
    signed_ok = bool(artifact.get("signed")) and bool(artifact.get("verified"))
    return refuse_forged_pass(
        str(artifact.get("status") or "NOT RUN"),
        cert_present=present,
        signed=signed_ok,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output directory for sign-authenticode-result.json",
    )
    ap.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_MSI,
        help="File to sign (default: WiX MSI under packaging/windows/wix/out)",
    )
    ap.add_argument(
        "--dry-cert",
        action="store_true",
        help=(
            "Harness only: with cert env set, skip signtool → BLOCKED "
            "(live never forges PASS from dry-cert)"
        ),
    )
    args = ap.parse_args(argv)

    artifact = build_live_result(
        out_dir=args.out,
        target=args.target,
        run_signtool=not args.dry_cert,
    )
    result_path = write_result_json(artifact, args.out)
    br_status = signing_status_for_build_result(artifact)

    print(f"{CARD_ID} Windows Authenticode LIVE")
    print(f"mode={MODE}  certConfigured={artifact['certConfigured']}  status={artifact['status']}")
    print(f"signed={artifact.get('signed')}  verified={artifact.get('verified')}")
    print(f"signingStatus(for Build Result)={br_status}")
    print(f"detail={artifact['detail']}")
    print(f"result={result_path.as_posix()}")
    if artifact["status"] == "FAIL":
        return 1
    # NOT RUN / PARTIAL / BLOCKED / PASS → exit 0 (missing cert is not a failure).
    return 0


if __name__ == "__main__":
    sys.exit(main())
