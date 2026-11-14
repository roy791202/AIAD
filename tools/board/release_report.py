#!/usr/bin/env python3
"""Append a release record into PROJECT-BOARD.html #board-snapshot.releases.

BDD-PD-RELEASE-REC-01: version / artifacts / reportPath; #release shows recent
deployments; empty releases[] still has empty-state UI in the HTML shell.

Writes via PD-BOARD-SAFE-01 helper when present; otherwise board_watch.mutate_html
(snapshot-only — never whole-file shell overwrite). No Firebase; no elevated install.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BOARD_DIR = Path(__file__).resolve().parent
REPO = BOARD_DIR.parents[1]
DOCS = REPO / "docs"
DEFAULT_BOARD = DOCS / "PROJECT-BOARD.html"
TAIPEI = timezone(timedelta(hours=8))

if str(DOCS) not in sys.path:
    sys.path.insert(0, str(DOCS))
if str(BOARD_DIR) not in sys.path:
    sys.path.insert(0, str(BOARD_DIR))

import board_watch  # noqa: E402

# Prefer PD-BOARD-SAFE-01 helper when present (snapshot-only mutate).
_SAFE_MUTATE = None
for _mod_name, _fn_name in (
    ("board_safe_mutate", "mutate_board_snapshot"),
    ("board_safe", "mutate_board_snapshot"),
    ("board_safe", "mutate_snapshot"),
):
    try:
        _mod = __import__(_mod_name)
        _fn = getattr(_mod, _fn_name, None)
        if callable(_fn):
            _SAFE_MUTATE = _fn
            break
    except ImportError:
        continue


def now_iso() -> str:
    return datetime.now(TAIPEI).isoformat(timespec="seconds")


def size_text(nbytes: int) -> str:
    if nbytes < 1024:
        return "%d B" % nbytes
    if nbytes < 1024 * 1024:
        return "%.1f KB" % (nbytes / 1024.0)
    return "%.1f MB" % (nbytes / (1024.0 * 1024.0))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_artifact(path: Path, label: str, checked_at: str, repo: Path | None = None) -> dict:
    """Build one artifact row for #release (label / path / exists / sizeText)."""
    root = repo or REPO
    abs_path = path if path.is_absolute() else (root / path)
    try:
        rel = abs_path.resolve().relative_to(root.resolve())
        display = str(rel).replace("\\", "/")
    except ValueError:
        display = str(abs_path)
    exists = abs_path.is_file()
    art: dict = {
        "label": label,
        "path": display,
        "exists": exists,
        "checkedAt": checked_at,
    }
    if exists:
        nbytes = abs_path.stat().st_size
        art["bytes"] = nbytes
        art["sizeText"] = size_text(nbytes)
        art["sha256"] = _sha256_file(abs_path)
    return art


def build_release(
    *,
    version: str,
    artifacts: list[dict],
    report_path: str | None,
    kind: str,
    recorded_by: str,
    released_at: str | None = None,
    release_id: str | None = None,
    embed_report_md: bool = True,
    repo: Path | None = None,
) -> dict:
    """Build a release object matching PROJECT-BOARD #release renderRelease shape."""
    root = repo or REPO
    ts = released_at or now_iso()
    ver = version.lstrip("v")
    rid = release_id or ("v" + ver)
    release: dict = {
        "id": rid,
        "version": ver,
        "kind": kind if kind in ("installer", "portable") else "installer",
        "releasedAt": ts,
        "recordedAt": ts,
        "recordedBy": recorded_by if recorded_by in ("user", "agent") else "agent",
        "artifacts": list(artifacts),
    }
    if report_path:
        release["reportPath"] = report_path.replace("\\", "/")
        if embed_report_md:
            rp = Path(report_path)
            if not rp.is_absolute():
                rp = root / rp
            if rp.is_file():
                text = rp.read_text(encoding="utf-8")
                # Keep board snapshot bounded; UI folds full markdown.
                release["reportMd"] = text if len(text) <= 80_000 else text[:80_000] + "\n\n…(truncated)…"
    return release


def _mutate_snapshot(board_path: Path, mutator):
    """Prefer PD-BOARD-SAFE-01 helper; fall back to board_watch.mutate_html."""
    if _SAFE_MUTATE is not None:
        return _SAFE_MUTATE(board_path, mutator)
    return board_watch.mutate_html(board_path, mutator)


def append_release(board_path: Path, release: dict) -> dict:
    """Append one release into snapshot.releases only (HTML shell preserved)."""
    if not isinstance(release, dict) or not release.get("version"):
        raise ValueError("release requires version")
    if "artifacts" not in release or not isinstance(release["artifacts"], list):
        raise ValueError("release requires artifacts list")

    def mutator(data: dict) -> dict:
        rels = data.setdefault("releases", [])
        if not isinstance(rels, list):
            raise ValueError("snapshot.releases is not a list")
        # Replace same id/version if re-recording; else append.
        rid = release.get("id") or ("v" + str(release["version"]))
        kept = [
            r
            for r in rels
            if not (
                isinstance(r, dict)
                and (r.get("id") == rid or str(r.get("version")) == str(release["version"]))
            )
        ]
        kept.append(release)
        data["releases"] = kept
        data["asOf"] = release.get("recordedAt") or data.get("asOf")
        return release

    return _mutate_snapshot(Path(board_path), mutator)


def list_releases(board_path: Path) -> list:
    html = Path(board_path).read_text(encoding="utf-8")
    _p, inner, _s = board_watch.split_snapshot(html)
    data = board_watch.load_snapshot_text(inner)
    return list(data.get("releases") or [])


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--board",
        default=os.environ.get("HB_BOARD_TASKS") or str(DEFAULT_BOARD),
        help="PROJECT-BOARD.html path",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("append", help="Append one release into snapshot.releases")
    a.add_argument("--version", required=True, help="SemVer without required v prefix")
    a.add_argument(
        "--artifact",
        action="append",
        default=[],
        metavar="PATH",
        help="Artifact path (repeatable); relative to repo root preferred",
    )
    a.add_argument(
        "--label",
        action="append",
        default=[],
        metavar="LABEL",
        help="Label per --artifact (repeatable; default MSI/artifact)",
    )
    a.add_argument("--report-path", default="", help="Path to release report markdown")
    a.add_argument("--kind", default="installer", choices=("installer", "portable"))
    a.add_argument("--by", default="agent", choices=("agent", "user"))
    a.add_argument("--id", default="", help="Release id (default v<version>)")
    a.add_argument("--released-at", default="", help="ISO timestamp (default now)")
    a.add_argument(
        "--no-embed-report",
        action="store_true",
        help="Store reportPath only; do not embed reportMd",
    )

    sub.add_parser("list", help="Print snapshot.releases as JSON")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    board = Path(args.board)
    if args.cmd == "list":
        print(json.dumps(list_releases(board), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "append":
        if not args.artifact:
            print("rejected: at least one --artifact required", file=sys.stderr)
            return 1
        ts = args.released_at or now_iso()
        arts = []
        for i, raw in enumerate(args.artifact):
            label = args.label[i] if i < len(args.label) else ("MSI" if raw.lower().endswith(".msi") else "成品")
            arts.append(build_artifact(Path(raw), label, ts, REPO))
        release = build_release(
            version=args.version,
            artifacts=arts,
            report_path=args.report_path or None,
            kind=args.kind,
            recorded_by=args.by,
            released_at=ts,
            release_id=args.id or None,
            embed_report_md=not args.no_embed_report,
            repo=REPO,
        )
        stored = append_release(board, release)
        print(
            "appended release v%s id=%s artifacts=%d reportPath=%s"
            % (
                stored.get("version"),
                stored.get("id"),
                len(stored.get("artifacts") or []),
                stored.get("reportPath") or "",
            )
        )
        return 0

    print("unknown command", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
