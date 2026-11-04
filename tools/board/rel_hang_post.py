#!/usr/bin/env python3
"""PD-REL-HANG-POST-01 — hang Post-Remain Build Result + key artifacts into #release.

BDD-PD-REL-HANG-POST-01: append/update snapshot.releases v0.1.0 (or equiv);
reportPath → Post-Remain BR (or best-available build-0.1.0-* with honest PARTIAL);
artifacts include MSI / SBOM when present; never rewrite signing NOT RUN as PASS.

Soft dep PD-REL-BR-POST-REMAIN-01: prefer that card's BR; else hang best-available.
Reuses release_report + rel_hang_final helpers (snapshot-only mutate).
No git tag; no store listing.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, MutableMapping, Sequence

BOARD_DIR = Path(__file__).resolve().parent
REPO = BOARD_DIR.parents[1]
DOCS = REPO / "docs"
DEFAULT_BOARD = DOCS / "PROJECT-BOARD.html"
TAIPEI = timezone(timedelta(hours=8))

CARD_ID = "PD-REL-HANG-POST-01"
BDD_ID = "BDD-PD-REL-HANG-POST-01"
SOFT_DEP_CARD = "PD-REL-BR-POST-REMAIN-01"
DEFAULT_VERSION = "0.1.0"
BR_GLOB_PREFIX = "build-0.1.0-"

if str(BOARD_DIR) not in sys.path:
    sys.path.insert(0, str(BOARD_DIR))

import release_report  # noqa: E402
import rel_hang_final as rhf  # noqa: E402

_BR_MD_RE = re.compile(r"^build-0\.1\.0-.+\.md$", re.IGNORECASE)
_POST_NAME_RE = re.compile(r"post[-_]?remain", re.IGNORECASE)


def now_iso() -> str:
    return datetime.now(TAIPEI).isoformat(timespec="seconds")


def _repo_rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _list_build_br_mds(repo: Path) -> list[Path]:
    reports = repo / "reports"
    if not reports.is_dir():
        return []
    return [
        p
        for p in reports.iterdir()
        if p.is_file() and _BR_MD_RE.match(p.name)
    ]


def _br_card_id(md_path: Path) -> str | None:
    sidecar = md_path.with_suffix(".json")
    if sidecar.is_file():
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict):
            cid = data.get("cardId") or data.get("card")
            if cid:
                return str(cid)
    if md_path.is_file():
        text = md_path.read_text(encoding="utf-8")
        m = re.search(r"\*\*Card:\*\*\s*(\S+)", text)
        if m:
            return m.group(1).strip()
    return None


def find_post_remain_br(repo: Path | None = None) -> Path | None:
    """Prefer BR authored by soft-dep card; else filename matching post-remain."""
    root = repo or REPO
    candidates = _list_build_br_mds(root)
    if not candidates:
        return None

    by_card = [p for p in candidates if _br_card_id(p) == SOFT_DEP_CARD]
    if by_card:
        by_card.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return by_card[0]

    by_name = [p for p in candidates if _POST_NAME_RE.search(p.name)]
    if by_name:
        by_name.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return by_name[0]
    return None


def find_best_available_br(repo: Path | None = None) -> Path | None:
    """Newest reports/build-0.1.0-*.md (any variant)."""
    root = repo or REPO
    candidates = _list_build_br_mds(root)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def resolve_br_for_hang(
    repo: Path | None = None,
    *,
    poll_seconds: float = 0.0,
    poll_interval: float = 2.0,
) -> tuple[Path, str]:
    """Return (br_path, hang_source) where source is post-remain|best-available.

    Soft dep: poll briefly for Post-Remain BR; else best-available.
    """
    root = repo or REPO
    deadline = time.monotonic() + max(0.0, float(poll_seconds))
    while True:
        post = find_post_remain_br(root)
        if post is not None:
            return post, "post-remain"
        if time.monotonic() >= deadline:
            break
        time.sleep(max(0.2, float(poll_interval)))

    best = find_best_available_br(root)
    if best is None:
        raise FileNotFoundError(
            "no reports/%s*.md under %s" % (BR_GLOB_PREFIX, root / "reports")
        )
    return best, "best-available"


def load_post_br_meta(report_path: Path, repo: Path | None = None) -> dict[str, Any]:
    """Load BR meta; reuse final hang loader shape."""
    return rhf.load_final_br_meta(report_path, repo)


def refuse_signing_forged_pass(release: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Delegate anti-forge rule (BDD: 禁偽 PASS)."""
    return rhf.refuse_signing_forged_pass(release)


def hang_post_to_release(
    board_path: Path,
    *,
    version: str = DEFAULT_VERSION,
    report_path: Path | str | None = None,
    repo: Path | None = None,
    embed_report_md: bool = True,
    include_missing_artifacts: bool = False,
    poll_seconds: float = 0.0,
) -> dict:
    """Append/replace v0.1.0 release pointing at Post-Remain (or best) BR + MSI/SBOM."""
    root = repo or REPO
    hang_source = "override"
    if report_path:
        rp = Path(report_path)
        if not rp.is_absolute():
            rp = root / rp
        # Classify override when it matches soft-dep.
        if _br_card_id(rp) == SOFT_DEP_CARD or _POST_NAME_RE.search(rp.name):
            hang_source = "post-remain"
        else:
            hang_source = "best-available"
    else:
        rp, hang_source = resolve_br_for_hang(root, poll_seconds=poll_seconds)

    if not rp.is_file():
        raise FileNotFoundError("Build Result not found: %s" % rp)

    meta = load_post_br_meta(rp, root)
    ver = str(version or meta.get("version") or DEFAULT_VERSION).lstrip("v")
    ts = str(meta.get("generatedAt") or now_iso())
    arts = rhf.collect_key_artifacts(
        repo=root, checked_at=ts, include_missing=include_missing_artifacts
    )
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
    br_status = str(meta.get("status") or "PARTIAL")
    # Soft-dep fallback must stay honest PARTIAL when not the dedicated Post-Remain BR.
    if hang_source == "best-available" and br_status.upper() == "PASS":
        br_status = "PARTIAL"
    release["buildResultStatus"] = br_status
    release["signingStatus"] = str(meta.get("signingStatus") or "NOT RUN")
    release["cardId"] = CARD_ID
    release["bdd"] = BDD_ID
    release["hangSource"] = hang_source
    release["softDepCard"] = SOFT_DEP_CARD
    refuse_signing_forged_pass(release)
    # HARD: hang must not invent overall PASS when BR is PARTIAL / signing NOT RUN.
    if (
        release["signingStatus"].upper() == "NOT RUN"
        and release["buildResultStatus"].upper() == "PASS"
    ):
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

    h = sub.add_parser("hang", help="Hang Post-Remain / best BR into snapshot.releases")
    h.add_argument("--version", default=DEFAULT_VERSION)
    h.add_argument(
        "--report-path",
        default="",
        help="Override BR path (default: poll soft-dep then best-available)",
    )
    h.add_argument(
        "--poll-seconds",
        type=float,
        default=0.0,
        help="Seconds to wait for Post-Remain BR before best-available fallback",
    )
    h.add_argument("--no-embed-report", action="store_true")
    h.add_argument(
        "--include-missing",
        action="store_true",
        help="Include missing MSI/SBOM rows with exists=false",
    )

    sub.add_parser("find-br", help="Print resolved BR path + hang source")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    root = Path(args.repo)
    if args.cmd == "find-br":
        try:
            p, source = resolve_br_for_hang(root, poll_seconds=0.0)
        except FileNotFoundError:
            print("none", file=sys.stderr)
            return 1
        print("%s\t%s" % (_repo_rel(p, root), source))
        return 0

    if args.cmd == "hang":
        stored = hang_post_to_release(
            Path(args.board),
            version=args.version,
            report_path=args.report_path or None,
            repo=root,
            embed_report_md=not args.no_embed_report,
            include_missing_artifacts=bool(args.include_missing),
            poll_seconds=float(args.poll_seconds),
        )
        print(
            "hung release v%s id=%s status=%s signing=%s source=%s reportPath=%s artifacts=%d"
            % (
                stored.get("version"),
                stored.get("id"),
                stored.get("buildResultStatus"),
                stored.get("signingStatus"),
                stored.get("hangSource"),
                stored.get("reportPath") or "",
                len(stored.get("artifacts") or []),
            )
        )
        return 0

    print("unknown command", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
