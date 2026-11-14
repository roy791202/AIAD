# sgenaxis-guard (PD-GUARD-01)

Pure Rust **GUARD** gate: envelope integrity + path allow／protect + rejection reasons.

Authority: `docs/PRODUCT-DEVELOPMENT.md` §6 GUARD · board `BDD-PD-GUARD-01` · product-plan GUARD-001.

| Piece | Role |
|-------|------|
| `Envelope` | Approval, primary／integration modules, allow／protect path globs |
| `RedEvidence` | Behavioral RED vs compile／env／missing |
| `check_start_implementation` | Unapproved or invalid RED → reject (traceable codes) |
| `check_changes` | Protect wins over allow; `MODULE_BOUNDARY_ESCAPE`; traversal |
| `check_implementation_request` | Combined start + path gate |
| `RejectReason` | Stable `CODE:detail` traces |

## Rules

1. **Not approved** or **non-behavioral RED** → cannot start implementation.
2. **Protect** list always rejects (even if path is also on allowlist).
3. **Allow** list does not override module boundary — foreign module paths need `integration_modules`.
4. Path `..` → `PATH_TRAVERSAL`.
5. On allow: return `envelope_hash` (FNV-1a hex of canonical fields).

No OS I/O — callers supply logical paths (from planner／diff).

## Test

```powershell
$env:Path = "$env:USERPROFILE\.cargo\bin;" + $env:Path
cd D:\AIAD\apps\sgenaxis-desktop\crates\sgenaxis-guard
cargo test
```

## Out of scope

- OS write-denial probes (GUARD-002 / later)
- Agent CLI／MCP／HoneyBadger／:8788
- Mutating approved contracts／BDD expectations
