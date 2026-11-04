"""PD-MCP-LIVE-SMOKE-01 — Live MCP connect／tool smoke (or NOT RUN).

BDD-PD-MCP-LIVE-SMOKE-01: under approval, run one Live connect／tool／stream
reconcile against an explicit local MCP endpoint from env, or record a clear
skip. Secrets must not appear in settings projection. Never claim DryRun as
Live PASS. No cloud gateway; no forced paid service.

Allow-scope: exec／adapters／tests／scripts／reports.
Env gate: SGENAXIS_MCP_LIVE_ENDPOINT (empty／:8788／:8787 → NOT RUN).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "apps" / "sgenaxis-desktop"
EXEC_DIR = DESKTOP / "crates" / "sgenaxis-exec"
EXEC_MANIFEST = EXEC_DIR / "Cargo.toml"
PROBE_RS = EXEC_DIR / "src" / "mcp_live_target.rs"
SMOKE_RS = EXEC_DIR / "tests" / "live_mcp_smoke.rs"

ENV_ENDPOINT = "SGENAXIS_MCP_LIVE_ENDPOINT"
FILTER = "live_mcp_smoke_connect_tool_or_skip"


def _cargo_bin() -> str:
    home = Path.home() / ".cargo" / "bin" / ("cargo.exe" if os.name == "nt" else "cargo")
    if home.is_file():
        return str(home)
    return "cargo"


def _probe_endpoint() -> Optional[str]:
    """Return env endpoint if present and activatable; else None (NOT RUN)."""
    raw = (os.environ.get(ENV_ENDPOINT) or "").strip()
    if not raw:
        return None
    if ":8788" in raw or ":8787" in raw:
        return None
    return raw


def test_deliverables_present():
    assert EXEC_MANIFEST.is_file()
    assert PROBE_RS.is_file()
    assert SMOKE_RS.is_file()
    text = SMOKE_RS.read_text(encoding="utf-8")
    assert "PD-MCP-LIVE-SMOKE-01" in text
    assert "probe_mcp_live_smoke_target" in text
    assert "dry_run: false" in text or "dry_run:false" in text.replace(" ", "")
    probe = PROBE_RS.read_text(encoding="utf-8")
    assert ENV_ENDPOINT in probe
    assert "NOT RUN" in probe or "None" in probe


def test_projection_contract_mentions_no_secret_leak():
    text = SMOKE_RS.read_text(encoding="utf-8")
    assert "must-not-leak-in-projection" in text
    assert "has_secret" in text
    # Must not treat DryRun as Live PASS.
    assert "DryRun" in text and ("not count" in text.lower() or "not DryRun" in text or "Live PASS" in text)


def test_live_mcp_smoke_cargo_or_not_run():
    """Run compiled smoke; missing toolchain fails, absent optional target reports NOT RUN."""
    probed = _probe_endpoint()
    cargo = _cargo_bin()
    if shutil.which(cargo) is None and not Path(cargo).is_file():
        pytest.fail("FIXTURE_SETUP: cargo／rustc required — cannot execute live smoke binary")

    env = os.environ.copy()
    cargo_home = Path.home() / ".cargo" / "bin"
    if cargo_home.is_dir():
        env["PATH"] = str(cargo_home) + os.pathsep + env.get("PATH", "")

    cmd = [
        cargo,
        "test",
        "--manifest-path",
        str(EXEC_MANIFEST),
        "--features",
        "real-mcp",
        "--test",
        "live_mcp_smoke",
        FILTER,
        "--",
        "--nocapture",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(EXEC_DIR),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    print(out)

    if probed is None:
        assert proc.returncode == 0, f"expected skip-pass without target; rc={proc.returncode}\n{out}"
        assert "NOT RUN" in out or "no activatable MCP" in out
        # Must not claim Live PASS when skipping.
        assert "PD-MCP-LIVE-SMOKE-01 PASS" not in out
        return

    assert proc.returncode == 0, (
        f"Live MCP smoke FAIL for endpoint={probed}; rc={proc.returncode}\n{out}"
    )
    assert "PD-MCP-LIVE-SMOKE-01 PASS" in out or "test result: ok" in out.lower()
    assert "dry_run=false" in out.lower() or "Live, not DryRun" in out or "PASS" in out


if __name__ == "__main__":
    print("probe endpoint:", _probe_endpoint())
    raise SystemExit(pytest.main([__file__, "-q", "--tb=short"]))
