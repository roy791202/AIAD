# Agent entrypoints — architecture notes (PROPOSED)

**Card:** `PD-RUST-AGENT-ENTRYPOINTS-01`  
**Module:** `agent-integration`  
**Status:** `PLANNING_ONLY` · `PROPOSED_NOT_APPROVED` · `NOT_READY_FOR_IMPLEMENTATION`  
**Date:** 2026-10-26 Asia/Taipei

This packet does **not** approve Ports, Skeleton, RED, production edits, or board green. It is an integration map only.

## Intent

Reuse the **first closed-loop** task / run / report / evidence contracts owned by `PD-RUST-AGENT-LOOP-01` (and related Host / WORK / EVID gates). Capability-specific delivery is **delegated** to existing follow-on cards — this module must **not** invent a second SSOT, second lease authority, or parallel acceptance path.

## Capability → owner cards (routing, not ownership transfer)

| Capability | Delivery card(s) | Shared contract source | Local SSOT? |
|---|---|---|---|
| Noninteractive CLI launch (product → Agent CLI) | `PD-RUST-CLI-ENTRY-IMPL-01` (+ `PD-RUST-DISPATCH-MODES-DEC-01` / cli-first envelope) | AGENT-LOOP run/lease/cancel/report | **No** |
| Inbound Agent connection (Agent → product tools) | `PD-RUST-INBOUND-MCP-IMPL-01` (+ MCP transport DEC) | Same Application claim/report ports | **No** |
| Claude Code compatibility matrix | `PD-RUST-CLAUDE-COMPAT-01` | Same; versioned provider row | **No** |
| Codex compatibility matrix | `PD-RUST-CODEX-COMPAT-01` | Same; independent row (Claude PASS ≠ Codex PASS) | **No** |
| EluSlot-hosted interactive Agent (PTY / native panel) | `PD-RUST-EMBEDDED-AGENT-PLAN-01` → `DEC-01` → later IMPL | Session proposal; must still bind project + evidence gates | **No** |
| Agent-hosted EluSlot UI | `PD-RUST-AGENT-HOSTED-UI-01` (deps: DISPATCH-MODES-DEC + INBOUND-MCP) | Read-only first; writes separately approved | **No** |

## Proposed architecture principles (A1–A12)

| ID | Principle | Note |
|---|---|---|
| A1 | Single authoritative Rust Application Host | Entrypoints are adapters; Host owns leases / acceptance |
| A2 | First closed-loop contracts are shared | Task / run / cancel / report / EVID identity stay one family |
| A3 | Entrypoint ≠ provider | CLI path, inbound MCP, and embedded session are orthogonal axes |
| A4 | Provider ≠ acceptance | Child / Agent SUCCESS never auto-greens product work |
| A5 | Versioned capability rows | Each provider/mode records version, scope, PASS/FAIL/BLOCKED/NOT RUN / unsupported |
| A6 | Unsupported is first-class | Missing target or unverified interface → explicit NOT_SUPPORTED / NOT RUN, never silent PASS |
| A7 | No duplicate SSOT | Do not create parallel task store, board writer, or report authority here |
| A8 | Driving vs driven adapters stay distinct | Inbound MCP ≠ outbound CLI/MCP provider semantics |
| A9 | Embedded session is a separate seam | ProcessPort noninteractive drain ≠ PTY/session (see embedded-agents gaps) |
| A10 | Compatibility cards own provider evidence | This module indexes rows; it does not re-run provider suites |
| A11 | Architecture gates before Skeleton/RED | Unapproved schema/API/Ports/ownership/transaction/BDD remain protected |
| A12 | Integration report is observational | `module.html` summarizes routing + readiness; it is not a release gate by itself |

## Diagram A — entrypoint fan-in (shared Application)

```
Operators / Agents / Hosts
  ├─ CLI-ENTRY (product launches CLI) ──┐
  ├─ INBOUND-MCP (Agent claims tools) ──┤
  ├─ EMBEDDED (EluSlot hosts session) ──┼──► Application Host
  └─ AGENT-HOSTED-UI (Agent hosts UI) ──┘         │
                                                  ▼
                         shared task/run/lease/cancel/report/EVID
                                                  │
                         ◄── CLI / process adapters (driven)
                         ◄── provider-compat evidence (indexed only)
```

## Diagram B — ownership & non-duplication

```
OWNERSHIP
  AGENT-LOOP (+ Host/WORK/EVID)  = closed-loop contract SSOT (proposed until approved)
  CLI-ENTRY / INBOUND-MCP / EMBEDDED / HOSTED-UI = adapter + UX delivery
  CLAUDE-COMPAT / CODEX-COMPAT   = versioned capability evidence rows
  THIS CARD (agent-integration)  = routing map + readiness index only

FORBIDDEN
  second task/run store
  entrypoint-local acceptance
  provider success → board green
  guessing argv/auth across providers
  absorbing PTY into ProcessPort without DEC
```

## Related named packets (cite only)

- `reports/rust-improvements/continuous/cli-first-envelope/module.html` — noninteractive first-slice proposal for DISPATCH-MODES-DEC
- `reports/rust-improvements/embedded-agents/module.html` — EA-A/EA-B + ProcessPort gaps for EMBEDDED-AGENT-DEC
- `reports/rust-improvements/dispatch-modes/module.html` — multi-axis dispatch ownership / transport / hosting (PROPOSED)

## Explicit non-goals

- Production Port / DTO / schema changes
- Live Claude Code / Codex / network / secret access
- Approving DISPATCH-MODES-DEC, EMBEDDED-AGENT-DEC, MCP transport, Guard, or AGENT-LOOP architecture
- Implementing CLI-ENTRY, INBOUND-MCP, compat, or embedded slices
- Board green / commit / push / release
