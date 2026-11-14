#!/usr/bin/env python3
"""PD-M4-LINUX-STUB-01 - Linux packaging entry (AppImage stub).

Re-runnable. Non-Linux hosts -> status NOT RUN (exit 0; never forge PASS).
On Linux -> emit a minimal AppImage stub artifact with PackSpec fields
(os / arch / path / sha256 / status). Store publish is out of scope.

Usage (repo root or this directory)::

    python packaging/linux/build_linux_stub.py
    python packaging/linux/build-linux-stub.py
    python packaging/linux/build_linux_stub.py --out packaging/linux/out
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

CARD_ID = "PD-M4-LINUX-STUB-01"
BDD_ID = "BDD-PD-M4-LINUX-STUB-01"
FORMAT = "AppImage"  # chosen stub format (deb alternative not used)
VALID_STATUS = frozenset({"PASS", "FAIL", "BLOCKED", "NOT RUN", "PARTIAL"})

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "out"


def host_is_linux(system: str | None = None) -> bool:
    name = (system if system is not None else platform.system()).strip().lower()
    return name == "linux"


def host_arch() -> str:
    m = platform.machine().lower()
    if m in {"x86_64", "amd64"}:
        return "x64"
    if m in {"aarch64", "arm64"}:
        return "arm64"
    return m or "unknown"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_appimage_stub(out_dir: Path, arch: str, version: str) -> Path:
    """Create a deterministic placeholder AppImage (not a real AppImage runtime)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"SGenAxis-{version}-linux-{arch}.AppImage"
    path = out_dir / name
    # Stub marker only; not store-publishable.
    payload = (
        b"#!PD-M4-LINUX-STUB-01 AppImage placeholder\n"
        b"This is NOT a real AppImage. Do not publish to stores.\n"
        + f"version={version}\narch={arch}\n".encode("utf-8")
    )
    path.write_bytes(payload)
    return path


def build_result(
    *,
    out_dir: Path,
    system: str | None = None,
    version: str = "0.1.0",
) -> dict:
    """Return a PackSpec-shaped artifact dict. Never reports PASS on non-Linux."""
    linux = host_is_linux(system)
    arch = host_arch()
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    base = {
        "card": CARD_ID,
        "bdd": BDD_ID,
        "format": FORMAT,
        "os": "linux",
        "arch": arch,
        "version": version,
        "store_publish": False,
        "generatedAt": ts,
        "hostSystem": system if system is not None else platform.system(),
    }
    if not linux:
        artifact = {
            **base,
            "path": None,
            "sha256": None,
            "status": "NOT RUN",
            "detail": (
                f"host is {base['hostSystem']!r}, not Linux - "
                "Linux AppImage stub NOT RUN (never forged PASS)"
            ),
        }
    else:
        path = _write_appimage_stub(out_dir, arch, version)
        digest = _sha256_file(path)
        # Stub packaging only: PARTIAL until a real AppImage toolchain verifies on Linux.
        artifact = {
            **base,
            "path": str(path.as_posix()),
            "sha256": digest,
            "status": "PARTIAL",
            "detail": (
                "Linux host: wrote AppImage stub placeholder "
                "(not store-ready; not a forged full PASS)"
            ),
        }

    status = artifact["status"]
    if status not in VALID_STATUS:
        raise RuntimeError(f"invalid PackSpec status {status!r}")
    if not linux and status == "PASS":
        raise RuntimeError("refusing forged PASS on non-Linux host")
    return artifact


def write_result_json(artifact: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "linux-stub-result.json"
    result_path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output directory for result JSON and (on Linux) AppImage stub",
    )
    ap.add_argument("--version", default="0.1.0", help="Stub package version label")
    args = ap.parse_args(argv)

    artifact = build_result(out_dir=args.out, version=args.version)
    result_path = write_result_json(artifact, args.out)

    print(f"{CARD_ID} Linux packaging stub ({FORMAT})")
    print(f"host={artifact['hostSystem']}  status={artifact['status']}")
    print(f"detail={artifact['detail']}")
    print(f"result={result_path.as_posix()}")
    if artifact.get("path"):
        print(f"artifact={artifact['path']}  sha256={artifact['sha256']}")
    # Exit 0 for NOT RUN / PARTIAL - absence of Linux is not a failure.
    if artifact["status"] == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
