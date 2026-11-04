#!/usr/bin/env python3
"""PD-VERIFY-HANG-01 — hang elevated VERIFY + Live smoke into Build Result.

BDD-PD-VERIFY-HANG-01:
  - Attach elev VERIFY-INSTALL and Live CLI smoke status into a Build Result /
    reports artifact.
  - Missing run → NOT RUN.
  - Failure → FAIL / PARTIAL (worst-wins rollup).
  - Never write NOT RUN as PASS (refuse forged PASS).

ELEV / LIVE producers may land in parallel — missing inputs are accepted as
fixture paths or honest NOT RUN payloads (packaging read-only).
"""
from __future__ import annotations

import argparse
import json
import os
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

TAIPEI = timezone(timedelta(hours=8))

CARD_ID = "PD-VERIFY-HANG-01"
BDD_ID = "BDD-PD-VERIFY-HANG-01"
SCHEMA = "aiad.verify-hang.v1"

DEFAULT_ELEV_REL = "packaging/windows/wix/out/verify-install-result.json"
LIVE_GLOB = "live-cli-smoke-*.json"
LIVE_FALLBACK = "live-smoke-result.json"

# Row names hung into Build Result.verification
ELEV_ROW = "ELEV-VERIFY"
LIVE_ROW = "LIVE-CLI-SMOKE"


class VerifyHangError(ValueError):
    """Invalid elev / live hang input."""


def now_iso() -> str:
    return datetime.now(TAIPEI).isoformat(timespec="seconds")


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _stamp(iso: str | None = None) -> str:
    ts = iso or now_iso()
    stamp = re.sub(r"[^0-9T]", "", ts.replace("+", "p").replace(":", ""))[:15]
    return stamp or datetime.now(TAIPEI).strftime("%Y%m%dT%H%M%S")


def missing_payload(kind: str, *, detail: str = "", evidence: str = "") -> dict:
    """Honest NOT RUN payload when elev/live evidence is absent."""
    return {
        "schema": SCHEMA,
        "kind": kind,
        "status": "NOT RUN",
        "overall": "NOT RUN",
        "source": "missing",
        "detail": detail or ("%s evidence missing — NOT RUN (not forged PASS)" % kind),
        "evidence": evidence,
        "checks": [],
        "live_executed": False,
        "elevated": False,
    }


def _coerce_status(raw: Any, *, default: str = "NOT RUN") -> str:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return br.normalize_status(default)
    return br.normalize_status(raw)


def _elev_live_checks(checks: Sequence[Any]) -> list[Mapping[str, Any]]:
    """Elevated install rows (exclude VI-CONTRACT-* dry-contract checks)."""
    out: list[Mapping[str, Any]] = []
    for c in checks:
        if not isinstance(c, Mapping):
            continue
        cid = str(c.get("id") or "").upper()
        if not cid.startswith("VI-"):
            continue
        if "CONTRACT" in cid:
            continue
        out.append(c)
    return out


def summarize_elev(payload: Mapping[str, Any]) -> str:
    """Derive hang status from elev VERIFY JSON (never invent PASS from missing live)."""
    if not payload:
        return "NOT RUN"
    if payload.get("source") == "missing":
        return "NOT RUN"

    live = bool(
        payload.get("live_executed")
        or payload.get("run_elevated")
        or payload.get("elevated_process")
        or payload.get("elevated")
    )
    checks = list(payload.get("checks") or [])
    elev_checks = _elev_live_checks(checks)
    elev_statuses = [
        _coerce_status(c.get("status"), default="NOT RUN") for c in elev_checks
    ]

    # 缺跑 → NOT RUN (unless a live/elev attempt already recorded FAIL/PARTIAL).
    if not live:
        if any(s == "FAIL" for s in elev_statuses):
            return "FAIL"
        if any(s == "PARTIAL" for s in elev_statuses):
            return "PARTIAL"
        if any(s == "BLOCKED" for s in elev_statuses):
            return "BLOCKED"
        # All missing / NOT RUN / contract-only — honest NOT RUN (not PARTIAL from overall).
        return "NOT RUN"

    statuses: list[str] = list(elev_statuses)
    if "overall" in payload or "status" in payload:
        statuses.append(
            _coerce_status(payload.get("overall") or payload.get("status"), default="NOT RUN")
        )
    if not statuses:
        return "PARTIAL"
    return br.rollup_status(statuses)


def summarize_live(payload: Mapping[str, Any]) -> str:
    """Derive hang status from Live CLI smoke JSON."""
    if not payload:
        return "NOT RUN"
    if payload.get("source") == "missing":
        return "NOT RUN"
    live = bool(payload.get("live_executed") or payload.get("executed") or payload.get("ran"))
    checks = list(payload.get("checks") or payload.get("steps") or [])
    statuses: list[str] = []
    if "overall" in payload or "status" in payload:
        statuses.append(
            _coerce_status(payload.get("overall") or payload.get("status"), default="NOT RUN")
        )
    for c in checks:
        if isinstance(c, Mapping):
            statuses.append(_coerce_status(c.get("status"), default="NOT RUN"))
    if not statuses:
        return "NOT RUN" if not live else "PARTIAL"
    rolled = br.rollup_status(statuses)
    if not live and rolled == "PASS":
        # Fixture claimed PASS without execution — refuse forge.
        return "NOT RUN"
    return rolled


def refuse_forged_pass(build_status: Any, hung_statuses: Sequence[Any]) -> str:
    """Worst-wins rollup; NOT RUN / FAIL / PARTIAL never become PASS."""
    base = _coerce_status(build_status, default="NOT RUN")
    hung = [_coerce_status(s, default="NOT RUN") for s in hung_statuses]
    return br.rollup_status([base] + hung)


def load_elev_verify(
    path: Path | str | None = None,
    *,
    repo: Path | None = None,
) -> dict:
    """Load elev VERIFY JSON; missing file → NOT RUN payload (fixture/parallel OK)."""
    root = repo or REPO
    if path is None:
        p = root / DEFAULT_ELEV_REL
    else:
        p = Path(path)
        if not p.is_absolute():
            p = root / p
    if not p.is_file():
        return missing_payload(
            "elev",
            detail="elev VERIFY JSON missing — NOT RUN (accept parallel/fixture)",
            evidence=_rel(p, root),
        )
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return missing_payload(
            "elev",
            detail="elev VERIFY unreadable: %s" % exc,
            evidence=_rel(p, root),
        )
    if not isinstance(data, Mapping):
        raise VerifyHangError("elev payload must be object, got %r" % type(data))
    out = dict(data)
    out.setdefault("schema", SCHEMA)
    out["kind"] = "elev"
    out["evidence"] = _rel(p, root)
    out["source"] = "file"
    out["status"] = summarize_elev(out)
    out["overall"] = out["status"]
    return out


def find_latest_live(repo: Path) -> Path | None:
    reports = repo / "reports"
    if not reports.is_dir():
        return None
    candidates = sorted(reports.glob(LIVE_GLOB), key=lambda x: x.stat().st_mtime, reverse=True)
    if candidates:
        return candidates[0]
    fallback = reports / LIVE_FALLBACK
    return fallback if fallback.is_file() else None


def load_live_smoke(
    path: Path | str | None = None,
    *,
    repo: Path | None = None,
) -> dict:
    """Load Live CLI smoke JSON; missing → NOT RUN (parallel land OK)."""
    root = repo or REPO
    if path is None:
        found = find_latest_live(root)
        if found is None:
            return missing_payload(
                "live",
                detail=(
                    "Live CLI smoke JSON missing "
                    "(reports/%s or %s) — NOT RUN" % (LIVE_GLOB, LIVE_FALLBACK)
                ),
                evidence="reports/",
            )
        p = found
    else:
        p = Path(path)
        if not p.is_absolute():
            p = root / p
    if not p.is_file():
        return missing_payload(
            "live",
            detail="Live smoke JSON missing — NOT RUN (accept parallel/fixture)",
            evidence=_rel(p, root),
        )
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return missing_payload(
            "live",
            detail="Live smoke unreadable: %s" % exc,
            evidence=_rel(p, root),
        )
    if not isinstance(data, Mapping):
        raise VerifyHangError("live payload must be object, got %r" % type(data))
    out = dict(data)
    out.setdefault("schema", SCHEMA)
    out["kind"] = "live"
    out["evidence"] = _rel(p, root)
    out["source"] = "file"
    out["status"] = summarize_live(out)
    out["overall"] = out["status"]
    return out


def _upsert_verification_row(
    verif: list[dict],
    name: str,
    status: Any,
    *,
    detail: str = "",
    evidence: str = "",
) -> list[dict]:
    row = br.build_verification_row(name, status, detail=detail, evidence=evidence)
    out: list[dict] = []
    replaced = False
    for existing in verif:
        if existing.get("name") == name:
            out.append(row)
            replaced = True
        else:
            out.append(existing)
    if not replaced:
        out.append(row)
    return out


def attach_elev_to_build_result(
    result: MutableMapping[str, Any],
    elev: Mapping[str, Any] | None = None,
    *,
    repo: Path | None = None,
) -> MutableMapping[str, Any]:
    """Hang elev VERIFY into Build Result verification + status rollup."""
    payload = elev if elev is not None else load_elev_verify(repo=repo or REPO)
    st = summarize_elev(payload)
    detail = str(payload.get("detail") or "")
    if not detail:
        live = bool(
            payload.get("live_executed")
            or payload.get("run_elevated")
            or payload.get("elevated_process")
            or payload.get("elevated")
        )
        detail = (
            "elevated live=%s; source=%s; overall=%s"
            % (live, payload.get("source") or "?", st)
        )
    evid = str(payload.get("evidence") or DEFAULT_ELEV_REL)
    result["verification"] = _upsert_verification_row(
        list(result.get("verification") or []),
        ELEV_ROW,
        st,
        detail=detail,
        evidence=evid,
    )
    result["status"] = refuse_forged_pass(result.get("status") or "NOT RUN", [st])
    _stamp_hang_meta(result, elev_status=st, elev_evidence=evid)
    return result


def attach_live_to_build_result(
    result: MutableMapping[str, Any],
    live: Mapping[str, Any] | None = None,
    *,
    repo: Path | None = None,
) -> MutableMapping[str, Any]:
    """Hang Live CLI smoke into Build Result verification + status rollup."""
    payload = live if live is not None else load_live_smoke(repo=repo or REPO)
    st = summarize_live(payload)
    detail = str(payload.get("detail") or payload.get("summary") or "")
    if not detail:
        detail = "live_executed=%s; source=%s; overall=%s" % (
            bool(payload.get("live_executed") or payload.get("executed") or payload.get("ran")),
            payload.get("source") or "?",
            st,
        )
    evid = str(payload.get("evidence") or "reports/")
    result["verification"] = _upsert_verification_row(
        list(result.get("verification") or []),
        LIVE_ROW,
        st,
        detail=detail,
        evidence=evid,
    )
    result["status"] = refuse_forged_pass(result.get("status") or "NOT RUN", [st])
    _stamp_hang_meta(result, live_status=st, live_evidence=evid)
    return result


def _stamp_hang_meta(
    result: MutableMapping[str, Any],
    *,
    elev_status: str | None = None,
    elev_evidence: str | None = None,
    live_status: str | None = None,
    live_evidence: str | None = None,
) -> None:
    meta = dict(result.get("verifyHang") or {})
    meta["schema"] = SCHEMA
    meta["cardId"] = CARD_ID
    meta["bdd"] = BDD_ID
    if elev_status is not None:
        meta["elevStatus"] = elev_status
    if elev_evidence is not None:
        meta["elevEvidence"] = elev_evidence
    if live_status is not None:
        meta["liveStatus"] = live_status
    if live_evidence is not None:
        meta["liveEvidence"] = live_evidence
    result["verifyHang"] = meta
    reqs = list(result.get("requirementTraceability") or [])
    for tid in (BDD_ID, CARD_ID):
        if tid not in reqs:
            reqs.append(tid)
    result["requirementTraceability"] = reqs
    pending = list(result.get("pending") or [])
    if elev_status == "NOT RUN":
        line = "PD-VERIFY-HANG-01: elevated VERIFY still NOT RUN (do not forge PASS)"
        if line not in pending:
            pending.append(line)
    if live_status == "NOT RUN":
        line = "PD-VERIFY-HANG-01: Live CLI smoke still NOT RUN (do not forge PASS)"
        if line not in pending:
            pending.append(line)
    result["pending"] = pending
    risks = list(result.get("risks") or [])
    if elev_status in ("NOT RUN", "FAIL", "PARTIAL") or live_status in (
        "NOT RUN",
        "FAIL",
        "PARTIAL",
    ):
        line = (
            "Elevated VERIFY / Live smoke hang: elev=%s live=%s — Build Result must not claim PASS"
            % (meta.get("elevStatus", "?"), meta.get("liveStatus", "?"))
        )
        if line not in risks:
            risks.append(line)
    result["risks"] = risks


def attach_verify_hang(
    result: MutableMapping[str, Any],
    *,
    elev: Mapping[str, Any] | None = None,
    live: Mapping[str, Any] | None = None,
    elev_path: Path | str | None = None,
    live_path: Path | str | None = None,
    repo: Path | None = None,
) -> MutableMapping[str, Any]:
    """Hang both elev VERIFY and Live smoke; rollup refuses forged PASS."""
    root = repo or REPO
    elev_payload = elev if elev is not None else load_elev_verify(elev_path, repo=root)
    live_payload = live if live is not None else load_live_smoke(live_path, repo=root)
    attach_elev_to_build_result(result, elev_payload, repo=root)
    attach_live_to_build_result(result, live_payload, repo=root)
    # Final gate: both hung statuses.
    result["status"] = refuse_forged_pass(
        result.get("status") or "NOT RUN",
        [summarize_elev(elev_payload), summarize_live(live_payload)],
    )
    return result


def write_hang_summary(
    result: Mapping[str, Any],
    *,
    repo: Path | None = None,
    out_path: Path | None = None,
) -> Path:
    """Write a short hang summary markdown under reports/."""
    root = repo or REPO
    meta = result.get("verifyHang") or {}
    ts = _stamp(str(result.get("generatedAt") or "") or None)
    path = out_path or (root / "reports" / ("verify-hang-%s.md" % ts))
    if not path.is_absolute():
        path = root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Verify Hang — %s" % CARD_ID,
        "",
        "- **BDD:** %s" % BDD_ID,
        "- **Build Result status:** %s" % result.get("status"),
        "- **Elev status:** %s" % meta.get("elevStatus", "NOT RUN"),
        "- **Live status:** %s" % meta.get("liveStatus", "NOT RUN"),
        "- **Elev evidence:** `%s`" % (meta.get("elevEvidence") or "none"),
        "- **Live evidence:** `%s`" % (meta.get("liveEvidence") or "none"),
        "",
        "## Rule",
        "",
        "Missing run → **NOT RUN**. Failure → **FAIL** / **PARTIAL**. "
        "**NOT RUN must not be written as PASS.**",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    side = path.with_suffix(".json")
    side.write_text(
        json.dumps(
            {
                "schema": SCHEMA,
                "cardId": CARD_ID,
                "bdd": BDD_ID,
                "buildResultStatus": result.get("status"),
                "verifyHang": meta,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser(
        "hang-demo",
        help="Generate/load Build Result, hang elev+live, write reports",
    )
    d.add_argument("--elev", default="", help="Elev VERIFY JSON (default packaging path)")
    d.add_argument("--live", default="", help="Live smoke JSON (default reports glob)")
    d.add_argument("--from-build", default="", help="Existing Build Result .json to attach onto")
    d.add_argument("--out", default="", help="Output Build Result .md path")
    d.add_argument("--summary-out", default="", help="verify-hang summary .md path")
    d.add_argument("--no-json", action="store_true")

    a = sub.add_parser("attach", help="Attach elev+live onto an existing Build Result JSON")
    a.add_argument("build_json", help="Path to build-*.json")
    a.add_argument("--elev", default="")
    a.add_argument("--live", default="")
    a.add_argument("--out", default="", help="Rewrite Build Result .md (default beside json)")

    v = sub.add_parser("summarize", help="Print elev/live hang statuses from inputs")
    v.add_argument("--elev", default="")
    v.add_argument("--live", default="")

    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    root = REPO

    if args.cmd == "summarize":
        elev = load_elev_verify(args.elev or None, repo=root)
        live = load_live_smoke(args.live or None, repo=root)
        print(
            json.dumps(
                {
                    "elevStatus": summarize_elev(elev),
                    "liveStatus": summarize_live(live),
                    "elevEvidence": elev.get("evidence"),
                    "liveEvidence": live.get("evidence"),
                    "wouldRefusePass": refuse_forged_pass(
                        "PASS", [summarize_elev(elev), summarize_live(live)]
                    )
                    != "PASS",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.cmd == "attach":
        bj = Path(args.build_json)
        if not bj.is_absolute():
            bj = root / bj
        result = json.loads(bj.read_text(encoding="utf-8-sig"))
        attach_verify_hang(
            result,
            elev_path=args.elev or None,
            live_path=args.live or None,
            repo=root,
        )
        out = Path(args.out) if args.out else bj.with_suffix(".md")
        if not out.is_absolute():
            out = root / out
        path = br.write_report(result, out, also_json=True, repo=root)
        summary = write_hang_summary(result, repo=root)
        print(
            "attached %s status=%s elev=%s live=%s summary=%s"
            % (
                path,
                result["status"],
                (result.get("verifyHang") or {}).get("elevStatus"),
                (result.get("verifyHang") or {}).get("liveStatus"),
                summary,
            )
        )
        return 0

    if args.cmd == "hang-demo":
        if args.from_build:
            bj = Path(args.from_build)
            if not bj.is_absolute():
                bj = root / bj
            result = json.loads(bj.read_text(encoding="utf-8-sig"))
        else:
            result = br.candidate_v010_from_packaging(repo=root)
            # Start from an optimistic PASS to prove refuse_forged_pass in demo when hung NOT RUN.
            # Real hang will rollup down — never leave forged PASS.
        attach_verify_hang(
            result,
            elev_path=args.elev or None,
            live_path=args.live or None,
            repo=root,
        )
        out = Path(args.out) if args.out else br.default_report_path(
            str(result.get("version") or "0.1.0"),
            generated_at=str(result.get("generatedAt") or now_iso()),
            dest="reports",
            repo=root,
        )
        path = br.write_report(result, out, also_json=not args.no_json, repo=root)
        summary = write_hang_summary(
            result,
            repo=root,
            out_path=Path(args.summary_out) if args.summary_out else None,
        )
        print(
            "wrote %s status=%s elev=%s live=%s summary=%s"
            % (
                path,
                result["status"],
                (result.get("verifyHang") or {}).get("elevStatus"),
                (result.get("verifyHang") or {}).get("liveStatus"),
                summary,
            )
        )
        # Exit: FAIL → 1; otherwise 0 (NOT RUN/PARTIAL recorded honestly).
        return 1 if result.get("status") == "FAIL" else 0

    print("unknown command", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
