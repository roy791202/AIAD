# BDD + TDD

流程：**Story → BDD 情境 → TDD 封包 → Task 以 Red→Green→Refactor 實作 → 獨立驗證**。

## 誰負責什麼
| 產出 | 誰寫 | 誰能改 |
|---|---|---|
| `.feature` 情境 | 預製期高階模型，使用者核准 | 只有高階模型或使用者（記錄理由；PR 需 spec-change 標籤） |
| **TDD 封包**：每個情境的測試名稱、層級、斷言、預期值、fixtures、介面實測步驟 | 預製期高階模型 | 同上 |
| 測試程式碼 | 開發代理依封包寫（或啟用預製期已寫好的測試） | 開發代理可補骨架與 fixture 程式，**斷言與預期值必須與封包一致** |
| 產品程式 | 開發代理 | 開發代理 |
| 封包一致性核對與重跑 | 獨立 TDD 代理 | — |

## BDD 情境
- 每個 Story 一個 Gherkin 檔（位置與命名見 [project.md](project.md)），Given／When／Then 只寫可觀察行為，不寫實作細節。
- 情境 ID：`<Story 或卡 ID>-<序號>`。
- 必含：正常、負向（錯誤輸入、依賴失效）、邊界（min、min+1、max-1、max、空、超大）、安全（越權、注入）情境；安全、記憶體、效能案例依 [readiness.md](readiness.md)、[performance.md](performance.md)，一樣掛在情境 ID 下。

## TDD 封包
- 每個情境 ≥1 個測試，測試名稱帶情境 ID（例如 `s_12_1_顯示外送員位置`）。
- 標明層級：單元（領域層純測試）／整合（Adapter 對真實依賴）／E2E（對應 BDD）。應用層用假 Port 測。
- 含分層依賴檢查（內層不得引用外層）與各目標平台、依賴失效降級情境。
- 建工單前要能跑出**有效 RED**（因功能未做而失敗，不是編譯錯或打錯字）。

## Red → Green → Refactor（開發代理，每個測試都照做）
1. **Red**：寫或啟用測試，跑一次，確認是「功能還沒做」而失敗。把**指令與失敗輸出**存成證據（位置見 [project.md](project.md)）。
2. **Green**：只寫讓它通過的最少**正確**程式；不得為過測試寫死回傳值。
3. **Refactor**：測試保持 Green 下整理，全部測試再跑一次。
- RED 證據以**證據檔**為準，不靠 commit 順序（PR 會 Squash，且 hook 不允許留下失敗中的 commit）。
- **沒有失敗中的測試，就不寫產品程式。**
- Task 只有兩種結局：涵蓋情境全 Green，或 `RESLICE_REQUIRED`。

## 禁止（開發代理）
修改或刪除 `.feature`、削弱斷言、改預期值、新增 skip／only／ignore、只為過測試寫死回傳值。覺得情境錯了 → 回報 `SPEC_CONFLICT`。

## 追溯表
寫在 Story 卡 `bdd` 欄或 `docs/bdd/TRACE.md`：

| Story | 情境 | 測試 | Task | PR |
|---|---|---|---|---|
| S-12 | S-12-1 顯示即時位置 | `s_12_1_*`（單元）、`s_12_1.feature`（E2E） | T-31 | #45 |

## 驗收時檢查
追溯表完整；驗證代理自己重跑全 Green；RED 證據存在且早於 Green；測試斷言與封包一致；PR 沒改 `.feature`、沒削弱斷言、沒新增 skip。
