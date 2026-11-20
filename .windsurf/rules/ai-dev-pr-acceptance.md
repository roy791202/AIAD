---
trigger: model_decision
description: "PR 驗收期（獨立 TDD 驗證代理，必要時加獨立高階審查代理）：當工單標成 READY_FOR_TDD，要依 TDD 封包重跑測試、實際操作介面截圖錄影、 審查並決定 PR 能否合併時使用。"
---
# PR 驗收期

## 硬性規則
- 你必須是**另外啟動的獨立代理**，不是寫這張卡的代理，也不延續它的對話。
- 不改產品程式、不改測試斷言；發現問題只記錄並退回。
- 不採信開發代理的「已測過」，一切重跑。
- 驗收紀錄寫明開發者與驗證者身分；相同即無效。
角色、何時需要高階審查、Done 條件見 [roles-and-gates.md](../../.agents/skills/ai-dev-pipeline/references/roles-and-gates.md)。

## A. 實測（獨立 TDD 代理，一律執行）
1. 核對測試與 TDD 封包一致（斷言、預期值沒被削弱、沒新增 skip、RED 證據存在）——[bdd-tdd.md](../../.agents/skills/ai-dev-pipeline/references/bdd-tdd.md)。
2. 重跑自動化測試（含分層依賴檢查、覆蓋率、安全與錯誤情境、有預算的效能回歸）；能在多個平台跑就各跑一次。
3. 依封包的介面實測步驟**實際操作產品介面**，每步截圖、關鍵流程錄影，存到證據位置（[project.md](../../.agents/skills/ai-dev-pipeline/references/project.md)）。
4. 逐項記 PASS／FAIL；無法執行記 NOT RUN 並寫原因，不得偽造 PASS。
5. 寫驗收報告，結論 `TDD_PASS` 或 `TDD_FAIL`；FAIL 附失敗步驟與截圖退回實作期。

## B. 審查（獨立高階代理；符合必要條件時執行）
每項明顯違反就退回；小問題列建議不擋 PR。

| 檢查 | 依據 |
|---|---|
| 只改允許範圍；開發者 ≠ 驗證者 | 工單、[roles-and-gates.md](../../.agents/skills/ai-dev-pipeline/references/roles-and-gates.md) |
| 架構與分層、Port、耦合、平台寫死 | [architecture.md](../../.agents/skills/ai-dev-pipeline/references/architecture.md) |
| Clean Code 與寫法 | [coding-standards.md](../../.agents/skills/ai-dev-pipeline/references/coding-standards.md) |
| 測試、交易、併發、日誌、安全、記憶體 | [readiness.md](../../.agents/skills/ai-dev-pipeline/references/readiness.md) |
| 複雜度與效能宣稱 | [performance.md](../../.agents/skills/ai-dev-pipeline/references/performance.md) |
| BDD/TDD 追溯、RED 證據、未改情境 | [bdd-tdd.md](../../.agents/skills/ai-dev-pipeline/references/bdd-tdd.md) |
| 完整性：沒有只做一部分、沒有 TODO 樁 | 工單（範圍太大退回預製期重切） |
| hook／CI 未被修改或繞過、CI guard 全過 | [enforcement.md](../../.agents/skills/ai-dev-pipeline/references/enforcement.md) |
| 看板：一 PR 一 Task、燈號與實況相符、board.json 通過驗證 | [board-and-lights.md](../../.agents/skills/ai-dev-pipeline/references/board-and-lights.md) |
| Conventional Commits、版本與 CHANGELOG（發版時） | [release.md](../../.agents/skills/ai-dev-pipeline/references/release.md) |

## 結果
- 全部通過 → 回報給高階模型／Owner，由他們把 draft PR 轉 ready 並合併；合併後才設 Done／藍燈。
- 不通過 → 列出要修改的項目，卡退回 In Progress（黃或紅燈＋原因），附證據。
- **完成關卡**：有產出、獨立 `TDD_PASS`、（必要時）獨立審查通過、PR 已合併。
