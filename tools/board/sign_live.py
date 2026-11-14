#!/usr/bin/env python3
"""PD-REMAIN-SIGN-LIVE-01 — hang live Authenticode result onto Build Result signingStatus.

Reads ``packaging/windows/out/sign-authenticode-result.json`` (or ``--result``).
Missing file / missing cert → NOT RUN. Live PASS requires ``signed`` + ``verified``
and ``certConfigured``. Never maps NOT RUN → PASS. Does not purchase certificates.

Usage::

    python tools/board/sign_live.py
    python tools/board/sign_live.py --result packaging/windows/out/sign-authenticode-result.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from build_result import normalize_status

REPO = Path(__file__).resolve().parents[2]
DEFAULT_RESULT = (
    REPO / "packaging" / "windows" / "out" / "sign-authenticode-result.json"
)
CARD_ID = "PD-REMAIN-SIGN-LIVE-01"


def refuse_forged_pass(
    status: str,
    *,
    cert_configured: bool,
    signed: bool = False,
    verified: bool = False,
) -> str:
    st = normalize_status(status)
    if not cert_configured and st == "PASS":
        return "NOT RUN"
    if st == "PASS" and not (signed and verified):
        return "FAIL" if cert_configured else "NOT RUN"
    return st


def load_signing_status(
    result_path: Path | None = None,
    *,
    missing: str = "NOT RUN",
) -> str:
    """Load live/stub JSON → Build Result ``signingStatus`` string."""
    path = result_path if result_path is not None else DEFAULT_RESULT
    if not path.is_file():
        return refuse_forged_pass(missing, cert_configured=False)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return refuse_forged_pass("BLOCKED", cert_configured=False)
    if not isinstance(data, Mapping):
        return refuse_forged_pass("BLOCKED", cert_configured=False)
    cert = bool(data.get("certConfigured"))
    signed = bool(data.get("signed"))
    verified = bool(data.get("verified"))
    # Legacy stub JSON without verified: only refuse forge when cert missing;
    # live mode (mode=live or card id) requires verified for PASS.
    mode = str(data.get("mode") or "")
    card = str(data.get("card") or "")
    is_live = mode == "live" or card == CARD_ID
    raw = data.get("status") or missing
    if is_live:
        return refuse_forged_pass(
            str(raw),
            cert_configured=cert,
            signed=signed,
            verified=verified,
        )
    if not cert and normalize_status(str(raw)) == "PASS":
        return "NOT RUN"
    return normalize_status(str(raw))


def verification_row(result_path: Path | None = None) -> dict[str, Any]:
    """Optional verification row for Build Result aggregation."""
    path = result_path if result_path is not None else DEFAULT_RESULT
    status = load_signing_status(path)
    detail = "Authenticode live/stub result missing — NOT RUN"
    evidence = str(path.as_posix())
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            detail = str(data.get("detail") or detail)
        except (OSError, json.JSONDecodeError):
            detail = "Authenticode result unreadable"
    return {
        "name": "SIGNING",
        "status": status,
        "detail": detail,
        "evidence": evidence,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--result",
        type=Path,
        default=DEFAULT_RESULT,
        help="Path to sign-authenticode-result.json",
    )
    args = ap.parse_args(argv)
    status = load_signing_status(args.result)
    row = verification_row(args.result)
    print(f"{CARD_ID} signingStatus={status}")
    print(f"detail={row['detail']}")
    print(f"evidence={row['evidence']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
