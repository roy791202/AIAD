"""Read-only report projection from SPEC/EVID-like JSON fixtures.

INV-REPORT / BDD-PD-REPORT-01:
  - Reads SPEC + EVID only
  - Writes HTML + markdown artifacts under out_dir
  - Never mutates SPEC/EVID inputs
  - Empty evidence → NOT RUN (never forge PASS)
  - HTML-escape untrusted text; offline (no CDN/fetch)
"""
from __future__ import annotations

import hashlib
import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ProjectResult:
    html_path: Path
    md_path: Path
    fingerprint: str
    evidence_status: str


def fingerprint_sources(spec_path: Path, evid_path: Path) -> str:
    """SHA-256 of SPEC then EVID bytes (source fingerprint for offline audit)."""
    h = hashlib.sha256()
    h.update(spec_path.read_bytes())
    h.update(b"\0")
    h.update(evid_path.read_bytes())
    return h.hexdigest()


def _load_json(path: Path) -> Mapping[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("%s must be a JSON object" % path)
    return data


def _evidence_status(evid: Mapping[str, Any]) -> str:
    results = evid.get("results")
    if not isinstance(results, list) or len(results) == 0:
        return "NOT RUN"
    statuses: Sequence[Any] = [r.get("status") for r in results if isinstance(r, dict)]
    if not statuses:
        return "NOT RUN"
    if all(s == "PASS" for s in statuses):
        return "PASS"
    if any(s in (None, "NOT RUN", "not_run", "skipped", "SKIPPED") for s in statuses):
        # mixed / pending → surface NOT RUN when any incomplete
        if all(s == "PASS" or s in (None, "NOT RUN", "not_run") for s in statuses) and not all(
            s == "PASS" for s in statuses
        ):
            return "NOT RUN"
    if any(s == "FAIL" for s in statuses):
        return "FAIL"
    # preserve first concrete status string; never invent PASS
    first = statuses[0]
    return str(first) if first is not None else "NOT RUN"


def _escape(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _render_html(spec: Mapping[str, Any], evid: Mapping[str, Any], fingerprint: str, status: str) -> str:
    results = evid.get("results") if isinstance(evid.get("results"), list) else []
    rows = []
    if not results:
        rows.append(
            "<tr><td colspan=\"3\"><strong>NOT RUN</strong> — no evidence results</td></tr>"
        )
    else:
        for r in results:
            if not isinstance(r, dict):
                continue
            rows.append(
                "<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
                % (
                    _escape(r.get("id")),
                    _escape(r.get("status") or "NOT RUN"),
                    _escape(r.get("observed_at")),
                )
            )
    return """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SGenAxis Report — %s</title>
<style>
body{font:15px/1.6 system-ui,sans-serif;margin:2rem;color:#172c39;background:#f2f5f7}
h1{font-size:1.6rem}table{border-collapse:collapse;width:100%%;background:#fff}
th,td{border:1px solid #dce4e9;padding:.5rem .75rem;text-align:left}
th{background:#eef4f5}.meta{color:#526876;font-size:.9rem}
code{background:#edf2f4;padding:2px 5px;border-radius:4px;overflow-wrap:anywhere}
.status{font-weight:700}
</style>
</head>
<body>
<header>
  <p class="meta">SGenAxis · PD-REPORT-01 · read-only projection</p>
  <h1>%s</h1>
  <p>%s</p>
</header>
<section>
  <h2>Source</h2>
  <ul>
    <li>Spec ID: <code>%s</code></li>
    <li>Spec version: <code>%s</code></li>
    <li>Spec status: <code>%s</code></li>
    <li>Evidence overall: <span class="status">%s</span></li>
    <li>Source fingerprint (SHA-256): <code>%s</code></li>
  </ul>
</section>
<section>
  <h2>Evidence</h2>
  <table>
    <thead><tr><th>ID</th><th>Status</th><th>Observed</th></tr></thead>
    <tbody>
%s
    </tbody>
  </table>
</section>
<footer class="meta"><p>Offline artifact · no CDN · does not write back SPEC/EVID</p></footer>
</body>
</html>
""" % (
        _escape(spec.get("id")),
        _escape(spec.get("title") or spec.get("id")),
        _escape(spec.get("summary")),
        _escape(spec.get("id")),
        _escape(spec.get("version")),
        _escape(spec.get("status")),
        _escape(status),
        _escape(fingerprint),
        "\n".join(rows),
    )


def _render_markdown(spec: Mapping[str, Any], evid: Mapping[str, Any], fingerprint: str, status: str) -> str:
    results = evid.get("results") if isinstance(evid.get("results"), list) else []
    lines = [
        "# Report — %s" % (spec.get("title") or spec.get("id")),
        "",
        "| Field | Value |",
        "|-------|-------|",
        "| Spec ID | `%s` |" % spec.get("id"),
        "| Spec version | `%s` |" % spec.get("version"),
        "| Spec status | `%s` |" % spec.get("status"),
        "| Evidence overall | **%s** |" % status,
        "| Source fingerprint | `%s` |" % fingerprint,
        "",
        "## Summary",
        "",
        str(spec.get("summary") or ""),
        "",
        "## Evidence results",
        "",
    ]
    if not results:
        lines.append("- **NOT RUN** — no evidence results")
    else:
        for r in results:
            if not isinstance(r, dict):
                continue
            st = r.get("status") or "NOT RUN"
            lines.append("- `%s`: **%s**" % (r.get("id"), st))
    lines.extend(["", "---", "", "_Read-only projection (PD-REPORT-01). Does not mutate SPEC/EVID._", ""])
    return "\n".join(lines)


def project_report(*, spec_path: Path, evid_path: Path, out_dir: Path) -> ProjectResult:
    """Project SPEC+EVID into HTML and markdown under out_dir. Never writes inputs."""
    spec_path = Path(spec_path)
    evid_path = Path(evid_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # read-only load
    spec = _load_json(spec_path)
    evid = _load_json(evid_path)
    fp = fingerprint_sources(spec_path, evid_path)
    status = _evidence_status(evid)

    html_path = out_dir / "report.html"
    md_path = out_dir / "report.md"
    html_path.write_text(_render_html(spec, evid, fp, status), encoding="utf-8")
    md_path.write_text(_render_markdown(spec, evid, fp, status), encoding="utf-8")

    return ProjectResult(
        html_path=html_path,
        md_path=md_path,
        fingerprint=fp,
        evidence_status=status,
    )
