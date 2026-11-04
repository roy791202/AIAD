"""PD-REL-02: WiX embeds real Tauri release exe + SHA-256 contract.

Validates staging path, manifest payload digests, and build-msi.ps1 hash gate.
Does not force elevated msiexec /qn install; does not touch :8788.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = Path(os.environ.get("SGENAXIS_PACKAGING_TEST_ROOT", str(ROOT))).resolve()
WIX_DIR = ARTIFACT_ROOT / "packaging" / "windows" / "wix"
MANIFEST_PATH = WIX_DIR / "packaging.manifest.json"
BUILD_SCRIPT = WIX_DIR / "build-msi.ps1"
PAYLOAD_EXE = WIX_DIR / "payload" / "SGenAxis.exe"
TAURI_RELEASE = (
    ARTIFACT_ROOT
    / "apps"
    / "sgenaxis-desktop"
    / "src-tauri"
    / "target"
    / "release"
    / "sgenaxis-desktop.exe"
)
MIN_REAL_EXE_BYTES = 100_000


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest: {MANIFEST_PATH}"
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_tauri_release_exe_exists_for_staging():
    assert TAURI_RELEASE.is_file(), (
        f"missing Tauri release exe (build desktop first): {TAURI_RELEASE}"
    )
    assert TAURI_RELEASE.stat().st_size >= MIN_REAL_EXE_BYTES


def test_manifest_declares_payload_source_and_sha256():
    payload = _load_manifest()["payload"]
    assert payload["stage_name"] == "SGenAxis.exe"
    assert payload["source_relpath"].replace("\\", "/").endswith(
        "sgenaxis-desktop.exe"
    )
    assert re.fullmatch(r"[0-9a-f]{64}", payload["sha256"]), payload["sha256"]
    assert int(payload["bytes"]) >= MIN_REAL_EXE_BYTES


def test_manifest_payload_sha256_matches_tauri_release_on_disk():
    payload = _load_manifest()["payload"]
    digest = _sha256(TAURI_RELEASE)
    size = TAURI_RELEASE.stat().st_size
    assert digest == payload["sha256"], (
        f"Tauri release SHA-256 mismatch: got {digest}, expected {payload['sha256']}"
    )
    assert size == int(payload["bytes"]), (
        f"Tauri release size mismatch: got {size}, expected {payload['bytes']}"
    )


def test_staged_payload_is_real_exe_matching_manifest():
    assert PAYLOAD_EXE.is_file(), f"missing staged payload: {PAYLOAD_EXE}"
    size = PAYLOAD_EXE.stat().st_size
    assert size >= MIN_REAL_EXE_BYTES, (
        f"payload looks like scaffold stub ({size} bytes); stage real Tauri exe"
    )
    payload = _load_manifest()["payload"]
    digest = _sha256(PAYLOAD_EXE)
    assert digest == payload["sha256"]
    assert size == int(payload["bytes"])
    # Staged copy must match Tauri source byte-for-byte.
    assert digest == _sha256(TAURI_RELEASE)


def test_tracked_template_hashes_still_match():
    manifest = _load_manifest()
    for rel, expected in manifest["files"].items():
        path = WIX_DIR / rel
        assert path.is_file(), f"manifest lists missing file: {rel}"
        assert _sha256(path) == expected, f"SHA-256 mismatch for {rel}"


def test_build_script_stages_tauri_and_verifies_hash():
    text = BUILD_SCRIPT.read_text(encoding="utf-8")
    lower = text.lower()
    assert "sgenaxis-desktop.exe" in lower
    assert "sha256" in lower or "get-filehash" in lower
    assert "payload.sha256" in lower or "payload" in lower
    assert "packaging.manifest.json" in text
    assert re.search(r"\bwix\s+build\b", lower)
    assert not re.search(r"(?m)^\s*&?\s*makensis\b", text, flags=re.IGNORECASE)
    assert not re.search(r"(?m)^\s*&?\s*iscc\b", text, flags=re.IGNORECASE)
    # Out of scope: script must not invoke elevated silent install.
    assert not re.search(r"(?m)^\s*&?\s*msiexec\b", text, flags=re.IGNORECASE)


def test_build_msi_stages_and_embeds_when_wix_present(tmp_path: Path):
    """Required real MSI build; missing prerequisites fail fixture setup."""
    import shutil
    import subprocess

    if shutil.which("wix") is None:
        pytest.fail("FIXTURE_SETUP: wix CLI required for the MSI build test")

    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        pytest.fail("FIXTURE_SETUP: PowerShell required for the MSI build test")

    out_dir = tmp_path / "out"
    msi = out_dir / "SGenAxis-0.1.0-windows-x64.msi"
    proc = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(BUILD_SCRIPT),
            "-OutDir",
            str(out_dir),
        ],
        cwd=str(WIX_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"build-msi.ps1 failed ({proc.returncode}):\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert msi.is_file(), f"MSI not produced: {msi}"
    assert msi.stat().st_size > MIN_REAL_EXE_BYTES
    sha_file = Path(str(msi) + ".sha256")
    assert sha_file.is_file()
    recorded = sha_file.read_text(encoding="ascii").strip().split()[0].lower()
    assert recorded == _sha256(msi)
