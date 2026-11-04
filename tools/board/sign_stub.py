#!/usr/bin/env python3
"""PD-SIGN-STUB-01 — hang Authenticode stub result onto Build Result signingStatus.

Reads ``packaging/windows/out/sign-authenticode-result.json`` (or ``--result``)
and returns a normalized status. Missing file / missing cert → NOT RUN.
Never maps NOT RUN → PASS.

Usage::

    python tools/board/sign_stub.py
    python tools/board/sign_stub.py --result packaging/windows/out/sign-authenticode-result.json
    python tools/board/build_result.py ...  # pass signing_status=load_signing_status()
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

# Reuse Build Result vocabulary.
from build_result import normalize_status

REPO = Path(__file__).resolve().parents[2]
DEFAULT_RESULT = (
    REPO / "packaging" / "windows" / "out" / "sign-authenticode-result.json"
)


def refuse_forged_pass(status: str, *, cert_configured: bool) -> str:
    st = normalize_status(status)
    if not cert_configured and st == "PASS":
        return "NOT RUN"
    return st


def load_signing_status(
    result_path: Path | None = None,
    *,
    missing: str = "NOT RUN",
) -> str:
    """Load stub JSON → Build Result ``signingStatus`` string."""
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
    raw = data.get("status") or missing
    return refuse_forged_pass(str(raw), cert_configured=cert)


def verification_row(result_path: Path | None = None) -> dict[str, Any]:
    """Optional verification row for Build Result aggregation."""
    path = result_path if result_path is not None else DEFAULT_RESULT
    status = load_signing_status(path)
    detail = "Authenticode stub result missing — NOT RUN"
    evidence = str(path.as_posix())
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            detail = str(data.get("detail") or detail)
        except (OSError, json.JSONDecodeError):
            detail = "Authenticode stub result unreadable"
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
    print(f"PD-SIGN-STUB-01 signingStatus={status}")
    print(f"detail={row['detail']}")
    print(f"evidence={row['evidence']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
