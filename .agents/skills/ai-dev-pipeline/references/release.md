# 分支、版本、發布與回滾

## 必做（所有專案）
| 項目 | 規則 |
|---|---|
| 分支 | main 隨時可佈署；功能分支 `feature/<task-id>-<slug>`，一個 Task 一個 PR |
| 合併 | 一律 Squash and Merge；commit 用 Conventional Commits（`feat:`／`fix:`／`feat!:`） |
| 衝突 | 開發代理 rebase 並解，**解完重跑 CI 與 TDD**，不在解衝突時改行為 |
| 回滾程式 | 用 `git revert`（新 commit）；不 force push、不改 main 歷史 |
| 版本 | SemVer：不相容 → Major；相容新功能 → Minor；修正／Hotfix → Patch；RC 如 `v2.5.0-rc.1`；tag 一律 `vX.Y.Z` |
| 版本檔 | 所有版本檔（例：`Cargo.toml`、`package.json`、`tauri.conf.json`）版本一致，由同一支工具更新 |
| CHANGELOG | Keep a Changelog 分類（Added／Changed／Fixed／Security），發版必更新 |

**一般流程**：PR Green → Squash 進 main → 打 `vX.Y.Z-rc.N` → 獨立驗證代理對 RC 跑 BDD/E2E、安全掃描、效能回歸 → 高階模型或使用者核准 → 打 `vX.Y.Z` 發布。
**Hotfix**：從發布 tag 拉 `hotfix/<version>` → 寫重現 Bug 的失敗測試（Red）→ 修到 Green → 獨立驗證 → 打 Patch tag → back-merge 回 main。

## 發布前檢查
- tag 指向已驗證過的同一個 commit；版本號升級正確；CHANGELOG 有條目。
- 安裝檔已簽章（或明確標示未簽章並記 NOT RUN）。
- 有回滾計畫：回到哪個版本（`rollbackRef`）、誰執行；資料 migration 向下相容或有反向 migration。
- 核准人（`approvedBy`）是高階模型或使用者，**絕不是開發代理**。
- 回滾後補備註與事後檢討，寫進失敗經驗文件。

## 選用（只在有服務端或 updater 放量機制時才做）
不適用時不建、不填，避免過度設計。
| 機制 | 說明 |
|---|---|
| 環境 Dev／Staging／Prod | Staging 完全模擬 Prod 跑 RC；桌面 updater 頻道 `dev`／`beta`／`stable` |
| Canary／Gradual Rollout | 1% 或內部頻道 → 5% → 50% → 100%，每階段健康 Green 才升級 |
| Feature Flag | 設定檔開關；寫負責人與移除日期；不做複雜旗標平台；只在無法再切卡時用 |
| 健康指標 | 崩潰率、錯誤率、關鍵流程成功率，以及每階段觀察時間 |
| 回滾順序 | 先關 Feature Flag → 指回 `rollbackRef` → `git revert` |

## Deployment 卡（看板 level = Deployment）
狀態 Planned → Deploying → Verifying → Released（藍燈）／Rolled Back（紅燈）。
欄位：`version`、`releaseType`（Major/Minor/Patch/Hotfix/RC）、`environment`、`strategy`（Direct／Canary／Gradual／FeatureFlag）、`includes`、`gitRef`、`commitSha`、`changelogUrl`、`buildUrl`、`rollbackPlan`、`rollbackRef`、`deployedAt`、`approvedBy`；放量欄位（`rolloutPercent`、`featureFlags`、`healthChecks`）只在用到選用機制時填。Prod 必填 `rollbackPlan` 與 `approvedBy`（`validate-board.ps1` 強制）。

## 審查時
PR 標題／commit 符合 Conventional Commits；發版時 SemVer 正確、版本檔一致、CHANGELOG 有條目；Deployment 卡 `releaseType` 與升版一致、Prod 卡有 `rollbackPlan` 與非開發代理的 `approvedBy`；Hotfix 有重現測試並規劃 back-merge。
