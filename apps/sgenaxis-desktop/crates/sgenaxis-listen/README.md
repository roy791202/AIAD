# sgenaxis-listen（PD-LISTEN-01 / PD-LISTEN-02 / PD-LISTEN-RECON-01）

Adapter 事件 → **debounce** → Domain Event → Dirty／投影。

## BDD

- `BDD-PD-LISTEN-01`：Adapter 事件 debounce 後驅動 Dirty；UI 只訂閱投影不直撞 OS。
- `BDD-PD-LISTEN-02`：專案 root 內檔案變更經 debounce 進 Dirty；停止 watch 無洩漏；fake 路徑仍可測。
- `BDD-PD-LISTEN-RECON-01`：監聽中行程異常結束 → `AgentReconcile`；投影與 EXEC `ExitClassification` 一致；不丟最後 chunk；不重複派發已結束 Run。

## 管線

```
FakeFsSource (tests) ｜ WinFsNotify (Windows + os-notify)
  → SourceEvent
  → EventBridge (FakeClock｜SystemClock + window)
       · Agent Exited／Failed → 立即 flush（不等 debounce）
       · 保留最後 Chunk → DomainEvent::AgentDirty(Chunk) 再 Exited
       · 非 Success → DomainEvent::AgentReconcile（待對帳；≠工項綠燈）
       · ended_runs 拒絕再 ingest 同一 RunId
  → DomainEvent
       ├─ DirtySet::mark_property
       ├─ ListenProjection::apply（classification／pending_reconcile／ended_runs）
       └─ Engine indicator tasks (listen-fs｜listen-git｜listen-agent → yellow)
UI ← Engine::subscribe / ListenProjection snapshot only
```

## 測試

```powershell
$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
cd D:\AIAD\apps\sgenaxis-desktop\crates\sgenaxis-listen
cargo test --color never
```

- Fake path：`FsNotifySource` on `FakeFsSource`（無 OS）。
- Windows：`win_fs_notify_*` 真 OS `notify`（ReadDirectoryChanges）。
- Recon：`crash_emits_reconcile_keeps_last_chunk_blocks_redispatch` 等。

## 不做（本卡）

- macOS／Linux watcher（明確 out of scope）
- 真 CLI pipe／MCP notification 宿主接線
- HoneyBadger／`:8788`／`:8787`
- 自行把看板 zone 改 green（§7.1）
