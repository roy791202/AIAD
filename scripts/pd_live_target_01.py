#!/usr/bin/env python3
"""PD-LIVE-TARGET-01 — probe local Agent CLIs (PATH／host settings); never spawn.

BDD-PD-LIVE-TARGET-01:
  Detect usable CLI (claude｜cursor-agent｜codex｜antigravity) via PATH or read
  host settings; if none → explicit NOT RUN; secrets never enter the projection;
  artifact consumed by PD-LIVE-CLI-SMOKE-01.

Usage (from repo root)::

    python scripts/pd_live_target_01.py
    python scripts/pd_live_target_01.py --out reports/live-cli-target-result.json

Exit 0 for PASS and NOT RUN (absence is a valid probe outcome). Exit 1 only on
script／IO failure.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "live-cli-target-result.json"

TOOL_KEYS = ("claude", "cursor-agent", "codex", "antigravity")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _host_settings_candidates() -> list[Path]:
    paths: list[Path] = []
    local = os.environ.get("LOCALAPPDATA") or ""
    if local:
        paths.append(Path(local) / "SGenAxis" / "host-settings.json")
        paths.append(Path(local) / "SGenAxis" / "agent-settings.json")
    home = Path.home()
    paths.append(home / ".config" / "SGenAxis" / "host-settings.json")
    paths.append(home / ".config" / "SGenAxis" / "agent-settings.json")
    # Repo-local fixtures (optional)
    paths.append(ROOT / "reports" / "fixtures" / "host-settings.json")
    return paths


def _strip_secrets(obj: Any) -> Any:
    """Recursively drop secret-bearing keys; never project token values."""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if lk in {"secret_token", "secret", "token", "password", "api_key", "apikey"}:
                continue
            out[k] = _strip_secrets(v)
        return out
    if isinstance(obj, list):
        return [_strip_secrets(x) for x in obj]
    return obj


def _cli_paths_from_settings(raw: dict[str, Any]) -> dict[str, str]:
    """Extract configured CLI paths from host or agent settings JSON."""
    safe = _strip_secrets(raw)
    agent = safe.get("agent") if isinstance(safe.get("agent"), dict) else safe
    cli = agent.get("cli") if isinstance(agent, dict) else None
    if not isinstance(cli, dict):
        return {}
    mapping = {
        "claude": ("claude", "path"),
        "cursor-agent": ("cursor_agent", "path"),
        "codex": ("codex", "path"),
        "antigravity": ("antigravity", "path"),
    }
    found: dict[str, str] = {}
    for tool, (field, path_key) in mapping.items():
        block = cli.get(field)
        if isinstance(block, dict):
            p = str(block.get(path_key) or "").strip()
            if p:
                found[tool] = p
    return found


def _settings_projection(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not raw:
        return {
            "cli_selected": "claude",
            "claude_path": "claude",
            "cursor_agent_path": "cursor-agent",
            "codex_path": "codex",
            "antigravity_path": "antigravity",
            "mcp_server_name": "",
            "mcp_endpoint": "",
            "mcp_has_secret": False,
            "settings_file": None,
        }
    safe = _strip_secrets(raw)
    agent = safe.get("agent") if isinstance(safe.get("agent"), dict) else safe
    cli = agent.get("cli") if isinstance(agent, dict) else {}
    mcp = agent.get("mcp") if isinstance(agent, dict) else {}
    if not isinstance(cli, dict):
        cli = {}
    if not isinstance(mcp, dict):
        mcp = {}

    def path_of(field: str, default: str) -> str:
        block = cli.get(field)
        if isinstance(block, dict):
            return str(block.get("path") or default)
        return default

    selected = cli.get("selected") or "claude"
    if isinstance(selected, dict):
        selected = "claude"
    # Detect secret presence without reading value (already stripped).
    had_secret = False
    if isinstance(raw.get("agent"), dict):
        mcp_raw = raw["agent"].get("mcp")
        if isinstance(mcp_raw, dict):
            tok = mcp_raw.get("secret_token")
            had_secret = bool(tok)
    elif isinstance(raw.get("mcp"), dict):
        tok = raw["mcp"].get("secret_token")
        had_secret = bool(tok)

    return {
        "cli_selected": str(selected),
        "claude_path": path_of("claude", "claude"),
        "cursor_agent_path": path_of("cursor_agent", "cursor-agent"),
        "codex_path": path_of("codex", "codex"),
        "antigravity_path": path_of("antigravity", "antigravity"),
        "mcp_server_name": str(mcp.get("server_name") or ""),
        "mcp_endpoint": str(mcp.get("endpoint") or ""),
        "mcp_has_secret": had_secret,
    }


def _path_exists(p: str) -> bool:
    try:
        return Path(p).expanduser().exists()
    except OSError:
        return False


def probe() -> dict[str, Any]:
    targets: list[dict[str, str]] = []
    seen: set[str] = set()

    settings_raw: dict[str, Any] | None = None
    settings_file: str | None = None
    for cand in _host_settings_candidates():
        if cand.is_file():
            try:
                settings_raw = json.loads(cand.read_text(encoding="utf-8"))
                settings_file = str(cand)
                break
            except (OSError, json.JSONDecodeError):
                continue

    # 1) Host settings configured paths that exist on disk.
    if settings_raw:
        for tool, path in _cli_paths_from_settings(settings_raw).items():
            if tool in seen:
                continue
            if _path_exists(path):
                targets.append(
                    {"tool": tool, "path": str(Path(path).expanduser()), "source": "host_settings"}
                )
                seen.add(tool)

    # 2) PATH lookup (shutil.which) — no spawn of the agent CLI itself.
    for tool in TOOL_KEYS:
        if tool in seen:
            continue
        which = shutil.which(tool)
        if which:
            targets.append({"tool": tool, "path": which, "source": "path"})
            seen.add(tool)

    proj = _settings_projection(settings_raw)
    proj["settings_file"] = settings_file

    if targets:
        status = "PASS"
        detail = f"{len(targets)} CLI target(s) detected for live smoke"
    else:
        status = "NOT RUN"
        detail = "no usable CLI on PATH or in host settings — NOT RUN (never forged PASS)"

    result = {
        "card": "PD-LIVE-TARGET-01",
        "status": status,
        "targets": targets,
        "settings": proj,
        "detail": detail,
        "probedAt": _utc_now(),
        "host": os.name,
    }
    # Hard guard: serialized artifact must never contain secret values／keys.
    blob = json.dumps(result, ensure_ascii=False)
    if "secret_token" in blob.lower():
        raise RuntimeError("probe artifact leaked secret_token key")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PD-LIVE-TARGET-01 live CLI target probe")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="JSON artifact path (default: reports/live-cli-target-result.json)",
    )
    args = parser.parse_args(argv)

    try:
        result = probe()
    except Exception as exc:  # noqa: BLE001 — surface as FAIL for the script only
        print(f"PD-LIVE-TARGET-01 FAIL: {exc}", file=sys.stderr)
        return 1

    out: Path = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"PD-LIVE-TARGET-01 status={result['status']} targets={len(result['targets'])}")
    print(f"PD-LIVE-TARGET-01 wrote {out}")
    for t in result["targets"]:
        print(f"  - {t['tool']}: {t['path']} ({t['source']})")
    if result["status"] == "NOT RUN":
        print(f"PD-LIVE-TARGET-01 detail: {result['detail']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
