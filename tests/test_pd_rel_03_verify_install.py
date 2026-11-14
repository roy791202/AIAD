"""PD-REL-03: VERIFY-INSTALL contract — checklist + runnable hook.

Covers exit / log / files / shortcut checklist items.
Without elevation, elevated checks must be NOT RUN (never forged PASS).
Does not force elevated msiexec /qn for green; does not touch :8788.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WIX_DIR = ROOT / "packaging" / "windows" / "wix"
MANIFEST_PATH = WIX_DIR / "packaging.manifest.json"
CHECKLIST_PATH = WIX_DIR / "verify-install.checklist.json"
VERIFY_SCRIPT = WIX_DIR / "verify-install.ps1"
README_PATH = WIX_DIR / "README.md"
WXS_PATH = WIX_DIR / "SGenAxis.wxs"
OUT_DIR = WIX_DIR / "out"
RESULT_JSON = OUT_DIR / "verify-install-result.json"

REQUIRED_CATEGORIES = {"exit", "log", "files", "shortcut"}
REQUIRED_ELEVATED_IDS = {
    "VI-EXIT-INSTALL",
    "VI-EXIT-UNINSTALL",
    "VI-LOG-INSTALL",
    "VI-FILE-EXE",
    "VI-SHORTCUT-STARTMENU",
    "VI-FILE-GONE",
    "VI-SHORTCUT-GONE",
}


def _load_json(path: Path) -> dict:
    assert path.is_file(), f"missing: {path}"
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _is_elevated() -> bool:
    """Best-effort Windows admin check; False on non-Windows or failure."""
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return False


def test_verify_install_artifacts_exist():
    for path in (CHECKLIST_PATH, VERIFY_SCRIPT, README_PATH, MANIFEST_PATH, WXS_PATH):
        assert path.is_file(), f"missing PD-REL-03 artifact: {path}"


def test_checklist_covers_exit_log_files_shortcut():
    data = _load_json(CHECKLIST_PATH)
    assert data["card"] == "PD-REL-03"
    checks = data["checks"]
    assert isinstance(checks, list) and checks
    cats = {c["category"] for c in checks}
    assert REQUIRED_CATEGORIES <= cats, f"missing categories: {REQUIRED_CATEGORIES - cats}"
    ids = {c["id"] for c in checks}
    assert REQUIRED_ELEVATED_IDS <= ids
    elevated = [c for c in checks if c.get("requires_elevated")]
    assert elevated, "expected elevated checks in checklist"
    for c in elevated:
        assert c["category"] in REQUIRED_CATEGORIES


def test_manifest_declares_verify_install_hook():
    manifest = _load_json(MANIFEST_PATH)
    vi = manifest["verify_install"]
    assert vi["checklist"] == "verify-install.checklist.json"
    assert vi["script"] == "verify-install.ps1"
    assert set(vi["categories"]) == REQUIRED_CATEGORIES
    assert vi.get("elevated_required_for_live") is True
    assert "NOT RUN" in vi.get("non_elevated_policy", "") or vi.get(
        "non_elevated_status"
    ) == "NOT RUN"


def test_manifest_tracked_hashes_include_verify_artifacts():
    files = _load_json(MANIFEST_PATH)["files"]
    for rel in ("verify-install.ps1", "verify-install.checklist.json", "README.md"):
        assert rel in files, f"manifest.files missing {rel}"
        path = WIX_DIR / rel
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == files[rel], f"SHA-256 mismatch for {rel}"


def test_wxs_declares_exe_and_start_menu_shortcut():
    text = WXS_PATH.read_text(encoding="utf-8")
    assert "SGenAxis.exe" in text or "SGenAxisExe" in text
    assert "Shortcut" in text
    assert "ApplicationStartMenuShortcut" in text or "ProgramMenuFolder" in text
    assert "INSTALLFOLDER" in text


def test_readme_documents_verify_install_aligned_to_wix():
    text = README_PATH.read_text(encoding="utf-8")
    lower = text.lower()
    assert "verify-install" in lower
    assert "not run" in lower
    assert "msiexec" in lower and "/qn" in lower
    assert "exit" in lower and "log" in lower
    assert "shortcut" in lower or "start menu" in lower
    assert "wix" in lower
    assert "verify-install.ps1" in text
    assert "verify-install.checklist.json" in text
    # Must not claim elevated install is required for contract green.
    assert "does **not** force elevated" in lower or "does not force elevated" in lower


def test_verify_script_does_not_self_elevate_or_force_msiexec():
    text = VERIFY_SCRIPT.read_text(encoding="utf-8")
    lower = text.lower()
    assert "not run" in lower
    assert "run elevated" in lower or "runelevated" in lower.replace("-", "")
    # Must not invoke UAC self-elevation helpers.
    assert "runas" not in lower or "does not self-elevate" in lower
    assert "shellexecute" not in lower.replace(" ", "")
    assert "-verb" not in lower or "runas" not in lower
    # msiexec only under the elevated live branch (guarded by canLive / RunElevated).
    assert "msiexec" in lower
    assert re.search(r"\$canlive|canlive", text, flags=re.IGNORECASE)


def test_verify_install_ps1_marks_elevated_not_run_without_elevation():
    """Runnable hook: non-elevated invocation must NOT forge PASS on elevated checks."""
    if _is_elevated():
        pytest.skip(  # ci:allow-test-disable: env guard: elevated process cannot assert the NOT-RUN path
            "process is elevated — cannot assert NOT RUN path; live path optional"
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(VERIFY_SCRIPT),
        ],
        cwd=str(WIX_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"verify-install.ps1 failed ({proc.returncode}):\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert RESULT_JSON.is_file(), f"missing result JSON: {RESULT_JSON}"
    result = _load_json(RESULT_JSON)
    assert result["card"] == "PD-REL-03"
    assert result["overall"] in ("PARTIAL", "NOT RUN", "PASS")
    # Without -RunElevated, live must not have executed.
    assert result.get("live_executed") is False
    by_id = {c["id"]: c for c in result["checks"]}
    for eid in REQUIRED_ELEVATED_IDS:
        assert eid in by_id, f"missing check result {eid}"
        assert by_id[eid]["status"] == "NOT RUN", (
            f"{eid} must be NOT RUN when not elevated; got {by_id[eid]['status']}"
        )
        assert by_id[eid]["status"] != "PASS"
    # Overall must not claim full PASS when elevated rows were NOT RUN.
    assert result["overall"] in ("PARTIAL", "NOT RUN")
    cats = {c["category"] for c in result["checks"]}
    assert REQUIRED_CATEGORIES <= cats


def test_verify_install_does_not_run_elevated_when_flag_absent_even_if_admin():
    """Protect: green path never forces /qn — omit -RunElevated → NOT RUN elevated rows."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(VERIFY_SCRIPT),
            # intentionally no -RunElevated
        ],
        cwd=str(WIX_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    result = _load_json(RESULT_JSON)
    assert result.get("run_elevated") is False
    assert result.get("live_executed") is False
    for c in result["checks"]:
        if c["id"] in REQUIRED_ELEVATED_IDS:
            assert c["status"] == "NOT RUN", c
