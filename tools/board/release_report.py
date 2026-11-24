#!/usr/bin/env python3
"""Build one release record JSON (BDD-PD-RELEASE-REC-01, PD-BOARD-GAPS-RELEASE-01).

The board's single source of truth is docs/board.json; this tool never writes
any board file. ``build`` prints the release record to stdout or writes it to
``--out``. Callers write ``<report>.release.json`` next to their report.
No Firebase; no elevated install.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BOARD_DIR = Path(__file__).resolve().parent
REPO = BOARD_DIR.parents[1]
TAIPEI = timezone(timedelta(hours=8))
RELEASE_JSON_SUFFIX = ".release.json"


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
    """Build one release record (id / version / artifacts / reportPath ...)."""
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
                # Keep the record bounded; consumers fold full markdown.
                release["reportMd"] = text if len(text) <= 80_000 else text[:80_000] + "\n\n…(truncated)…"
    return release


def release_json_path(report_path: Path) -> Path:
    """``reports/x.md`` -> ``reports/x.release.json`` (same folder as the report)."""
    report = Path(report_path)
    return report.with_name(report.stem + RELEASE_JSON_SUFFIX)


def release_json_text(release: dict) -> str:
    return json.dumps(release, ensure_ascii=False, indent=2) + "\n"


def write_release_json(release: dict, out_path: Path) -> Path:
    """Write one release record JSON file; creates parent folders."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(release_json_text(release), encoding="utf-8", newline="\n")
    return out


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="Build one release record JSON (stdout or --out)")
    b.add_argument("--version", required=True, help="SemVer without required v prefix")
    b.add_argument(
        "--artifact",
        action="append",
        default=[],
        metavar="PATH",
        help="Artifact path (repeatable); relative to repo root preferred",
    )
    b.add_argument(
        "--label",
        action="append",
        default=[],
        metavar="LABEL",
        help="Label per --artifact (repeatable; default MSI/artifact)",
    )
    b.add_argument("--report-path", default="", help="Path to release report markdown")
    b.add_argument("--kind", default="installer", choices=("installer", "portable"))
    b.add_argument("--by", default="agent", choices=("agent", "user"))
    b.add_argument("--id", default="", help="Release id (default v<version>)")
    b.add_argument("--released-at", default="", help="ISO timestamp (default now)")
    b.add_argument(
        "--no-embed-report",
        action="store_true",
        help="Store reportPath only; do not embed reportMd",
    )
    b.add_argument("--out", default="", help="Write the release JSON here instead of stdout")
    return ap


def _default_label(raw_path: str) -> str:
    return "MSI" if raw_path.lower().endswith(".msi") else "成品"


def _release_from_args(args: argparse.Namespace) -> dict:
    ts = args.released_at or now_iso()
    artifacts = [
        build_artifact(
            Path(raw),
            args.label[i] if i < len(args.label) else _default_label(raw),
            ts,
            REPO,
        )
        for i, raw in enumerate(args.artifact)
    ]
    return build_release(
        version=args.version,
        artifacts=artifacts,
        report_path=args.report_path or None,
        kind=args.kind,
        recorded_by=args.by,
        released_at=ts,
        release_id=args.id or None,
        embed_report_md=not args.no_embed_report,
        repo=REPO,
    )


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not args.artifact:
        print("rejected: at least one --artifact required", file=sys.stderr)
        return 1
    release = _release_from_args(args)
    if args.out:
        out = write_release_json(release, Path(args.out))
        print("wrote release v%s id=%s to %s" % (release["version"], release["id"], out), file=sys.stderr)
        return 0
    sys.stdout.write(release_json_text(release))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
