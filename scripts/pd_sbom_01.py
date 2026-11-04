#!/usr/bin/env python3
"""PD-SBOM-01 re-runnable CycloneDX/SPDX SBOM generation.

Writes ``reports/sbom-<ts>.md`` (+ JSON) and raw ``.cdx.json`` / ``.spdx.json``.
If latest ``reports/sec-scan-*.json`` has untriaged high/critical, ``blocksBuildPass``
is set so a Build Result cannot claim PASS merely because an SBOM exists
(see ``tools/board/sbom.py``).

Does **not** force merge-block; exit 1 only when overall SBOM status is FAIL.

Usage (from repo root)::

    python scripts/pd_sbom_01.py
    python scripts/pd_sbom_01.py --attach-demo
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "tools" / "board"
if str(BOARD) not in sys.path:
    sys.path.insert(0, str(BOARD))

import sbom  # noqa: E402


def _ensure_tool_path() -> None:
    """Prefer common WinGet install dirs + cargo bin for syft."""
    extras: list[str] = []
    cargo = Path.home() / ".cargo" / "bin"
    if cargo.is_dir():
        extras.append(str(cargo))
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if local.is_dir():
        for pattern in ("Anchore.Syft_*", "Aquasecurity.Syft_*", "syft_*"):
            for d in local.glob(pattern):
                extras.append(str(d))
    if extras:
        os.environ["Path"] = os.pathsep.join(extras + [os.environ.get("Path", "")])


def main(argv: list[str] | None = None) -> int:
    _ensure_tool_path()
    args = list(argv) if argv is not None else sys.argv[1:]
    if not args:
        args = ["run"]
    elif args[0] not in ("run", "gate-status", "attach-demo"):
        args = ["run"] + args
    print("PD-SBOM-01", " ".join(args))
    rc = sbom.main(args)
    if rc == 0:
        print("PD-SBOM-01 done")
    else:
        print(
            "PD-SBOM-01 FAIL (status recorded; not a merge-block)",
            file=sys.stderr,
        )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
