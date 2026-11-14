# Risks, dependency blockers, NOT_READY reasons

**Card:** `PD-RUST-AGENT-ENTRYPOINTS-01`  
**Date:** 2026-10-26 Asia/Taipei

## Hard blockers (implementation forbidden)

| ID | Blocker | Why it blocks this card |
|---|---|---|
| BLK-01 | `PD-RUST-AGENT-LOOP-01` architecture / contract / BDD / Skeleton not approved | First closed-loop SSOT and shared run/report semantics are the reuse target; without them this card would invent a fork |
| BLK-02 | Architecture gates unset for schema / API / Ports / ownership / transaction / BDD | Card note: protected until approved — no Skeleton/RED |
| BLK-03 | `PD-RUST-DISPATCH-MODES-DEC-01` open (benign fixture scope + real provider targets) | CLI-ENTRY / INBOUND-MCP / COMPAT delivery blocked; integration index cannot claim ready adapters |
| BLK-04 | `PD-RUST-EMBEDDED-AGENT-PLAN-01` packet exists but `PD-RUST-EMBEDDED-AGENT-DEC-01` mode (PTY vs native) not owner-approved | Embedded capability row remains proposed |
| BLK-05 | MCP transport / Guard / report-ingress related DECs incomplete as applicable to inbound path | Inbound MCP delivery cannot honestly show PASS |
| BLK-06 | Real Claude / Codex version · path · argv · auth-ready · allowed target not owner-supplied | Compat rows stuck at NOT RUN |

## Soft / sequencing dependencies

| Card | Role vs this packet |
|---|---|
| `PD-RUST-CLI-ENTRY-IMPL-01` | Owns CLI delivery evidence |
| `PD-RUST-INBOUND-MCP-IMPL-01` | Owns inbound adapter evidence |
| `PD-RUST-CLAUDE-COMPAT-01` | Owns Claude versioned matrix |
| `PD-RUST-CODEX-COMPAT-01` | Owns Codex versioned matrix |
| `PD-RUST-AGENT-HOSTED-UI-01` | Separate Agent-hosts-UI direction |
| `PD-RUST-REPORT-INGRESS-IMPL-01` | Shared report mutation path (not invented here) |

Named plan packets already available as **proposals** (not approvals):

- `reports/rust-improvements/continuous/cli-first-envelope/module.html`
- `reports/rust-improvements/embedded-agents/module.html`
- `reports/rust-improvements/dispatch-modes/module.html`

## NOT_READY_FOR_IMPLEMENTATION — reasons checklist

- [x] PLANNING_ONLY by card charter
- [x] Architecture status = `PROPOSED_NOT_APPROVED` (this packet)
- [x] AGENT-LOOP closed-loop contracts not approved for reuse binding
- [x] No formal Skeleton
- [x] Intended RED = NOT RUN / backlog only
- [x] No production Port/adapter changes authorized
- [x] Provider targets incomplete
- [x] Open DECs on dispatch / embedded / transport as applicable
- [ ] *(future)* Owner accepts routing map and clears BLK-01…06 for a bounded slice

## Risks

| Risk | Impact | Mitigation (planning) |
|---|---|---|
| Second SSOT drift | Divergent task/run/report semantics per entrypoint | Route-only module; forbid local stores |
| Treating settings defaults as verified provider APIs | False compat PASS | Require owner-named version/path/argv; status NOT RUN until verified |
| Claude proof reused for Codex | Incorrect release claims | Independent rows + INV-AE-02 |
| Silent PTY / stdin extension | Security & architecture bypass | CF07 / BDD-AE-05; DEC for embedded only |
| Premature green of this yellow card | Process violation | Stay yellow; READY_FOR_TDD = planning review only |
| Integration index mistaken for delivery | Work duplicated or orphaned | Explicit owner-card column on every row |

## What READY_FOR_TDD means here

Independent TDD Gate may review **planning completeness** (routing, diagrams, invariants, BDD sketch, blockers, honesty of NOT_READY). It must **not** expect executable RED or production tests for this PLANNING_ONLY card.
