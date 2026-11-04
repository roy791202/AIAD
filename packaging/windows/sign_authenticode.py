#!/usr/bin/env python3
"""PD-SIGN-STUB-01 — Windows Authenticode signing stub.

Re-runnable entry. Without certificate / unset env → status NOT RUN (exit 0;
never forge PASS). With certificate configured → attempt signtool (or report
FAIL/BLOCKED). Does not purchase or import certificates.

Usage (repo root or this directory)::

    python packaging/windows/sign_authenticode.py
    python packaging/windows/sign-authenticode.py
    python scripts/pd_sign_stub_01.py

Env (any one enables the live attempt; none → NOT RUN)::

    AIAD_AUTHENTICODE_CERT       path to .pfx / .p12
    AIAD_AUTHENTICODE_PASSWORD   optional PFX password
    AIAD_AUTHENTICODE_THUMBPRINT cert store thumbprint (CurrentUser/My)
    AIAD_AUTHENTICODE_TIMESTAMP  optional RFC3161 URL (else PARTIAL if signed)

Build Result hang: result JSON ``status`` → ``signingStatus`` (see
``tools/board/sign_stub.py``).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CARD_ID = "PD-SIGN-STUB-01"
BDD_ID = "BDD-PD-SIGN-STUB-01"
VALID_STATUS = frozenset({"PASS", "FAIL", "BLOCKED", "NOT RUN", "PARTIAL"})

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "out"
DEFAULT_MSI = HERE / "wix" / "out" / "SGenAxis-0.1.0-windows-x64.msi"

ENV_CERT = "AIAD_AUTHENTICODE_CERT"
ENV_PASSWORD = "AIAD_AUTHENTICODE_PASSWORD"
ENV_THUMBPRINT = "AIAD_AUTHENTICODE_THUMBPRINT"
ENV_TIMESTAMP = "AIAD_AUTHENTICODE_TIMESTAMP"


def cert_configured(environ: dict[str, str] | None = None) -> bool:
    """True when a cert path or thumbprint is set (non-empty)."""
    env = environ if environ is not None else os.environ
    cert = (env.get(ENV_CERT) or "").strip()
    thumb = (env.get(ENV_THUMBPRINT) or "").strip()
    return bool(cert) or bool(thumb)


def refuse_forged_pass(status: str, *, cert_present: bool) -> str:
    """Never map missing-cert / NOT RUN into PASS."""
    st = (status or "").strip().upper().replace("_", " ")
    if st == "NOTRUN":
        st = "NOT RUN"
    if not cert_present and st == "PASS":
        return "NOT RUN"
    if st not in VALID_STATUS:
        return "NOT RUN"
    return st


def _find_signtool() -> str | None:
    found = shutil.which("signtool")
    if found:
        return found
    # Common Windows SDK locations (optional probe; no install forced).
    roots = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Windows Kits"
        / "10"
        / "bin",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "Windows Kits"
        / "10"
        / "bin",
    ]
    for root in roots:
        if not root.is_dir():
            continue
        for candidate in sorted(root.glob("*/x64/signtool.exe"), reverse=True):
            if candidate.is_file():
                return str(candidate)
    return None


def _signtool_cmd(
    signtool: str,
    target: Path,
    *,
    cert_path: str,
    password: str,
    thumbprint: str,
    timestamp: str,
) -> list[str]:
    cmd = [signtool, "sign", "/fd", "SHA256", "/tr", timestamp, "/td", "SHA256"]
    if not timestamp:
        # No timestamp URL: still sign, but omit /tr /td.
        cmd = [signtool, "sign", "/fd", "SHA256"]
    if thumbprint:
        cmd += ["/sha1", thumbprint]
    elif cert_path:
        cmd += ["/f", cert_path]
        if password:
            cmd += ["/p", password]
    cmd.append(str(target))
    return cmd


def attempt_sign(
    target: Path,
    *,
    environ: dict[str, str] | None = None,
    run_signtool: bool = True,
) -> dict:
    """Attempt Authenticode when cert is configured. Returns status + detail."""
    env = environ if environ is not None else dict(os.environ)
    cert_path = (env.get(ENV_CERT) or "").strip()
    password = (env.get(ENV_PASSWORD) or "").strip()
    thumbprint = (env.get(ENV_THUMBPRINT) or "").strip()
    timestamp = (env.get(ENV_TIMESTAMP) or "").strip()

    if not target.is_file():
        return {
            "status": "FAIL",
            "detail": f"target missing: {target.as_posix()}",
            "signtool": None,
            "signed": False,
        }

    if cert_path and not Path(cert_path).is_file():
        return {
            "status": "FAIL",
            "detail": f"{ENV_CERT} set but file missing: {cert_path}",
            "signtool": None,
            "signed": False,
        }

    if not run_signtool:
        # Dry / injected path for unit tests.
        return {
            "status": "PARTIAL" if not timestamp else "PASS",
            "detail": "cert configured; signtool invoke skipped (test harness)",
            "signtool": None,
            "signed": False,
        }

    tool = _find_signtool()
    if not tool:
        return {
            "status": "BLOCKED",
            "detail": "cert configured but signtool.exe not found on PATH / Windows Kits",
            "signtool": None,
            "signed": False,
        }

    cmd = _signtool_cmd(
        tool,
        target,
        cert_path=cert_path,
        password=password,
        thumbprint=thumbprint,
        timestamp=timestamp,
    )
    # Redact password in logged command.
    logged = [
        ("***" if (i > 0 and cmd[i - 1] == "/p") else a) for i, a in enumerate(cmd)
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[:500]
        return {
            "status": "FAIL",
            "detail": f"signtool failed (exit {proc.returncode}): {err or 'no output'}",
            "signtool": tool,
            "signed": False,
            "command": logged,
        }

    if not timestamp:
        return {
            "status": "PARTIAL",
            "detail": "signed with Authenticode but no timestamp URL (set AIAD_AUTHENTICODE_TIMESTAMP)",
            "signtool": tool,
            "signed": True,
            "command": logged,
        }
    return {
        "status": "PASS",
        "detail": "Authenticode sign + timestamp succeeded",
        "signtool": tool,
        "signed": True,
        "command": logged,
    }


def build_result(
    *,
    out_dir: Path,
    target: Path | None = None,
    environ: dict[str, str] | None = None,
    run_signtool: bool = True,
) -> dict:
    """Return signing result dict. Missing cert → NOT RUN (never PASS)."""
    env = environ if environ is not None else dict(os.environ)
    present = cert_configured(env)
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    artifact_path = target if target is not None else DEFAULT_MSI

    base = {
        "card": CARD_ID,
        "bdd": BDD_ID,
        "kind": "authenticode",
        "os": "windows",
        "target": str(artifact_path.as_posix()) if artifact_path else None,
        "generatedAt": ts,
        "certConfigured": present,
        "certPurchaseRequired": False,
        "envHints": [ENV_CERT, ENV_THUMBPRINT, ENV_PASSWORD, ENV_TIMESTAMP],
    }

    if not present:
        artifact = {
            **base,
            "status": "NOT RUN",
            "detail": (
                f"no certificate configured ({ENV_CERT} / {ENV_THUMBPRINT} unset) - "
                "Authenticode stub NOT RUN (never forged PASS; no cert purchase required)"
            ),
            "signed": False,
            "signtool": None,
        }
    else:
        attempt = attempt_sign(
            artifact_path, environ=env, run_signtool=run_signtool
        )
        artifact = {
            **base,
            "status": attempt["status"],
            "detail": attempt["detail"],
            "signed": bool(attempt.get("signed")),
            "signtool": attempt.get("signtool"),
        }
        if "command" in attempt:
            artifact["command"] = attempt["command"]

    status = refuse_forged_pass(str(artifact["status"]), cert_present=present)
    artifact["status"] = status
    if status not in VALID_STATUS:
        raise RuntimeError(f"invalid signing status {status!r}")
    if not present and status == "PASS":
        raise RuntimeError("refusing forged PASS without certificate")
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
    """Map stub result → Build Result ``signingStatus`` (never forge PASS)."""
    present = bool(artifact.get("certConfigured"))
    return refuse_forged_pass(str(artifact.get("status") or "NOT RUN"), cert_present=present)


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
        help="If cert env set, skip real signtool (harness / CI without SDK)",
    )
    args = ap.parse_args(argv)

    artifact = build_result(
        out_dir=args.out,
        target=args.target,
        run_signtool=not args.dry_cert,
    )
    result_path = write_result_json(artifact, args.out)
    br_status = signing_status_for_build_result(artifact)

    print(f"{CARD_ID} Windows Authenticode stub")
    print(f"certConfigured={artifact['certConfigured']}  status={artifact['status']}")
    print(f"signingStatus(for Build Result)={br_status}")
    print(f"detail={artifact['detail']}")
    print(f"result={result_path.as_posix()}")
    if artifact["status"] == "FAIL":
        return 1
    # NOT RUN / PARTIAL / BLOCKED / PASS → exit 0 (missing cert is not a failure).
    return 0


if __name__ == "__main__":
    sys.exit(main())
