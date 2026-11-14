#!/usr/bin/env python3
"""PD-REL-HANG-FINAL-01 — hang final Build Result + key artifacts into #release.

BDD-PD-REL-HANG-FINAL-01: append/update snapshot.releases v0.1.0 (or equiv);
reportPath → latest reports/build-0.1.0-final-*.md; artifacts include MSI / SBOM
when present; never rewrite signing NOT RUN as PASS.

Reuses release_report (snapshot-only mutate). No git tag; no store listing.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, MutableMapping, Sequence

BOARD_DIR = Path(__file__).resolve().parent
REPO = BOARD_DIR.parents[1]
DOCS = REPO / "docs"
DEFAULT_BOARD = DOCS / "PROJECT-BOARD.html"
TAIPEI = timezone(timedelta(hours=8))

CARD_ID = "PD-REL-HANG-FINAL-01"
BDD_ID = "BDD-PD-REL-HANG-FINAL-01"
DEFAULT_VERSION = "0.1.0"
FINAL_BR_GLOB = "build-0.1.0-final-*.md"
MSI_REL = "packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi"

if str(BOARD_DIR) not in sys.path:
    sys.path.insert(0, str(BOARD_DIR))

import release_report  # noqa: E402

_FINAL_BR_RE = re.compile(r"^build-0\.1\.0-final-.+\.md$", re.IGNORECASE)


def now_iso() -> str:
    return datetime.now(TAIPEI).isoformat(timespec="seconds")


def find_latest_final_br(repo: Path | None = None) -> Path | None:
    """Return newest reports/build-0.1.0-final-*.md under repo, or None."""
    root = repo or REPO
    reports = root / "reports"
    if not reports.is_dir():
        return None
    candidates = [
        p
        for p in reports.iterdir()
        if p.is_file() and _FINAL_BR_RE.match(p.name)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _repo_rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def load_final_br_meta(report_path: Path, repo: Path | None = None) -> dict[str, Any]:
    """Load companion .json if present; else parse status from markdown lightly."""
    root = repo or REPO
    meta: dict[str, Any] = {
        "version": DEFAULT_VERSION,
        "status": "PARTIAL",
        "signingStatus": "NOT RUN",
    }
    sidecar = report_path.with_suffix(".json")
    if sidecar.is_file():
        data = json.loads(sidecar.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            meta["version"] = str(data.get("version") or DEFAULT_VERSION).lstrip("v")
            meta["status"] = str(data.get("status") or "PARTIAL")
            meta["signingStatus"] = str(data.get("signingStatus") or "NOT RUN")
            meta["generatedAt"] = data.get("generatedAt")
            meta["id"] = data.get("id")
            meta["kind"] = data.get("kind") or "installer"
            meta["recordedBy"] = data.get("recordedBy") or "agent"
            if isinstance(data.get("artifacts"), list):
                meta["brArtifacts"] = data["artifacts"]
            return meta

    if report_path.is_file():
        text = report_path.read_text(encoding="utf-8")
        m = re.search(r"\*\*Status:\*\*\s*(\S+)", text)
        if m:
            meta["status"] = m.group(1).strip()
        if re.search(r"## Signing status\s*\n\s*NOT RUN", text, re.IGNORECASE):
            meta["signingStatus"] = "NOT RUN"
        elif re.search(r"## Signing status\s*\n\s*PASS", text, re.IGNORECASE):
            # Only accept PASS from markdown if explicitly present — hang still
            # refuses forged PASS without Authenticode evidence elsewhere.
            meta["signingStatus"] = "PASS"
    meta["reportPath"] = _repo_rel(report_path, root)
    return meta


def find_latest_sbom(repo: Path, suffix: str) -> Path | None:
    """Newest reports/sbom-*.{cdx.json|spdx.json} matching suffix."""
    reports = repo / "reports"
    if not reports.is_dir():
        return None
    # suffix e.g. ".cdx.json" or ".spdx.json"
    found: list[Path] = []
    for p in reports.iterdir():
        name = p.name.lower()
        if p.is_file() and name.startswith("sbom-") and name.endswith(suffix.lower()):
            found.append(p)
    if not found:
        return None
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found[0]


def collect_key_artifacts(
    *,
    repo: Path | None = None,
    checked_at: str | None = None,
    include_missing: bool = True,
) -> list[dict]:
    """MSI (+ .sha256) and SBOM CycloneDX/SPDX paths when present."""
    root = repo or REPO
    ts = checked_at or now_iso()
    arts: list[dict] = []

    msi = root / MSI_REL
    arts.append(release_report.build_artifact(msi, "MSI", ts, root))
    sha_side = Path(str(msi) + ".sha256")
    if sha_side.is_file() or include_missing:
        # Only add sha sidecar when it exists (avoid noisy missing rows).
        if sha_side.is_file():
            arts.append(release_report.build_artifact(sha_side, "MSI.sha256", ts, root))

    cdx = find_latest_sbom(root, ".cdx.json")
    if cdx is not None:
        arts.append(release_report.build_artifact(cdx, "SBOM-CycloneDX", ts, root))
    elif include_missing:
        placeholder = root / "reports" / "sbom-missing.cdx.json"
        arts.append(release_report.build_artifact(placeholder, "SBOM-CycloneDX", ts, root))

    spdx = find_latest_sbom(root, ".spdx.json")
    if spdx is not None:
        arts.append(release_report.build_artifact(spdx, "SBOM-SPDX", ts, root))
    elif include_missing:
        placeholder = root / "reports" / "sbom-missing.spdx.json"
        arts.append(release_report.build_artifact(placeholder, "SBOM-SPDX", ts, root))

    if not include_missing:
        arts = [a for a in arts if a.get("exists")]
    return arts


def refuse_signing_forged_pass(release: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Never let a hang rewrite signing NOT RUN into PASS on the release row.

    BDD-PD-REL-HANG-FINAL-01: 不得把 NOT RUN 簽章寫成 PASS.
    """
    forged = bool(release.pop("_forgedSigningPass", False))
    sig = str(release.get("signingStatus") or "NOT RUN").upper()
    br_st = str(release.get("buildResultStatus") or "").upper()
    # Hang has no Authenticode evidence of its own. Refuse PASS when:
    # - caller marked a forged promotion, or
    # - overall Build Result is not PASS (PARTIAL / NOT RUN / FAIL / …).
    if sig == "PASS" and (forged or br_st != "PASS"):
        release["signingStatus"] = "NOT RUN"
    elif sig in ("", "NONE", "NULL"):
        release["signingStatus"] = "NOT RUN"
    return release


def hang_final_to_release(
    board_path: Path,
    *,
    version: str = DEFAULT_VERSION,
    report_path: Path | str | None = None,
    repo: Path | None = None,
    embed_report_md: bool = True,
    include_missing_artifacts: bool = False,
) -> dict:
    """Append/replace v0.1.0 release pointing at final BR + MSI/SBOM artifacts."""
    root = repo or REPO
    rp = Path(report_path) if report_path else find_latest_final_br(root)
    if rp is None:
        raise FileNotFoundError(
            "no reports/%s under %s" % (FINAL_BR_GLOB, root / "reports")
        )
    if not rp.is_absolute():
        rp = root / rp
    if not rp.is_file():
        raise FileNotFoundError("final Build Result not found: %s" % rp)

    meta = load_final_br_meta(rp, root)
    ver = str(version or meta.get("version") or DEFAULT_VERSION).lstrip("v")
    ts = str(meta.get("generatedAt") or now_iso())
    arts = collect_key_artifacts(
        repo=root, checked_at=ts, include_missing=include_missing_artifacts
    )
    # Prefer live MSI/SBOM collection; fall back to BR artifact rows if empty.
    if not arts and isinstance(meta.get("brArtifacts"), list):
        arts = list(meta["brArtifacts"])

    rel_path = _repo_rel(rp, root)
    release = release_report.build_release(
        version=ver,
        artifacts=arts,
        report_path=rel_path,
        kind=str(meta.get("kind") or "installer"),
        recorded_by=str(meta.get("recordedBy") or "agent"),
        released_at=ts,
        release_id=str(meta.get("id") or ("v" + ver)),
        embed_report_md=embed_report_md,
        repo=root,
    )
    release["buildResultStatus"] = str(meta.get("status") or "PARTIAL")
    release["signingStatus"] = str(meta.get("signingStatus") or "NOT RUN")
    release["cardId"] = CARD_ID
    release["bdd"] = BDD_ID
    refuse_signing_forged_pass(release)
    # HARD: hang must not invent overall PASS when BR is PARTIAL / signing NOT RUN.
    if release["signingStatus"].upper() == "NOT RUN" and release["buildResultStatus"].upper() == "PASS":
        release["buildResultStatus"] = "PARTIAL"
    return release_report.append_release(Path(board_path), release)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--board",
        default=os.environ.get("HB_BOARD_TASKS") or str(DEFAULT_BOARD),
        help="PROJECT-BOARD.html path",
    )
    ap.add_argument("--repo", default=str(REPO), help="Repo root")
    sub = ap.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("hang", help="Hang final BR into snapshot.releases")
    h.add_argument("--version", default=DEFAULT_VERSION)
    h.add_argument(
        "--report-path",
        default="",
        help="Override final BR path (default: latest build-0.1.0-final-*.md)",
    )
    h.add_argument("--no-embed-report", action="store_true")
    h.add_argument(
        "--include-missing",
        action="store_true",
        help="Include missing MSI/SBOM rows with exists=false",
    )

    sub.add_parser("find-br", help="Print latest final BR path")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    root = Path(args.repo)
    if args.cmd == "find-br":
        p = find_latest_final_br(root)
        if not p:
            print("none", file=sys.stderr)
            return 1
        print(_repo_rel(p, root))
        return 0

    if args.cmd == "hang":
        stored = hang_final_to_release(
            Path(args.board),
            version=args.version,
            report_path=args.report_path or None,
            repo=root,
            embed_report_md=not args.no_embed_report,
            include_missing_artifacts=bool(args.include_missing),
        )
        print(
            "hung release v%s id=%s status=%s signing=%s reportPath=%s artifacts=%d"
            % (
                stored.get("version"),
                stored.get("id"),
                stored.get("buildResultStatus"),
                stored.get("signingStatus"),
                stored.get("reportPath") or "",
                len(stored.get("artifacts") or []),
            )
        )
        return 0

    print("unknown command", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
