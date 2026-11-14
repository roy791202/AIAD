#!/usr/bin/env python3
"""Cross-platform PackSpec / artifact contract (BDD-PD-M4-PACK-SPEC-01).

Defines pack artifact fields: os / arch / path / sha256 / status.
status ∈ PASS | FAIL | BLOCKED | NOT RUN | PARTIAL (same vocabulary as Build Result).

Hooks:
  - ``to_build_result_artifacts`` / ``apply_to_build_result`` → PD-BUILD-RESULT-01
  - ``to_release_artifacts`` → PD-RELEASE-REC-01 (#release / snapshot.releases)

No forced real pack PASS: missing / non-host OS rows stay NOT RUN or BLOCKED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

BOARD_DIR = Path(__file__).resolve().parent
REPO = BOARD_DIR.parents[1]

if str(BOARD_DIR) not in sys.path:
    sys.path.insert(0, str(BOARD_DIR))

import build_result as br  # noqa: E402
import release_report  # noqa: E402

TAIPEI = timezone(timedelta(hours=8))

SCHEMA_ID = "aiad.pack-spec.v1"
CARD_ID = "PD-M4-PACK-SPEC-01"
BDD_ID = "BDD-PD-M4-PACK-SPEC-01"

VALID_STATUSES = br.VALID_STATUSES
VALID_OS: tuple[str, ...] = ("windows", "macos", "linux")
VALID_ARCH: tuple[str, ...] = ("x64", "arm64", "x86", "universal")

_OS_ALIASES = {
    "windows": "windows",
    "win": "windows",
    "win32": "windows",
    "win64": "windows",
    "macos": "macos",
    "mac": "macos",
    "darwin": "macos",
    "osx": "macos",
    "linux": "linux",
}

_ARCH_ALIASES = {
    "x64": "x64",
    "amd64": "x64",
    "x86_64": "x64",
    "x86-64": "x64",
    "arm64": "arm64",
    "aarch64": "arm64",
    "arm": "arm64",
    "x86": "x86",
    "i386": "x86",
    "ia32": "x86",
    "universal": "universal",
    "uni": "universal",
    "fat": "universal",
}

REQUIRED_ARTIFACT_FIELDS: tuple[str, ...] = ("os", "arch", "path", "sha256", "status")


class PackSpecError(ValueError):
    """Invalid PackSpec field or status."""


def now_iso() -> str:
    return datetime.now(TAIPEI).isoformat(timespec="seconds")


def normalize_status(raw: Any) -> str:
    """Reuse Build Result vocabulary (PASS|FAIL|BLOCKED|NOT RUN|PARTIAL)."""
    try:
        return br.normalize_status(raw)
    except br.BuildResultError as exc:
        raise PackSpecError(str(exc)) from exc


def normalize_os(raw: Any) -> str:
    if raw is None:
        raise PackSpecError("os is required")
    key = str(raw).strip().lower().replace("_", "")
    out = _OS_ALIASES.get(key) or _OS_ALIASES.get(str(raw).strip().lower())
    if out is None or out not in VALID_OS:
        raise PackSpecError(
            "illegal os %r (allowed: %s)" % (raw, " | ".join(VALID_OS))
        )
    return out


def normalize_arch(raw: Any) -> str:
    if raw is None:
        raise PackSpecError("arch is required")
    key = str(raw).strip().lower().replace(" ", "")
    out = _ARCH_ALIASES.get(key)
    if out is None or out not in VALID_ARCH:
        raise PackSpecError(
            "illegal arch %r (allowed: %s)" % (raw, " | ".join(VALID_ARCH))
        )
    return out


def normalize_path(raw: Any) -> str:
    if raw is None:
        raise PackSpecError("path is required")
    s = str(raw).strip().replace("\\", "/")
    if not s:
        raise PackSpecError("path is empty")
    return s


def normalize_sha256(raw: Any, *, allow_empty: bool = True) -> str:
    """Normalize sha256 hex; empty allowed when file missing / NOT RUN."""
    if raw is None:
        if allow_empty:
            return ""
        raise PackSpecError("sha256 is required")
    s = str(raw).strip().lower()
    if not s:
        if allow_empty:
            return ""
        raise PackSpecError("sha256 is empty")
    if s.startswith("sha256:"):
        s = s[7:].strip()
    if len(s) != 64 or any(c not in "0123456789abcdef" for c in s):
        raise PackSpecError("sha256 must be 64 hex chars, got %r" % raw)
    return s


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_pack_artifact(
    *,
    os: Any,
    arch: Any,
    path: Any,
    status: Any = "NOT RUN",
    sha256: Any = "",
    label: str = "",
    format: str = "",
    notes: str = "",
    exists: bool | None = None,
    bytes: int | None = None,
) -> dict:
    """Build one PackSpec artifact row (os / arch / path / sha256 / status)."""
    row: dict[str, Any] = {
        "os": normalize_os(os),
        "arch": normalize_arch(arch),
        "path": normalize_path(path),
        "sha256": normalize_sha256(sha256, allow_empty=True),
        "status": normalize_status(status),
    }
    if label:
        row["label"] = str(label).strip()
    if format:
        row["format"] = str(format).strip()
    if notes:
        row["notes"] = str(notes).strip()
    if exists is not None:
        row["exists"] = bool(exists)
    if bytes is not None:
        row["bytes"] = int(bytes)
    return row


def validate_pack_artifact(row: Mapping[str, Any]) -> dict:
    """Validate and normalize one artifact; returns a clean dict."""
    if not isinstance(row, Mapping):
        raise PackSpecError("artifact must be a mapping")
    for key in REQUIRED_ARTIFACT_FIELDS:
        if key not in row:
            raise PackSpecError("artifact missing required field %r" % key)
    return build_pack_artifact(
        os=row["os"],
        arch=row["arch"],
        path=row["path"],
        sha256=row.get("sha256", ""),
        status=row["status"],
        label=str(row.get("label") or ""),
        format=str(row.get("format") or ""),
        notes=str(row.get("notes") or ""),
        exists=row.get("exists") if "exists" in row else None,
        bytes=row.get("bytes") if "bytes" in row else None,
    )


def validate_pack_spec(spec: Mapping[str, Any]) -> dict:
    """Validate a PackSpec document; returns a normalized copy."""
    if not isinstance(spec, Mapping):
        raise PackSpecError("pack spec must be a mapping")
    schema = str(spec.get("schema") or SCHEMA_ID).strip()
    if schema != SCHEMA_ID:
        raise PackSpecError("unsupported schema %r (expected %s)" % (schema, SCHEMA_ID))
    arts_in = spec.get("artifacts")
    if not isinstance(arts_in, list):
        raise PackSpecError("artifacts must be a list")
    arts = [validate_pack_artifact(a) for a in arts_in]
    out: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "cardId": str(spec.get("cardId") or CARD_ID),
        "bdd": str(spec.get("bdd") or BDD_ID),
        "version": str(spec.get("version") or "").strip().lstrip("v") or "0.0.0",
        "product": str(spec.get("product") or "SGenAxis"),
        "generatedAt": str(spec.get("generatedAt") or now_iso()),
        "artifacts": arts,
        "status": normalize_status(
            spec["status"] if "status" in spec else br.rollup_status(a["status"] for a in arts)
        ),
    }
    if spec.get("notes"):
        out["notes"] = str(spec["notes"])
    return out


def resolve_artifact_file(
    row: Mapping[str, Any],
    *,
    repo: Path | None = None,
    status_if_missing: str = "NOT RUN",
    compute_sha_if_present: bool = True,
) -> dict:
    """Fill exists/bytes/sha256 from disk; never forge PASS when missing."""
    root = repo or REPO
    base = validate_pack_artifact(row)
    rel = Path(base["path"])
    abs_path = rel if rel.is_absolute() else (root / rel)
    exists = abs_path.is_file()
    base["exists"] = exists
    if exists:
        base["bytes"] = abs_path.stat().st_size
        if compute_sha_if_present:
            digest = _sha256_file(abs_path)
            declared = base.get("sha256") or ""
            if declared and declared != digest:
                base["status"] = normalize_status("FAIL")
                base["notes"] = (
                    (base.get("notes") or "")
                    + ("; " if base.get("notes") else "")
                    + "sha256 mismatch (declared≠file)"
                ).strip("; ")
            else:
                base["sha256"] = digest
        # Do not upgrade status to PASS merely because the file exists.
    else:
        base["sha256"] = base.get("sha256") or ""
        # Missing file: keep FAIL/BLOCKED if already set; otherwise status_if_missing.
        if base["status"] in ("PASS", "PARTIAL"):
            base["status"] = normalize_status(status_if_missing)
            note = "path missing - cannot claim %s" % row.get("status", "PASS")
            base["notes"] = (
                (base.get("notes") or "") + ("; " if base.get("notes") else "") + note
            ).strip("; ")
        elif base["status"] not in ("FAIL", "BLOCKED", "NOT RUN"):
            base["status"] = normalize_status(status_if_missing)
    return base


def default_matrix_v010(*, generated_at: str | None = None) -> dict:
    """Canonical mac|linux|win PackSpec for v0.1.0 (no forged cross-OS PASS)."""
    ts = generated_at or now_iso()
    win = build_pack_artifact(
        os="windows",
        arch="x64",
        path="packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi",
        sha256="",
        status="PARTIAL",
        label="MSI",
        format="msi",
        notes="WiX MSI; elevated VERIFY-INSTALL may be NOT RUN",
    )
    mac = build_pack_artifact(
        os="macos",
        arch="universal",
        path="packaging/macos/out/SGenAxis-0.1.0-macos-universal.dmg",
        sha256="",
        status="NOT RUN",
        label="DMG",
        format="dmg",
        notes="M4 stub path - no real pack required this card",
    )
    linux = build_pack_artifact(
        os="linux",
        arch="x64",
        path="packaging/linux/out/SGenAxis-0.1.0-linux-x64.AppImage",
        sha256="",
        status="NOT RUN",
        label="AppImage",
        format="AppImage",
        notes="M4 stub path - no real pack required this card",
    )
    return validate_pack_spec(
        {
            "schema": SCHEMA_ID,
            "cardId": CARD_ID,
            "bdd": BDD_ID,
            "version": "0.1.0",
            "product": "SGenAxis",
            "generatedAt": ts,
            "artifacts": [win, mac, linux],
            "notes": (
                "Cross-platform PackSpec contract. Real pack PASS is not required; "
                "mac/linux stay NOT RUN until stub/real packs land."
            ),
        }
    )


def load_pack_spec(path: Path, *, resolve_files: bool = False, repo: Path | None = None) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    spec = validate_pack_spec(data)
    if resolve_files:
        root = repo or REPO
        spec["artifacts"] = [
            resolve_artifact_file(a, repo=root) for a in spec["artifacts"]
        ]
        spec["status"] = br.rollup_status(a["status"] for a in spec["artifacts"])
    return spec


def write_pack_spec(spec: Mapping[str, Any], path: Path) -> Path:
    clean = validate_pack_spec(spec)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(clean, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def to_build_result_artifacts(artifacts: Sequence[Mapping[str, Any]]) -> list[dict]:
    """Map PackSpec rows → Build Result / release_report artifact shape."""
    out: list[dict] = []
    for raw in artifacts:
        a = validate_pack_artifact(raw)
        label = a.get("label") or ("%s-%s" % (a["os"], a["arch"]))
        row: dict[str, Any] = {
            "label": label,
            "path": a["path"],
            "os": a["os"],
            "arch": a["arch"],
            "sha256": a.get("sha256") or "",
            "packStatus": a["status"],
        }
        if "exists" in a:
            row["exists"] = a["exists"]
        if "bytes" in a:
            row["bytes"] = a["bytes"]
            row["sizeText"] = release_report.size_text(int(a["bytes"]))
        if a.get("format"):
            row["format"] = a["format"]
        if a.get("notes"):
            row["notes"] = a["notes"]
        out.append(row)
    return out


def to_release_artifacts(
    artifacts: Sequence[Mapping[str, Any]],
    *,
    checked_at: str | None = None,
    repo: Path | None = None,
    only_existing: bool = False,
) -> list[dict]:
    """Map PackSpec → release_report.build_artifact rows (for snapshot.releases)."""
    root = repo or REPO
    ts = checked_at or now_iso()
    out: list[dict] = []
    for raw in artifacts:
        a = validate_pack_artifact(raw)
        if only_existing:
            p = Path(a["path"])
            abs_p = p if p.is_absolute() else (root / p)
            if not abs_p.is_file():
                continue
        label = a.get("label") or ("%s-%s" % (a["os"], a["arch"]))
        art = release_report.build_artifact(Path(a["path"]), label, ts, root)
        art["os"] = a["os"]
        art["arch"] = a["arch"]
        art["packStatus"] = a["status"]
        if a.get("sha256") and not art.get("sha256"):
            art["sha256"] = a["sha256"]
        out.append(art)
    return out


def to_target_matrix(artifacts: Sequence[Mapping[str, Any]]) -> list[dict]:
    """PackSpec → Build Result targetMatrix rows."""
    rows: list[dict] = []
    for raw in artifacts:
        a = validate_pack_artifact(raw)
        rows.append(
            {
                "target": "%s-%s" % (a["os"], a["arch"]),
                "os": a["os"],
                "arch": a["arch"],
                "status": a["status"],
                "notes": a.get("notes") or a.get("path") or "",
            }
        )
    return rows


def apply_to_build_result(
    result: MutableMapping[str, Any],
    pack_spec: Mapping[str, Any],
    *,
    merge_artifacts: bool = True,
    set_target_matrix: bool = True,
) -> MutableMapping[str, Any]:
    """Hang PackSpec into an existing Build Result (artifacts + targetMatrix + trace)."""
    spec = validate_pack_spec(pack_spec)
    pack_arts = to_build_result_artifacts(spec["artifacts"])
    if merge_artifacts:
        existing = list(result.get("artifacts") or [])
        # Prefer PackSpec rows; keep prior labels not covered by pack paths.
        pack_paths = {a["path"] for a in pack_arts}
        kept = [a for a in existing if a.get("path") not in pack_paths]
        result["artifacts"] = kept + pack_arts
    else:
        result["artifacts"] = pack_arts
    if set_target_matrix:
        result["targetMatrix"] = to_target_matrix(spec["artifacts"])
    traces = list(result.get("requirementTraceability") or [])
    for tid in (BDD_ID, CARD_ID):
        if tid not in traces:
            traces.append(tid)
    result["requirementTraceability"] = traces
    result["packSpec"] = {
        "schema": SCHEMA_ID,
        "status": spec["status"],
        "version": spec.get("version"),
        "artifactCount": len(spec["artifacts"]),
    }
    # Roll overall with pack statuses (worst-wins); never invent PASS.
    result["status"] = br.rollup_status(
        [result.get("status") or "NOT RUN", spec["status"]]
        + [a["status"] for a in spec["artifacts"]]
    )
    return result


def hang_pack_spec_to_release(
    board_path: Path,
    pack_spec: Mapping[str, Any],
    *,
    report_path: str | None = None,
    kind: str = "installer",
    recorded_by: str = "agent",
    repo: Path | None = None,
) -> dict:
    """Append a release row whose artifacts come from PackSpec (via release_report)."""
    root = repo or REPO
    spec = validate_pack_spec(pack_spec)
    arts = to_release_artifacts(spec["artifacts"], repo=root, only_existing=False)
    release = release_report.build_release(
        version=str(spec.get("version") or "0.0.0"),
        artifacts=arts,
        report_path=report_path,
        kind=kind,
        recorded_by=recorded_by,
        repo=root,
    )
    release["packSpecStatus"] = spec["status"]
    release["packSpecSchema"] = SCHEMA_ID
    return release_report.append_release(Path(board_path), release)


def schema_document() -> dict:
    """JSON Schema (draft-07-ish) for PackSpec artifacts."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://aiad.local/schemas/pack-spec.v1.json",
        "title": "AIAD PackSpec v1",
        "description": (
            "Cross-platform pack artifact contract (BDD-PD-M4-PACK-SPEC-01). "
            "Required artifact fields: os, arch, path, sha256, status."
        ),
        "type": "object",
        "required": ["schema", "artifacts"],
        "properties": {
            "schema": {"const": SCHEMA_ID},
            "cardId": {"type": "string"},
            "bdd": {"type": "string"},
            "version": {"type": "string"},
            "product": {"type": "string"},
            "generatedAt": {"type": "string"},
            "status": {"enum": list(VALID_STATUSES)},
            "notes": {"type": "string"},
            "artifacts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": list(REQUIRED_ARTIFACT_FIELDS),
                    "properties": {
                        "os": {"enum": list(VALID_OS)},
                        "arch": {"enum": list(VALID_ARCH)},
                        "path": {"type": "string", "minLength": 1},
                        "sha256": {
                            "type": "string",
                            "description": "64 hex chars, or empty when NOT RUN / missing",
                        },
                        "status": {"enum": list(VALID_STATUSES)},
                        "label": {"type": "string"},
                        "format": {"type": "string"},
                        "notes": {"type": "string"},
                        "exists": {"type": "boolean"},
                        "bytes": {"type": "integer", "minimum": 0},
                    },
                    "additionalProperties": True,
                },
            },
        },
        "additionalProperties": True,
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Write default v0.1.0 PackSpec JSON")
    g.add_argument(
        "--out",
        default=str(REPO / "packaging" / "pack-spec.v1.json"),
        help="Output PackSpec JSON path",
    )
    g.add_argument(
        "--resolve",
        action="store_true",
        help="Resolve paths on disk (sha256 / exists); never forge PASS",
    )

    v = sub.add_parser("validate", help="Validate a PackSpec JSON file")
    v.add_argument("path")

    s = sub.add_parser("schema", help="Print JSON Schema to stdout or --out")
    s.add_argument("--out", default="", help="Optional schema file path")

    h = sub.add_parser(
        "hang-demo",
        help="Demo: apply PackSpec onto a Build Result candidate (stdout JSON summary)",
    )
    h.add_argument(
        "--pack",
        default=str(REPO / "packaging" / "pack-spec.v1.json"),
        help="PackSpec JSON",
    )

    args = ap.parse_args(list(argv) if argv is not None else None)

    if args.cmd == "generate":
        spec = default_matrix_v010()
        if args.resolve:
            spec["artifacts"] = [
                resolve_artifact_file(a, repo=REPO) for a in spec["artifacts"]
            ]
            spec["status"] = br.rollup_status(a["status"] for a in spec["artifacts"])
        path = write_pack_spec(spec, Path(args.out))
        print(
            "wrote %s status=%s artifacts=%d"
            % (path, spec["status"], len(spec["artifacts"]))
        )
        return 0

    if args.cmd == "validate":
        spec = load_pack_spec(Path(args.path))
        print(
            "ok schema=%s status=%s artifacts=%d"
            % (spec["schema"], spec["status"], len(spec["artifacts"]))
        )
        return 0

    if args.cmd == "schema":
        doc = schema_document()
        text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8", newline="\n")
            print("wrote %s" % out)
        else:
            sys.stdout.write(text)
        return 0

    if args.cmd == "hang-demo":
        pack_path = Path(args.pack)
        if pack_path.is_file():
            spec = load_pack_spec(pack_path, resolve_files=True, repo=REPO)
        else:
            spec = default_matrix_v010()
            spec["artifacts"] = [
                resolve_artifact_file(a, repo=REPO) for a in spec["artifacts"]
            ]
            spec["status"] = br.rollup_status(a["status"] for a in spec["artifacts"])
        result = br.candidate_v010_from_packaging(repo=REPO)
        apply_to_build_result(result, spec)
        summary = {
            "buildResultStatus": result["status"],
            "packSpecStatus": result.get("packSpec", {}).get("status"),
            "artifacts": len(result.get("artifacts") or []),
            "targetMatrix": result.get("targetMatrix"),
            "requirementTraceability": result.get("requirementTraceability"),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    raise PackSpecError("unknown command")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PackSpecError as exc:
        print("rejected: %s" % exc, file=sys.stderr)
        raise SystemExit(1)
