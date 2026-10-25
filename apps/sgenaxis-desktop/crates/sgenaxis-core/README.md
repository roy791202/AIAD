# sgenaxis-core (PD-DIRTY-01 + PD-FLOW-01)

Pure Rust **Property + Dirty + Evaluation** and **FLOW lamp state machine** for SGenAxis.

- **No** Tauri dependency  
- **No** OS / CLI / Git / Agent adapters (Ports＋Adapters：`PD-ADAPT-01` → `sgenaxis-ports` / `sgenaxis-adapters`; Core must not import adapters)  
- UI must consume **snapshots / subscriptions** only — never call OS from Core

Authority: `docs/PRODUCT-DEVELOPMENT.md` §4 stage 2 · §5.5 lamps · FLOW module.

## Layout

```
crates/sgenaxis-core/
  Cargo.toml
  README.md
  src/
    lib.rs          # Engine facade + unit tests
    property.rs     # PropertyId / PropertyStore
    dirty.rs        # DirtySet / mark_dirty
    eval.rs         # evaluate / propagate → BoardProjection
    projection.rs   # Zone, TaskRecord, BoardProjection
    flow.rs         # PD-FLOW-01: TaskFlow lamp SM + acceptance gate
```

## API (minimal)

| Piece | Role |
|-------|------|
| `PropertyStore` | Source-of-truth values (`task.{id}.zone` / `.title`) |
| `DirtySet` / `Engine::mark_dirty` | Mark changed properties (+ projection sink) |
| `Engine::evaluate` | Propagate dirty → rebuild `BoardProjection` |
| `Engine::snapshot` / `subscribe` | Read-only projection for UI / tests |
| `Engine::set_zone` / `set_title` / `upsert_task` | Convenience mutations (fake board) |
| `TaskFlow` / `FlowEvent` | Lamp SM (gray→…→green); reason + `accepted` + EVID gate |
| `FlowError::CompleteWithoutAcceptance` | COMPLETE without accept → reject, state kept |
| `FlowError::AcceptWithoutEvidence` / `CompleteWithoutEvidence` | PD-FLOW-EVID-GATE-01: Accept／Complete need `evidence_ready` |

Fake board projection fields: zone counts (`gray`/`blue`/`yellow`/`red`/`green`) + titles.
`TaskFlow.lamp` is a [`Zone`] — same vocabulary as UI projection.

## Test

Requires Rust toolchain (`rustc` + `cargo`).

```powershell
cd D:\AIAD\apps\sgenaxis-desktop\crates\sgenaxis-core
cargo test
```

Expected: unit tests pass — e.g. change one task zone → projection yellow/gray counts update.

### Observed (PD-FLOW-01)

`cargo test` → **16 passed**（含 FLOW 燈號／COMPLETE 閘門／非法轉移／冪等／投影對齊）。

## Optional host re-export

`apps/sgenaxis-desktop/src-tauri` may path-depend on this crate and `pub use sgenaxis_core as core;` — no Tauri types leak into Core.

## Non-goals (PD-FLOW-01)

- Ports / adapters, WiX, CLI/MCP Agent, HoneyBadger, ports 8788/8787  
- FLOW-002 DAG 排程／FLOW-003 REPLAN  
- Wiring Vanilla UI to commands (later `PD-CMD-01`)  
- Admin board extinguish（滅燈交母對話；本卡只 READY_FOR_GREEN）
