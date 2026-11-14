# Claude Code compatibility matrix — lead / exec / cancel / error / report / EVID

**Card:** PD-RUST-CLAUDE-COMPAT-01  
**Date:** 2026-10-26 Asia/Taipei  
**Rule:** Unverified = NOT RUN. Probe ≠ PASS. Stay yellow.

## Version / runtime header (probe only)

| Field | Value | Class |
|-------|--------|-------|
| claude_code_version | 2.1.191 | probe |
| claude_cli_path | `C:\Users\g6812\AppData\Roaming\npm\claude.cmd` | probe |
| selected_mode_id | _(none locked for live)_ | NOT_RUN |
| os | Windows 10.0.19045 | probe |
| shell | powershell | probe |
| auth_readiness | NOT_PROBED | — |
| live capability exercise | — | **NOT RUN** |

## Axis × mode status

| Axis | Planned assertion (summary) | MODE-CLI-HEADLESS | MODE-INBOUND-MCP | MODE-EMBEDDED-UI |
|------|-----------------------------|-------------------|------------------|------------------|
| **lead** | Authorized claim → one lease; stale/unauth → zero mutation | N/A (product Assign) / planned later as Assign gate | **NOT RUN** (blocked: INBOUND-MCP + AGENT-LOOP) | N/A |
| **exec** | Named version+mode runs; exit classified; no auto-green | **NOT RUN** (blocked: CLI-ENTRY + AGENT-LOOP) | **NOT RUN** | **NOT RUN** (host UI NOT VERIFIED) |
| **cancel** | One terminal; lease at terminal only | **NOT RUN** | **NOT RUN** | **NOT RUN** |
| **error** | Missing path/auth → no start; runtime fail → Failed, prior EVID intact | **NOT RUN** | **NOT RUN** | **NOT RUN** |
| **report** | Identity/lease/idempotency; conflict reject | **NOT RUN** | **NOT RUN** | projection only / **NOT RUN** |
| **EVID** | Bind run/task/revision; HTML trace; success ≠ FLOW green | **NOT RUN** | **NOT RUN** | **NOT RUN** |

## Dependency gate column

| Dependency | Blocks axes | Live status implication |
|------------|-------------|-------------------------|
| PD-RUST-AGENT-LOOP-01 | lead, exec, cancel, report, EVID | BLOCKED → matrix stays NOT RUN |
| PD-RUST-CLI-ENTRY-IMPL-01 | exec, cancel, error (CLI mode) | BLOCKED → CLI columns NOT RUN |
| PD-RUST-INBOUND-MCP-IMPL-01 | lead, report (MCP mode) | BLOCKED → MCP columns NOT RUN |
| PLANNING_ONLY / contract unset | all | NOT_READY_FOR_IMPLEMENTATION |

## Result-class legend

| Class | Meaning |
|-------|---------|
| PASS | Controlled run met Then; version+mode+runtime recorded |
| FAIL | Controlled run violated Then |
| BLOCKED | Dependency/contract/env gate prevents attempt |
| NOT_RUN | Not attempted (planning, unavailable, or deferred) |
| PARTIAL | Some observables met; terminal incomplete — never upgrade to PASS silently |

## Honest summary

- **Planned:** full six-axis matrix under locked mode + version.  
- **Executed live:** none.  
- **Probe only:** Claude Code `2.1.191` on PATH.  
- **UI assumption:** rejected — MODE-EMBEDDED-UI = NOT VERIFIED.
