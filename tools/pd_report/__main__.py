"""CLI: python -m pd_report --spec PATH --evid PATH --out DIR [--json]

PD-REPORT-UI-01: ``--json`` emits the UI call-boundary DTO (stdout).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .project import project_report
from .ui_call import project_for_ui


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="PD-REPORT-01/UI-01: read-only SPEC/EVID → HTML + markdown (never writes specs)."
    )
    ap.add_argument("--spec", required=True, type=Path, help="SPEC JSON path (read-only)")
    ap.add_argument("--evid", required=True, type=Path, help="EVID JSON path (read-only)")
    ap.add_argument("--out", required=True, type=Path, help="Output directory for report artifacts")
    ap.add_argument(
        "--json",
        action="store_true",
        help="PD-REPORT-UI-01: print call-boundary DTO as JSON (write_back=false)",
    )
    args = ap.parse_args(argv)
    if args.json:
        import json

        dto = project_for_ui(spec_path=args.spec, evid_path=args.evid, out_dir=args.out)
        # Omit large bodies from stdout IPC unless needed — keep paths + status.
        slim = {
            "html_path": dto["html_path"],
            "md_path": dto["md_path"],
            "fingerprint": dto["fingerprint"],
            "evidence_status": dto["evidence_status"],
            "write_back": False,
        }
        print(json.dumps(slim, ensure_ascii=False))
        return 0

    result = project_report(spec_path=args.spec, evid_path=args.evid, out_dir=args.out)
    print("wrote %s" % result.html_path)
    print("wrote %s" % result.md_path)
    print("fingerprint %s" % result.fingerprint)
    print("evidence_status %s" % result.evidence_status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
