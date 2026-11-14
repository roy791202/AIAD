# Claude Code compatibility — verification plan

**Card:** PD-RUST-CLAUDE-COMPAT-01  
**Module:** agent-compatibility  
**State:** PLANNING_ONLY / NOT_READY_FOR_IMPLEMENTATION  
**Plan status:** READY_FOR_TDD (design packet complete; live verification NOT RUN)  
**Zone rule:** stay yellow; never self-green

## Intent

Given an approved module contract and controlled inputs, execute compatibility verification for Claude Code across **lead / exec / cancel / error / report / EVID**, recording **exact Claude Code version**, **selected mode**, and **runtime** fields. Capabilities not exercised stay **NOT RUN**. Do not assume all Agent windows share the same UI.

## Selected modes (proposed — owner lock required before live)

| Mode id | Surface | Lead semantics | Notes |
|---------|---------|----------------|-------|
| MODE-CLI-HEADLESS | Product → outbound CLI (`claude` / approved argv) | Product Assign (not Agent claim) | First candidate after benign fixture |
| MODE-INBOUND-MCP | Claude Code → inbound MCP tools | ClaimAgentRun | Requires INBOUND-MCP-IMPL |
| MODE-EMBEDDED-UI | Agent-window / MCP Apps UI | N/A (projection) | Capability-dependent; **NOT VERIFIED**; must not gate tools path |

Rule: one evidence row = one mode + one version + one runtime. No cross-mode PASS collapse.

## Version / runtime fields (mandatory on evidence)

- `claude_code_version`
- `claude_cli_path`
- `selected_mode_id`
- `os` / `shell`
- `cwd_policy`
- `auth_readiness` (`READY` | `NOT_READY` | `NOT_PROBED`)
- `argv_or_tool_surface`
- `runtime_started_at` / `runtime_ended_at`
- `result_class` ∈ {PASS, FAIL, BLOCKED, NOT_RUN, PARTIAL}

### Probe (2026-10-26) — not verification

| Field | Value |
|-------|--------|
| claude_cli_path | `C:\Users\g6812\AppData\Roaming\npm\claude.cmd` |
| claude_code_version | `2.1.191` |
| os | Windows 10.0.19045 |
| shell | powershell |
| auth_readiness | NOT_PROBED |
| live lead/exec/cancel/error/report/EVID | **NOT RUN** |

## Dependency blockers

| Dependency | Why blocking |
|------------|----------------|
| PD-RUST-AGENT-LOOP-01 | Shared claim↔run↔report↔EVID loop must be approved before Claude substitutes fixtures |
| PD-RUST-CLI-ENTRY-IMPL-01 | Outbound CLI entry argv/cwd/cancel binding |
| PD-RUST-INBOUND-MCP-IMPL-01 | Inbound query/claim/report adapter |
| Card note PLANNING_ONLY | Owner-approved contract + controlled inputs not cleared |

Until cleared: matrix live cells remain **NOT RUN** or **BLOCKED** — never forged PASS from docs / Fake MCP / version probe alone.

## Phased slices

| Slice | When | Scope | Output |
|-------|------|-------|--------|
| CC-V0 | Now | Design packet (this plan + BDD + matrix + module.html) | READY_FOR_TDD |
| CC-V1 | After owner mode lock + deps | Scripted/fixture path through approved ports (no live Claude required) | Fixture evidence + version fields template filled as N/A provider |
| CC-V2 | After CLI-ENTRY | MODE-CLI-HEADLESS live: exec/cancel/error + report/EVID | Per-axis results |
| CC-V3 | After INBOUND-MCP | MODE-INBOUND-MCP live: lead/claim + report races | Per-axis results |
| CC-V4 | Optional | MODE-EMBEDDED-UI capability detect | HOST_NOT_VERIFIED or limited PASS; tools path independent |

## TDD taxonomy (NOT RUN — define before RED)

| Class | Planned cases (examples) |
|-------|---------------------------|
| normal | claim→exec→report→EVID; CLI headless controlled task |
| boundary | exact argv/cwd; busy single Run; lease edge |
| invalid | malformed report; wrong run id; unapproved claim |
| dependency_failure | missing binary; auth NOT_READY; MCP unavailable |
| partial_failure | chunks then crash; cancel/report race |
| state | lease pre/post; exactly-one terminal |
| transaction | atomic claim+lease; dedup report; reject preserves prior |
| lifecycle | Running→Reported\|Failed\|Cancelled; restart new run id |
| regression | Fake≠Live; success≠green; UI absence≠tool FAIL |

**Valid RED gate:** compiles; fails because target Claude-compat behavior is missing — not because of harness typos. Independent verification + HTML trace; do not weaken assertions.

## Non-goals

- Production schema/API/Ports edits
- Board green / commit / push
- Treating docs or `claude --version` as compatibility PASS
- Assuming embedded UI parity across hosts

## Owner decisions still open

1. Lock first live mode: CLI-HEADLESS vs INBOUND-MCP (recommended order: fixture → CLI → MCP).
2. Name exact approved argv / tool names / auth-ready checklist for the selected install (`2.1.191` on this host is probe-only until re-locked at run time).
3. Whether MODE-EMBEDDED-UI is in-scope for this card or deferred to embedded-agent work.

## Canonical artifacts

- `module.html` — human review projection
- `module.json` — structured SSOT for this packet
- `module.feature` — BDD draft
- `matrix.md` — axis status matrix
- `reports/dispatch-pd/PD-RUST-CLAUDE-COMPAT-01.md` — dispatch report
