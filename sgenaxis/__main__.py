"""python -m sgenaxis            start the workbench
python -m sgenaxis report ...  report a dispatched card (see report_cli)"""

import sys

from sgenaxis.app import main
from sgenaxis.report_cli import report_main

if __name__ == "__main__":
    if sys.argv[1:2] == ["report"]:
        raise SystemExit(report_main(sys.argv[2:]))
    raise SystemExit(main())
