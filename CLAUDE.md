<!-- 由 tools/skills/sync_skills.py 自 .agents/skills 產生；請改來源後重跑，不要直接編輯 -->

# AI 開發流程規則（AI Dev Skills）

> 驗證角色絕對不可以是開發程式角色。

## 技能索引

- **ai-dev-pipeline**（`.agents/skills/ai-dev-pipeline/SKILL.md`）：AI 開發主索引（先讀這份）：用 AI 代理把產品或功能從規劃做到 PR 時使用。列出不變原則、流程主線、狀態碼與關卡， 並指出何時去讀哪一份技術參考（references/），不需要一次讀完全部。
- **ai-dev-preproduction**（`.agents/skills/ai-dev-preproduction/SKILL.md`）：預製期（高階 AI 模型）：當要從零規劃一個產品或新功能時使用，依序產出需求、UI/UX、架構骨架、Stories/Epics、BDD、TDD 封包、 工單與看板，並同步到使用者慣用的工單工具。
- **ai-dev-implementation**（`.agents/skills/ai-dev-implementation/SKILL.md`）：實作期（中低階 AI 模型）：當要依已核准的工單、BDD 與 TDD 封包實作一張工單（Task）時使用。
- **ai-dev-pr-acceptance**（`.agents/skills/ai-dev-pr-acceptance/SKILL.md`）：PR 驗收期（獨立 TDD 驗證代理，必要時加獨立高階審查代理）：當工單標成 READY_FOR_TDD，要依 TDD 封包重跑測試、實際操作介面截圖錄影、 審查並決定 PR 能否合併時使用。
- **ai-dev-production-readiness**（`.agents/skills/ai-dev-production-readiness/SKILL.md`）：上線就緒標準：規劃、實作或審查程式時，要確認測試策略、資料一致性與併發、可觀測性、安全防禦、記憶體、效能與發布回滾是否到位時使用。
- **ai-dev-product-tests**（`.agents/skills/ai-dev-product-tests/SKILL.md`）：產品測試索引：要為 Phase 1 業務邏輯（M01–M08）或 UI/UX 參數調整寫測試（RED）、或以獨立驗證代理重跑驗收時使用。 列出共用規則與 9 份測試參考的對照，只讀當下那一份。

開工前先載入 `ai-dev-pipeline`（主索引）；它的路由表會指出何時讀 `.agents/skills/ai-dev-pipeline/references/` 底下哪一份技術參考。不要一次讀完全部。

來源在 `.agents/skills`（進版控）；`.claude/skills` 是本機產生的副本（被 gitignore）。新 clone 或改了來源後執行 `python tools/skills/sync_skills.py`。
