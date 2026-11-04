#!/usr/bin/env python3
"""PD-SBOM-01 — produce CycloneDX/SPDX SBOM and hang into Build Result / sec.

BDD-PD-SBOM-01:
  - Rerunnable generation writes SBOM artifact(s) under ``reports/``.
  - Tool / generation failure is explicit (FAIL or NOT RUN), never silent PASS.
  - Report is citeable by sec_scan / Build Result (``attach_to_build_result``).
  - High-severity **untriaged** findings (from attached sec gate or
    ``reports/sec-scan-*.json``) must not allow a Build Result to claim PASS
    merely because an SBOM file exists.

Does **not** force CI merge-block; optional hang only.

Tool (best-effort; missing → NOT RUN):
  - ``syft`` → CycloneDX JSON (preferred) and/or SPDX JSON
"""
from __future__ import annotations

import argparse
import json
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

CARD_ID = "PD-SBOM-01"
BDD_ID = "BDD-PD-SBOM-01"
SCHEMA = "aiad.sbom.v1"

# Prefer CycloneDX; SPDX is alternate / dual emit.
DEFAULT_FORMAT = "cyclonedx-json"
ALT_FORMAT = "spdx-json"

VALID_SBOM_STATUSES = frozenset(br.VALID_STATUSES)


class SbomError(ValueError):
    """Invalid SBOM / gate input."""


def now_iso() -> str:
    return datetime.now(TAIPEI).isoformat(timespec="seconds")


def _stamp(iso: str | None = None) -> str:
    ts = iso or now_iso()
    stamp = re.sub(r"[^0-9T]", "", ts.replace("+", "p").replace(":", ""))[:15]
    return stamp or datetime.now(TAIPEI).strftime("%Y%m%dT%H%M%S")


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def _run(
    cmd: Sequence[str],
    *,
    cwd: Path,
    timeout: int = 900,
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


def default_scan_roots(repo: Path) -> list[Path]:
    """Filesystem roots worth cataloging (lockfile-backed tree; prefer src-tauri over full desktop)."""
    candidates = [
        # Prefer Rust lockfile tree — avoids huge node_modules under apps/sgenaxis-desktop.
        repo / "apps" / "sgenaxis-desktop" / "src-tauri",
        repo / "apps" / "sgenaxis-desktop",
        repo,
    ]
    seen: set[Path] = set()
    out: list[Path] = []
    for p in candidates:
        try:
            key = p.resolve()
        except OSError:
            continue
        if key in seen or not p.is_dir():
            continue
        seen.add(key)
        out.append(p)
    return out


def _format_ext(fmt: str) -> str:
    if "spdx" in fmt:
        return "spdx.json"
    return "cdx.json"


def run_syft_leg(
    repo: Path,
    *,
    source: Path,
    fmt: str,
    out_file: Path,
    syft_bin: str | None = None,
) -> dict[str, Any]:
    """Run one syft scan → SBOM file; return leg dict."""
    bin_path = syft_bin or which("syft")
    name = "sbom-%s" % ("spdx" if "spdx" in fmt else "cyclonedx")
    if not bin_path:
        return {
            "name": name,
            "tool": "syft",
            "format": fmt,
            "status": "NOT RUN",
            "detail": "syft not on PATH",
            "componentCount": 0,
            "artifact": "",
        }
    out_file.parent.mkdir(parents=True, exist_ok=True)
    # dir: scheme avoids docker/image heuristics for filesystem trees.
    try:
        src_rel = str(source.resolve().relative_to(repo.resolve())).replace("\\", "/")
    except ValueError:
        src_rel = str(source)
    source_arg = "dir:%s" % source
    proc = _run(
        [
            bin_path,
            "scan",
            source_arg,
            "-o",
            "%s=%s" % (fmt, out_file),
            "-q",
        ],
        cwd=repo,
        timeout=1200,
    )
    artifact_rel = ""
    if out_file.is_file() and out_file.stat().st_size > 2:
        try:
            artifact_rel = str(out_file.resolve().relative_to(repo.resolve())).replace("\\", "/")
        except ValueError:
            artifact_rel = str(out_file)

    component_count = 0
    parse_ok = False
    if out_file.is_file() and out_file.stat().st_size > 2:
        try:
            data = json.loads(out_file.read_text(encoding="utf-8-sig") or "{}")
            parse_ok = isinstance(data, dict)
            if parse_ok:
                component_count = _count_components(data, fmt)
        except json.JSONDecodeError:
            parse_ok = False

    if proc.returncode != 0:
        return {
            "name": name,
            "tool": "syft",
            "format": fmt,
            "status": "FAIL",
            "detail": "syft exit %s on %s: %s"
            % (proc.returncode, src_rel, (proc.stderr or proc.stdout or "")[:400]),
            "componentCount": component_count,
            "artifact": artifact_rel,
            "source": src_rel,
        }
    if not parse_ok or not artifact_rel:
        return {
            "name": name,
            "tool": "syft",
            "format": fmt,
            "status": "FAIL",
            "detail": "syft produced no valid SBOM JSON for %s" % src_rel,
            "componentCount": 0,
            "artifact": artifact_rel,
            "source": src_rel,
        }
    return {
        "name": name,
        "tool": "syft",
        "format": fmt,
        "status": "PASS",
        "detail": "%s — %d component(s)" % (src_rel, component_count),
        "componentCount": component_count,
        "artifact": artifact_rel,
        "source": src_rel,
    }


def _count_components(data: Mapping[str, Any], fmt: str) -> int:
    if "spdx" in fmt:
        pkgs = data.get("packages")
        if isinstance(pkgs, list):
            return len(pkgs)
        return 0
    comps = data.get("components")
    if isinstance(comps, list):
        return len(comps)
    return 0


def load_sec_gate(repo: Path | None = None) -> dict[str, Any] | None:
    """Load latest PD-SEC-SCAN-01 gate (if any) so SBOM cannot forge PASS over high untriaged."""
    root = repo or REPO
    try:
        import sec_scan as _sec_scan  # noqa: PLC0415 — optional hang; avoid import cycle at module load
    except ImportError:
        return None
    scan = _sec_scan.load_latest_scan(root)
    if scan is None:
        return None
    gate = dict(scan.get("gate") or {})
    return {
        "status": scan.get("status"),
        "blocksBuildPass": bool(gate.get("blocksBuildPass")),
        "untriagedHighCount": int(gate.get("untriagedHighCount") or 0),
        "evidence": scan.get("evidence") or "",
        "schema": scan.get("schema"),
    }


def rollup_sbom_status(legs: Sequence[Mapping[str, Any]]) -> str:
    statuses = [br.normalize_status(leg.get("status") or "NOT RUN") for leg in legs]
    if not statuses:
        return "NOT RUN"
    return br.rollup_status(statuses)


def build_sbom_result(
    *,
    legs: Sequence[Mapping[str, Any]],
    generated_at: str | None = None,
    formats: Sequence[str] | None = None,
    sec_gate: Mapping[str, Any] | None = None,
    repo_rel_evidence: str = "",
) -> dict[str, Any]:
    status = rollup_sbom_status(legs)
    ts = generated_at or now_iso()
    high_n = 0
    blocks = False
    if sec_gate:
        high_n = int(sec_gate.get("untriagedHighCount") or 0)
        blocks = bool(sec_gate.get("blocksBuildPass")) or high_n > 0
    artifacts = [str(leg.get("artifact") or "") for leg in legs if leg.get("artifact")]
    return {
        "schema": SCHEMA,
        "cardId": CARD_ID,
        "bdd": BDD_ID,
        "status": status,
        "generatedAt": ts,
        "formats": list(formats or [DEFAULT_FORMAT]),
        "legs": list(legs),
        "artifacts": artifacts,
        "summary": _summary_text(status, legs, high_n),
        "evidence": repo_rel_evidence,
        "secGate": dict(sec_gate) if sec_gate else None,
        "gate": {
            "rule": (
                "SBOM success must not forge Build Result PASS when "
                "sec high/critical findings remain untriaged"
            ),
            "blocksBuildPass": blocks,
            "untriagedHighCount": high_n,
        },
    }


def _summary_text(
    status: str,
    legs: Sequence[Mapping[str, Any]],
    high_n: int,
) -> str:
    parts = ["overall=%s" % status]
    for leg in legs:
        parts.append("%s=%s" % (leg.get("name"), leg.get("status")))
    parts.append("untriagedHigh=%d" % high_n)
    return "; ".join(parts)


def apply_sbom_gate(
    build_status: Any,
    sbom: Mapping[str, Any] | None,
) -> str:
    """Refuse forged PASS when SBOM missing/failed or sec high untriaged.

    - ``sbom`` is None → treat as NOT RUN (PASS → NOT RUN).
    - SBOM FAIL → cannot leave PASS (→ FAIL).
    - ``gate.blocksBuildPass`` (sec high untriaged) → PASS/PARTIAL/NOT RUN → FAIL.
    - Otherwise worst-wins rollup of build + SBOM status.
    """
    st = br.normalize_status(build_status)
    if sbom is None:
        if st == "PASS":
            return "NOT RUN"
        return st
    blocks = bool((sbom.get("gate") or {}).get("blocksBuildPass"))
    high_n = int((sbom.get("gate") or {}).get("untriagedHighCount") or 0)
    sbom_st = br.normalize_status(sbom.get("status") or "NOT RUN")
    if high_n > 0 or blocks:
        if st == "PASS":
            return "FAIL"
        if st in ("NOT RUN", "PARTIAL"):
            return "FAIL"
        return st
    if sbom_st == "FAIL":
        if st == "PASS":
            return "FAIL"
        return br.rollup_status([st, "FAIL"])
    return br.rollup_status([st, sbom_st])


def attach_to_build_result(
    result: MutableMapping[str, Any],
    sbom: Mapping[str, Any],
) -> MutableMapping[str, Any]:
    """Hang SBOM into Build Result: verification rows + gate (no forged PASS)."""
    gated = apply_sbom_gate(result.get("status") or "NOT RUN", sbom)
    result["status"] = gated
    high_n = int((sbom.get("gate") or {}).get("untriagedHighCount") or 0)
    arts = ", ".join(sbom.get("artifacts") or []) or (sbom.get("evidence") or "reports/sbom-*")
    summary_line = (
        "PD-SBOM-01 %s — %s; untriagedHigh=%d; artifacts=%s"
        % (sbom.get("status"), sbom.get("summary") or "", high_n, arts)
    )
    # Prefer dedicated field; also fold into securitySummary for citeability by sec.
    result["sbomSummary"] = summary_line
    prev_sec = str(result.get("securitySummary") or "").strip()
    if prev_sec:
        result["securitySummary"] = prev_sec + " | " + summary_line
    else:
        result["securitySummary"] = summary_line

    verif = list(result.get("verification") or [])
    for leg in sbom.get("legs") or []:
        verif.append(
            br.build_verification_row(
                str(leg.get("name") or "sbom"),
                leg.get("status") or "NOT RUN",
                detail=str(leg.get("detail") or ""),
                evidence=str(leg.get("artifact") or sbom.get("evidence") or ""),
            )
        )
    verif.append(
        br.build_verification_row(
            "SBOM-GATE",
            "FAIL" if high_n or (sbom.get("gate") or {}).get("blocksBuildPass") else (
                "FAIL" if br.normalize_status(sbom.get("status") or "NOT RUN") == "FAIL" else "PASS"
            ),
            detail=(
                "blocks Build Result PASS (%d untriaged high from sec)" % high_n
                if high_n or (sbom.get("gate") or {}).get("blocksBuildPass")
                else (
                    "SBOM generation failed"
                    if br.normalize_status(sbom.get("status") or "NOT RUN") == "FAIL"
                    else "SBOM ok; no untriaged high/critical from sec gate"
                )
            ),
            evidence=str(sbom.get("evidence") or arts),
        )
    )
    result["verification"] = verif

    pending = list(result.get("pending") or [])
    if high_n:
        pending.append(
            "Triage %d high/critical finding(s) (sec) before PASS — SBOM alone is not clearance"
            % high_n
        )
    if br.normalize_status(sbom.get("status") or "NOT RUN") in ("FAIL", "NOT RUN"):
        pending.append("Re-run PD-SBOM-01 (`scripts/pd_sbom_01.py`) until SBOM status is PASS/PARTIAL")
    result["pending"] = pending

    risks = list(result.get("risks") or [])
    if high_n:
        risks.append(
            "Untriaged high/critical from sec — SBOM attach cannot forge PASS (gated to %s)."
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


def render_sbom_markdown(sbom: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# SBOM — %s" % CARD_ID)
    lines.append("")
    lines.append("- **Status:** %s" % sbom.get("status"))
    lines.append("- **Generated:** %s" % (sbom.get("generatedAt") or ""))
    lines.append("- **BDD:** %s" % (sbom.get("bdd") or BDD_ID))
    lines.append("- **Schema:** %s" % (sbom.get("schema") or SCHEMA))
    lines.append("- **Formats:** %s" % ", ".join(sbom.get("formats") or []))
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(str(sbom.get("summary") or "none"))
    lines.append("")
    lines.append("## Legs")
    lines.append("")
    for leg in sbom.get("legs") or []:
        lines.append(
            "- **%s** (%s / %s) — %s — %s"
            % (
                leg.get("name"),
                leg.get("tool"),
                leg.get("format"),
                leg.get("status"),
                leg.get("detail") or "",
            )
        )
        if leg.get("artifact"):
            lines.append("  - artifact: `%s`" % leg["artifact"])
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    arts = sbom.get("artifacts") or []
    if not arts:
        lines.append("none")
    else:
        for a in arts:
            lines.append("- `%s`" % a)
    lines.append("")
    lines.append("## Gate (Build Result / sec)")
    lines.append("")
    gate = sbom.get("gate") or {}
    lines.append("- **blocksBuildPass:** %s" % gate.get("blocksBuildPass"))
    lines.append("- **untriagedHighCount:** %s" % gate.get("untriagedHighCount"))
    lines.append("- **rule:** %s" % gate.get("rule"))
    sec = sbom.get("secGate")
    if sec:
        lines.append(
            "- **secGate:** status=%s blocksBuildPass=%s untriagedHigh=%s evidence=`%s`"
            % (
                sec.get("status"),
                sec.get("blocksBuildPass"),
                sec.get("untriagedHighCount"),
                sec.get("evidence") or "",
            )
        )
    else:
        lines.append("- **secGate:** none (no reports/sec-scan-*.json)")
    lines.append("")
    lines.append("## Status vocabulary")
    lines.append("")
    lines.append("PASS | FAIL | PARTIAL | NOT RUN (Build Result may also use BLOCKED)")
    lines.append("")
    lines.append("## Cite")
    lines.append("")
    lines.append(
        "Hang via `build_result.py generate --attach-sbom` or "
        "`sbom.attach_to_build_result` / `sec_scan` consumers reading this report."
    )
    lines.append("")
    return "\n".join(lines)


def default_sbom_report_path(
    *,
    generated_at: str | None = None,
    repo: Path | None = None,
) -> Path:
    root = repo or REPO
    return root / "reports" / ("sbom-%s.md" % _stamp(generated_at))


def write_sbom_report(
    sbom: Mapping[str, Any],
    out_path: Path | None = None,
    *,
    also_json: bool = True,
    repo: Path | None = None,
) -> Path:
    root = repo or REPO
    path = Path(out_path) if out_path else default_sbom_report_path(
        generated_at=str(sbom.get("generatedAt") or "") or None,
        repo=root,
    )
    if not path.is_absolute():
        path = root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_sbom_markdown(sbom), encoding="utf-8", newline="\n")
    if also_json:
        path.with_suffix(".json").write_text(
            json.dumps(sbom, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return path


def run_full_sbom(
    repo: Path | None = None,
    *,
    formats: Sequence[str] | None = None,
    source: Path | None = None,
    generated_at: str | None = None,
    include_sec_gate: bool = True,
    syft_bin: str | None = None,
) -> dict[str, Any]:
    root = repo or REPO
    fmts = list(formats) if formats else [DEFAULT_FORMAT, ALT_FORMAT]
    roots = default_scan_roots(root)
    src = source or (roots[0] if roots else root)
    ts = generated_at or now_iso()
    stamp = _stamp(ts)
    legs: list[dict[str, Any]] = []
    for fmt in fmts:
        out_file = root / "reports" / ("sbom-%s.%s" % (stamp, _format_ext(fmt)))
        legs.append(
            run_syft_leg(
                root,
                source=src,
                fmt=fmt,
                out_file=out_file,
                syft_bin=syft_bin,
            )
        )
    sec_gate = load_sec_gate(root) if include_sec_gate else None
    return build_sbom_result(
        legs=legs,
        generated_at=ts,
        formats=fmts,
        sec_gate=sec_gate,
    )


def load_latest_sbom(repo: Path | None = None) -> dict[str, Any] | None:
    """Load newest ``reports/sbom-*.json`` sidecar (report schema, not raw CDX/SPDX)."""
    root = repo or REPO
    reports = root / "reports"
    if not reports.is_dir():
        return None
    candidates = sorted(
        reports.glob("sbom-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        # Skip raw syft dumps named sbom-<stamp>.cdx.json / .spdx.json
        name = path.name.lower()
        if name.endswith(".cdx.json") or name.endswith(".spdx.json"):
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

    r = sub.add_parser("run", help="Generate CycloneDX/SPDX SBOM + reports/sbom-*.md")
    r.add_argument("--repo", default="", help="Repo root (default: AIAD)")
    r.add_argument("--source", default="", help="Directory to scan (default: apps/sgenaxis-desktop)")
    r.add_argument(
        "--format",
        action="append",
        dest="formats",
        default=None,
        help="syft output format (repeatable). Default: cyclonedx-json + spdx-json",
    )
    r.add_argument("--out", default="", help="Output .md path")
    r.add_argument("--no-json", action="store_true")
    r.add_argument("--no-sec-gate", action="store_true", help="Do not load sec-scan gate")

    g = sub.add_parser(
        "gate-status",
        help="Print gated Build Result status given candidate status + optional sbom JSON",
    )
    g.add_argument("build_status")
    g.add_argument("--sbom", default="", help="Path to sbom-*.json (default: latest)")
    g.add_argument("--repo", default="")

    a = sub.add_parser("attach-demo", help="Demo: Build Result then attach latest SBOM")
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
        source = Path(args.source) if args.source else None
        if source is not None and not source.is_absolute():
            source = repo / source
        sbom = run_full_sbom(
            repo,
            formats=args.formats,
            source=source,
            include_sec_gate=not args.no_sec_gate,
        )
        out = Path(args.out) if args.out else default_sbom_report_path(
            generated_at=sbom["generatedAt"], repo=repo
        )
        path = write_sbom_report(sbom, out, also_json=not args.no_json, repo=repo)
        try:
            rel = str(path.resolve().relative_to(repo.resolve())).replace("\\", "/")
        except ValueError:
            rel = str(path)
        sbom["evidence"] = rel
        path = write_sbom_report(sbom, path, also_json=not args.no_json, repo=repo)
        print(
            "wrote %s status=%s blocksBuildPass=%s artifacts=%s"
            % (
                path,
                sbom["status"],
                sbom["gate"]["blocksBuildPass"],
                ",".join(sbom.get("artifacts") or []) or "(none)",
            )
        )
        if sbom["status"] == "FAIL":
            return 1
        return 0

    if args.cmd == "gate-status":
        sbom = None
        if args.sbom:
            sbom = json.loads(Path(args.sbom).read_text(encoding="utf-8-sig"))
        else:
            sbom = load_latest_sbom(repo)
        print(apply_sbom_gate(args.build_status, sbom))
        return 0

    if args.cmd == "attach-demo":
        sbom = load_latest_sbom(repo)
        if sbom is None:
            print("no sbom-*.json found — run `sbom.py run` first", file=sys.stderr)
            return 1
        result = br.build_result(
            version=args.version,
            summary="Demo Build Result with PD-SBOM-01 attached",
            artifacts=[],
            verification=[{"name": "demo-unit", "status": "PASS"}],
            status="PASS",
            signing_status="NOT RUN",
            security_summary="pending SBOM attach",
            requirement_traceability=["BDD-PD-BUILD-RESULT-01"],
            card_id=CARD_ID,
        )
        result["status"] = "PASS"
        attach_to_build_result(result, sbom)
        out = Path(args.out) if args.out else br.default_report_path(
            result["version"],
            generated_at=result["generatedAt"],
            dest="reports",
            repo=repo,
        )
        # Avoid colliding with packaging candidate names.
        if not args.out:
            out = repo / "reports" / (
                "build-%s-sbom-attach-demo.md" % result["version"]
            )
        path = br.write_report(result, out, also_json=True, repo=repo)
        print(
            "wrote %s status=%s sbom=%s"
            % (path, result["status"], str(result.get("sbomSummary") or "")[:120])
        )
        return 0

    print("unknown command", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
