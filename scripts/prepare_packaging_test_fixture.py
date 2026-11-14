"""Build a real MSI fixture in a fresh, isolated directory; never install it."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REL = Path("apps/sgenaxis-desktop/src-tauri/target/release/sgenaxis-desktop.exe")
TEMPLATES = (
    "packaging.manifest.json", "SGenAxis.wxs", "README.md", "build-msi.ps1",
    "refresh_manifest_hashes.py", "verify-install.ps1", "verify-install.checklist.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New isolated fixture root")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error(f"fixture output must not exist: {output}")
    source = ROOT / SOURCE_REL
    if not source.is_file() or source.stat().st_size < 100_000:
        parser.error(f"FIXTURE_SETUP: build the real Tauri release first: {source}")
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None or shutil.which("wix") is None:
        parser.error("FIXTURE_SETUP: PowerShell and WiX CLI are required")
    wix_source = ROOT / "packaging/windows/wix"
    # Validate the versioned template contract before recalculating the payload.
    manifest = json.loads((wix_source / "packaging.manifest.json").read_text(encoding="utf-8-sig"))
    for name, digest in manifest["files"].items():
        if sha256(wix_source / name) != digest:
            parser.error(f"FIXTURE_SETUP: tracked template digest mismatch: {name}")
    wix_target = output / "packaging/windows/wix"
    wix_target.mkdir(parents=True)
    for name in TEMPLATES:
        shutil.copy2(wix_source / name, wix_target / name)
    destination = output / SOURCE_REL
    destination.parent.mkdir(parents=True)
    shutil.copy2(source, destination)
    logs = []
    for command in (
        [sys.executable, str(wix_target / "refresh_manifest_hashes.py")],
        [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(wix_target / "build-msi.ps1")],
    ):
        result = subprocess.run(command, cwd=wix_target, capture_output=True, text=True, errors="replace")
        logs.append({"command": command, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode:
            (output / "fixture-build.json").write_text(json.dumps(logs, indent=2), encoding="utf-8")
            raise SystemExit(f"FIXTURE_SETUP: command failed: {command}\n{result.stdout}\n{result.stderr}")
    msi = wix_target / "out/SGenAxis-0.1.0-windows-x64.msi"
    evidence = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_exe": str(source), "source_sha256": sha256(source),
        "msi_sha256": sha256(msi), "commands": logs,
        "install_verification": "NOT RUN", "release_approval": "NOT RUN",
    }
    (output / "fixture-build.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    report = output / "reports/dispatch-pd/PD-REL-02.md"
    report.parent.mkdir(parents=True)
    report.write_text(
        "# Isolated packaging test fixture\n\nBuild: PASS\n"
        f"Payload SHA-256: {evidence['source_sha256']}\n\nMSI SHA-256: {evidence['msi_sha256']}\n\n"
        "Install verification: NOT RUN\nRelease approval: NOT RUN\nEvidence: fixture-build.json\n",
        encoding="utf-8",
    )
    print(f"SGENAXIS_PACKAGING_TEST_ROOT={output}")


if __name__ == "__main__":
    main()
