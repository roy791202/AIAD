# Codex compatibility evidence matrix

**Card:** PD-RUST-CODEX-COMPAT-01  
**Module:** agent-compatibility  
**Provider:** Codex only (independent of Claude / Cursor / Antigravity / DryRun)  
**Fill rule:** each cell = `PASS` | `FAIL` | `BLOCKED` | `NOT RUN` + evidence path. Empty at planning = **NOT RUN**.

## Target identity (required before any non-NOT-RUN cell)

| Field | Value (planning) | Notes |
|---|---|---|
| Codex version | **UNSET** | Must be explicit; repo default is not a version |
| Executable path | **UNSET** | settings default `codex` is placeholder only |
| Argv | **UNSET** | settings default `["exec"]` unverified as live contract |
| Host OS / arch | **UNSET** | Record actual spawn host, not planner machine assumption |
| Auth ready | **UNSET** | enum only; never paste secrets |
| Modes in scope | **UNSET** | CLI / inbound-MCP / both |
| Owner authorization | **absent** | PLANNING_ONLY |

## Contract dimensions × scenarios

Rows = BDD / case IDs. Columns = required observation dimensions from card Then-clause.

| Case | Permission | Cancel | Error | Report | Evidence | Overall |
|---|---|---|---|---|---|---|
| CX-B01 happy controlled run | NOT RUN | N/A | N/A | NOT RUN | NOT RUN | NOT RUN |
| CX-B02 cancel + drain | NOT RUN | NOT RUN | N/A | NOT RUN | NOT RUN | NOT RUN |
| CX-B03 invalid / stale reject | NOT RUN | N/A | NOT RUN | N/A | NOT RUN | NOT RUN |
| CX-B04 nonzero / malformed | NOT RUN | N/A | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| CX-B05 inbound MCP parity | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| CX-B06 non-inheritance | N/A | N/A | N/A | N/A | NOT RUN | NOT RUN |
| CX-B07 duplicate / restart | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| CX-N01 normal (TDD backlog) | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| CX-N02 boundary | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| CX-N03 invalid input | NOT RUN | N/A | NOT RUN | N/A | NOT RUN | NOT RUN |
| CX-N04 dependency failure | NOT RUN | N/A | NOT RUN | N/A | NOT RUN | NOT RUN |
| CX-N05 partial failure | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| CX-N06 state / transaction | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| CX-N07 lifecycle | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| CX-N08 regression vs Claude PASS | N/A | N/A | N/A | N/A | NOT RUN | NOT RUN |

### Dimension definitions (assertable)

| Dimension | Observable Then |
|---|---|
| **Permission** | Prompt / deny / timeout paths match approved contract; no auto-approve flag or silent bypass; if Codex requires interactive permission and stdin is null → explicit `BLOCKED`/`ARCHITECTURE_GAP`, not silent PTY. |
| **Cancel** | Host ACK; continued poll; exactly one terminal; lease release at terminal only; product not greened. |
| **Error** | Preflight reject, spawn fail, nonzero exit, stream error, malformed claim each classified; no retry/login fallback invented. |
| **Report** | Host task/run/source/fingerprint binding; child-claimed IDs untrusted; ingress auth rules if MCP in scope. |
| **Evidence** | Version + host + case id + capture hashes + matrix cell; labeled simulated vs real. |

## Non-inheritance guard

| Other Agent result | Effect on Codex row |
|---|---|
| Claude Code PASS | **None** — Codex stays NOT RUN until own evidence |
| Cursor Agent PASS | **None** |
| DryRun / FakeProcess PASS | **None** — not real Codex |
| Inbound MCP with non-Codex agent PASS | **None** for Codex provider row |
| Aggregate “CLI tools configured” | **None** — settings keys ≠ compatibility |

## Blockers preventing matrix fill

1. Dependencies PLANNING_ONLY (AGENT-LOOP, CLI-ENTRY-IMPL, INBOUND-MCP-IMPL).
2. DISPATCH-MODES-DEC open for true provider target.
3. Owner Codex version/path/argv/host/auth/scope unset.
4. No card-local harness under allow-scope yet (design only).

## Honesty row

| Claim | Status |
|---|---|
| Planning packet complete for TDD review | yes (this delivery) |
| Executable RED | NOT RUN |
| Live Codex invocation | NOT RUN |
| Secrets / auth tokens accessed | NOT ACCESSED |
| Board green | FORBIDDEN / not done |
