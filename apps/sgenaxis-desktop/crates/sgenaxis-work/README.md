# sgenaxis-work (PD-WORK-01)

專案登錄、root 綁定、執行租約。UI 切換只改視圖投影，不改寫 Run-bound root。

## BDD

`BDD-PD-WORK-01`：可登錄專案並綁 root；執行租約中拒重綁；切換只改視圖投影。

`BDD-PD-EXEC-BIND-01`：`bind_run`／`preflight_run_binding` 凍結 root＋工項＋fingerprint；與 EXEC `start_run` 一致，缺一或租約不符拒跑。

`BDD-PD-EXEC-SINGLE-01`：同時僅一活躍執行租約；第二個 `acquire_lease`／跨專案租約被拒；投影 `active_run()` 至多一筆。

`BDD-PD-EXEC-CANCEL-01`：`preflight_run_binding` 在租約仍活躍時（含同 fingerprint）回 `LeaseActive` — 禁盲目重跑；cancel／crash／exit 對帳後 `release_lease` 才可再派工。

對照舊封包語意：`BDD-WORK-001-*`（登錄／缺失／別名）、`BDD-WORK-002-01/02`（切換／租約拒重綁）。

## API

| 符號 | 角色 |
|------|------|
| `WorkspaceService` | register / rebind_root / acquire_lease / release_lease / select / projection |
| `PathProbePort` + `FakePathProbe` | 路徑探測（Fake OK） |
| `WorkspaceStorePort` + `FakeWorkspaceStore` | 專案登錄儲存（Fake OK） |
| `WorkspaceProjection` | 選中專案 vs `active_leases[].bound_root` 分離 |

## 測試

```powershell
$env:Path = "$env:USERPROFILE\.cargo\bin;" + $env:Path
cd D:\AIAD\apps\sgenaxis-desktop\crates\sgenaxis-work
cargo test
```

## 不做

- UI / Tauri command 接線（`PD-CMD-01`）
- SQLite 真 store、真 OS path probe adapter
- HoneyBadger / `:8788` / `:8787`
