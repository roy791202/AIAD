"""PD-REL-01: WiX packaging contract — template structure + hash metadata.

Validates the Windows packager scaffold without requiring a full MSI install.
Candle/light (WiX v3) may be absent; WiX v4+ `wix build` is preferred when present.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WIX_DIR = ROOT / "packaging" / "windows" / "wix"
MANIFEST_PATH = WIX_DIR / "packaging.manifest.json"
WXS_PATH = WIX_DIR / "SGenAxis.wxs"
README_PATH = WIX_DIR / "README.md"
BUILD_SCRIPT = WIX_DIR / "build-msi.ps1"

# Stable UpgradeCode — must match SGenAxis.wxs (upgrade identity).
EXPECTED_UPGRADE_CODE = "B7E4C2A1-9F83-4D6E-A1B2-C3D4E5F60718"
GUID_RE = re.compile(
    r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest: {MANIFEST_PATH}"
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_wix_scaffold_required_files_exist():
    for path in (WXS_PATH, MANIFEST_PATH, README_PATH, BUILD_SCRIPT):
        assert path.is_file(), f"missing PD-REL-01 artifact: {path}"


def test_manifest_declares_wix_primary_forbids_nsis_inno():
    manifest = _load_manifest()
    packager = manifest["packager"]
    assert packager["primary"] == "wix"
    forbidden = {item.lower() for item in packager["forbidden_primary"]}
    assert "nsis" in forbidden
    assert "inno" in forbidden
    assert packager["product"] == "SGenAxis"
    assert packager["version"] == "0.1.0"
    assert packager["artifact_name_pattern"] == "SGenAxis-{version}-windows-x64.msi"


def test_manifest_marks_non_windows_unsupported():
    targets = _load_manifest()["targets"]
    assert targets["windows"]["status"] == "supported"
    assert targets["windows"]["format"] == "msi"
    assert targets["macos"]["status"] == "unsupported"
    assert targets["linux"]["status"] == "unsupported"
    for key in ("macos", "linux"):
        assert "M4" in targets[key].get("reason", "") or "unsupported" in targets[key]["status"]


def test_manifest_file_hashes_match_on_disk():
    manifest = _load_manifest()
    files = manifest["files"]
    assert "SGenAxis.wxs" in files
    assert "README.md" in files
    assert "build-msi.ps1" in files
    assert "refresh_manifest_hashes.py" in files
    # Manifest must not hash itself (chicken/egg); other tracked files must match.
    for rel, expected in files.items():
        path = WIX_DIR / rel
        assert path.is_file(), f"manifest lists missing file: {rel}"
        digest = _sha256(path)
        assert digest == expected, f"SHA-256 mismatch for {rel}: got {digest}, expected {expected}"


def test_manifest_silent_commands_are_msiexec():
    silent = _load_manifest()["silent"]
    assert "msiexec" in silent["install"].lower()
    assert "/i" in silent["install"].lower() or "/i " in silent["install"]
    assert "/qn" in silent["install"].lower()
    assert "msiexec" in silent["uninstall"].lower()
    assert "/x" in silent["uninstall"].lower()
    assert "/qn" in silent["uninstall"].lower()


def test_wxs_declares_sgenaxis_package_and_stable_upgrade_code():
    text = WXS_PATH.read_text(encoding="utf-8")
    assert 'Name="SGenAxis"' in text or "Name='SGenAxis'" in text
    assert "Manufacturer" in text
    assert EXPECTED_UPGRADE_CODE in text
    assert GUID_RE.match(EXPECTED_UPGRADE_CODE)
    assert 'Version="0.1.0"' in text or "Version='0.1.0'" in text
    # WiX v4+ Package schema (not Product-only v3-only without Package).
    assert "<Package" in text
    assert "http://wixtoolset.org/schemas/v4/wxs" in text
    # Must not be an NSIS (.nsi) or Inno ([Setup]) script disguised as WiX.
    assert "!define" not in text
    assert "[Setup]" not in text
    assert "AppName=" not in text


def test_wxs_has_install_folder_feature_and_embed_cab():
    text = WXS_PATH.read_text(encoding="utf-8")
    assert "INSTALLFOLDER" in text
    assert 'Id="Main"' in text or "Id='Main'" in text
    assert "EmbedCab" in text or "MediaTemplate" in text
    assert "MajorUpgrade" in text
    assert "ProgramFiles64Folder" in text or "ProgramFilesFolder" in text


def test_wxs_major_upgrade_removes_prior_including_same_version():
    """Installer must uninstall prior SGenAxis (same UpgradeCode) then overwrite payload.

    Same-Version rebuilds (new ProductCode, Version still 0.1.0) require
    AllowSameVersionUpgrades; otherwise ARP keeps the old product / files conflict.
    """
    text = WXS_PATH.read_text(encoding="utf-8")
    assert "AllowSameVersionUpgrades" in text
    assert re.search(
        r'AllowSameVersionUpgrades\s*=\s*"yes"', text, re.IGNORECASE
    ), "MajorUpgrade must allow same-version upgrades to replace prior install"
    assert "afterInstallInitialize" in text
    assert "DowngradeErrorMessage" in text


def test_readme_documents_silent_install_and_verify():
    text = README_PATH.read_text(encoding="utf-8")
    lower = text.lower()
    assert "msiexec" in lower
    assert "/qn" in lower
    assert "uninstall" in lower or "/x" in lower
    assert "verify-install" in lower or "silent" in lower
    assert "wix" in lower
    assert "nsis" in lower  # must mention NSIS is not primary
    assert "inno" in lower


def test_build_script_uses_wix_build_not_nsis_inno():
    text = BUILD_SCRIPT.read_text(encoding="utf-8")
    lower = text.lower()
    assert "wix" in lower and "build" in lower
    assert re.search(r"\bwix\s+build\b", lower)
    # May mention makensis/iscc only as non-primary; must not invoke them.
    assert not re.search(r"(?m)^\s*&?\s*makensis\b", text, flags=re.IGNORECASE)
    assert not re.search(r"(?m)^\s*&?\s*iscc\b", text, flags=re.IGNORECASE)
    assert "SGenAxis.wxs" in text or "sgenaxis.wxs" in lower
    assert "not the primary" in lower or "not primary" in lower or "forbidden" in lower


def test_payload_stage_documented_or_present():
    """Payload may be a staged Tauri binary or a scaffold placeholder."""
    payload_dir = WIX_DIR / "payload"
    assert payload_dir.is_dir(), "payload/ stage directory required for bind path"
    readme = payload_dir / "README.txt"
    assert readme.is_file()
    # Either real exe or scaffold stub for contract / optional wix build.
    stub = payload_dir / "SGenAxis.exe"
    assert stub.is_file(), "payload/SGenAxis.exe required (Tauri release or scaffold stub)"


@pytest.mark.parametrize(
    "tool",
    ["candle", "light", "wix"],
)
def test_tool_probe_is_documented_in_manifest(tool: str):
    """Manifest records which WiX toolchain entrypoints are expected (v3 vs v4+)."""
    tools = _load_manifest()["toolchain"]
    assert tool in tools
    assert "preferred" in tools[tool] or "role" in tools[tool]
