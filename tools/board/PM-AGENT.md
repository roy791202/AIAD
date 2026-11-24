# PM Agent 必作事項（看板工具 · 硬性）

母對話／PM Agent 操作開發看板 **`docs/board.json`** 時必須遵守。
完整規則：`.agents/skills/ai-dev-pipeline/references/board-and-lights.md`（看板、燈號、讀取範圍）與 `roles-and-gates.md`（角色、PR、Done 條件）；SSOT 摘要亦見 `docs/PRODUCT-DEVELOPMENT.md` §7（Done 規則 §7.1、讀取範圍 §7.2、PM 必作 §7.3）。兩者衝突時以 references 為準。

燈號：**Gray** 未開始／暫停、**Green** 進行順利（不代表完成）、**Yellow** 有風險、**Red** 卡住或待決策、**Blue** 完成（只在 Done／Released）。

## 0. 寫入硬規則

- 只改**本卡**：更新 `updatedAt`；在 `history` 追加 `{at, from, to, by, note}`；決策、阻擋、退回原因追加到 `notes`（`{at, by, text}`）。只追加，不改刪舊紀錄或別人的備註。
- **禁止**整檔重寫 `docs/board.json` 或用過期副本覆蓋。
- 每次改完跑 `.ai-hooks/validate-board.ps1`，不通過不得提交。
- 永不占用 `:8788`。

## 1. 建卡（必作）

安排下一批工作時，**必須先寫入 `docs/board.json`**，不可只在對話口頭列清單：

| 步驟 | 動作 |
|------|------|
| 1 | 新增卡片：`level`（Story／Task）、`parentId` 指向上層 Epic／Feature／Story，`status=Todo`、`light=Gray` |
| 2 | 必填欄位齊：`id`／`level`／`title`／`parentId`／`status`／`light`／`createdAt`／`updatedAt`；視情況 `owner`／`role`／`hours`（只 Task）／`storyPoints`（只 Story）／`bdd` 或 `scenarioIds`；允許／保護範圍、AC、依賴寫進 `notes` |
| 3 | 上層卡 `notes` 追加「本批已建卡：…」一筆 |
| 4 | **有待 owner 決策者 → 走 §2，不得直接開工** |

## 2. 決策項目 → 紅燈（必作）

凡屬 **待決策／待核准／範圍未拍板／REPLAN／SPEC_CONFLICT／發布門檻未定** 的項目：

| 步驟 | 動作 |
|------|------|
| 1 | 建卡或在既有卡上標明決策 |
| 2 | **`light=Red`**，`lightReason` 以「**待決策：**」開頭（≤200 字）；自動派工一律跳過待決策卡 |
| 3 | `notes` 追加一筆，條列每項決策：問題／選項／影響卡 ID／建議 |
| 4 | 決策未關閉前：**禁止**把依賴該決策的卡移到 `In Progress` 或派 subagent |
| 5 | Owner 拍板後：`notes` 追加「已決：…」，紅燈解除（依狀態回 Gray／Green）；純決策卡若要設 Done 仍依 §7.1（無 PR 須註明）；再派依賴卡 |

範本 `notes` 文字：

```text
待決策事項:
- [ ] DEC-1: 問題／選項 A·B／影響 PD-XXX／建議 A
- [ ] DEC-2: …
狀態: 紅燈阻塞依賴卡派工，直至 owner 回覆。
```

## 3. 分派 subagent（必作）

決策已清或本批無決策後：

| 步驟 | 動作 |
|------|------|
| 1 | 卡 `Todo`→`In Progress`、`light=Green`、填 `startedAt`；上層卡 `notes` 記「開工：…」 |
| 2 | 每張卡 **一個** 開發代理；prompt **只含該卡欄位**（§7.2） |
| 3 | 另起 **獨立 TDD Gate**（佇列 = 本批 ID）；開發代理不可自設 Done（§7.1） |
| 4 | 開發代理標 `READY_FOR_TDD`、開 draft PR、卡移 `In Review` （交付時依自測填 `tdd=Green`；CI `guard` 要求 PR 對應卡為 `In Review`＋`tdd=Green`，涵蓋情境皆 Green）→ TDD 代理寫 `<ID>-TDD-REVIEW.md` → `TDD_PASS` 且 PR 合併後，**僅高階模型／使用者**設 `status=Done`、`light=Blue`、`completedAt` |

## 4. 角色對照

| 角色 | 必作 | 禁作 |
|------|------|------|
| **PM Agent（高階模型／母對話）** | 建卡、決策紅燈＋待決策清單、派開發／TDD、三項條件成立後設 Done／Blue、合併 PR | 跳過建卡直接開工；決策未決就派依賴卡；無 `TDD_PASS` 設 Done |
| **開發代理** | 產出＋報告＋draft PR；卡最多到 `In Review` | 設 Done／Blue／Released／`approvedBy`；讀整板 |
| **TDD 代理** | 親跑測＋ REVIEW；回報 `TDD_PASS`／`TDD_FAIL` | 設 Done／Blue；改產品程式；改測試斷言（測試基礎設施壞掉除外，需註明） |

## 5. 檢查清單（每批開工前）

- [ ] 卡片已寫入 `docs/board.json`（非僅聊天），`validate-board.ps1` 通過
- [ ] 所有決策項已 **紅燈**，`lightReason` 以「待決策：」開頭且 `notes` 有待決策清單
- [ ] 無未決決策阻塞本批，或 owner 已書面拍板
- [ ] 卡已 `In Progress`／Green＋subagent 已派（§7.2 prompt）
- [ ] TDD Gate 已掛；Done 路徑（產出＋`TDD_PASS`＋PR 合併）清楚

## 已知落差（工具尚未跟上本規則，未改程式）

- `tools/board/poll_next_work.py`：已修正（PD-BOARD-GAPS-POLL-01）。改為唯讀 `docs/board.json`，篩 `status`∈{Todo, Backlog, In Progress}，排除 Epic（除非 `--include-epic`）與待決策卡，依 `light` Red>Yellow>Gray>Green、`updatedAt` 舊→新、`id` 排序；檔案不存在或 JSON 壞回 exit 2。
- `tools/board/poll_extinguish.py`：已修正（PD-BOARD-GAPS-POLL-01）。仍一律拒絕（exit 2），訊息改為「只有高階模型／使用者才可設 Done／Blue；須獨立 `TDD_PASS` 與 PR 合併」；`docs/start-board-extinguish.cmd` 末行同步。
- `tools/board/dispatch-agents.json` 的 `skip_kinds` 依賴已停用的 `kind=decision`；應改成跳過 `light=Red` 且 `lightReason` 以「待決策：」開頭的卡。
- `tools/board/SNAPSHOT-SAFE.md`、`board_core.snapshot_safe`、`board.py report` 仍是寫 `#board-snapshot` 的舊流程。
- `docs/start-board-watch.cmd`／`docs/board_watch.py`：仍在埠 28789 提供並寫回已不存在的 `docs/PROJECT-BOARD.html`，目前無法使用；看板請直接看 `docs/board.json`。
