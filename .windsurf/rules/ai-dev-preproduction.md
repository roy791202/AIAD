---
trigger: model_decision
description: "預製期（高階 AI 模型）：當要從零規劃一個產品或新功能時使用，依序產出需求、UI/UX、架構骨架、Stories/Epics、BDD、TDD 封包、 工單與看板，並同步到使用者慣用的工單工具。"
---
# 預製期（高階 AI 模型）

先讀主索引 `ai-dev-pipeline` 的不變原則與 [project.md](../../.agents/skills/ai-dev-pipeline/references/project.md)，再讀失敗經驗文件，把過去的卡關盲點寫進規格和工單。
每一步產出存入 `docs/`，**請使用者確認後才進下一步**。每步只在需要時讀對應參考。

| # | 步驟 | 產出 | 參考 |
|---|---|---|---|
| 1 | 需求羅列 | 目標使用者、核心情境、功能清單、非功能需求（平台、可用性、效能預算、讀寫比例、併發、敏感資料、日誌與監控）、範圍外、里程碑、待決問題 | [readiness.md](../../.agents/skills/ai-dev-pipeline/references/readiness.md)、[performance.md](../../.agents/skills/ai-dev-pipeline/references/performance.md) |
| 2 | UI/UX | 參考產品對照表、主要畫面、流程、空／載入／錯誤／降級狀態；刪掉超出需求的設計 | [ux.md](../../.agents/skills/ai-dev-pipeline/references/ux.md) |
| 3 | 架構骨架 | 選型與理由、捨棄方案、分層與目錄、Ports/Adapters、依賴圖、每個主要 Use Case 的資料流、交易邊界、鎖策略、錯誤與日誌格式、權限模型；依專案製作順序建出可啟動的空殼 | [architecture.md](../../.agents/skills/ai-dev-pipeline/references/architecture.md) |
| 4 | 工作層級 | Epic → Feature → Story（估 Story Point），對應模組、層級與畫面 | [board-and-lights.md](../../.agents/skills/ai-dev-pipeline/references/board-and-lights.md) |
| 5 | BDD | 每個 Story 的 `.feature`：正常、負向、邊界、安全情境 | [bdd-tdd.md](../../.agents/skills/ai-dev-pipeline/references/bdd-tdd.md) |
| 6 | TDD 封包 | 每個情境的測試名稱、層級、斷言、預期值、fixtures、介面實測步驟；追溯表；確認有效 RED | [bdd-tdd.md](../../.agents/skills/ai-dev-pipeline/references/bdd-tdd.md) |
| 7 | 工單（Task） | 見下方切片規則 | — |
| 8 | 看板 | 在 `docs/board.json` 建卡（Backlog、灰燈），通過 `validate-board.ps1`；待決事項建紅燈決策卡；同步使用者的工單工具 | [board-and-lights.md](../../.agents/skills/ai-dev-pipeline/references/board-and-lights.md) |
| 9 | 發布規劃 | 每個 Feature／Epic 的預計版本、回滾方式；有放量機制才規劃 Canary／Flag | [release.md](../../.agents/skills/ai-dev-pipeline/references/release.md) |

## 工單內容
ID、標題、所屬 Epic/Story、所屬層級、涵蓋情境 ID（`scenarioIds`）、TDD 封包路徑、**允許修改與保護的檔案範圍**、相依工單、完成定義、估計工時（小時，不給 Story Point）。寫到中低階模型不用猜就能實作；盡量一張只動一層。

## 切片規則：一輪做完、TDD 交付，不留半成品
- 垂直切片：每張交付一個可觀察的行為，TDD 能在一個代理工作階段內全部轉 Green。
- 參考上限：情境 1–3 個、修改檔案約 5 個、最多跨 2 層、一個代理的上下文放得下；超過就再切。
- 每張可獨立合併，不依賴未完成的卡；不開「第 1/N 部分」。
- Feature Flag 只在無法再切時用，寫明理由與移除時機。

## 完成關卡
每個 Story ≥1 情境、每個情境有測試且能跑出有效 RED、每張 Task 列出涵蓋情境；架構選型有理由且符合分層方向；UI/UX 有參考依據且無過度設計；看板通過驗證、估算齊全；每張工單符合切片規則；**使用者已核准**。
