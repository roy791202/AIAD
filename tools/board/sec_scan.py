#!/usr/bin/env python3
"""PD-SEC-SCAN-01 — dependency CVE + secret scan (hangable into Build Result).

BDD-PD-SEC-SCAN-01:
  - Rerunnable scan produces a report under ``reports/``.
  - High-severity findings not yet triaged must not allow a Build Result to
    claim PASS (gate via ``apply_security_gate`` / ``attach_to_build_result``).
  - Status vocabulary (explicit): PASS | FAIL | PARTIAL | NOT RUN.

Does **not** force CI merge-block; optional hang only.

Tools (best-effort; missing → NOT RUN for that leg):
  - Secrets: ``gitleaks``
  - CVE / deps: ``trivy fs`` (Cargo.lock / package-lock / requirements)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

BOARD_DIR = Path(__file__).resolve().parent
REPO = BOARD_DIR.parents[1]

if str(BOARD_DIR) not in sys.path:
    sys.path.insert(0, str(BOARD_DIR))

import build_result as br  # noqa: E402

TAIPEI = timezone(timedelta(hours=8))

CARD_ID = "PD-SEC-SCAN-01"
BDD_ID = "BDD-PD-SEC-SCAN-01"
SCHEMA = "aiad.sec-scan.v1"

# Severities that block Build Result PASS until triage.
HIGH_SEVS = frozenset({"CRITICAL", "HIGH"})

VALID_SCAN_STATUSES = frozenset(br.VALID_STATUSES)  # PASS|FAIL|BLOCKED|NOT RUN|PARTIAL


class SecScanError(ValueError):
    """Invalid scan / triage input."""


def now_iso() -> str:
    return datetime.now(TAIPEI).isoformat(timespec="seconds")


def _stamp(iso: str | None = None) -> str:
    ts = iso or now_iso()
    stamp = re.sub(r"[^0-9T]", "", ts.replace("+", "p").replace(":", ""))[:15]
    return stamp or datetime.now(TAIPEI).strftime("%Y%m%dT%H%M%S")


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def load_triage(path: Path | None) -> set[str]:
    """Load waived finding ids from JSON ``{"waived":[{"id":"..."}, ...]}`` or ``["id",...]``."""
    if path is None or not path.is_file():
        return set()
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    out: set[str] = set()
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str) and item.strip():
                out.add(item.strip())
            elif isinstance(item, Mapping) and item.get("id"):
                out.add(str(item["id"]).strip())
        return out
    if isinstance(raw, Mapping):
        for key in ("waived", "triaged", "accepted"):
            for item in raw.get(key) or []:
                if isinstance(item, str) and item.strip():
                    out.add(item.strip())
                elif isinstance(item, Mapping) and item.get("id"):
                    out.add(str(item["id"]).strip())
        return out
    raise SecScanError("triage file must be list or object, got %r" % type(raw))


def finding_id(kind: str, **parts: Any) -> str:
    bits = [kind] + [str(parts[k]) for k in sorted(parts) if parts[k] is not None]
    return "|".join(bits)


def _run(
    cmd: Sequence[str],
    *,
    cwd: Path,
    timeout: int = 600,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def run_secret_scan(
    repo: Path,
    *,
    gitleaks_bin: str | None = None,
) -> dict[str, Any]:
    """Run gitleaks detect; return leg dict with status + findings."""
    bin_path = gitleaks_bin or which("gitleaks")
    if not bin_path:
        return {
            "name": "secret-scan",
            "tool": "gitleaks",
            "status": "NOT RUN",
            "detail": "gitleaks not on PATH",
            "findings": [],
        }
    out_json = repo / "reports" / "_sec-scan-gitleaks.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    # gitleaks writes report even when leaks found (exit 1).
    proc = _run(
        [
            bin_path,
            "detect",
            "--source",
            str(repo),
            "--report-format",
            "json",
            "--report-path",
            str(out_json),
            "--no-banner",
            "--exit-code",
            "1",
        ],
        cwd=repo,
        timeout=900,
    )
    findings: list[dict[str, Any]] = []
    if out_json.is_file() and out_json.stat().st_size > 2:
        try:
            data = json.loads(out_json.read_text(encoding="utf-8-sig") or "[]")
        except json.JSONDecodeError:
            data = []
        if isinstance(data, list):
            for row in data:
                if not isinstance(row, Mapping):
                    continue
                fid = finding_id(
                    "secret",
                    rule=row.get("RuleID") or row.get("Rule") or "unknown",
                    file=row.get("File") or row.get("Match") or "",
                    line=row.get("StartLine") or row.get("Line") or "",
                )
                findings.append(
                    {
                        "id": fid,
                        "kind": "secret",
                        "severity": "HIGH",
                        "rule": row.get("RuleID") or row.get("Rule") or "",
                        "file": row.get("File") or "",
                        "line": row.get("StartLine") or "",
                        "description": row.get("Description") or row.get("Message") or "",
                    }
                )
    # exit 0 = clean; 1 = leaks; other = tool failure
    if proc.returncode not in (0, 1):
        return {
            "name": "secret-scan",
            "tool": "gitleaks",
            "status": "PARTIAL",
            "detail": "gitleaks exit %s: %s"
            % (proc.returncode, (proc.stderr or proc.stdout or "")[:400]),
            "findings": findings,
            "evidence": str(out_json.relative_to(repo)).replace("\\", "/")
            if out_json.is_file()
            else "",
        }
    status = "FAIL" if findings else "PASS"
    return {
        "name": "secret-scan",
        "tool": "gitleaks",
        "status": status,
        "detail": "%d finding(s)" % len(findings) if findings else "clean",
        "findings": findings,
        "evidence": str(out_json.relative_to(repo)).replace("\\", "/")
        if out_json.is_file()
        else "",
    }


def _trivy_targets(repo: Path) -> list[Path]:
    candidates = [
        repo / "apps" / "sgenaxis-desktop" / "src-tauri" / "Cargo.lock",
        repo / "apps" / "sgenaxis-desktop" / "package-lock.json",
        repo / "requirements.txt",
    ]
    return [p for p in candidates if p.is_file()]


def run_cve_scan(
    repo: Path,
    *,
    trivy_bin: str | None = None,
) -> dict[str, Any]:
    """Run trivy fs on known lockfiles / requirements."""
    bin_path = trivy_bin or which("trivy")
    if not bin_path:
        return {
            "name": "cve-scan",
            "tool": "trivy",
            "status": "NOT RUN",
            "detail": "trivy not on PATH",
            "findings": [],
        }
    targets = _trivy_targets(repo)
    if not targets:
        return {
            "name": "cve-scan",
            "tool": "trivy",
            "status": "NOT RUN",
            "detail": "no lockfile/requirements targets found",
            "findings": [],
        }

    findings: list[dict[str, Any]] = []
    details: list[str] = []
    evidence_paths: list[str] = []
    any_ok = False
    any_fail_tool = False

    for target in targets:
        rel = str(target.relative_to(repo)).replace("\\", "/")
        out_json = repo / "reports" / ("_sec-scan-trivy-%s.json" % target.name.replace(".", "_"))
        # Scan the concrete lockfile / requirements path for predictable targets.
        proc = _run(
            [
                bin_path,
                "fs",
                "--scanners",
                "vuln",
                "--format",
                "json",
                "--output",
                str(out_json),
                "--quiet",
                str(target),
            ],
            cwd=repo,
            timeout=1200,
        )

        if proc.returncode not in (0, 1):
            any_fail_tool = True
            details.append("%s: trivy exit %s" % (rel, proc.returncode))
            continue

        any_ok = True
        if out_json.is_file():
            evidence_paths.append(str(out_json.relative_to(repo)).replace("\\", "/"))
            try:
                data = json.loads(out_json.read_text(encoding="utf-8-sig") or "{}")
            except json.JSONDecodeError:
                data = {}
            for result in data.get("Results") or []:
                if not isinstance(result, Mapping):
                    continue
                target_name = result.get("Target") or rel
                for vuln in result.get("Vulnerabilities") or []:
                    if not isinstance(vuln, Mapping):
                        continue
                    sev = str(vuln.get("Severity") or "UNKNOWN").upper()
                    vid = vuln.get("VulnerabilityID") or vuln.get("PkgID") or "unknown"
                    pkg = vuln.get("PkgName") or ""
                    fid = finding_id("cve", id=vid, pkg=pkg, target=target_name)
                    findings.append(
                        {
                            "id": fid,
                            "kind": "cve",
                            "severity": sev,
                            "cve": vid,
                            "package": pkg,
                            "installed": vuln.get("InstalledVersion") or "",
                            "fixed": vuln.get("FixedVersion") or "",
                            "target": target_name,
                            "title": vuln.get("Title") or "",
                        }
                    )
        details.append("%s: ok" % rel)

    if not any_ok and any_fail_tool:
        status = "PARTIAL"
    elif not any_ok:
        status = "NOT RUN"
    else:
        high = [f for f in findings if str(f.get("severity") or "").upper() in HIGH_SEVS]
        if high:
            status = "FAIL"
        elif findings:
            status = "PARTIAL"  # medium/low only
        else:
            status = "PASS"
        if any_fail_tool and status == "PASS":
            status = "PARTIAL"

    return {
        "name": "cve-scan",
        "tool": "trivy",
        "status": status,
        "detail": "; ".join(details) + (" | %d vuln(s)" % len(findings) if findings else " | clean"),
        "findings": findings,
        "evidence": "; ".join(evidence_paths),
        "targets": [str(t.relative_to(repo)).replace("\\", "/") for t in targets],
    }


def untriaged_high(findings: Sequence[Mapping[str, Any]], waived: set[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in findings:
        sev = str(f.get("severity") or "").upper()
        if sev not in HIGH_SEVS:
            continue
        fid = str(f.get("id") or "")
        if fid and fid in waived:
            continue
        out.append(dict(f))
    return out


def rollup_scan_status(legs: Sequence[Mapping[str, Any]], *, high_untriaged: int) -> str:
    """Explicit scan overall: PASS|FAIL|PARTIAL|NOT RUN (plus BLOCKED via rollup if present)."""
    statuses = [br.normalize_status(leg.get("status") or "NOT RUN") for leg in legs]
    if not statuses:
        return "NOT RUN"
    if high_untriaged > 0:
        # High not triaged → never PASS; prefer FAIL over softer states.
        base = br.rollup_status(statuses)
        if base == "PASS":
            return "FAIL"
        if base == "NOT RUN":
            return "FAIL"
        if base == "PARTIAL":
            return "FAIL"
        return base  # FAIL or BLOCKED
    return br.rollup_status(statuses)


def _leg_status_after_triage(leg: Mapping[str, Any], waived: set[str]) -> str:
    """Recompute a leg status ignoring waived finding ids (NOT RUN / tool PARTIAL kept)."""
    raw = br.normalize_status(leg.get("status") or "NOT RUN")
    if raw == "NOT RUN":
        return "NOT RUN"
    # Tool glitch PARTIAL without findings stays PARTIAL.
    findings = list(leg.get("findings") or [])
    remaining = [f for f in findings if str(f.get("id") or "") not in waived]
    if not remaining:
        # All findings waived (or clean) — keep tool PARTIAL if scanner errored mid-way.
        if raw == "PARTIAL" and not findings:
            return "PARTIAL"
        return "PASS"
    high = [
        f
        for f in remaining
        if str(f.get("severity") or "").upper() in HIGH_SEVS
    ]
    if high:
        return "FAIL"
    return "PARTIAL"


def build_scan_result(
    *,
    secret_leg: Mapping[str, Any],
    cve_leg: Mapping[str, Any],
    waived: set[str] | None = None,
    generated_at: str | None = None,
    repo_rel_evidence: str = "",
) -> dict[str, Any]:
    waived = waived or set()
    all_findings = list(secret_leg.get("findings") or []) + list(cve_leg.get("findings") or [])
    high = untriaged_high(all_findings, waived)
    legs = []
    for raw_leg in (secret_leg, cve_leg):
        leg = dict(raw_leg)
        leg["status"] = _leg_status_after_triage(leg, waived)
        legs.append(leg)
    status = rollup_scan_status(legs, high_untriaged=len(high))
    ts = generated_at or now_iso()
    return {
        "schema": SCHEMA,
        "cardId": CARD_ID,
        "bdd": BDD_ID,
        "status": status,
        "generatedAt": ts,
        "legs": legs,
        "findings": all_findings,
        "untriagedHigh": high,
        "waivedIds": sorted(waived),
        "summary": _summary_text(status, legs, high),
        "evidence": repo_rel_evidence,
        "gate": {
            "rule": "high-severity untriaged → Build Result must not claim PASS",
            "blocksBuildPass": len(high) > 0,
            "untriagedHighCount": len(high),
        },
    }


def _summary_text(status: str, legs: Sequence[Mapping[str, Any]], high: Sequence[Mapping[str, Any]]) -> str:
    parts = ["overall=%s" % status]
    for leg in legs:
        parts.append("%s=%s" % (leg.get("name"), leg.get("status")))
    parts.append("untriagedHigh=%d" % len(high))
    return "; ".join(parts)


def apply_security_gate(
    build_status: Any,
    scan: Mapping[str, Any] | None,
) -> str:
    """Refuse forged PASS when high findings remain untriaged.

    Returns a Build Result vocabulary status. If ``scan`` is None → treat security
    as NOT RUN (PASS becomes NOT RUN / kept if already worse).
    """
    st = br.normalize_status(build_status)
    if scan is None:
        if st == "PASS":
            return "NOT RUN"
        return st
    blocks = bool((scan.get("gate") or {}).get("blocksBuildPass"))
    high_n = int((scan.get("gate") or {}).get("untriagedHighCount") or 0)
    if high_n > 0 or blocks:
        if st == "PASS":
            return "FAIL"
        # Keep FAIL/BLOCKED; upgrade soft incompleteness to FAIL so PASS cannot slip.
        if st in ("NOT RUN", "PARTIAL"):
            return "FAIL"
        return st
    # Scan present and gate clear: roll up scan status into build (worst-wins).
    scan_st = br.normalize_status(scan.get("status") or "NOT RUN")
    return br.rollup_status([st, scan_st])


def attach_to_build_result(
    result: MutableMapping[str, Any],
    scan: Mapping[str, Any],
) -> MutableMapping[str, Any]:
    """Hang scan into a Build Result dict: securitySummary + verification rows + gate."""
    gated = apply_security_gate(result.get("status") or "NOT RUN", scan)
    result["status"] = gated
    high_n = int((scan.get("gate") or {}).get("untriagedHighCount") or 0)
    result["securitySummary"] = (
        "PD-SEC-SCAN-01 %s — %s; untriagedHigh=%d; evidence=%s"
        % (
            scan.get("status"),
            scan.get("summary") or "",
            high_n,
            scan.get("evidence") or "reports/sec-scan-*.md",
        )
    )
    verif = list(result.get("verification") or [])
    for leg in scan.get("legs") or []:
        verif.append(
            br.build_verification_row(
                str(leg.get("name") or "sec"),
                leg.get("status") or "NOT RUN",
                detail=str(leg.get("detail") or ""),
                evidence=str(leg.get("evidence") or scan.get("evidence") or ""),
            )
        )
    verif.append(
        br.build_verification_row(
            "SEC-GATE",
            "FAIL" if high_n else "PASS",
            detail=(
                "blocks Build Result PASS (%d untriaged high)" % high_n
                if high_n
                else "no untriaged high/critical"
            ),
            evidence=str(scan.get("evidence") or ""),
        )
    )
    result["verification"] = verif
    pending = [
        p
        for p in (result.get("pending") or [])
        if "PD-SEC-SCAN-01: attach" not in str(p)
    ]
    if high_n:
        pending.append(
            "Triage %d high/critical finding(s) in reports/sec-scan-triage.json before PASS"
            % high_n
        )
    result["pending"] = pending
    risks = list(result.get("risks") or [])
    if high_n:
        risks.append(
            "Untriaged high/critical CVE or secrets — Build Result PASS forged=false (gated to %s)."
            % gated
        )
    result["risks"] = risks
    reqs = list(result.get("requirementTraceability") or [])
    if BDD_ID not in reqs:
        reqs.append(BDD_ID)
    if CARD_ID not in reqs:
        reqs.append(CARD_ID)
    result["requirementTraceability"] = reqs
    return result


def render_scan_markdown(scan: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Security Scan — %s" % CARD_ID)
    lines.append("")
    lines.append("- **Status:** %s" % scan.get("status"))
    lines.append("- **Generated:** %s" % (scan.get("generatedAt") or ""))
    lines.append("- **BDD:** %s" % (scan.get("bdd") or BDD_ID))
    lines.append("- **Schema:** %s" % (scan.get("schema") or SCHEMA))
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(str(scan.get("summary") or "none"))
    lines.append("")
    lines.append("## Legs")
    lines.append("")
    for leg in scan.get("legs") or []:
        lines.append(
            "- **%s** (%s) — %s — %s"
            % (
                leg.get("name"),
                leg.get("tool"),
                leg.get("status"),
                leg.get("detail") or "",
            )
        )
        if leg.get("evidence"):
            lines.append("  - evidence: `%s`" % leg["evidence"])
    lines.append("")
    lines.append("## Gate (Build Result)")
    lines.append("")
    gate = scan.get("gate") or {}
    lines.append("- **blocksBuildPass:** %s" % gate.get("blocksBuildPass"))
    lines.append("- **untriagedHighCount:** %s" % gate.get("untriagedHighCount"))
    lines.append("- **rule:** %s" % gate.get("rule"))
    lines.append("")
    lines.append("## Untriaged high / critical")
    lines.append("")
    high = scan.get("untriagedHigh") or []
    if not high:
        lines.append("none")
    else:
        for f in high:
            lines.append(
                "- `%s` — %s — %s"
                % (f.get("id"), f.get("severity"), f.get("title") or f.get("description") or f.get("cve") or "")
            )
    lines.append("")
    lines.append("## All findings")
    lines.append("")
    findings = scan.get("findings") or []
    if not findings:
        lines.append("none")
    else:
        for f in findings[:200]:
            lines.append(
                "- `%s` — %s — %s"
                % (f.get("id"), f.get("severity"), f.get("kind"))
            )
        if len(findings) > 200:
            lines.append("- … +%d more" % (len(findings) - 200))
    lines.append("")
    lines.append("## Waived ids")
    lines.append("")
    waived = scan.get("waivedIds") or []
    if not waived:
        lines.append("none")
    else:
        for wid in waived:
            lines.append("- `%s`" % wid)
    lines.append("")
    lines.append("## Status vocabulary")
    lines.append("")
    lines.append("PASS | FAIL | PARTIAL | NOT RUN (Build Result may also use BLOCKED)")
    lines.append("")
    return "\n".join(lines)


def default_scan_report_path(
    *,
    generated_at: str | None = None,
    repo: Path | None = None,
) -> Path:
    root = repo or REPO
    return root / "reports" / ("sec-scan-%s.md" % _stamp(generated_at))


def write_scan_report(
    scan: Mapping[str, Any],
    out_path: Path | None = None,
    *,
    also_json: bool = True,
    repo: Path | None = None,
) -> Path:
    root = repo or REPO
    path = Path(out_path) if out_path else default_scan_report_path(
        generated_at=str(scan.get("generatedAt") or "") or None,
        repo=root,
    )
    if not path.is_absolute():
        path = root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_scan_markdown(scan), encoding="utf-8", newline="\n")
    if also_json:
        path.with_suffix(".json").write_text(
            json.dumps(scan, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return path


def run_full_scan(
    repo: Path | None = None,
    *,
    triage_path: Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    root = repo or REPO
    triage = triage_path or (root / "reports" / "sec-scan-triage.json")
    waived = load_triage(triage if triage.is_file() else None)
    secret = run_secret_scan(root)
    cve = run_cve_scan(root)
    ts = generated_at or now_iso()
    # evidence filled after write; placeholder for now
    scan = build_scan_result(
        secret_leg=secret,
        cve_leg=cve,
        waived=waived,
        generated_at=ts,
    )
    return scan


def load_latest_scan(repo: Path | None = None) -> dict[str, Any] | None:
    """Load newest ``reports/sec-scan-*.json`` sidecar if present."""
    root = repo or REPO
    reports = root / "reports"
    if not reports.is_dir():
        return None
    candidates = sorted(reports.glob("sec-scan-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates:
        if path.name.startswith("sec-scan-triage"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("schema") == SCHEMA:
            return data
    return None


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="Run CVE + secret scan and write reports/sec-scan-*.md")
    r.add_argument("--repo", default="", help="Repo root (default: AIAD)")
    r.add_argument("--triage", default="", help="Triage JSON path")
    r.add_argument("--out", default="", help="Output .md path")
    r.add_argument("--no-json", action="store_true")

    g = sub.add_parser(
        "gate-status",
        help="Print gated Build Result status given a candidate status + optional scan JSON",
    )
    g.add_argument("build_status")
    g.add_argument("--scan", default="", help="Path to sec-scan-*.json (default: latest)")
    g.add_argument("--repo", default="")

    a = sub.add_parser("attach-demo", help="Demo: generate Build Result then attach latest scan")
    a.add_argument("--repo", default="")
    a.add_argument("--out", default="", help="Output Build Result .md")
    a.add_argument("--version", default="0.1.0")

    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    repo = Path(args.repo) if getattr(args, "repo", "") else REPO
    if not repo.is_absolute():
        repo = Path.cwd() / repo

    if args.cmd == "run":
        triage = Path(args.triage) if args.triage else repo / "reports" / "sec-scan-triage.json"
        scan = run_full_scan(repo, triage_path=triage if triage.is_file() else None)
        out = Path(args.out) if args.out else default_scan_report_path(
            generated_at=scan["generatedAt"], repo=repo
        )
        path = write_scan_report(scan, out, also_json=not args.no_json, repo=repo)
        try:
            rel = str(path.resolve().relative_to(repo.resolve())).replace("\\", "/")
        except ValueError:
            rel = str(path)
        scan["evidence"] = rel
        # rewrite with evidence filled
        path = write_scan_report(scan, path, also_json=not args.no_json, repo=repo)
        print("wrote %s status=%s blocksBuildPass=%s" % (
            path,
            scan["status"],
            scan["gate"]["blocksBuildPass"],
        ))
        # Exit: FAIL → 1; PARTIAL → 0 (recorded, not merge-block); NOT RUN → 0
        if scan["status"] == "FAIL":
            return 1
        return 0

    if args.cmd == "gate-status":
        scan = None
        if args.scan:
            scan = json.loads(Path(args.scan).read_text(encoding="utf-8-sig"))
        else:
            scan = load_latest_scan(repo)
        print(apply_security_gate(args.build_status, scan))
        return 0

    if args.cmd == "attach-demo":
        scan = load_latest_scan(repo)
        if scan is None:
            print("no sec-scan-*.json found — run `sec_scan.py run` first", file=sys.stderr)
            return 1
        result = br.build_result(
            version=args.version,
            summary="Demo Build Result with PD-SEC-SCAN-01 attached",
            artifacts=[],
            verification=[{"name": "demo-unit", "status": "PASS"}],
            status="PASS",
            signing_status="NOT RUN",
            security_summary="pending attach",
            requirement_traceability=["BDD-PD-BUILD-RESULT-01"],
            card_id=CARD_ID,
        )
        # signing NOT RUN would already rollup — set explicit PASS then attach gate
        result["status"] = "PASS"
        attach_to_build_result(result, scan)
        out = Path(args.out) if args.out else br.default_report_path(
            result["version"],
            generated_at=result["generatedAt"],
            dest="reports",
            repo=repo,
        )
        path = br.write_report(result, out, also_json=True, repo=repo)
        print("wrote %s status=%s security=%s" % (path, result["status"], result["securitySummary"][:120]))
        return 0

    print("unknown command", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
