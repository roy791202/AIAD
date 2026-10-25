"""PD-REPORT-UI-01 — UI call boundary into pd_report (read-only projection).

Host／Tauri invoke this module (via ``python -m pd_report`` or import) to
project SPEC+EVID. Never mutates SPEC／EVID. Empty evidence → NOT RUN.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .project import ProjectResult, project_report


def project_for_ui(
    *,
    spec_path: Path | str,
    evid_path: Path | str,
    out_dir: Path | str,
) -> Mapping[str, Any]:
    """Call boundary: project report and return a JSON-serialisable DTO.

    Guarantees:
      - ``write_back`` is always ``False`` (specs never written)
      - empty EVID results → ``evidence_status`` == ``NOT RUN``
    """
    spec_path = Path(spec_path)
    evid_path = Path(evid_path)
    out_dir = Path(out_dir)

    spec_before = spec_path.read_bytes()
    evid_before = evid_path.read_bytes()

    result: ProjectResult = project_report(
        spec_path=spec_path, evid_path=evid_path, out_dir=out_dir
    )

    if spec_path.read_bytes() != spec_before or evid_path.read_bytes() != evid_before:
        raise RuntimeError("pd_report call boundary mutated SPEC/EVID (forbidden)")

    return {
        "html_path": str(result.html_path),
        "md_path": str(result.md_path),
        "fingerprint": result.fingerprint,
        "evidence_status": result.evidence_status,
        "write_back": False,
        "html_body": result.html_path.read_text(encoding="utf-8"),
        "md_body": result.md_path.read_text(encoding="utf-8"),
    }


def project_for_ui_json(
    *,
    spec_path: Path | str,
    evid_path: Path | str,
    out_dir: Path | str,
) -> str:
    """Same as :func:`project_for_ui` but as a JSON string (stdout IPC)."""
    return json.dumps(
        project_for_ui(spec_path=spec_path, evid_path=evid_path, out_dir=out_dir),
        ensure_ascii=False,
    )
