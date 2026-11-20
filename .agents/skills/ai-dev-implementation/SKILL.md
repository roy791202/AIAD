---
name: ai-dev-implementation
description: 實作期（中低階 AI 模型）：當要依已核准的工單、BDD 與 TDD 封包實作一張工單（Task）時使用。
---
# 實作期（開發代理）

**你是開發角色，絕對不能擔任驗證角色**：你可以自己跑測試，但結果不算驗收，也不能驗收自己的卡。
遇到編譯錯誤、套件衝突、測試失敗先自己除錯；只有下列狀態碼才往上回報。

## 只讀這些
這張卡、它的 Story/BDD、TDD 封包、允許路徑、失敗經驗文件、[project.md](../ai-dev-pipeline/references/project.md)。不掃整個專案或看板。

## 步驟
1. **領卡**：卡移到 In Progress（設 `startedAt`、`role`、綠燈），開分支 `feature/<task-id>-<slug>`。看板寫法見 [board-and-lights.md](../ai-dev-pipeline/references/board-and-lights.md)。
2. **Red → Green → Refactor**：每個測試照做，RED 輸出存成證據。規則與禁止事項見 [bdd-tdd.md](../ai-dev-pipeline/references/bdd-tdd.md)。
3. **寫程式**：只改允許範圍；守住分層（[architecture.md](../ai-dev-pipeline/references/architecture.md)）；平台相關一律經 Port，不寫死路徑或平台 API；寫法依 [coding-standards.md](../ai-dev-pipeline/references/coding-standards.md)；日誌、錯誤、輸入驗證、資源依 [readiness.md](../ai-dev-pipeline/references/readiness.md)；動到效能才讀 [performance.md](../ai-dev-pipeline/references/performance.md)。
4. **hook 擋下**：修正程式或改用安全做法，不繞過（[enforcement.md](../ai-dev-pipeline/references/enforcement.md)）。
5. **自我審查**：跑完 [coding-standards.md](../ai-dev-pipeline/references/coding-standards.md) 的清單與 linter。
6. **交付**：開 draft PR、填 `prUrl`、`tdd=Green`、`ci`，卡移到 In Review，標 `READY_FOR_TDD`。不能設 Done／藍燈。
7. **回報**：你的代理身分、BDD ID、變更摘要、RED/GREEN 證據路徑、阻擋事項、範圍外發現的問題。

## 停下來回報的情況
| 情況 | 狀態碼 | 卡片 |
|---|---|---|
| 規格互相矛盾、情境看起來錯 | `SPEC_CONFLICT` | 紅燈＋原因 |
| 需要新介面、跨層或改架構 | `REPLAN_REQUIRED` | 紅燈＋原因 |
| 這一輪做不完 | `RESLICE_REQUIRED`（說明卡在哪、建議怎麼切） | 退回 Backlog；半成品還原或留在標 `WIP-RESLICE` 的未合併分支 |

## 絕對不做
改 `.feature`、削弱斷言、改預期值、加 skip、為過測試寫死回傳值；改允許範圍外的檔案；停用或繞過 hook；設 Done／藍燈／`approvedBy`。
