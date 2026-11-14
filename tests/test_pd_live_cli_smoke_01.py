"""PD-LIVE-CLI-SMOKE-01 — Live CLI start→chunk→exit smoke (or NOT RUN).

BDD-PD-LIVE-CLI-SMOKE-01: under approval, run one Live start→chunk→exit against
an explicit local Agent CLI, or record a clear skip reason. Secrets must not
appear in settings projection. No cloud gateway.

Allow-scope: exec／adapters／tests. Coordinates with PD-LIVE-TARGET-01 PATH probe.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "apps" / "sgenaxis-desktop"
EXEC_DIR = DESKTOP / "crates" / "sgenaxis-exec"
EXEC_MANIFEST = EXEC_DIR / "Cargo.toml"
ADAPTERS_PROBE = DESKTOP / "crates" / "sgenaxis-adapters" / "src" / "cli_probe.rs"
SMOKE_RS = EXEC_DIR / "tests" / "live_cli_smoke.rs"

CANDIDATES = ("claude", "cursor-agent", "codex", "antigravity")
FILTER = "live_cli_smoke_start_chunk_exit_or_skip"


def _cargo_bin() -> str:
    home = Path.home() / ".cargo" / "bin" / ("cargo.exe" if os.name == "nt" else "cargo")
    if home.is_file():
        return str(home)
    return "cargo"


def _which_agent_cli() -> Optional[Tuple[str, str]]:
    """Return (key, path) for first PATH-visible Agent CLI, else None."""
    for key in CANDIDATES:
        path = shutil.which(key)
        if path:
            # Prefer non-ps1 on Windows (Command spawn).
            low = path.lower()
            if low.endswith(".ps1"):
                cmd = shutil.which(f"{key}.cmd") or shutil.which(f"{key}.exe")
                if cmd:
                    return key, cmd
                continue
            return key, path
    return None


def test_deliverables_present():
    assert EXEC_MANIFEST.is_file()
    assert ADAPTERS_PROBE.is_file()
    assert SMOKE_RS.is_file()
    text = SMOKE_RS.read_text(encoding="utf-8")
    assert "PD-LIVE-CLI-SMOKE-01" in text
    assert "probe_agent_cli" in text
    assert "--version" in text
    probe = ADAPTERS_PROBE.read_text(encoding="utf-8")
    assert "AGENT_CLI_CANDIDATES" in probe
    assert "secret" not in probe.lower() or "never" in probe.lower()


def test_projection_contract_mentions_no_secret_leak():
    """Sanity: smoke source asserts projection omits secret values."""
    text = SMOKE_RS.read_text(encoding="utf-8")
    assert "must-not-leak-in-projection" in text
    assert "proj.mcp.has_secret" in text or "has_secret" in text


def test_live_cli_smoke_cargo_or_not_run():
    """Run compiled smoke; missing toolchain fails, absent optional CLI reports NOT RUN."""
    probed = _which_agent_cli()
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
        "real-spawn",
        "--test",
        "live_cli_smoke",
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
        # No CLI: test must return early (pass) with NOT RUN message.
        assert proc.returncode == 0, f"expected skip-pass without CLI; rc={proc.returncode}\n{out}"
        assert "NOT RUN" in out or "no Agent CLI" in out
        return

    assert proc.returncode == 0, (
        f"Live smoke FAIL for {probed[0]} @ {probed[1]}; rc={proc.returncode}\n{out}"
    )
    assert "PD-LIVE-CLI-SMOKE-01 PASS" in out or "test result: ok" in out.lower()


if __name__ == "__main__":
    # Mini runner without pytest for report evidence.
    probed = _which_agent_cli()
    print("probe:", probed)
    raise SystemExit(pytest.main([__file__, "-q", "--tb=short"]))
