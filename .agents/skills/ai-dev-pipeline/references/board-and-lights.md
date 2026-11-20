# 看板、工作層級與燈號

**唯一權威**：`docs/board.json`，格式與規則由 `.ai-hooks/validate-board.ps1` 強制（hook、Git hook、CI 都跑同一支）。若另有工單工具（Linear、Jira、GitHub Issues），兩邊同步，以 board.json 為準。舊的 `PROJECT-BOARD.html`／`#board-snapshot`／`zone` 寫法已停用。

## 工作層級
| 層級 | 含義 | 時間 | 估算 |
|---|---|---|---|
| Epic | 大版本、跨季度目標 | 多個 Sprint | 不估 |
| Feature | 支撐 Epic 的中型模組 | 1～2 個 Sprint | 不估 |
| Story | 使用者視角的價值切片（「作為…我想要…以便…」） | 1 個 Sprint 內 | Story Point |
| Task | 完成 Story 的技術工作；**一個代理工作階段內做完並 TDD Green** | 實際工時（小時） | 小時，**不給 Story Point** |
| PR | 一個 Task 一個 PR | — | — |

## 欄位（status）
`Backlog` → `Todo` → `In Progress` → `In Review` → `Done`（Deployment 卡另有 Planned → Deploying → Verifying → Released／Rolled Back）。
- `READY_FOR_TDD` ＝ 移到 In Review；`RESLICE_REQUIRED` ＝ 退回 Backlog；Done 依 [roles-and-gates.md](roles-and-gates.md) 的三項條件。

## 健康燈號（light，每張卡必填）
| 燈 | 含義 | 用在 |
|---|---|---|
| Gray | 未開始／暫停 | Backlog、Todo 預設；暫停也用灰並寫原因 |
| Green | 進行順利（**不代表完成**） | In Progress、In Review 且無風險 |
| Yellow | 有風險 | 工時超過估算、TDD Red 過久、被退回一次 |
| Red | 卡住或待決策 | 相依卡住、CI 失敗、`RESLICE_REQUIRED` 待處理、多次退回、**待使用者／高階決策** |
| Blue | 完成 | 只在 Done／Released |

- 黃、紅必填 `lightReason`（≤200 字）。
- **待決策**：卡設 Red，`lightReason` 以「待決策：」開頭，`notes` 條列每項決策（問題／選項／影響卡 ID／建議）。決策未關，依賴它的卡不得派工；自動派工一律跳過待決策卡。
- 上層匯總：子項全藍 → 藍；全未開始 → 灰；其餘取進行中子項最差（紅 > 黃 > 綠）。
- 產品 App 內的燈號語意另見 `docs/PRODUCT-DEVELOPMENT.md` §5.5，與開發看板無關，勿混用。

## 卡片欄位
必填：`id`、`level`、`title`、`parentId`、`status`、`light`、`createdAt`、`updatedAt`。視情況：`lightReason`、`owner`、`role`、`sprint`、`tdd`（None/Red/Green）、`ci`、`prUrl`（http(s)）、`storyPoints`（只 Story）、`hours`（只 Task）。
- Story 用 `bdd`（情境 ID、Given/When/Then 摘要、測試名稱、狀態）；Story 進 In Review／Done 時情境必須全 Green。
- Task 用 `scenarioIds` 列出涵蓋的情境。
- 時間一律 ISO 8601 含時區；`startedAt`（進 In Progress）、`completedAt`（進 Done，不可早於 startedAt）。

## 每次動卡都要做
- 更新 `updatedAt`，在 `history` 追加 `{at, from, to, by, note}`（只追加不改舊紀錄，最多 200 筆）。
- 決策、阻擋、退回原因寫進 `notes`（`at`、`by`、`text`），不刪改別人的備註。
- 只改**自己這張卡**；不整檔重寫、不用過期副本覆蓋。

## 讀取範圍（省 token，硬性）
| 角色 | 可讀 | 禁止（除非卡片 AC 明示） |
|---|---|---|
| 派工者 | 把該卡 id／BDD／TDD 封包／允許與保護範圍寫進 prompt | 叫子代理讀整份 board.json 或其他卡的報告 |
| 開發代理 | prompt 摘錄、本卡報告、本卡允許路徑 | 讀其他卡、整板搜尋 |
| 驗證代理 | 佇列中各卡的報告與測試指令 | 一次載入全部卡的備註 |
