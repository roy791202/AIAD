# -*- coding: utf-8 -*-
"""PD-REL-ARTIFACTS-POST-01 — Post-Remain artifacts inventory paths / sha / anti-forge."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "reports" / "artifacts-v0.1.md"

REQUIRED_PHRASES = (
    "BDD-PD-REL-ARTIFACTS-POST-01",
    "PD-REL-ARTIFACTS-POST-01",
    "Post-Remain",
    "MSI",
    "SBOM",
    "Build Result",
    "sha256",
    "NOT RUN",
    "缺檔",
    "不得暗示未簽章已 PASS",
)

REQUIRED_PATH_HINTS = (
    "packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi",
    "reports/sbom-",
    "reports/build-0.1.0-post-remain",
    "packaging/windows/out/sign-authenticode-result.json",
)

ANTI_PASS_MARKERS = (
    "不得暗示未簽章已 PASS",
    "Anti-PASS-forge",
    "缺檔 ≠ PASS",
)

# Live Post-Remain MSI sha (PD-REL-MSI-REBUILD-01 / post-remain BR)
POST_REMAIN_MSI_SHA = "09683a10b9aad5edbb35f768f2adcb32e2e0ad6d197a43869ad51a8044a632f8"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_post_artifacts_inventory_exists() -> None:
    assert DOC.is_file(), f"missing {DOC}"


def test_post_artifacts_inventory_required_phrases() -> None:
    text = DOC.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        assert phrase in text, f"expected phrase {phrase!r}"


def test_post_artifacts_lists_msi_sbom_post_remain_br() -> None:
    text = DOC.read_text(encoding="utf-8")
    for hint in REQUIRED_PATH_HINTS:
        assert hint in text, f"expected path hint {hint!r}"
    assert "build-0.1.0-post-remain.md" in text
    assert "build-0.1.0-post-remain.json" in text


def test_post_artifacts_marks_missing_and_not_run() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "缺檔" in text
    assert "NOT RUN" in text
    assert "缺檔 ≠ PASS" in text or "缺檔≠PASS" in text


def test_post_artifacts_anti_unsigned_pass_forge() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert any(m in text for m in ANTI_PASS_MARKERS)
    assert "不得暗示未簽章已 PASS" in text
    assert re.search(r"簽章[\s\S]{0,500}?\*\*NOT RUN\*\*", text) or (
        "`signed` | `false`" in text and "NOT RUN" in text
    )
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
    assert "未簽章已 PASS" not in text.replace("不得暗示未簽章已 PASS", "")


def test_post_remain_msi_sha_matches_live_and_inventory() -> None:
    text = DOC.read_text(encoding="utf-8")
    msi = ROOT / "packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi"
    if not msi.is_file():
        assert "缺檔" in text or "NOT RUN" in text
        return
    digest = _sha256_file(msi)
    assert digest == POST_REMAIN_MSI_SHA
    assert digest in text, "inventory must quote live Post-Remain MSI sha256"
    # Stale Rel-Freeze MSI sha must not be the authoritative quoted MSI sha
    assert "facbfc8112991929b9142514cbea43903d270c4d04cc86715d805eec690ff5fb" not in text.split(
        "## 2. SBOM"
    )[0]


def test_post_remain_br_sha_when_present() -> None:
    text = DOC.read_text(encoding="utf-8")
    br_md = ROOT / "reports" / "build-0.1.0-post-remain.md"
    br_json = ROOT / "reports" / "build-0.1.0-post-remain.json"
    if not br_md.is_file() or not br_json.is_file():
        assert "缺檔" in text and ("post-remain" in text.lower() or "Post-Remain" in text)
        return
    assert _sha256_file(br_md) in text
    assert _sha256_file(br_json) in text
    assert "PARTIAL" in text


def test_sign_result_status_is_not_run() -> None:
    stub = ROOT / "packaging/windows/out/sign-authenticode-result.json"
    assert stub.is_file(), "sign result missing — inventory still requires NOT RUN semantics"
    data = json.loads(stub.read_text(encoding="utf-8-sig"))
    assert data.get("status") == "NOT RUN"
    assert data.get("signed") is False
    assert data.get("certConfigured") is False
    text = DOC.read_text(encoding="utf-8")
    assert "sign-authenticode-result.json" in text
    assert "不得暗示未簽章已 PASS" in text
