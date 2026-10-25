# sgenaxis-evid (PD-EVID-01)

Immutable test **evidence** store: classify runner output, bind versions, gate green lights.

## Rules

| Rule | Behavior |
|------|----------|
| Valid behavioral RED | `build_ok` + assertion / missing-behavior failure; linked to BDD |
| Infra failure | compile / fixture damage → **reject** RED qualification |
| Empty exit 0 | **NotMeasured** — never PASS |
| Version bind | every record stamps `spec_hash` + `worktree_fingerprint` |
| Provider done ≠ green | `provider_success_implies_task_green` is always `false`; `evaluate_ready_for_green` needs Pass evidence |
| FLOW Accept／Complete | `evidence_allows_flow_accept_or_complete` — gaps → false; lamp hint `yellow` (PD-FLOW-EVID-GATE-01) |

## Test

```powershell
cd apps/sgenaxis-desktop/crates/sgenaxis-evid
cargo test
```

## Inspector projection (PD-EVID-UI-01)

`project_inspector_evidence` — read-only summary for UI Inspector:

- Empty evidence → `NOT RUN`／`未測`
- Provider Success → `provider_success_implies_green: false`; `product_lamp_hint` never auto-`green`
- `ReadyForGreen` still yields lamp hint `yellow` (awaiting admin extinguish)

## Non-goals (this card)

- Real process spawn / cargo runner adapter (later)
- SQLite persistence (in-memory store first)
- Board zone mutation / admin-green
- Ports `:8788` / `:8787`
