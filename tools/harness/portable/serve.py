# -*- coding: utf-8 -*-
"""Portable no-MSI UI server (PD-HARNESS-PORTABLE-01).

Serves apps/sgenaxis-desktop/ui with mock Tauri bridge injected before app.js.
Also mounts Workbench HTML for side-by-side IA对照.

  python tools/harness/portable/serve.py
  python tools/harness/portable/serve.py --port 28790 --stress 500

Open http://127.0.0.1:28790/  (UI+mock)
     http://127.0.0.1:28790/workbench/  (git_workbench_interactive.html)
"""
from __future__ import annotations

import argparse
import functools
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
UI = ROOT / "apps" / "sgenaxis-desktop" / "ui"
HARNESS = Path(__file__).resolve().parent
WORKBENCH = ROOT / "git_workbench_interactive.html"
DEFAULT_PORT = 28790  # not 8788 / 28789 board


class HarnessHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, stress: int = 0, **kwargs):
        self.stress = stress
        super().__init__(*args, **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[harness] " + (fmt % args) + "\n")

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send_injected_index()
            return
        if path.startswith("/harness/"):
            rel = path[len("/harness/") :]
            target = (HARNESS / rel).resolve()
            if not str(target).startswith(str(HARNESS.resolve())):
                self.send_error(403)
                return
            return self._send_file(target, self._guess(target))
        if path in ("/workbench", "/workbench/"):
            return self._send_file(WORKBENCH, "text/html; charset=utf-8")
        # UI static
        rel = path.lstrip("/")
        target = (UI / rel).resolve()
        if not str(target).startswith(str(UI.resolve())):
            self.send_error(403)
            return
        if not target.is_file():
            self.send_error(404)
            return
        return self._send_file(target, self._guess(target))

    def _guess(self, p: Path) -> str:
        if p.suffix == ".js":
            return "application/javascript; charset=utf-8"
        if p.suffix == ".css":
            return "text/css; charset=utf-8"
        if p.suffix == ".html":
            return "text/html; charset=utf-8"
        if p.suffix == ".svg":
            return "image/svg+xml"
        return "application/octet-stream"

    def _send_file(self, target: Path, ctype: str) -> None:
        if not target.is_file():
            self.send_error(404)
            return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_injected_index(self) -> None:
        html = (UI / "index.html").read_text(encoding="utf-8")
        q = f"?stress={self.stress}" if self.stress else ""
        inject = (
            f'  <script>window.__SGENAXIS_HARNESS_BOOT__={{stress:{self.stress}}};</script>\n'
            f'  <script src="/harness/mock_tauri_bridge.js{q}"></script>\n'
            f'  <script src="app.js" defer></script>'
        )
        if '<script src="app.js" defer></script>' in html:
            html = html.replace('<script src="app.js" defer></script>', inject)
        else:
            html = html.replace("</body>", inject + "\n</body>")
        banner = (
            '<div id="harness-banner" style="position:sticky;top:0;z-index:9999;'
            "background:#252117;color:#f2b544;border-bottom:1px solid #5b4b29;"
            'padding:6px 12px;font:12px/1.4 Segoe UI,Microsoft JhengHei,sans-serif">'
            "PORTABLE HARNESS · mock IPC · 假資料≠產品證據 · "
            f"stress={self.stress} · "
            '<a href="/workbench/" style="color:#8bb8ff">對照 Workbench</a> · '
            '<a href="/harness/checklist-workbench.md" style="color:#8bb8ff">驗證清單</a>'
            "</div>"
        )
        if "<body>" in html:
            html = html.replace("<body>", "<body>\n" + banner, 1)
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    ap = argparse.ArgumentParser(description="SGenAxis portable harness server")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--stress", type=int, default=0, help="fake task count for mock board")
    ap.add_argument("--bind", default="127.0.0.1")
    args = ap.parse_args()
    if not UI.is_dir():
        print("FAIL: UI dir missing:", UI, file=sys.stderr)
        return 2
    if not (HARNESS / "mock_tauri_bridge.js").is_file():
        print("FAIL: mock bridge missing", file=sys.stderr)
        return 2
    handler = functools.partial(HarnessHandler, stress=args.stress)
    # directory unused; we override GET
    httpd = ThreadingHTTPServer((args.bind, args.port), handler)
    url = f"http://{args.bind}:{args.port}/"
    if args.stress:
        url += f"?stress={args.stress}"
    print("SGenAxis portable harness (no MSI)")
    print("  UI+mock :", url)
    print("  Workbench:", f"http://{args.bind}:{args.port}/workbench/")
    print("  Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
