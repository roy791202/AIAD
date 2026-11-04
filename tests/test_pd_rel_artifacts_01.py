# -*- coding: utf-8 -*-
"""PD-REL-ARTIFACTS-01 — assert artifacts inventory paths / sha / status anti-forge."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "reports" / "artifacts-v0.1.md"

REQUIRED_PHRASES = (
    "BDD-PD-REL-ARTIFACTS-01",
    "PD-REL-ARTIFACTS-01",
    "MSI",
    "SBOM",
    "Build Result",
    "gonogo",
    "sha256",
    "NOT RUN",
    "缺檔",
    "不得暗示未簽章已 PASS",
)

REQUIRED_PATH_HINTS = (
    "packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi",
    "reports/sbom-",
    "reports/build-0.1.0-final-",
    "reports/gonogo-",
    "packaging/windows/out/sign-authenticode-result.json",
)

ANTI_PASS_MARKERS = (
    "不得暗示未簽章已 PASS",
    "Anti-PASS-forge",
    "缺檔 ≠ PASS",
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_artifacts_inventory_exists() -> None:
    assert DOC.is_file(), f"missing {DOC}"


def test_artifacts_inventory_required_phrases() -> None:
    text = DOC.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        assert phrase in text, f"expected phrase {phrase!r}"


def test_artifacts_inventory_lists_msi_sbom_br_gonogo() -> None:
    text = DOC.read_text(encoding="utf-8")
    for hint in REQUIRED_PATH_HINTS:
        assert hint in text, f"expected path hint {hint!r}"


def test_artifacts_inventory_marks_missing_and_not_run() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "缺檔" in text
    assert "NOT RUN" in text
    assert "缺檔 ≠ PASS" in text or "缺檔≠PASS" in text or "缺檔不得" in text


def test_artifacts_inventory_anti_unsigned_pass_forge() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert any(m in text for m in ANTI_PASS_MARKERS)
    assert "不得暗示未簽章已 PASS" in text
    # Signing section must stay NOT RUN (not rewritten PASS)
    assert re.search(r"簽章[\s\S]{0,400}?\*\*NOT RUN\*\*", text) or (
        "signed` | `false`" in text and "NOT RUN" in text
    )
    # Affirmative forge claims only (avoid substring of「不得暗示未簽章已 PASS」)
    forbidden = (
        "未簽章＝PASS",
        "未簽章=PASS",
        "signing=PASS",
        "signing = PASS",
        "legs.signing=PASS",
        "Authenticode 已 PASS",
        "本清單整體=PASS",
    )
    for bad in forbidden:
        assert bad not in text, f"anti-forge: must not contain {bad!r}"
    # Required negation (BDD)
    assert "不得暗示未簽章已 PASS" in text
    # Must not claim unsigned MSI is signed-PASS
    assert "未簽章已 PASS" not in text.replace("不得暗示未簽章已 PASS", "")


def test_listed_msi_sha_matches_file_when_present() -> None:
    """Live check: inventory MSI sha must match on-disk file (no silent drift)."""
    text = DOC.read_text(encoding="utf-8")
    msi = ROOT / "packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi"
    if not msi.is_file():
        assert "缺檔" in text or "NOT RUN" in text
        return
    digest = _sha256_file(msi)
    assert digest in text, "inventory must quote live MSI sha256"
    # Do not pin a stale Rel-Freeze digest — Post-Remain rebuild updates MSI sha.


def test_sign_stub_status_is_not_run() -> None:
    stub = ROOT / "packaging/windows/out/sign-authenticode-result.json"
    assert stub.is_file(), "sign stub result missing — inventory still requires NOT RUN semantics"
    data = json.loads(stub.read_text(encoding="utf-8-sig"))
    assert data.get("status") == "NOT RUN"
    assert data.get("signed") is False
    assert data.get("certConfigured") is False
    text = DOC.read_text(encoding="utf-8")
    assert "sign-authenticode-result.json" in text
    # Inventory must not claim signing PASS while stub is NOT RUN
    assert "不得暗示未簽章已 PASS" in text
