#!/usr/bin/env python3
"""Produce structured Build Result reports (BDD-PD-BUILD-RESULT-01).

Status vocabulary (only): PASS | FAIL | BLOCKED | NOT RUN | PARTIAL.

Writes Markdown under ``reports/`` (default) or ``releases/``. Optionally
appends a board ``#release`` row via ``release_report`` (snapshot-only).

No signing; no macOS/Linux packaging (M4). Reuses ``release_report.build_artifact``.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

BOARD_DIR = Path(__file__).resolve().parent
REPO = BOARD_DIR.parents[1]

if str(BOARD_DIR) not in sys.path:
    sys.path.insert(0, str(BOARD_DIR))

import release_report  # noqa: E402

TAIPEI = timezone(timedelta(hours=8))

VALID_STATUSES: tuple[str, ...] = ("PASS", "FAIL", "BLOCKED", "NOT RUN", "PARTIAL")
_STATUS_SET = frozenset(VALID_STATUSES)

# Worst-wins rollup (higher = worse). FAIL beats BLOCKED; NOT RUN is incomplete.
_STATUS_RANK = {
    "PASS": 0,
    "NOT RUN": 1,
    "PARTIAL": 2,
    "BLOCKED": 3,
    "FAIL": 4,
}

_SEMVER_RE = re.compile(r"^v?\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$")


class BuildResultError(ValueError):
    """Invalid Build Result field or status."""


def now_iso() -> str:
    return datetime.now(TAIPEI).isoformat(timespec="seconds")


def normalize_status(raw: Any) -> str:
    """Map free-form status text to the fixed vocabulary; reject unknowns."""
    if raw is None:
        raise BuildResultError("status is required")
    s = str(raw).strip()
    if not s:
        raise BuildResultError("status is empty")
    key = s.upper().replace("_", " ")
    aliases = {
        "PASS": "PASS",
        "OK": "PASS",
        "FAIL": "FAIL",
        "FAILED": "FAIL",
        "FAILURE": "FAIL",
        "BLOCKED": "BLOCKED",
        "BLOCK": "BLOCKED",
        "NOT RUN": "NOT RUN",
        "NOTRUN": "NOT RUN",
        "SKIPPED": "NOT RUN",
        "SKIP": "NOT RUN",
        "PARTIAL": "PARTIAL",
    }
    compact = key.replace(" ", "")
    out = aliases.get(key) or aliases.get(compact)
    if out is None or out not in _STATUS_SET:
        raise BuildResultError(
            "illegal status %r (allowed: %s)" % (raw, " | ".join(VALID_STATUSES))
        )
    return out


def rollup_status(statuses: Iterable[Any]) -> str:
    """Worst-wins overall status from verification rows."""
    worst = "PASS"
    rank = _STATUS_RANK[worst]
    any_row = False
    for raw in statuses:
        any_row = True
        st = normalize_status(raw)
        r = _STATUS_RANK[st]
        if r > rank:
            rank = r
            worst = st
    if not any_row:
        return "NOT RUN"
    return worst


def _require_semver(version: str) -> str:
    ver = (version or "").strip().lstrip("v")
    if not _SEMVER_RE.match(ver) and not _SEMVER_RE.match("v" + ver):
        raise BuildResultError("version must look like SemVer, got %r" % version)
    return ver


def build_verification_row(
    name: str,
    status: Any,
    *,
    detail: str = "",
    evidence: str = "",
) -> dict:
    row = {
        "name": str(name).strip() or "check",
        "status": normalize_status(status),
    }
    if detail:
        row["detail"] = detail
    if evidence:
        row["evidence"] = evidence
    return row


def build_result(
    *,
    version: str,
    summary: str,
    artifacts: Sequence[Mapping[str, Any]],
    verification: Sequence[Mapping[str, Any]],
    status: Any | None = None,
    changed_files: Sequence[str] | None = None,
    build_command: str = "",
    commit: str = "",
    branch: str = "",
    dependency_versions: Mapping[str, Any] | Sequence[str] | str | None = None,
    target_matrix: Sequence[Mapping[str, Any]] | None = None,
    failed_checks: Sequence[str] | None = None,
    signing_status: Any = "NOT RUN",
    security_summary: str = "",
    requirement_traceability: Sequence[str] | None = None,
    risks: Sequence[str] | None = None,
    rollback: Sequence[str] | None = None,
    pending: Sequence[str] | None = None,
    kind: str = "installer",
    recorded_by: str = "agent",
    generated_at: str | None = None,
    card_id: str = "PD-BUILD-RESULT-01",
) -> dict:
    """Build a structured Build Result object (summary / artifacts / verification / status)."""
    ver = _require_semver(version)
    ts = generated_at or now_iso()

    arts: list[dict] = []
    for a in artifacts:
        if not isinstance(a, Mapping):
            raise BuildResultError("artifact must be a mapping")
        arts.append(dict(a))

    verif: list[dict] = []
    for row in verification:
        if not isinstance(row, Mapping):
            raise BuildResultError("verification row must be a mapping")
        verif.append(
            build_verification_row(
                str(row.get("name") or row.get("id") or "check"),
                row.get("status"),
                detail=str(row.get("detail") or ""),
                evidence=str(row.get("evidence") or ""),
            )
        )

    if status is None:
        overall = rollup_status(r["status"] for r in verif)
        # Signing / matrix rows may already be in verification; keep explicit signing.
        overall = rollup_status([overall, normalize_status(signing_status)])
    else:
        overall = normalize_status(status)

    failed = list(failed_checks) if failed_checks is not None else [
        "%s (%s)" % (r["name"], r.get("detail") or r["status"])
        for r in verif
        if r["status"] == "FAIL"
    ]

    deps: Any
    if dependency_versions is None:
        deps = []
    elif isinstance(dependency_versions, (str, Mapping)):
        deps = dependency_versions
    else:
        deps = list(dependency_versions)

    result: dict = {
        "schema": "aiad.build-result.v1",
        "cardId": card_id,
        "bdd": "BDD-PD-BUILD-RESULT-01",
        "version": ver,
        "id": "v" + ver,
        "kind": kind if kind in ("installer", "portable") else "installer",
        "status": overall,
        "summary": (summary or "").strip() or ("Build Result for v%s" % ver),
        "generatedAt": ts,
        "recordedBy": recorded_by if recorded_by in ("user", "agent") else "agent",
        "changedFiles": list(changed_files or []),
        "buildCommand": build_command or "",
        "artifacts": arts,
        "commit": commit or "",
        "branch": branch or "",
        "dependencyVersions": deps,
        "targetMatrix": [dict(r) for r in (target_matrix or [])],
        "verification": verif,
        "failedChecks": failed,
        "signingStatus": normalize_status(signing_status),
        "securitySummary": security_summary or "none",
        "requirementTraceability": list(requirement_traceability or []),
        "risks": list(risks or []),
        "rollback": list(rollback or []),
        "pending": list(pending or []),
    }
    return result


def render_markdown(result: Mapping[str, Any]) -> str:
    """Render Full Build Result markdown (fixed field order)."""
    if result.get("status") not in _STATUS_SET:
        raise BuildResultError("result.status illegal: %r" % result.get("status"))

    lines: list[str] = []
    ver = str(result.get("version") or "")
    lines.append("# Build Result — v%s" % ver)
    lines.append("")
    lines.append("- **Status:** %s" % result["status"])
    lines.append("- **Generated:** %s" % (result.get("generatedAt") or ""))
    lines.append("- **Card:** %s" % (result.get("cardId") or ""))
    lines.append("- **BDD:** %s" % (result.get("bdd") or "BDD-PD-BUILD-RESULT-01"))
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(str(result.get("summary") or "none"))
    lines.append("")
    lines.append("## Changed files")
    lines.append("")
    cf = result.get("changedFiles") or []
    if cf:
        for p in cf:
            lines.append("- `%s`" % p)
    else:
        lines.append("none")
    lines.append("")
    lines.append("## Build command")
    lines.append("")
    lines.append("```")
    lines.append(str(result.get("buildCommand") or "none"))
    lines.append("```")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    arts = result.get("artifacts") or []
    if not arts:
        lines.append("none")
    else:
        for a in arts:
            label = a.get("label") or "artifact"
            path = a.get("path") or ""
            exists = a.get("exists")
            size = a.get("sizeText") or ""
            sha = a.get("sha256") or ""
            bits = ["**%s**" % label, "`%s`" % path]
            if exists is False:
                bits.append("missing")
            elif exists is True:
                bits.append("exists")
            if size:
                bits.append(size)
            if sha:
                bits.append("sha256=`%s`" % sha)
            lines.append("- " + " — ".join(bits))
    lines.append("")
    lines.append("## Commit / branch")
    lines.append("")
    commit = result.get("commit") or "none"
    branch = result.get("branch") or "none"
    lines.append("- **branch:** `%s`" % branch)
    lines.append("- **commit:** `%s`" % commit)
    lines.append("")
    lines.append("## Dependency versions")
    lines.append("")
    deps = result.get("dependencyVersions")
    if not deps:
        lines.append("none")
    elif isinstance(deps, Mapping):
        for k, v in deps.items():
            lines.append("- **%s:** `%s`" % (k, v))
    elif isinstance(deps, str):
        lines.append(deps)
    else:
        for item in deps:
            lines.append("- %s" % item)
    lines.append("")
    lines.append("## Target OS / DCC matrix")
    lines.append("")
    matrix = result.get("targetMatrix") or []
    if not matrix:
        lines.append("none")
    else:
        lines.append("| Target | Status | Notes |")
        lines.append("| --- | --- | --- |")
        for row in matrix:
            lines.append(
                "| %s | %s | %s |"
                % (
                    row.get("target") or row.get("os") or "",
                    row.get("status") or "NOT RUN",
                    row.get("notes") or row.get("reason") or "",
                )
            )
    lines.append("")
    lines.append("## Verification")
    lines.append("")
    verif = result.get("verification") or []
    if not verif:
        lines.append("- **NOT RUN** — no verification rows")
    else:
        for row in verif:
            detail = row.get("detail") or ""
            evid = row.get("evidence") or ""
            extra = detail
            if evid:
                extra = (extra + "; " if extra else "") + "evidence: %s" % evid
            if extra:
                lines.append("- **%s** — %s — %s" % (row["name"], row["status"], extra))
            else:
                lines.append("- **%s** — %s" % (row["name"], row["status"]))
    lines.append("")
    lines.append("## Failed checks")
    lines.append("")
    failed = result.get("failedChecks") or []
    if not failed:
        lines.append("none")
    else:
        for item in failed:
            lines.append("- %s" % item)
    lines.append("")
    lines.append("## Signing status")
    lines.append("")
    lines.append(str(result.get("signingStatus") or "NOT RUN"))
    lines.append("")
    lines.append("## Security summary")
    lines.append("")
    lines.append(str(result.get("securitySummary") or "none"))
    lines.append("")
    lines.append("## Requirement traceability")
    lines.append("")
    reqs = result.get("requirementTraceability") or []
    if not reqs:
        lines.append("none")
    else:
        for r in reqs:
            lines.append("- %s" % r)
    lines.append("")
    lines.append("## Risks")
    lines.append("")
    risks = result.get("risks") or []
    if not risks:
        lines.append("none")
    else:
        for r in risks:
            lines.append("- %s" % r)
    lines.append("")
    lines.append("## Rollback")
    lines.append("")
    rb = result.get("rollback") or []
    if not rb:
        lines.append("none")
    else:
        for i, step in enumerate(rb, 1):
            lines.append("%d. %s" % (i, step))
    lines.append("")
    lines.append("## Pending")
    lines.append("")
    pending = result.get("pending") or []
    if not pending:
        lines.append("none")
    else:
        for p in pending:
            lines.append("- %s" % p)
    lines.append("")
    return "\n".join(lines)


def default_report_path(
    version: str,
    *,
    generated_at: str | None = None,
    dest: str = "reports",
    repo: Path | None = None,
) -> Path:
    """``reports/build-<semver>-<ts>.md`` or under ``releases/``."""
    root = repo or REPO
    ver = _require_semver(version)
    ts = generated_at or now_iso()
    # filesystem-safe stamp from ISO
    stamp = re.sub(r"[^0-9T]", "", ts.replace("+", "p").replace(":", ""))[:15]
    if not stamp:
        stamp = datetime.now(TAIPEI).strftime("%Y%m%dT%H%M%S")
    folder = dest if dest in ("reports", "releases") else "reports"
    return root / folder / ("build-%s-%s.md" % (ver, stamp))


def write_report(
    result: Mapping[str, Any],
    out_path: Path | None = None,
    *,
    also_json: bool = True,
    repo: Path | None = None,
) -> Path:
    """Write Build Result markdown (and optional sidecar JSON) to reports/ or releases/."""
    root = repo or REPO
    path = Path(out_path) if out_path else default_report_path(
        str(result.get("version") or ""),
        generated_at=str(result.get("generatedAt") or "") or None,
        repo=root,
    )
    if not path.is_absolute():
        path = root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    md = render_markdown(result)
    path.write_text(md, encoding="utf-8", newline="\n")
    if also_json:
        side = path.with_suffix(".json")
        side.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return path


def hang_to_release(
    board_path: Path,
    result: Mapping[str, Any],
    report_path: str | Path,
    *,
    embed_report_md: bool = True,
    repo: Path | None = None,
) -> dict:
    """Append/replace one release row pointing at this Build Result (via release_report)."""
    root = repo or REPO
    rp = Path(report_path)
    try:
        rel = str(rp.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        rel = str(rp).replace("\\", "/")
    release = release_report.build_release(
        version=str(result["version"]),
        artifacts=list(result.get("artifacts") or []),
        report_path=rel,
        kind=str(result.get("kind") or "installer"),
        recorded_by=str(result.get("recordedBy") or "agent"),
        released_at=str(result.get("generatedAt") or now_iso()),
        release_id=str(result.get("id") or ("v" + str(result["version"]))),
        embed_report_md=embed_report_md,
        repo=root,
    )
    # Carry overall Build Result status for consumers that read snapshot.releases.
    release["buildResultStatus"] = result["status"]
    return release_report.append_release(Path(board_path), release)


def candidate_v010_from_packaging(
    *,
    repo: Path | None = None,
    commit: str = "",
    branch: str = "",
    generated_at: str | None = None,
) -> dict:
    """Assemble v0.1.0 candidate Build Result from packaging/ windows WiX evidence (read-only)."""
    root = repo or REPO
    ts = generated_at or now_iso()
    msi = root / "packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi"
    verify_json = root / "packaging/windows/wix/out/verify-install-result.json"
    manifest = root / "packaging/windows/wix/packaging.manifest.json"

    art = release_report.build_artifact(msi, "MSI", ts, root)
    arts = [art]
    sha_side = msi.with_suffix(msi.suffix + ".sha256")
    if sha_side.is_file():
        arts.append(release_report.build_artifact(sha_side, "MSI.sha256", ts, root))

    verify_rows: list[dict] = []
    overall_hint = "PARTIAL"
    elev_live = False
    elev_overall = "NOT RUN"
    if verify_json.is_file():
        data = json.loads(verify_json.read_text(encoding="utf-8-sig"))
        overall_hint = normalize_status(data.get("overall") or "PARTIAL")
        elev_overall = overall_hint
        elev_live = bool(
            data.get("live_executed")
            or data.get("run_elevated")
            or data.get("elevated_process")
            or data.get("elevated")
        )
        for c in data.get("checks") or []:
            verify_rows.append(
                build_verification_row(
                    str(c.get("id") or c.get("category") or "check"),
                    c.get("status") or "NOT RUN",
                    detail=str(c.get("detail") or ""),
                    evidence=str(verify_json.relative_to(root)).replace("\\", "/"),
                )
            )
    else:
        verify_rows.append(
            build_verification_row(
                "VERIFY-INSTALL",
                "NOT RUN",
                detail="verify-install-result.json missing",
            )
        )

    verify_rows.append(
        build_verification_row(
            "MSI-ARTIFACT",
            "PASS" if art.get("exists") else "FAIL",
            detail=str(art.get("path") or msi),
            evidence="packaging/windows/wix/out/",
        )
    )
    verify_rows.append(
        build_verification_row(
            "SIGNING",
            "NOT RUN",
            detail="No Authenticode / notarize this card (explicit out of scope)",
        )
    )
    verify_rows.append(
        build_verification_row(
            "PACK-MACOS",
            "NOT RUN",
            detail="M4 — macOS packs out of scope",
        )
    )
    verify_rows.append(
        build_verification_row(
            "PACK-LINUX",
            "NOT RUN",
            detail="M4 — Linux packs out of scope",
        )
    )

    deps: dict[str, str] = {"packager": "wix", "product": "SGenAxis", "version": "0.1.0"}
    if manifest.is_file():
        try:
            man = json.loads(manifest.read_text(encoding="utf-8-sig"))
            deps["wix_primary"] = str((man.get("packager") or {}).get("primary") or "wix")
            payload = man.get("payload") or {}
            if payload.get("sha256"):
                deps["payload_sha256"] = str(payload["sha256"])
        except (OSError, json.JSONDecodeError):
            pass

    # Overall: include packaging verify overall + our extra rows (signing NOT RUN → stays PARTIAL/NOT RUN).
    overall = rollup_status([overall_hint] + [r["status"] for r in verify_rows])

    win_notes = (
        "MSI present; elevated VERIFY-INSTALL %s (live=%s)"
        % (elev_overall, elev_live)
    )
    elev_risk = (
        "Elevated VERIFY-INSTALL evidence=%s live=%s — still do not forge overall PASS "
        "(signing / other legs may remain NOT RUN)."
        % (elev_overall, elev_live)
        if elev_live and elev_overall == "PASS"
        else "Elevated silent install/uninstall checks are NOT RUN — do not treat as release-ready PASS."
    )
    pending = [
        "Authenticode signing (out of this card)",
        "macOS/Linux packs (M4)",
        "PD-SEC-SCAN-01: attach reports/sec-scan-*.json (high untriaged must not forge PASS)",
        "PD-SBOM-01: attach reports/sbom-*.json (SBOM alone must not forge PASS over high untriaged)",
    ]
    if not (elev_live and elev_overall == "PASS"):
        pending.insert(0, "Elevated VERIFY-INSTALL (-RunElevated) when operator available")

    return build_result(
        version="0.1.0",
        summary=(
            "v0.1.0 Windows MSI candidate (SGenAxis). "
            "Structured Build Result from packaging evidence; "
            "elevated VERIFY-INSTALL=%s (live=%s); signing and non-Windows packs NOT RUN (M4)."
            % (elev_overall, elev_live)
        ),
        artifacts=arts,
        verification=verify_rows,
        status=overall,
        changed_files=[
            "packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi",
            "packaging/windows/wix/out/verify-install-result.json",
            "packaging/windows/wix/packaging.manifest.json",
        ],
        build_command="cd packaging/windows/wix; .\\build-msi.ps1",
        commit=commit,
        branch=branch,
        dependency_versions=deps,
        target_matrix=[
            {
                "target": "windows-x64",
                "status": elev_overall if elev_live else "PARTIAL",
                "notes": win_notes,
            },
            {"target": "macos", "status": "NOT RUN", "notes": "M4 — not WiX"},
            {"target": "linux", "status": "NOT RUN", "notes": "M4 — not WiX"},
        ],
        signing_status="NOT RUN",
        security_summary="No CVE/secret scan attached this pass — treat as NOT RUN / pending triage before green release.",
        requirement_traceability=[
            "BDD-PD-BUILD-RESULT-01",
            "PD-REL-02",
            "PD-REL-03",
            "PD-RELEASE-REC-01",
            "PD-REPORT-01",
        ],
        risks=[
            elev_risk,
            "Signing not performed — distribution channel may reject unsigned MSI.",
            "macOS/Linux artifacts intentionally absent (M4).",
        ],
        rollback=[
            "Do not distribute unsigned/unverified MSI beyond lab.",
            "Remove or quarantine packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi if a bad candidate is published.",
            "If a release row was appended, re-append a corrected reportPath via release_report or delete that release id in snapshot.releases via snapshot_safe.",
        ],
        pending=pending,
        generated_at=ts,
        card_id="PD-BUILD-RESULT-01",
    )


def attach_sbom(
    result: MutableMapping[str, Any],
    sbom_payload: Mapping[str, Any] | None = None,
    *,
    repo: Path | None = None,
) -> MutableMapping[str, Any]:
    """Hang PD-SBOM-01 into a Build Result (missing/FAIL / high untriaged → cannot claim PASS).

    If ``sbom_payload`` is None, loads latest ``reports/sbom-*.json`` (schema aiad.sbom.v1).
    """
    # Circular: sbom imports build_result for status vocabulary / verification rows.
    import sbom as _sbom  # noqa: PLC0415 — documented circular hang path

    payload = (
        sbom_payload if sbom_payload is not None else _sbom.load_latest_sbom(repo or REPO)
    )
    if payload is None:
        st = normalize_status(result.get("status") or "NOT RUN")
        if st == "PASS":
            result["status"] = "NOT RUN"
        line = (
            "PD-SBOM-01 NOT RUN — no reports/sbom-*.json; "
            "do not treat Build Result as SBOM-cleared PASS."
        )
        result["sbomSummary"] = line
        prev = str(result.get("securitySummary") or "").strip()
        result["securitySummary"] = (prev + " | " + line) if prev else line
        verif = list(result.get("verification") or [])
        verif.append(
            build_verification_row(
                "SBOM",
                "NOT RUN",
                detail="no sbom report attached",
            )
        )
        result["verification"] = verif
        return result
    return _sbom.attach_to_build_result(result, payload)


def attach_security_scan(
    result: MutableMapping[str, Any],
    scan: Mapping[str, Any] | None = None,
    *,
    repo: Path | None = None,
) -> MutableMapping[str, Any]:
    """Hang PD-SEC-SCAN-01 into a Build Result (high untriaged → cannot claim PASS).

    If ``scan`` is None, loads latest ``reports/sec-scan-*.json``.
    """
    # Circular: sec_scan imports build_result for status vocabulary / verification rows.
    import sec_scan as _sec_scan  # noqa: PLC0415 — documented circular hang path

    payload = scan if scan is not None else _sec_scan.load_latest_scan(repo or REPO)
    if payload is None:
        # Explicit NOT RUN — refuse forged PASS.
        st = normalize_status(result.get("status") or "NOT RUN")
        if st == "PASS":
            result["status"] = "NOT RUN"
        result["securitySummary"] = (
            "PD-SEC-SCAN-01 NOT RUN — no reports/sec-scan-*.json; "
            "do not treat Build Result as security-cleared PASS."
        )
        verif = list(result.get("verification") or [])
        verif.append(
            build_verification_row(
                "SEC-SCAN",
                "NOT RUN",
                detail="no sec-scan report attached",
            )
        )
        result["verification"] = verif
        return result
    return _sec_scan.attach_to_build_result(result, payload)


def attach_verify_hang(
    result: MutableMapping[str, Any],
    *,
    elev_path: str | Path | None = None,
    live_path: str | Path | None = None,
    repo: Path | None = None,
) -> MutableMapping[str, Any]:
    """Hang PD-VERIFY-HANG-01 elev VERIFY + Live smoke (missing → NOT RUN; never forge PASS)."""
    # Circular: verify_hang imports build_result for status vocabulary / verification rows.
    import verify_hang as _verify_hang  # noqa: PLC0415 — documented circular hang path

    return _verify_hang.attach_verify_hang(
        result,
        elev_path=elev_path,
        live_path=live_path,
        repo=repo or REPO,
    )


# --- PD-BR-FINAL-01: SBOM + Rel-Freeze + GoNoGo hang (never forge PASS) --------

FINAL_CARD_ID = "PD-BR-FINAL-01"
FINAL_BDD_ID = "BDD-PD-BR-FINAL-01"
REL_FREEZE_DEFAULT = "reports/milestone-validation-v0.1.md"

_REL_FREEZE_STATUS_RE = re.compile(
    r"##\s*8\.\s*Rel-Freeze.*?\|\s*Status\s*\|\s*\*?\*?([A-Z][A-Z ]*)\*?\*?\s*\|",
    re.IGNORECASE | re.DOTALL,
)
_REL_FREEZE_ROLLUP_RE = re.compile(
    r"\|\s*Rel-Freeze\s*\|\s*\*?\*?([A-Z][A-Z ]*)\*?\*?\s*\|",
    re.IGNORECASE,
)


def parse_rel_freeze_status(text: str) -> str:
    """Extract Rel-Freeze status from milestone-validation markdown; blank → NOT RUN."""
    if not (text or "").strip():
        return "NOT RUN"
    m = _REL_FREEZE_STATUS_RE.search(text)
    if m:
        return normalize_status(m.group(1))
    m2 = _REL_FREEZE_ROLLUP_RE.search(text)
    if m2:
        return normalize_status(m2.group(1))
    return "NOT RUN"


def find_latest_gonogo(reports_dir: Path) -> Path | None:
    """Latest ``reports/gonogo-*.json`` by mtime (machine evidence)."""
    if not reports_dir.is_dir():
        return None
    cands = sorted(
        reports_dir.glob("gonogo-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return cands[0] if cands else None


def refuse_hang_forged_pass(result: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Re-rollup after hangs; signing NOT RUN must not leave forged overall PASS.

    BDD-PD-BR-FINAL-01: hanging SBOM / Rel-Freeze / GoNoGo must not invent PASS;
    PARTIAL is allowed. Does not rewrite signing NOT RUN → PASS.
    """
    sign = normalize_status(result.get("signingStatus") or "NOT RUN")
    result["signingStatus"] = sign
    statuses = [r["status"] for r in (result.get("verification") or [])]
    statuses.append(sign)
    rolled = rollup_status(statuses)
    if sign == "NOT RUN" and rolled == "PASS":
        rolled = "PARTIAL"
    prev = normalize_status(result.get("status") or "NOT RUN")
    # Hang must not promote a non-PASS overall into PASS.
    if rolled == "PASS" and prev != "PASS":
        rolled = "PARTIAL" if prev in ("NOT RUN", "PARTIAL") else prev
    result["status"] = rolled
    return result


def attach_rel_freeze(
    result: MutableMapping[str, Any],
    *,
    freeze_path: str | Path | None = None,
    repo: Path | None = None,
) -> MutableMapping[str, Any]:
    """Hang Rel-Freeze evidence (milestone-validation); missing → NOT RUN, no forged PASS."""
    root = repo or REPO
    path = Path(freeze_path) if freeze_path else (root / REL_FREEZE_DEFAULT)
    prev = normalize_status(result.get("status") or "NOT RUN")

    if not path.is_file():
        st = "NOT RUN"
        detail = "Rel-Freeze evidence missing (%s)" % REL_FREEZE_DEFAULT
        evid = REL_FREEZE_DEFAULT
        line = "PD-BR-FINAL-01 Rel-Freeze NOT RUN — no milestone-validation report."
    else:
        text = path.read_text(encoding="utf-8")
        st = parse_rel_freeze_status(text)
        try:
            evid = str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
        except ValueError:
            evid = str(path).replace("\\", "/")
        detail = "Rel-Freeze status from milestone validation"
        line = "PD-BR-FINAL-01 Rel-Freeze %s — evidence=%s" % (st, evid)

    result["relFreezeSummary"] = line
    verif = list(result.get("verification") or [])
    verif.append(
        build_verification_row("REL-FREEZE", st, detail=detail, evidence=evid)
    )
    result["verification"] = verif

    pending = list(result.get("pending") or [])
    if st in ("NOT RUN", "FAIL", "BLOCKED"):
        pending.append(
            "Rel-Freeze incomplete (%s) — do not treat Build Result hang as release freeze PASS"
            % st
        )
    result["pending"] = pending

    reqs = list(result.get("requirementTraceability") or [])
    for tid in (FINAL_BDD_ID, FINAL_CARD_ID, "PD-MILESTONE-VAL-01"):
        if tid not in reqs:
            reqs.append(tid)
    result["requirementTraceability"] = reqs

    # Demote forged PASS when freeze missing/incomplete; then honest rollup.
    if prev == "PASS" and st != "PASS":
        result["status"] = "PARTIAL" if st in ("PARTIAL", "NOT RUN") else st
    return refuse_hang_forged_pass(result)


def attach_gonogo(
    result: MutableMapping[str, Any],
    gonogo_payload: Mapping[str, Any] | None = None,
    *,
    repo: Path | None = None,
) -> MutableMapping[str, Any]:
    """Hang PD-REL-GONOGO-01 evidence; missing → NOT RUN; never forge PASS / signing PASS."""
    root = repo or REPO
    prev = normalize_status(result.get("status") or "NOT RUN")
    payload = gonogo_payload
    evid = "(missing)"
    if payload is None:
        path = find_latest_gonogo(root / "reports")
        if path is not None and path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            try:
                evid = str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
            except ValueError:
                evid = str(path).replace("\\", "/")

    verif = list(result.get("verification") or [])

    if payload is None or not isinstance(payload, Mapping):
        verif.append(
            build_verification_row(
                "GONOGO",
                "NOT RUN",
                detail="no reports/gonogo-*.json",
                evidence="reports/",
            )
        )
        result["verification"] = verif
        result["gonogoSummary"] = (
            "PD-REL-GONOGO-01 NOT RUN — no gonogo report; "
            "do not treat Build Result as Go/NoGo-cleared PASS."
        )
        if prev == "PASS":
            result["status"] = "NOT RUN"
        pending = list(result.get("pending") or [])
        pending.append("Re-run PD-REL-GONOGO-01 until gonogo evidence exists")
        result["pending"] = pending
        return refuse_hang_forged_pass(result)

    verdict = str(payload.get("verdict") or "").strip()
    verdict_map = {
        "Go": "PASS",
        "Go-with-PARTIAL": "PARTIAL",
        "NoGo": "FAIL",
    }
    verdict_st = verdict_map.get(verdict, "NOT RUN")
    legs = payload.get("legs") or {}
    sign_leg = normalize_status(legs.get("signing") or "NOT RUN")
    # HARD: 簽章缺證維持 NOT RUN — never promote signingStatus via hang.
    if sign_leg == "NOT RUN":
        result["signingStatus"] = "NOT RUN"
    elif normalize_status(result.get("signingStatus") or "NOT RUN") == "NOT RUN":
        # Keep explicit NOT RUN on Build Result even if a leg claims otherwise without
        # this card forcing PASS (不做: 強制簽章 PASS).
        result["signingStatus"] = "NOT RUN"

    sources = payload.get("sources") or {}
    if sources.get("build_result"):
        evid = evid if evid != "(missing)" else str(sources.get("build_result"))

    verif.append(
        build_verification_row(
            "GONOGO",
            verdict_st,
            detail="verdict=%s gate=%s" % (verdict or "?", payload.get("gateRef") or ""),
            evidence=evid,
        )
    )
    verif.append(
        build_verification_row(
            "GONOGO-SIGNING",
            sign_leg,
            detail="gonogo signing leg (缺證 stays NOT RUN)",
            evidence=str(sources.get("signing") or evid),
        )
    )
    result["verification"] = verif
    result["gonogoSummary"] = (
        "PD-REL-GONOGO-01 %s — verdict=%s; signing=%s; evidence=%s"
        % (verdict_st, verdict or "?", sign_leg, evid)
    )
    result["gonogo"] = {
        "verdict": verdict,
        "status": verdict_st,
        "signing": sign_leg,
        "evidence": evid,
        "readyForGreen": bool(payload.get("readyForGreen")),
    }

    reqs = list(result.get("requirementTraceability") or [])
    for tid in (FINAL_BDD_ID, FINAL_CARD_ID, "BDD-PD-REL-GONOGO-01", "PD-REL-GONOGO-01"):
        if tid not in reqs:
            reqs.append(tid)
    result["requirementTraceability"] = reqs

    pending = list(result.get("pending") or [])
    if sign_leg == "NOT RUN":
        pending.append("Authenticode signing still NOT RUN (gonogo leg; not forced PASS)")
    if verdict_st == "FAIL":
        pending.append("Go/NoGo verdict is NoGo — resolve legs before release")
    result["pending"] = pending

    if prev == "PASS" and verdict_st != "PASS":
        result["status"] = verdict_st if verdict_st != "NOT RUN" else "NOT RUN"
    return refuse_hang_forged_pass(result)


def final_report_path(
    version: str,
    *,
    generated_at: str | None = None,
    dest: str = "reports",
    repo: Path | None = None,
) -> Path:
    """``reports/build-<semver>-final-<ts>.md``."""
    root = repo or REPO
    ver = _require_semver(version)
    ts = generated_at or now_iso()
    stamp = re.sub(r"[^0-9T]", "", ts.replace("+", "p").replace(":", ""))[:15]
    if not stamp:
        stamp = datetime.now(TAIPEI).strftime("%Y%m%dT%H%M%S")
    folder = dest if dest in ("reports", "releases") else "reports"
    return root / folder / ("build-%s-final-%s.md" % (ver, stamp))


def generate_final_v010(
    *,
    repo: Path | None = None,
    commit: str = "",
    branch: str = "",
    attach_security: bool = True,
    attach_verify: bool = True,
    freeze_path: str | Path | None = None,
    gonogo_payload: Mapping[str, Any] | None = None,
) -> dict:
    """Assemble final v0.1.0 Build Result hanging SBOM + Rel-Freeze + GoNoGo.

    Signing stays NOT RUN when evidence is missing; overall may be PARTIAL — never forged PASS.
    """
    root = repo or REPO
    result = candidate_v010_from_packaging(
        repo=root, commit=commit, branch=branch
    )
    if attach_security:
        attach_security_scan(result, repo=root)
    if attach_verify:
        attach_verify_hang(result, repo=root)
    attach_sbom(result, repo=root)
    attach_rel_freeze(result, freeze_path=freeze_path, repo=root)
    attach_gonogo(result, gonogo_payload, repo=root)
    stamp_refresh_card(result, FINAL_CARD_ID)
    # Card out of scope: never force signing PASS.
    if normalize_status(result.get("signingStatus") or "NOT RUN") == "PASS":
        # Only retain PASS if a SIGNING verification row already proves it; else demote.
        sign_rows = [
            r
            for r in (result.get("verification") or [])
            if str(r.get("name") or "").upper() in ("SIGNING", "GONOGO-SIGNING")
            and r.get("status") == "PASS"
        ]
        if not sign_rows:
            result["signingStatus"] = "NOT RUN"
    refuse_hang_forged_pass(result)
    summary = str(result.get("summary") or "")
    result["summary"] = (
        summary
        + " Final hang (PD-BR-FINAL-01): SBOM + Rel-Freeze + GoNoGo attached; "
        "signing NOT RUN when evidence missing; overall must not forge PASS (PARTIAL allowed)."
    )
    pending = list(result.get("pending") or [])
    for line in (
        "PD-BR-FINAL-01: board zone stays yellow until parent greens after TDD_PASS (§7.1)",
    ):
        if line not in pending:
            pending.append(line)
    result["pending"] = pending
    return result


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--board",
        default=os.environ.get("HB_BOARD_TASKS") or str(REPO / "docs" / "PROJECT-BOARD.html"),
        help="PROJECT-BOARD.html for optional --record-release",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Generate v0.1.0 candidate (or --version) Build Result")
    g.add_argument("--version", default="0.1.0")
    g.add_argument("--dest", choices=("reports", "releases"), default="reports")
    g.add_argument("--out", default="", help="Explicit output .md path")
    g.add_argument("--commit", default="")
    g.add_argument("--branch", default="")
    g.add_argument(
        "--record-release",
        action="store_true",
        help="Append snapshot.releases via release_report (reportPath → this Build Result)",
    )
    g.add_argument("--no-json", action="store_true", help="Skip sidecar .json")
    g.add_argument("--no-embed-report", action="store_true")
    g.add_argument(
        "--attach-security",
        action="store_true",
        help="Hang latest PD-SEC-SCAN-01 report (high untriaged refuses forged PASS)",
    )
    g.add_argument(
        "--attach-sbom",
        action="store_true",
        help="Hang latest PD-SBOM-01 report (missing/FAIL / high untriaged refuses forged PASS)",
    )
    g.add_argument(
        "--attach-verify-hang",
        action="store_true",
        help="Hang elev VERIFY + Live smoke (PD-VERIFY-HANG-01; missing → NOT RUN, never forge PASS)",
    )
    g.add_argument(
        "--elev-verify",
        default="",
        help="Optional elev VERIFY JSON path (with --attach-verify-hang)",
    )
    g.add_argument(
        "--live-smoke",
        default="",
        help="Optional Live CLI smoke JSON path (with --attach-verify-hang)",
    )
    g.add_argument(
        "--card-id",
        default="",
        help="Override result cardId / bdd stamp (e.g. PD-BR-REFRESH-01)",
    )
    g.add_argument(
        "--attach-rel-freeze",
        action="store_true",
        help="Hang Rel-Freeze evidence from milestone-validation (missing → NOT RUN)",
    )
    g.add_argument(
        "--attach-gonogo",
        action="store_true",
        help="Hang latest PD-REL-GONOGO-01 report (missing → NOT RUN; never forge PASS)",
    )
    g.add_argument(
        "--final",
        action="store_true",
        help="PD-BR-FINAL-01: SBOM+freeze+gonogo hang; write reports/build-*-final-*.md",
    )
    g.add_argument(
        "--rel-freeze",
        default="",
        help="Optional Rel-Freeze markdown path (with --attach-rel-freeze / --final)",
    )

    v = sub.add_parser("validate-status", help="Exit 0 if status is in vocabulary")
    v.add_argument("status")

    return ap


def stamp_refresh_card(result: MutableMapping[str, Any], card_id: str) -> MutableMapping[str, Any]:
    """Stamp a refresh card id + BDD onto an assembled Build Result (PD-BR-REFRESH-01)."""
    cid = (card_id or "").strip()
    if not cid:
        return result
    result["cardId"] = cid
    bdd = "BDD-%s" % cid
    result["bdd"] = bdd
    reqs = list(result.get("requirementTraceability") or [])
    for tid in (bdd, cid):
        if tid not in reqs:
            reqs.append(tid)
    result["requirementTraceability"] = reqs
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    if args.cmd == "validate-status":
        try:
            print(normalize_status(args.status))
            return 0
        except BuildResultError as exc:
            print("rejected: %s" % exc, file=sys.stderr)
            return 1

    if args.cmd == "generate":
        if args.version.lstrip("v") != "0.1.0":
            # Only packaging-backed generator is wired for 0.1.0 candidate this card.
            print(
                "rejected: only packaging-backed generator for 0.1.0 is implemented (got %r)"
                % args.version,
                file=sys.stderr,
            )
            return 1
        if args.final:
            result = generate_final_v010(
                repo=REPO,
                commit=args.commit,
                branch=args.branch,
                freeze_path=args.rel_freeze or None,
            )
        else:
            result = candidate_v010_from_packaging(
                repo=REPO,
                commit=args.commit,
                branch=args.branch,
            )
            if args.attach_security:
                attach_security_scan(result, repo=REPO)
            if args.attach_sbom:
                attach_sbom(result, repo=REPO)
            if args.attach_verify_hang:
                attach_verify_hang(
                    result,
                    elev_path=args.elev_verify or None,
                    live_path=args.live_smoke or None,
                    repo=REPO,
                )
            if args.attach_rel_freeze:
                attach_rel_freeze(
                    result,
                    freeze_path=args.rel_freeze or None,
                    repo=REPO,
                )
            if args.attach_gonogo:
                attach_gonogo(result, repo=REPO)
            if args.card_id:
                stamp_refresh_card(result, args.card_id)
        out = (
            Path(args.out)
            if args.out
            else (
                final_report_path(
                    result["version"],
                    generated_at=result["generatedAt"],
                    dest=args.dest,
                    repo=REPO,
                )
                if args.final
                else default_report_path(
                    result["version"],
                    generated_at=result["generatedAt"],
                    dest=args.dest,
                    repo=REPO,
                )
            )
        )
        path = write_report(result, out, also_json=not args.no_json, repo=REPO)
        print("wrote %s status=%s" % (path, result["status"]))
        if args.record_release:
            stored = hang_to_release(
                Path(args.board),
                result,
                path,
                embed_report_md=not args.no_embed_report,
                repo=REPO,
            )
            print(
                "recorded release id=%s buildResultStatus=%s reportPath=%s"
                % (
                    stored.get("id"),
                    stored.get("buildResultStatus"),
                    stored.get("reportPath"),
                )
            )
        return 0

    print("unknown command", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
