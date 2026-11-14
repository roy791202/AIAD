# sgenaxis-ports (PD-ADAPT-01 / PD-DEPLOY-PORT-01)

OS / CLI **Port traits only** for SGenAxis stage 2.5+.

Authority: `docs/PRODUCT-DEVELOPMENT.md` §3.2 and §4 stage 2.5.

## Ports

| Trait | Role |
|-------|------|
| `FileSystemPort` | exists / read / write_atomic / create_dir_all |
| `PathPort` | config_dir / cache_dir / join / normalize |
| `ProcessPort` | start / try_wait / cancel / try_read (`ProcessOutput`) |
| `GitPort` | status / log / diff (read; PD-GIT-01) |
| `GitWritePort` | commit / push with `GitWriteApproval` (PD-GIT-02) |
| `DeployPort` | capability / last_artifact_path / status (PD-DEPLOY-PORT-01; query only) |

Public surface uses `String` / `Vec<u8>` / opaque `ProcessId` — **no** `PathBuf`, `std::fs::File`, or `std::process::Child`.

## Dependency rule

- This crate has **zero** OS adapter deps.
- `sgenaxis-core` may later depend on **ports** (traits) but must **never** depend on `sgenaxis-adapters`.
- Adapters implement these traits in `../sgenaxis-adapters`.

## Test

Ports are traits — contract tests live in `sgenaxis-adapters`:

```powershell
cd D:\AIAD\apps\sgenaxis-desktop\crates\sgenaxis-adapters
cargo test
```

## Deploy notes

- Windows channel: WiX → MSI path convention helpers (`windows_wix_*`).
- macOS / Linux: adapters return `DeploySupport::Unsupported` (out of scope).
- Port does **not** run elevated install.

## Non-goals

Agent CLI/MCP (`PD-EXEC-*`), elevated MSI install, HoneyBadger, ports 8788/8787.
