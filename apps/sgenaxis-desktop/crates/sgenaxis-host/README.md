# sgenaxis-host (PD-HOST-01)

Tauri host domain (no WebView types here):

| Module | Role |
|--------|------|
| `lifecycle` | Booting → Ready → ShuttingDown → Stopped |
| `settings` | Persist `HostSettings` via `FileSystemPort` |
| `ipc` | Allowlisted invoke names; reject shell／exec |
| `composition` | Wire `BoxedPorts` + settings at boot |

**Not in scope:** WORK／FLOW business state, Agent spawn, HoneyBadger `:8788`／`:8787`.

## Test

```powershell
$env:Path = "$env:USERPROFILE\.cargo\bin;" + $env:Path
cd D:\AIAD\apps\sgenaxis-desktop\crates\sgenaxis-host
cargo test
```
