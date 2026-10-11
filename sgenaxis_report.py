"""Report command entry that works from any folder: python <this file> --outcome done --note "..."."""

from sgenaxis.report_cli import report_main

if __name__ == "__main__":
    raise SystemExit(report_main())
