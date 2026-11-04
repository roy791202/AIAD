# Contracts & invariants — agent-integration (PROPOSED)

**Card:** `PD-RUST-AGENT-ENTRYPOINTS-01`  
**Status:** Sketch only — **not** an approved contract. Executable Skeleton/RED remain blocked.

## Shared contract family (must not fork)

These identities are owned by the first closed-loop / Host path (`PD-RUST-AGENT-LOOP-01` and existing WORK/EVID gates). Entrypoint adapters **bind** to them; they do not redefine them:

| Concept | Invariant (PROPOSED) |
|---|---|
| Task / work item | One authoritative task identity per Host binding |
| Run / lease | Start requires approved binding + current fingerprint where enforced |
| Cancel | Request ACK + drain/terminal semantics per existing Host path; entrypoint cannot invent silent kill-as-success |
| Report / evidence | Authenticated or Host-bound report path; child/Agent claims are untrusted |
| Acceptance | Human / product gates only; provider exit 0 ≠ green |
| Source packet | NOT_READY / incomplete authority never grants implementation |

## Entrypoint-local obligations (integration)

| ID | Obligation |
|---|---|
| INV-AE-01 | Every capability row names owner card + dependency blockers |
| INV-AE-02 | Claude and Codex rows are independent; one PASS never implies the other |
| INV-AE-03 | Unsupported / NOT RUN / BLOCKED are publishable statuses, not omissions |
| INV-AE-04 | Version / path / argv / auth-ready / allowed target must be explicit before real-provider evidence claims |
| INV-AE-05 | Inbound MCP must not reuse outbound AgentProvider semantics |
| INV-AE-06 | Embedded interactive path must not silently extend ProcessPort stdin/PTY |
| INV-AE-07 | This module stores no second SSOT for tasks, leases, or board state |
| INV-AE-08 | Compatibility reports cite fixture or approved provider contract; no guessed classifiers |

## Capability row schema (index only — PROPOSED)

Each row in the integration matrix SHOULD eventually record:

- `capability_id` (cli-entry | inbound-mcp | claude-compat | codex-compat | embedded | agent-hosted-ui)
- `owner_card`
- `provider` / `mode` (when applicable)
- `version` (semver or vendor build id — **UNKNOWN** until supplied)
- `scope` (benign fixture | named install | interactive session | …)
- `compat_status` (`NOT RUN` | `PASS` | `FAIL` | `BLOCKED` | `NOT_SUPPORTED`)
- `evidence_path` (module HTML / review — empty until produced by owner card)
- `blockers` (card ids / DEC ids / missing owner inputs)

## Failure paths (observable — for future BDD)

| Failure | Expected observation (PROPOSED) |
|---|---|
| Missing AGENT-LOOP / architecture approval | Integration remains `NOT_READY_FOR_IMPLEMENTATION` |
| DEC open (DISPATCH / EMBEDDED / MCP transport / Guard) | Downstream delivery cards stay blocked; index shows BLOCKED |
| Provider target unspecified | Compat row `NOT RUN` / `NOT_SUPPORTED`, never synthetic PASS |
| Interactive-required provider on noninteractive CLI path | Capability failure / ARCHITECTURE_GAP — no silent PTY |
| Duplicate SSOT attempt in a delivery card | Architecture review FAIL — route back to shared Host |

## UI schema

**N/A for this card.** No new product UI surface. UI schemas live on delivery cards (CLI settings, inbound MCP tools, embedded panel, hosted UI) after their own architecture approval.
