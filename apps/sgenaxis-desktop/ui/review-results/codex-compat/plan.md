# PD-RUST-CODEX-COMPAT-01 — Verification plan (Codex)

**Module:** `agent-compatibility`  
**Card:** PD-RUST-CODEX-COMPAT-01  
**State:** `PLANNING_ONLY` / `NOT_READY_FOR_IMPLEMENTATION`  
**Execution:** `NOT RUN`  
**Date:** 2026-10-26 Asia/Taipei

## Intent

Prove that the **same approved module contracts** (permission, cancel, error, report, evidence) hold when the outbound CLI provider is a **named Codex installation** on a **named host**, using **controlled inputs**. Record measurable evidence. Do **not** inherit PASS from Claude Code, Cursor Agent, DryRun, or any other Agent.

## Non-negotiable rules

1. **Claude / other Agent PASS ≠ Codex PASS** — each provider row is independent (`PASS` | `FAIL` | `BLOCKED` | `NOT RUN`).
2. **Provider process success ≠ product green / acceptance.**
3. **Repo defaults** (`codex` + `["exec"]` in settings) are configuration placeholders, **not** verified Codex CLI contract.
4. No live Codex launch, auth probe, secret read, production edit, board green, commit, or push in this planning slice.
5. Assertions must not be weakened to obtain PASS.

## Dependency gate (must clear before execution)

| Dependency | Role for this card | Observed planning state |
|---|---|---|
| PD-RUST-AGENT-LOOP-01 | Approved agent-execution boundary: input / permission / cancel / report / evidence binding | PLANNING_ONLY |
| PD-RUST-CLI-ENTRY-IMPL-01 | Approved CLI entry use-cases: I/O, exit, cancel, evidence parity with report path | PLANNING_ONLY |
| PD-RUST-INBOUND-MCP-IMPL-01 | If inbound MCP is in scope for “same contract”: query → claim → report parity with CLI | PLANNING_ONLY |
| PD-RUST-DISPATCH-MODES-DEC-01 (indirect) | First-slice / true-provider targets still open; real Codex path/version/argv missing | RED decision open |

→ Formal Codex compatibility run stays **blocked** until contracts + owner-named Codex target exist. This packet only designs the verification.

## Phases

### CX-V0 — Planning packet (this delivery)

- Architecture views, contract/invariants, BDD draft, evidence matrix, AC.
- Status: **READY_FOR_TDD** (plan review only). Executable RED **NOT RUN**.

### CX-V1 — Target lock (owner)

Owner must supply before any live/fixture Codex row:

- Exact Codex **version** string and how it was obtained (`codex --version` or equivalent, once approved).
- Exact **host** identity (OS, arch, shell/host process that spawns).
- Exact **executable path** + ordered **argv** (no shell string).
- Auth readiness statement **without** exposing secrets (ready / not ready / N/A for fixture).
- Permitted project/task/files; runtime / cancel expectations.
- Which modes are in scope for this card: CLI-only vs CLI + inbound MCP parity.

Absent any required field → row stays **NOT RUN**, never inferred PASS.

### CX-V2 — Contract freeze

Freeze the shared contract IDs from agent-loop / CLI-entry / inbound-MCP (after those cards approve):

- Permission prompt / deny / never-auto-approve.
- Cancel ACK + drain + single terminal.
- Error classes (preflight reject, spawn fail, nonzero exit, malformed claim).
- Report identity binding (task/run/source/fingerprint); child claims untrusted.
- Evidence artifacts + HOST association; no silent promotion to acceptance.

### CX-V3 — Controlled verification (after approval)

Run **only** owner-authorized cases against the locked Codex target:

1. Happy / normal (controlled input → expected capture).
2. Boundary (empty output, large chunk, cwd bind).
3. Invalid (missing path, wrong argv shape, stale source).
4. Dependency failure (ProcessPort / HOST reject before spawn).
5. Partial failure (stdout then nonzero; mid-stream cancel).
6. State / transaction / lifecycle (lease, duplicate start blocked, restart new runId).
7. Regression: Claude PASS fixture must **not** mark Codex row.

Each case records permission / cancel / error / report / evidence cells in `matrix.md`.

### CX-V4 — Independent TDD Gate + Module HTML

- Intended RED must compile and fail on missing Codex-compat behavior (when Skeleton exists).
- Independent Gate: no weakened assertions; HTML traces BDD IDs → evidence paths.
- Parent may green **only** after `TDD_PASS` and owner acceptance — **this implementer never greens**.

## Evidence protocol (proposed)

| Artifact | Content |
|---|---|
| `evidence/codex-target.json` | version, path, argv, host, auth_ready enum, scope modes |
| `evidence/case-<id>/` | stdout/stderr capture hashes, exit, terminal event, timestamps |
| `evidence/matrix-result.json` | filled matrix cells with PASS/FAIL/BLOCKED/NOT RUN |
| `evidence/non-inheritance.md` | explicit statement that Claude/other rows are excluded |

Labels required in logs: `provider=Codex`, `simulated|real`, `local|host`.

## Out of scope (this card)

- Implementing CLI entry / inbound MCP / agent-loop production code.
- Guessing Codex flags from Claude defaults or internet folklore.
- PTY / embedded Agent panel (see embedded-agents).
- Auto-approve, secret harvest, package install, network probing.
- Board self-green / commit / push / release.
