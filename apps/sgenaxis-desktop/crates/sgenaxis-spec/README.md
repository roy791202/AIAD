# sgenaxis-spec (PD-SPEC-01)

Pure Rust **ModuleSpec / contract** library for SGenAxis.

BDD-PD-SPEC-01：可載入規格投影；核准修訂產新版本並使相關證據待重驗。

- **No** Tauri / OS / Git / Agent adapters  
- Load ModuleSpec JSON → [`SpecProjection`]  
- [`ApprovalStatus::Approved`] revisions are **immutable in place**  
- Changes → new Draft revision via [`SpecStore::revise_from_approved`]  
- Related [`EvidenceRef`] → [`EvidenceValidity::NeedsRevalidation`]

## Layout

```
crates/sgenaxis-spec/
  Cargo.toml
  README.md
  fixtures/sample_module_spec.json
  src/
    lib.rs          # re-exports + unit tests
    error.rs        # SpecError (incl. ReplanRequired)
    model.rs        # ModuleSpec / Contract / EvidenceRef
    projection.rs   # SpecProjection
    store.rs        # SpecStore load / approve / revise
```

## API

| Piece | Role |
|-------|------|
| `SpecStore::load_json` / `load_document` | Parse ModuleSpec + contracts |
| `SpecStore::projection` | Read-only 規格投影 |
| `SpecStore::approve` | Bind content hash; lock revision |
| `SpecStore::try_set_contract_body` | Draft OK; Approved → `REPLAN_REQUIRED` |
| `SpecStore::revise_from_approved` | New Draft version; invalidate evidence |
| `SpecStore::attach_evidence` | Bind evidence id to a revision |

## Test

```powershell
$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
cd D:\AIAD\apps\sgenaxis-desktop\crates\sgenaxis-spec
cargo test
```

Fixture: `fixtures/sample_module_spec.json` (included via `include_str!`).

## Out of scope

- UI / Tauri commands (`PD-CMD-01`)
- Full EVID store (`PD-EVID-01`)
- FLOW approval UI / board green
- HoneyBadger / ports 8788／8787
