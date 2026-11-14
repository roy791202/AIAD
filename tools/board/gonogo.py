#!/usr/bin/env python3
"""PD-REL-GONOGO-01 — aggregate v0.1 Go / NoGo / Go-with-PARTIAL.

BDD-PD-REL-GONOGO-01:
  - Summarize Build Result / checklist / signing / elev / SBOM statuses.
  - Verdicts: Go | NoGo | Go-with-PARTIAL.
  - Align with decided PD-DEC-V01-GATE-01: elev + Authenticode are **not**
    hard gates; Build Result PARTIAL + elev/sign NOT RUN may yield
    **Go-with-PARTIAL**.
  - **Never** rewrite NOT RUN → PASS.

If ``docs/RELEASE-CHECKLIST-v0.1.md`` is still blank, legs are derived from
the latest Build Result / sign stub / SBOM evidence (honest PARTIAL / NOT RUN)
and the dependency on PD-CHECKLIST-FILL-01 is documented — do not block forever.

Does **not**: store listing, force cert purchase, self-green the board card.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

BOARD_DIR = Path(__file__).resolve().parent
REPO = BOARD_DIR.parents[1]

if str(BOARD_DIR) not in sys.path:
    sys.path.insert(0, str(BOARD_DIR))

import build_result as br  # noqa: E402
import sign_stub  # noqa: E402

TAIPEI = timezone(timedelta(hours=8))

CARD_ID = "PD-REL-GONOGO-01"
BDD_ID = "BDD-PD-REL-GONOGO-01"
SCHEMA = "aiad.gonogo.v1"
GATE_REF = "PD-DEC-V01-GATE-01"

VERDICTS: tuple[str, ...] = ("Go", "NoGo", "Go-with-PARTIAL")
LEG_KEYS: tuple[str, ...] = (
    "build_result",
    "msi",
    "elev",
    "sec",
    "sbom",
    "signing",
    "changelog",
)

# Soft gates under V01-GATE — NOT RUN / PARTIAL here alone must not force NoGo.
SOFT_LEGS: frozenset[str] = frozenset({"elev", "signing"})

# Checklist section headings → leg key
_CHECKLIST_HEADINGS: tuple[tuple[str, str], ...] = (
    (r"1\.\s*MSI", "msi"),
    (r"2\.\s*Elev", "elev"),
    (r"3\.\s*Sec", "sec"),
    (r"4\.\s*SBOM", "sbom"),
    (r"5\.\s*簽章", "signing"),
    (r"6\.\s*CHANGELOG", "changelog"),
)

_STATUS_IN_LINE = re.compile(
    r"狀態[：:]\s*`?\s*(PASS|FAIL|NOT RUN|PARTIAL|BLOCKED|________)",
    re.IGNORECASE,
)
_SUMMARY_ROW = re.compile(
    r"^\|\s*([1-6])\s*\|\s*([^|]+)\|\s*(PASS|FAIL|NOT RUN|PARTIAL|BLOCKED|)\s*\|",
    re.IGNORECASE | re.MULTILINE,
)

_SUMMARY_KEY = {
    "1": "msi",
    "2": "elev",
    "3": "sec",
    "4": "sbom",
    "5": "signing",
    "6": "changelog",
}


class GonogoError(ValueError):
    """Invalid Go/NoGo input or policy violation."""


def now_iso() -> str:
    return datetime.now(TAIPEI).isoformat(timespec="seconds")


def _stamp(iso: str | None = None) -> str:
    ts = iso or now_iso()
    stamp = re.sub(r"[^0-9T]", "", ts.replace("+", "p").replace(":", ""))[:15]
    return stamp or datetime.now(TAIPEI).strftime("%Y%m%dT%H%M%S")


def normalize_leg_status(raw: Any) -> str:
    """Normalize to Build Result vocabulary; blank / placeholder → NOT RUN."""
    if raw is None:
        return "NOT RUN"
    s = str(raw).strip()
    if not s or set(s) <= {"_", " ", "-", "—"}:
        return "NOT RUN"
    return br.normalize_status(s)


def refuse_not_run_as_pass(status: Any) -> str:
    """HARD: NOT RUN must never become PASS."""
    st = normalize_leg_status(status)
    if st == "PASS" and str(status).strip().upper().replace("_", " ") in (
        "NOT RUN",
        "NOTRUN",
        "SKIPPED",
        "SKIP",
    ):
        return "NOT RUN"
    return st


def never_promote(status: str) -> str:
    """Identity guard used by tests — NOT RUN stays NOT RUN."""
    st = refuse_not_run_as_pass(status)
    if normalize_leg_status(status) == "NOT RUN" and st == "PASS":
        raise GonogoError("illegal promotion: NOT RUN → PASS")
    return st


# --- discovery -----------------------------------------------------------------


def _build_result_preference(path: Path) -> tuple[int, float]:
    """Higher is better: PASS/PARTIAL beat NOT RUN; then newer mtime."""
    rank = {
        "PASS": 4,
        "PARTIAL": 3,
        "NOT RUN": 1,
        "BLOCKED": 0,
        "FAIL": -1,
    }
    score = 1
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            st = refuse_not_run_as_pass(data.get("status") or "NOT RUN")
            score = rank.get(st, 1)
            # Prefer refreshed / hung candidates over demos
            name = path.name.lower()
            if "br-refresh" in name or "with-verify-hang" in name:
                score += 1
            if "demo" in name:
                score -= 2
    except (OSError, json.JSONDecodeError, GonogoError, br.BuildResultError):
        score = 0
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    return (score, mtime)


def find_latest_build_result(
    reports_dir: Path,
    *,
    version_prefix: str = "0.1",
) -> Path | None:
    """Pick best ``reports/build-<ver>-*.json`` (prefer PASS/PARTIAL over NOT RUN)."""
    if not reports_dir.is_dir():
        return None
    candidates: list[Path] = []
    for p in reports_dir.glob("build-*.json"):
        name = p.name.lower()
        if "sbom-attach-demo" in name or "sec-attach-demo" in name:
            continue
        if version_prefix and version_prefix not in name:
            continue
        candidates.append(p)
    if not candidates:
        for p in reports_dir.glob("build-*.json"):
            if "demo" not in p.name.lower():
                candidates.append(p)
    if not candidates:
        return None
    candidates.sort(key=_build_result_preference, reverse=True)
    return candidates[0]


def find_latest_sbom_report(reports_dir: Path) -> Path | None:
    if not reports_dir.is_dir():
        return None
    md = sorted(
        reports_dir.glob("sbom-*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    js = sorted(
        reports_dir.glob("sbom-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    # Prefer JSON machine status when present beside latest md
    if js:
        return js[0]
    if md:
        return md[0]
    return None


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise GonogoError("expected JSON object in %s" % path)
    return data


# --- checklist parsing ---------------------------------------------------------


def parse_checklist_statuses(text: str) -> dict[str, str | None]:
    """Extract per-leg status from RELEASE-CHECKLIST markdown.

    Returns ``None`` for a leg when the blank is unfilled (``________`` / empty).
    """
    out: dict[str, str | None] = {k: None for k in LEG_KEYS if k != "build_result"}

    # Summary table rows win when filled
    for m in _SUMMARY_ROW.finditer(text):
        key = _SUMMARY_KEY.get(m.group(1))
        raw = (m.group(3) or "").strip()
        if key and raw:
            out[key] = refuse_not_run_as_pass(raw)

    # Per-section 「狀態：」 lines fill gaps
    for heading_re, key in _CHECKLIST_HEADINGS:
        sec = re.search(
            rf"###\s*{heading_re}.*?(?=###|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if not sec:
            continue
        if out.get(key) is not None:
            continue
        sm = _STATUS_IN_LINE.search(sec.group(0))
        if not sm:
            continue
        raw = sm.group(1)
        if raw.startswith("_"):
            out[key] = None
        else:
            out[key] = refuse_not_run_as_pass(raw)

    return out


def checklist_is_filled(statuses: Mapping[str, str | None]) -> bool:
    keys = [k for k in LEG_KEYS if k != "build_result"]
    return all(statuses.get(k) is not None for k in keys)


# --- leg derivation from Build Result / evidence -------------------------------


def _verif_status(result: Mapping[str, Any], *names: str) -> str | None:
    rows = result.get("verification") or []
    wanted = {n.upper() for n in names}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        name = str(row.get("name") or "").upper()
        if name in wanted:
            return refuse_not_run_as_pass(row.get("status"))
    return None


def derive_legs_from_build_result(result: Mapping[str, Any]) -> dict[str, str]:
    """Honest derivation — never forges PASS from missing evidence."""
    overall = refuse_not_run_as_pass(result.get("status") or "NOT RUN")
    legs: dict[str, str] = {"build_result": overall}

    msi = _verif_status(result, "MSI-ARTIFACT")
    if msi is None:
        arts = result.get("artifacts") or []
        msi_ok = any(
            isinstance(a, Mapping)
            and a.get("exists")
            and str(a.get("path") or "").lower().endswith(".msi")
            for a in arts
        )
        msi = "PASS" if msi_ok else "NOT RUN"
    legs["msi"] = msi

    elev = _verif_status(result, "ELEV-VERIFY")
    if elev is None:
        vh = result.get("verifyHang")
        if isinstance(vh, Mapping) and vh.get("elevStatus"):
            elev = refuse_not_run_as_pass(vh.get("elevStatus"))
        else:
            elev = "NOT RUN"
    legs["elev"] = elev

    sec = _verif_status(result, "SEC-GATE", "cve-scan", "secret-scan")
    # Prefer worst of sec-related rows when multiple present
    sec_rows = []
    for name in ("SEC-GATE", "cve-scan", "secret-scan"):
        st = _verif_status(result, name)
        if st is not None:
            sec_rows.append(st)
    if sec_rows:
        legs["sec"] = br.rollup_status(sec_rows)
    else:
        summary = str(result.get("securitySummary") or "")
        if "PARTIAL" in summary.upper():
            legs["sec"] = "PARTIAL"
        elif "PASS" in summary.upper() and "NOT RUN" not in summary.upper():
            legs["sec"] = "PASS"
        elif summary and summary.lower() != "none":
            legs["sec"] = "PARTIAL"
        else:
            legs["sec"] = "NOT RUN"

    legs["signing"] = refuse_not_run_as_pass(
        result.get("signingStatus") or _verif_status(result, "SIGNING") or "NOT RUN"
    )

    # SBOM / CHANGELOG not always on BR — leave for other loaders
    legs.setdefault("sbom", "NOT RUN")
    legs.setdefault("changelog", "NOT RUN")
    return legs


def load_sbom_status(path: Path | None) -> str:
    if path is None or not path.is_file():
        return "NOT RUN"
    if path.suffix.lower() == ".json":
        try:
            data = load_json(path)
            return refuse_not_run_as_pass(
                data.get("status") or data.get("overall") or "NOT RUN"
            )
        except (OSError, json.JSONDecodeError, GonogoError):
            return "NOT RUN"
    text = path.read_text(encoding="utf-8")
    m = re.search(
        r"\*\*Status:\*\*\s*(PASS|FAIL|NOT RUN|PARTIAL|BLOCKED)",
        text,
        re.IGNORECASE,
    )
    if m:
        return refuse_not_run_as_pass(m.group(1))
    m2 = re.search(
        r"overall\s*=\s*(PASS|FAIL|NOT RUN|PARTIAL|BLOCKED)",
        text,
        re.IGNORECASE,
    )
    if m2:
        return refuse_not_run_as_pass(m2.group(1))
    return "NOT RUN"


def load_changelog_status(repo: Path) -> str:
    """PASS if CHANGELOG mentions v0.1; else PARTIAL/NOT RUN — never forge."""
    path = repo / "CHANGELOG.md"
    if not path.is_file():
        return "NOT RUN"
    text = path.read_text(encoding="utf-8")
    if re.search(r"v?0\.1(\.\d+)?", text):
        return "PASS"
    if text.strip():
        return "PARTIAL"
    return "NOT RUN"


# --- verdict -------------------------------------------------------------------


def compute_verdict(
    legs: Mapping[str, str],
    *,
    allow_partial: bool = True,
    elev_hard_gate: bool = False,
    sign_hard_gate: bool = False,
) -> str:
    """Map leg statuses → Go | NoGo | Go-with-PARTIAL (V01-GATE aware)."""
    normalized = {k: never_promote(legs.get(k, "NOT RUN")) for k in LEG_KEYS}

    # Any FAIL / BLOCKED → NoGo
    for st in normalized.values():
        if st in ("FAIL", "BLOCKED"):
            return "NoGo"

    br_st = normalized["build_result"]
    if br_st == "NOT RUN":
        return "NoGo"

    # MSI missing → cannot Go
    if normalized["msi"] == "NOT RUN":
        return "NoGo"

    # Soft-gate hard override (if owner flipped gates on — default False)
    if elev_hard_gate and normalized["elev"] != "PASS":
        return "NoGo"
    if sign_hard_gate and normalized["signing"] != "PASS":
        return "NoGo"

    if all(normalized[k] == "PASS" for k in LEG_KEYS):
        return "Go"

    # Remaining incompleteness
    soft_incomplete = any(
        normalized[k] in ("NOT RUN", "PARTIAL") for k in SOFT_LEGS
    )
    other_incomplete = any(
        normalized[k] in ("NOT RUN", "PARTIAL")
        for k in LEG_KEYS
        if k not in SOFT_LEGS
    )

    if br_st in ("PASS", "PARTIAL") and allow_partial:
        # V01-GATE: elev/sign NOT RUN alone → Go-with-PARTIAL
        if soft_incomplete or other_incomplete or br_st == "PARTIAL":
            return "Go-with-PARTIAL"
        return "Go"

    return "NoGo"


def merge_legs(
    derived: Mapping[str, str],
    checklist: Mapping[str, str | None],
    *,
    sbom: str,
    changelog: str,
    signing_override: str | None = None,
) -> tuple[dict[str, str], list[str]]:
    """Checklist filled values win; else derived / evidence. Returns legs + notes."""
    notes: list[str] = []
    legs: dict[str, str] = {}
    filled = checklist_is_filled(checklist)

    for key in LEG_KEYS:
        if key == "build_result":
            legs[key] = never_promote(derived.get("build_result", "NOT RUN"))
            continue
        cl = checklist.get(key)
        if cl is not None:
            legs[key] = never_promote(cl)
            continue
        if key == "sbom":
            legs[key] = never_promote(sbom)
        elif key == "changelog":
            legs[key] = never_promote(changelog)
        elif key == "signing" and signing_override is not None:
            legs[key] = never_promote(signing_override)
        else:
            legs[key] = never_promote(derived.get(key, "NOT RUN"))

    if not filled:
        notes.append(
            "RELEASE-CHECKLIST-v0.1 not fully filled — legs derived from "
            "Build Result / sign stub / SBOM / CHANGELOG (honest PARTIAL/"
            "NOT RUN). Dependency: PD-CHECKLIST-FILL-01."
        )
    return legs, notes


# --- report emit ---------------------------------------------------------------


def build_gonogo_report(
    *,
    legs: Mapping[str, str],
    verdict: str,
    sources: Mapping[str, str],
    notes: Sequence[str],
    version: str = "0.1.0",
    generated_at: str | None = None,
    gate_ref: str = GATE_REF,
) -> dict[str, Any]:
    if verdict not in VERDICTS:
        raise GonogoError("illegal verdict %r" % verdict)
    ts = generated_at or now_iso()
    # Final guard: no leg may show PASS if its source status was NOT RUN
    safe_legs = {k: never_promote(legs.get(k, "NOT RUN")) for k in LEG_KEYS}
    return {
        "schema": SCHEMA,
        "cardId": CARD_ID,
        "bdd": BDD_ID,
        "version": version.lstrip("v"),
        "verdict": verdict,
        "generatedAt": ts,
        "gateRef": gate_ref,
        "gatePolicy": {
            "allowPartial": True,
            "elevHardGate": False,
            "signHardGate": False,
            "note": (
                "PD-DEC-V01-GATE-01: Build Result PARTIAL allowed; "
                "elevated VERIFY-INSTALL and Authenticode are not hard gates "
                "(NOT RUN / PARTIAL → Go-with-PARTIAL, never forged PASS)."
            ),
        },
        "legs": safe_legs,
        "sources": dict(sources),
        "notes": list(notes),
        # READY_FOR_GREEN evidence for parent/TDD — never self-sets board zone=green.
        "readyForGreen": verdict in ("Go", "Go-with-PARTIAL"),
        "implementerStatus": "PARTIAL" if verdict == "Go-with-PARTIAL" else (
            "PASS" if verdict == "Go" else "FAIL"
        ),
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Go/NoGo — v%s" % report.get("version", "0.1.0"))
    lines.append("")
    lines.append("- **Verdict:** %s" % report["verdict"])
    lines.append("- **Generated:** %s" % (report.get("generatedAt") or ""))
    lines.append("- **Card:** %s" % (report.get("cardId") or CARD_ID))
    lines.append("- **BDD:** %s" % (report.get("bdd") or BDD_ID))
    lines.append("- **Gate:** %s" % (report.get("gateRef") or GATE_REF))
    lines.append(
        "- **Implementer status:** %s (READY_FOR_GREEN evidence; board stays yellow §7.1)"
        % (report.get("implementerStatus") or "")
    )
    lines.append("")
    lines.append("## Gate policy (PD-DEC-V01-GATE-01)")
    lines.append("")
    gp = report.get("gatePolicy") or {}
    lines.append(str(gp.get("note") or ""))
    lines.append("")
    lines.append("## Legs")
    lines.append("")
    lines.append("| Leg | Status |")
    lines.append("|-----|--------|")
    legs = report.get("legs") or {}
    for key in LEG_KEYS:
        lines.append("| %s | %s |" % (key, legs.get(key, "NOT RUN")))
    lines.append("")
    lines.append("## Sources")
    lines.append("")
    sources = report.get("sources") or {}
    if sources:
        for k, v in sources.items():
            lines.append("- **%s:** `%s`" % (k, v))
    else:
        lines.append("none")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    notes = report.get("notes") or []
    if notes:
        for n in notes:
            lines.append("- %s" % n)
    else:
        lines.append("none")
    lines.append("")
    lines.append("## Anti-forge")
    lines.append("")
    lines.append(
        "NOT RUN legs are listed as **NOT RUN**. This aggregator never rewrites "
        "NOT RUN → PASS. Soft-gate incompleteness (elev / signing) yields "
        "**Go-with-PARTIAL**, not Go."
    )
    lines.append("")
    lines.append("## Verdict vocabulary")
    lines.append("")
    lines.append("Go | NoGo | Go-with-PARTIAL")
    lines.append("")
    return "\n".join(lines)


def aggregate(
    *,
    repo: Path | None = None,
    build_result_path: Path | None = None,
    checklist_path: Path | None = None,
    sign_result_path: Path | None = None,
    sbom_path: Path | None = None,
    version: str = "0.1.0",
    allow_partial: bool = True,
) -> dict[str, Any]:
    root = repo or REPO
    reports = root / "reports"
    sources: dict[str, str] = {}

    br_path = build_result_path or find_latest_build_result(reports)
    if br_path is None or not br_path.is_file():
        derived = {k: "NOT RUN" for k in LEG_KEYS}
        derived["build_result"] = "NOT RUN"
        sources["build_result"] = "(missing)"
        notes = ["No Build Result JSON found under reports/ — verdict NoGo."]
        legs = derived
        verdict = compute_verdict(
            legs, allow_partial=allow_partial, elev_hard_gate=False, sign_hard_gate=False
        )
        return build_gonogo_report(
            legs=legs, verdict=verdict, sources=sources, notes=notes, version=version
        )

    result = load_json(br_path)
    sources["build_result"] = str(br_path.relative_to(root)).replace("\\", "/")
    derived = derive_legs_from_build_result(result)

    cl_path = checklist_path or (root / "docs" / "RELEASE-CHECKLIST-v0.1.md")
    checklist_raw: dict[str, str | None] = {
        k: None for k in LEG_KEYS if k != "build_result"
    }
    if cl_path.is_file():
        sources["checklist"] = str(cl_path.relative_to(root)).replace("\\", "/")
        checklist_raw = parse_checklist_statuses(cl_path.read_text(encoding="utf-8"))
    else:
        sources["checklist"] = "(missing)"

    sb_path = sbom_path or find_latest_sbom_report(reports)
    sbom_st = load_sbom_status(sb_path)
    if sb_path and sb_path.is_file():
        try:
            sources["sbom"] = str(sb_path.relative_to(root)).replace("\\", "/")
        except ValueError:
            sources["sbom"] = str(sb_path)

    sign_path = sign_result_path or sign_stub.DEFAULT_RESULT
    sign_st = sign_stub.load_signing_status(sign_path)
    try:
        sources["signing"] = str(sign_path.relative_to(root)).replace("\\", "/")
    except ValueError:
        sources["signing"] = str(sign_path)

    changelog_st = load_changelog_status(root)
    sources["changelog"] = "CHANGELOG.md"

    legs, notes = merge_legs(
        derived,
        checklist_raw,
        sbom=sbom_st,
        changelog=changelog_st,
        signing_override=sign_st,
    )
    # Prefer live sign stub over BR signingStatus when stub file exists
    if sign_path.is_file():
        legs["signing"] = never_promote(sign_st)

    notes.append(
        "Aligned with %s — elev/sign NOT RUN allowed → Go-with-PARTIAL." % GATE_REF
    )

    verdict = compute_verdict(
        legs,
        allow_partial=allow_partial,
        elev_hard_gate=False,
        sign_hard_gate=False,
    )
    return build_gonogo_report(
        legs=legs,
        verdict=verdict,
        sources=sources,
        notes=notes,
        version=str(result.get("version") or version),
    )


def write_report(
    report: Mapping[str, Any],
    *,
    out_dir: Path | None = None,
    stamp: str | None = None,
) -> tuple[Path, Path]:
    dest = out_dir or (REPO / "reports")
    dest.mkdir(parents=True, exist_ok=True)
    tag = stamp or _stamp(str(report.get("generatedAt") or ""))
    ver = str(report.get("version") or "0.1.0").lstrip("v")
    base = "gonogo-v%s-%s" % (ver, tag)
    md_path = dest / (base + ".md")
    json_path = dest / (base + ".json")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return md_path, json_path


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=str(REPO), help="Repository root")
    ap.add_argument("--build-result", default="", help="Path to build-*.json")
    ap.add_argument("--checklist", default="", help="Path to RELEASE-CHECKLIST md")
    ap.add_argument("--sign-result", default="", help="Authenticode stub JSON")
    ap.add_argument("--sbom", default="", help="SBOM report md/json")
    ap.add_argument("--version", default="0.1.0")
    ap.add_argument("--out-dir", default="", help="Output directory (default reports/)")
    ap.add_argument(
        "--no-write",
        action="store_true",
        help="Print JSON only; do not write reports/gonogo-*.md",
    )
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    root = Path(args.repo)
    report = aggregate(
        repo=root,
        build_result_path=Path(args.build_result) if args.build_result else None,
        checklist_path=Path(args.checklist) if args.checklist else None,
        sign_result_path=Path(args.sign_result) if args.sign_result else None,
        sbom_path=Path(args.sbom) if args.sbom else None,
        version=args.version,
    )
    if args.no_write:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["verdict"] != "NoGo" else 1

    out_dir = Path(args.out_dir) if args.out_dir else (root / "reports")
    md_path, json_path = write_report(report, out_dir=out_dir)
    print(
        "verdict=%s implementerStatus=%s md=%s json=%s"
        % (
            report["verdict"],
            report.get("implementerStatus"),
            md_path,
            json_path,
        )
    )
    # Exit 0 for Go / Go-with-PARTIAL (PARTIAL READY_FOR_GREEN); 1 for NoGo
    return 0 if report["verdict"] != "NoGo" else 1


if __name__ == "__main__":
    raise SystemExit(main())
