# -*- coding: utf-8 -*-
"""PD-OPEN-*: launch portable harness + stress hard-gate evidence.

Must open the program (HTTP UI) and run fake-data stress; writes evidence JSON
under reports/dispatch-pd/. Without ok=true, TDD must FAIL.

  python tools/harness/portable/open_stress_gate.py
  python tools/harness/portable/open_stress_gate.py --stress 500 --open-browser
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HARNESS = Path(__file__).resolve().parent
REPORTS = ROOT / "reports" / "dispatch-pd"
DEFAULT_PORT = 28790
TZ8 = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TZ8).strftime("%Y-%m-%dT%H:%M:%S%z")


def http_get(url: str, timeout: float = 8.0) -> tuple[int, int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "SGenAxis-OpenStressGate/1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        return int(resp.status), len(body), body[:200].decode("utf-8", errors="replace")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--stress", type=int, default=500)
    ap.add_argument("--open-browser", action="store_true", default=True)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--hold-sec", type=float, default=2.0)
    args = ap.parse_args()
    if args.no_browser:
        args.open_browser = False
    if args.stress < 1 or args.stress > 50000:
        print("stress out of range", file=sys.stderr)
        return 2

    # Generate fake board artifact used by stress path
    stress_out = HARNESS / "out" / "stress-board.json"
    gen = subprocess.run(
        [sys.executable, str(HARNESS / "stress_gen.py"), "-n", str(args.stress), "-o", str(stress_out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if gen.returncode != 0:
        print(gen.stderr or gen.stdout, file=sys.stderr)
        return gen.returncode or 1

    serve_cmd = [
        sys.executable,
        str(HARNESS / "serve.py"),
        "--port",
        str(args.port),
        "--stress",
        str(args.stress),
    ]
    proc = subprocess.Popen(
        serve_cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base = f"http://127.0.0.1:{args.port}"
    t0 = time.perf_counter()
    opened = False
    fetches: list[dict] = []
    ok = False
    err: str | None = None
    try:
        # wait until listening
        for _ in range(40):
            try:
                st, nbytes, _snip = http_get(base + "/")
                if st == 200 and nbytes > 500:
                    opened = True
                    break
            except (urllib.error.URLError, TimeoutError, OSError):
                time.sleep(0.15)
        if not opened:
            err = "server did not become ready"
        else:
            if args.open_browser:
                webbrowser.open(base + f"/?stress={args.stress}")
            paths = [
                "/",
                f"/?stress={args.stress}",
                "/workbench/",
                "/harness/mock_tauri_bridge.js",
                "/harness/checklist-workbench.md",
                "/app.js",
            ]
            for p in paths:
                try:
                    st, nbytes, snip = http_get(base + p)
                    fetches.append(
                        {
                            "path": p,
                            "status": st,
                            "bytes": nbytes,
                            "ok": st == 200 and nbytes > 0,
                            "snip": snip[:80],
                        }
                    )
                except Exception as e:  # noqa: BLE001
                    fetches.append({"path": p, "ok": False, "error": str(e)})
            time.sleep(max(0.0, args.hold_sec))
            stress_bytes = stress_out.stat().st_size if stress_out.is_file() else 0
            all_fetch_ok = all(f.get("ok") for f in fetches) and len(fetches) >= 4
            ok = opened and all_fetch_ok and stress_bytes > 1000 and gen.returncode == 0
            if not ok and err is None:
                err = "fetch or stress artifact failed"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    duration_ms = int((time.perf_counter() - t0) * 1000)
    ts = now_iso()

    launch = {
        "card": "PD-OPEN-LAUNCH-01",
        "opened": opened,
        "ok": opened,
        "base_url": base,
        "port": args.port,
        "browser_opened": bool(args.open_browser and opened),
        "pid": proc.pid,
        "at": ts,
        "message": "portable harness UI served" if opened else (err or "not opened"),
        "product_pass": False,
        "note": "harness open ≠ product GA PASS",
    }
    func = {
        "card": "PD-OPEN-FUNC-01",
        "ok": ok and opened,
        "depends_on_launch": True,
        "checks": [
            {"id": "ui_index", "ok": any(f.get("path") == "/" and f.get("ok") for f in fetches)},
            {
                "id": "workbench",
                "ok": any(f.get("path") == "/workbench/" and f.get("ok") for f in fetches),
            },
            {
                "id": "mock_bridge",
                "ok": any(
                    f.get("path") == "/harness/mock_tauri_bridge.js" and f.get("ok")
                    for f in fetches
                ),
            },
            {
                "id": "checklist",
                "ok": any(
                    f.get("path") == "/harness/checklist-workbench.md" and f.get("ok")
                    for f in fetches
                ),
            },
            {
                "id": "file_new_wired",
                "ok": "host_create_project_directory"
                in (ROOT / "apps/sgenaxis-desktop/ui/app.js").read_text(encoding="utf-8"),
            },
        ],
        "fetches": fetches,
        "at": ts,
        "product_pass": False,
    }
    func["ok"] = opened and all(c["ok"] for c in func["checks"])

    stress = {
        "card": "PD-OPEN-STRESS-GATE-01",
        "ok": bool(ok and opened and func["ok"]),
        "opened_program": opened,
        "n": args.stress,
        "duration_ms": duration_ms,
        "stress_board": str(stress_out.relative_to(ROOT)).replace("\\", "/"),
        "stress_board_bytes": stress_out.stat().st_size if stress_out.is_file() else 0,
        "fetches_ok": all(f.get("ok") for f in fetches),
        "at": ts,
        "error": err,
        "product_pass": False,
        "hard_gate": True,
        "note": "ok=true required for TDD_PASS; fake data ≠ product PASS",
    }
    # Hard rule: stress gate fails if program not opened
    if not opened:
        stress["ok"] = False
        stress["error"] = err or "program not opened"

    write_json(REPORTS / "PD-OPEN-LAUNCH-01-evidence.json", launch)
    write_json(REPORTS / "PD-OPEN-FUNC-01-evidence.json", func)
    write_json(REPORTS / "PD-OPEN-STRESS-GATE-01-evidence.json", stress)

    print(json.dumps({"launch": launch["ok"], "func": func["ok"], "stress": stress["ok"]}, ensure_ascii=False))
    return 0 if stress["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
