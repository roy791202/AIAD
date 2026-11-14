"""PD-M2-LIVE-MATRIX-01 — Live target × status matrix (PASS | NOT RUN | FAIL).

Aggregates CLI／MCP probe + smoke evidence under ``reports/``. Missing artifact
⇒ **NOT RUN**. Never promotes unrun cells to PASS (anti-forge).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from build_result import normalize_status, rollup_status

TAIPEI = timezone(timedelta(hours=8))

SCHEMA = "aiad.m2-live-matrix.v0.1"
CARD_ID = "PD-M2-LIVE-MATRIX-01"
BDD_ID = "BDD-PD-M2-LIVE-MATRIX-01"

# Cell vocabulary (card title / BDD). Overall may also be PARTIAL via rollup.
CELL_VOCAB: frozenset[str] = frozenset({"PASS", "NOT RUN", "FAIL"})

ANTI_FORGE_BAN = "禁止把未跑升 PASS"
ANTI_FORGE_BAN_EN = "must not promote unrun (NOT RUN) to PASS"

# Evidence paths relative to repo root (citable by M2-VAL).
EVIDENCE = {
    "cli_probe": "reports/live-cli-target-result.json",
    "cli_smoke": "reports/live-cli-smoke-result.json",
    "mcp_probe": "reports/live-mcp-target-result.json",
    "mcp_smoke": "reports/live-mcp-smoke-result.json",
}

CELL_ORDER: tuple[str, ...] = (
    "cli_probe",
    "cli_smoke",
    "mcp_probe",
    "mcp_smoke",
)

CELL_LABELS = {
    "cli_probe": "CLI probe (PD-LIVE-TARGET-01)",
    "cli_smoke": "CLI Live smoke (PD-LIVE-CLI-SMOKE-01)",
    "mcp_probe": "MCP probe / target",
    "mcp_smoke": "MCP Live smoke (PD-MCP-LIVE-SMOKE-01)",
}


@dataclass(frozen=True)
class Cell:
    key: str
    label: str
    status: str
    evidence: str
    detail: str
    ran: bool


def now_iso() -> str:
    return datetime.now(TAIPEI).isoformat(timespec="seconds")


def normalize_cell_status(raw: Any) -> str:
    """Normalize to cell vocab; map PARTIAL/BLOCKED → FAIL for matrix cells."""
    st = normalize_status(raw)
    if st in CELL_VOCAB:
        return st
    if st in ("PARTIAL", "BLOCKED"):
        return "FAIL"
    raise ValueError("illegal cell status %r (allowed: %s)" % (raw, " | ".join(sorted(CELL_VOCAB))))


def refuse_forge_pass(*, evidence_exists: bool, claimed: str) -> str:
    """Anti-forge: missing / unrun evidence cannot claim PASS."""
    claimed_n = normalize_cell_status(claimed)
    if not evidence_exists:
        return "NOT RUN"
    return claimed_n


def _read_json(path: Path) -> Mapping[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _status_from_payload(payload: Mapping[str, Any] | None) -> str | None:
    if payload is None:
        return None
    raw = payload.get("status")
    if raw is None:
        return None
    try:
        return normalize_cell_status(raw)
    except (ValueError, Exception):
        return "FAIL"


def _mcp_hint_from_cli_probe(repo: Path) -> tuple[bool, str]:
    """Soft MCP probe from CLI target settings when dedicated MCP artifact absent."""
    payload = _read_json(repo / EVIDENCE["cli_probe"])
    if not payload:
        return False, "no CLI probe artifact for MCP hint"
    settings = payload.get("settings") or {}
    endpoint = str(settings.get("mcp_endpoint") or "").strip()
    name = str(settings.get("mcp_server_name") or "").strip()
    if endpoint or name:
        return True, "mcp_endpoint/name present in live-cli-target settings"
    return False, "mcp_endpoint and mcp_server_name empty → no MCP target"


def resolve_cell(repo: Path, key: str) -> Cell:
    label = CELL_LABELS[key]
    rel = EVIDENCE[key]
    path = repo / rel
    payload = _read_json(path)

    if key == "mcp_probe" and payload is None:
        # Soft fallback: empty MCP settings in CLI probe ⇒ explicit NOT RUN (not PASS).
        has_target, detail = _mcp_hint_from_cli_probe(repo)
        if has_target:
            # Target declared but no dedicated probe artifact → still NOT RUN until probed.
            return Cell(
                key=key,
                label=label,
                status="NOT RUN",
                evidence=rel,
                detail="%s; dedicated artifact missing → NOT RUN" % detail,
                ran=False,
            )
        return Cell(
            key=key,
            label=label,
            status="NOT RUN",
            evidence=EVIDENCE["cli_probe"],
            detail=detail,
            ran=False,
        )

    if payload is None:
        return Cell(
            key=key,
            label=label,
            status="NOT RUN",
            evidence=rel,
            detail="artifact missing → NOT RUN (缺跑)",
            ran=False,
        )

    claimed = _status_from_payload(payload) or "NOT RUN"
    status = refuse_forge_pass(evidence_exists=True, claimed=claimed)
    # Empty targets on probe PASS → demote (anti-forge empty PASS).
    if key.endswith("_probe") and status == "PASS":
        targets = payload.get("targets")
        if isinstance(targets, list) and len(targets) == 0:
            status = "NOT RUN"
            detail = "status was PASS but targets=[] → demoted to NOT RUN"
        else:
            detail = str(payload.get("detail") or "artifact status=%s" % status)
    else:
        detail = str(payload.get("detail") or "artifact status=%s" % status)

    return Cell(
        key=key,
        label=label,
        status=status,
        evidence=rel,
        detail=detail,
        ran=True,
    )


def build_matrix(repo: Path) -> dict[str, Any]:
    cells = [resolve_cell(repo, k) for k in CELL_ORDER]
    cell_statuses = [c.status for c in cells]
    # Worst-wins: PASS+NOT RUN → NOT RUN (never forge overall PASS while incomplete).
    overall = rollup_status(cell_statuses)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "cardId": CARD_ID,
        "bdd": BDD_ID,
        "title": "Live 目標×狀態矩陣（PASS｜NOT RUN｜FAIL）",
        "generatedAt": now_iso(),
        "status": overall,
        "vocabulary": sorted(CELL_VOCAB),
        "cells": [
            {
                "key": c.key,
                "label": c.label,
                "status": c.status,
                "evidence": c.evidence,
                "detail": c.detail,
                "ran": c.ran,
            }
            for c in cells
        ],
        "antiForge": {
            "ban": ANTI_FORGE_BAN,
            "banEn": ANTI_FORGE_BAN_EN,
            "overallIsNotPassUnlessAllCellsPass": True,
            "missingArtifactIsNotRun": True,
        },
        "citeFor": ["PD-M2-VAL-01", "M2 acceptance"],
        "citePaths": [
            "reports/m2-live-matrix.md",
            "reports/m2-live-matrix.json",
        ],
        "outOfScope": [
            "Provider contract changes",
            "zone=green (§7.1)",
        ],
    }
    return payload


def render_md(payload: Mapping[str, Any]) -> str:
    cells: Sequence[Mapping[str, Any]] = payload.get("cells") or []
    rows = []
    for c in cells:
        rows.append(
            "| `%s` | %s | **%s** | `%s` | %s |"
            % (
                c.get("key"),
                c.get("label"),
                c.get("status"),
                c.get("evidence"),
                c.get("detail"),
            )
        )
    table = "\n".join(rows)
    overall = payload.get("status")
    return f"""# M2 Live 目標×狀態矩陣

| Field | Value |
|-------|--------|
| Card | `{payload.get("cardId")}` |
| BDD | `{payload.get("bdd")}` |
| Schema | `{payload.get("schema")}` |
| Generated | {payload.get("generatedAt")} |
| Overall | **{overall}** |
| Vocabulary | PASS \\| NOT RUN \\| FAIL |

> **Cite for M2 驗收（PD-M2-VAL-01）:** `reports/m2-live-matrix.md` (+ `reports/m2-live-matrix.json`)  
> **≠** 全 Live 閉環 PASS — 缺跑＝**NOT RUN**；禁止把未跑升 PASS。

---

## 1. Matrix（CLI／MCP 探測與冒煙）

| Key | Target | Status | Evidence | Detail |
|-----|--------|--------|----------|--------|
{table}

### Status rules

1. Cell vocabulary is exactly **PASS**｜**NOT RUN**｜**FAIL**.
2. Missing evidence artifact → **NOT RUN**（缺跑）.
3. Empty probe `targets=[]` cannot stay **PASS** → demote to **NOT RUN**.
4. Overall uses worst-wins; **PASS** only if every cell is PASS (otherwise incomplete／FAIL).

---

## 2. Anti-forge（{payload.get("bdd")}）

| Forbidden | Correct |
|-----------|---------|
| 缺跑／無產物仍寫 cell **PASS** | **禁止** → **NOT RUN** |
| DryRun／敘述冒煙當 Live matrix **PASS** | **禁止** — 需 citable artifact |
| Overall **PASS** while any cell is NOT RUN／FAIL | **禁止** |
| 本文件存在＝M2 全 Live 閉環完成 | **禁止** |

**Explicit ban phrase:** {ANTI_FORGE_BAN}

**EN:** {ANTI_FORGE_BAN_EN}

---

## 3. Citation map（M2 驗收）

| Consumer | How to cite |
|----------|-------------|
| PD-M2-VAL-01 | Read overall + per-cell status from this MD／JSON；list remaining **NOT RUN** |
| Build Result／GoNoGo（若引用） | Do not upgrade NOT RUN → PASS |

Paths: `reports/m2-live-matrix.md`, `reports/m2-live-matrix.json`.

---

## 4. Out of scope

- Provider 契約變更 — **不做**
- `zone=green` — **不做**（§7.1）
"""


def write_reports(repo: Path, payload: Mapping[str, Any] | None = None) -> tuple[Path, Path]:
    data = dict(payload) if payload is not None else build_matrix(repo)
    md_path = repo / "reports" / "m2-live-matrix.md"
    json_path = repo / "reports" / "m2-live-matrix.json"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_md(data), encoding="utf-8")
    json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return md_path, json_path


def main(argv: Sequence[str] | None = None) -> int:
    del argv  # unused — always write at repo root relative to this file
    repo = Path(__file__).resolve().parents[2]
    payload = build_matrix(repo)
    md_path, json_path = write_reports(repo, payload)
    print("wrote %s" % md_path.relative_to(repo))
    print("wrote %s" % json_path.relative_to(repo))
    print("overall=%s" % payload.get("status"))
    for c in payload.get("cells") or []:
        print("  %s=%s" % (c.get("key"), c.get("status")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
