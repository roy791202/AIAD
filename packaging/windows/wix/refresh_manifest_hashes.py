"""Refresh SHA-256 digests in packaging.manifest.json for tracked WiX files + payload."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MANIFEST = HERE / "packaging.manifest.json"
TRACKED = (
    "SGenAxis.wxs",
    "README.md",
    "build-msi.ps1",
    "refresh_manifest_hashes.py",
    "verify-install.ps1",
    "verify-install.checklist.json",
)
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not MANIFEST.is_file():
        raise SystemExit(f"missing {MANIFEST}")
    data = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    files = {}
    for name in TRACKED:
        path = HERE / name
        if not path.is_file():
            raise SystemExit(f"missing tracked file: {path}")
        files[name] = sha256(path)
    data["files"] = files

    payload = data.setdefault("payload", {})
    source_rel = payload.get(
        "source_relpath",
        "apps/sgenaxis-desktop/src-tauri/target/release/sgenaxis-desktop.exe",
    )
    source = REPO / source_rel
    if not source.is_file():
        staged = HERE / "payload" / payload.get("stage_name", "SGenAxis.exe")
        if staged.is_file() and staged.stat().st_size > 100_000:
            source = staged
        else:
            raise SystemExit(
                f"missing Tauri release exe for payload hash: {REPO / source_rel}"
            )
    payload_digest = sha256(source)
    size = source.stat().st_size
    payload["stage_name"] = payload.get("stage_name", "SGenAxis.exe")
    payload["source_relpath"] = source_rel.replace("\\", "/")
    payload["sha256"] = payload_digest
    payload["bytes"] = size
    data["payload"] = payload

    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"updated {MANIFEST}")
    for name, file_digest in files.items():
        print(f"  {name}: {file_digest}")
    print(f"  payload: {payload_digest} ({size} bytes) from {source}")


if __name__ == "__main__":
    main()
