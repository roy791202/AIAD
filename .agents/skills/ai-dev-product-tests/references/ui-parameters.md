# UI/UX 參數：測試參考

> 路徑以 repo 根 `D:\AIAD\.claude\worktrees\skills-index-structure-f8398d` 為基準；產品前綴 `apps/sgenaxis-desktop/`（下稱 `APP/`）。
> 狀態語意：**已核准**＝有規格／設計文件出處，或依 L3 決策 1 列「模組採納」（RC-29 SET01–SET14、ui-spec ALIGNED PROPOSAL），核准依據欄會註明；**待確認**＝只在程式碼或參考稿找到，沒有正式規格，不得判 TDD_PASS；**待決策**＝依賴 G01–G04（全部 PENDING_ARCHITECTURE_REVIEW），不寫成可驗收斷言。
> 「現況」欄的數值是程式目前的行為，只供盤點，不是規則。

## 1. 範圍與來源

| 功能 ID | 規格連結 | 交付卡 | BDD 場景 |
|---|---|---|---|
| F02 產品模板與偏好（專案偏好設定） | `docs/requirements-confirmation/phase1-spec/index.html#F02`（資料影響：偏好排除憑證、機器路徑，標「建議」）；決策 D05（同檔決策表：預設暫不套用、可選系統方案或匯入副本、憑證不帶入）；`docs/requirements-confirmation/requirements.json` items[RC-29].historical_bdd（SET01–SET14，註記「已批准不撤銷」，但 item.status＝NEEDS_CONFIRMATION） | `tasks/PD-P1-F02-DELIVERY-01.json`（BLOCKED_PENDING_APPROVED_ENVELOPE_AND_VALID_RED） | phase1.feature BDD-03／BDD-04 只講模板，**偏好沒有 phase1 BDD**；只能用 RC-29 的 SET01–SET14 |
| 設計 tokens | `docs/ui-design/ui-spec.json` → `tokens`；`metadata.image_note`、`metadata.mock_as_product_pass`；`docs/ui-design/README.md`（權威順序：Workbench 優先，圖稿不是證據） | 沒有專屬卡；跨 F04 的 UI 呈現（`PD-P1-F04-DELIVERY-01`） | 無 |
| UI Designer 元件屬性 | **沒有正式規格**。參考：`fixtures/sgenaxis-design/README.md`（format、預設路徑）、`fixtures/sgenaxis-design/sample.sgendesign`、`docs/Final-2026-10-25/UI-bhv.html` §6.1／§7（只有屬性名稱，沒有範圍） | `tasks/PD-P1-F04-DELIVERY-01.json`（依賴 G01、G04） | phase1.feature BDD-05／BDD-06（只講有 UI 才開窗，不講屬性） |
| 架構 DAG Inspector 節點屬性 | **沒有正式規格**。參考：`docs/Final-2026-10-25/SGGenAxis_Node_Architecture_Specification.html`（Module 收合／order 語意）、`UI-bhv.html` §2.2（UI Layer 屬性名稱） | `tasks/PD-P1-F04-DELIVERY-01.json` | 同上 |

盤點用的程式碼：
- 偏好：`APP/crates/sgenaxis-spec/src/project_preferences.rs`、`APP/ui/project-preferences-ui.js`、`APP/crates/sgenaxis-host/src/project_preferences.rs`、`APP/src-tauri` 的 `host_project_preferences_*` 指令。
- tokens：`APP/ui/styles.css` 的 `:root`、`APP/src-tauri/tauri.conf.json`（視窗尺寸）。
- Designer：`APP/ui/app.js`（`DESIGN_*`、`setDesignGridPx`、`setDesignFormSize`、`applyPropsFromInputs`、`UI_BHV_SECTIONS`）、`APP/ui/index.html`（`des*` 控制項）、`APP/crates/sgenaxis-host/src/uidesign_doc.rs`、`APP/src-tauri/src/commands.rs`（`uidesign_save_design`／`uidesign_load_design`）。
- 架構 DAG：`APP/ui/app.js`（`ARCH_*`、`setArchGridPx`、`setArchFormSize`、`setArchZoom`、`snapArchNode`、`applyArchInspectorInputs`、`readArchCommonInspector`、`archDocToXml`）、`APP/ui/index.html`（`archNode*`、`archWi*`、`archDep*`、`archUi*`）。

## 2. 業務規則

### 2.1 專案偏好設定

#### 參數表

存放位置：專案根下的 `.sgenaxis/preferences.json`（`PREFERENCES_PATH`），由 `host_project_preferences_save` 寫入。影響元件：Settings 的 `#project-policy-panel`（`data-policy=*`）、新建專案對話框「是否套用專案偏好設定？」。

| 參數 | 型別 | 預設 | 最小 | 最大 | 單位 | 存放位置 | 影響元件 | 狀態(已核准/待確認/待決策) |
|---|---|---|---|---|---|---|---|---|
| `format` / `formatVersion` | 字串／整數（固定） | `sgenaxis.project-preferences` / `1` | — | — | — | preferences.json 根 | 載入、匯入 | 已核准（「版本不支援要拒絕」：SET13）；字面值只在程式中 |
| `presetId` | 列舉 custom／conservative／balanced／throughput | 下拉預設 conservative；UI 保存時一律 `custom` | — | — | — | 根 | `data-policy="preset"`、新建對話框 | 已核准（套用後改成自訂，系統方案不變：SET01）；列舉值待確認 |
| 方案數值（每批／並行） | 整數對 | 保守 1/1、平衡 4/2、效率 8/4 | — | — | Task | `preset()` 程式常數 | 方案下拉文字 | 待確認（只在程式與 UI 文字，規格沒寫數值） |
| `modelPolicy.allowedModelIds` | 字串陣列（UI 用逗號分隔） | `[]` | 0 筆 | 未定義 | — | modelPolicy | `data-policy="modelIds"` | 待確認（不可重複、不可空白只在程式） |
| `modelPolicy.preferredModelId` | 字串或 null | null | — | — | — | modelPolicy | `data-policy="preferred"` | 待確認（必須在允許清單內只在程式；RC-23 BATCH02 只說不可換成未允許的模型） |
| `budget.maxInputTokens` | u64 或 null | null（未配置） | 1 | UI：9007199254740991（JS 安全整數上限）／Rust：18446744073709551615 | token | budget | `data-policy="input"` | 已核准：負數／不合法要拒絕（SET02）；上下限數值待確認；「空白＝未配置」待確認（SET02 字面寫「儲存空白…拒絕」，跟現況相反） |
| `budget.maxOutputTokens` | 同上 | null | 1 | 同上 | token | budget | `data-policy="output"` | 同上 |
| `budget.maxWallTimeSeconds` | 同上 | null | 1 | 同上 | 秒 | budget | `data-policy="seconds"` | 同上 |
| `batch.maxTasks` | u64 | 方案值；未配置時欄位顯示 1 | 1 | UI 9007199254740991／Rust u64 上限 | Task／批 | batch | `data-policy="tasks"` | 已核准：不合法要拒絕（SET02）；數值範圍待確認 |
| `batch.maxConcurrent` | u64 | 方案值；未配置時顯示 1 | 1 | ＝`maxTasks` | Task | batch | `data-policy="concurrent"` | 已核准：不合法要拒絕（SET02）；「不可大於 maxTasks」待確認（只在程式） |
| `batch.mode` / `batch.onLimit` | 列舉（固定 `suggest`／`block`） | suggest／block | — | — | — | batch | UI 沒有控制項 | 待確認（RC-23 問題「超額是否一律停止？」還沒回答） |
| `workflow.confirmBeforeRun` | 布林（固定 true） | true | — | — | — | workflow | UI 沒有控制項 | 待確認 |

#### 已核准

| 規則 ID | 規則 | 規格出處 | 核准依據 |
|---|---|---|---|
| R-UI-01 | 套用系統方案後調整再保存，結果是自訂政策；系統方案本身不被改寫 | requirements.json RC-29 SET01；D05 | 模組採納：RC-29 SET01（`requirements.json` items[RC-29].historical_bdd） |
| R-UI-02 | 保存負數或不合法上限時拒絕、保留原設定，並顯示欄位原因 | RC-29 SET02 | 模組採納：RC-29 SET02（`requirements.json` items[RC-29].historical_bdd） |
| R-UI-03 | 保存成功後重新開啟設定，或關閉再開專案，讀回相同的值與版本，不被本機預設悄悄取代 | RC-29 SET03、SET09 | 模組採納：RC-29 SET03、SET09（`requirements.json` items[RC-29].historical_bdd） |
| R-UI-04 | 兩個視窗基於同一版本，第二個保存過期修改時要回報衝突，不可覆寫 | RC-29 SET05 | 模組採納：RC-29 SET05（`requirements.json` items[RC-29].historical_bdd） |
| R-UI-05 | 保存時發生權限或 IO 失敗，原設定仍有效，並回報失敗 | RC-29 SET06 | 模組採納：RC-29 SET06（`requirements.json` items[RC-29].historical_bdd） |
| R-UI-06 | 專案 A、B 各自保存政策；切換專案時只顯示所選專案的值，不外洩也不覆寫 | RC-29 SET08 | 模組採納：RC-29 SET08（`requirements.json` items[RC-29].historical_bdd） |
| R-UI-07 | 沒有綁定專案時禁止保存，並提示先開專案 | RC-29 SET10 | 模組採納：RC-29 SET10（`requirements.json` items[RC-29].historical_bdd） |
| R-UI-08 | 匯入偏好檔時在新專案存一份獨立副本，來源不變，不帶入憑證或 Run 成本紀錄 | RC-29 SET12；F02 資料影響（偏好排除憑證、機器路徑）；D05 | 模組採納：RC-29 SET12（`requirements.json` items[RC-29].historical_bdd） |
| R-UI-09 | 偏好檔格式錯誤或版本不支援時拒絕並顯示原因，不宣稱套用成功 | RC-29 SET13 | 模組採納：RC-29 SET13（`requirements.json` items[RC-29].historical_bdd） |
| R-UI-10 | 新建專案時提供系統方案、匯入、暫不套用三個選項；選暫不套用時清楚標示尚未配置，不套用其他專案的偏好 | RC-29 SET11、SET14；D05 | 模組採納：RC-29 SET11、SET14（`requirements.json` items[RC-29].historical_bdd） |

#### 待決策

| 規則 ID | 卡在 | 目前選項 | 開發期處理 |
|---|---|---|---|
| R-UI-11 | G02（交易／Undo 協定） | 偏好修改是否進文件 Undo 堆疊：(a) 不進，只能「重新載入」放棄草稿；(b) 進單文件 Undo | 測試矩陣列「Undo 還原」為待決策；只驗現況「重新載入會先問是否捨棄」，不寫 Undo 斷言 |

### 2.2 設計 tokens

#### 參數表

規格存放：`docs/ui-design/ui-spec.json` → `tokens`。實作存放：`APP/ui/styles.css` 的 `:root`；最小視窗在 `APP/src-tauri/tauri.conf.json`。tokens 是建置時的常數，沒有使用者可調的 UI，也不會寫進專案。

| 參數 | 型別 | 預設 | 最小 | 最大 | 單位 | 存放位置 | 影響元件 | 狀態(已核准/待確認/待決策) |
|---|---|---|---|---|---|---|---|---|
| background / panel / panelRaised / border | 色碼 | #101112／#1b1d1f／#23262a／#34383e | — | — | hex | ui-spec tokens → css `--bg-window`／`--bg-panel`／`--bg-panel-raised`／`--border-color` | 視窗底色、面板、邊框 | 已核准 |
| text / muted | 色碼 | #eef0f3／#aeb5bf | — | — | hex | → `--text-primary`／`--text-secondary`（css 的 `--text-muted` 是 #6e7681，名稱對不上） | 文字 | 已核准（對應關係待確認） |
| blue / gray | 色碼 | #246bff／#a4adba | — | — | hex | → `--color-blue`／`--color-gray` | 主要按鈕、次要狀態 | 已核准 |
| running / attention / failed / complete | 色碼 | #56a8ff／#f2b544／#f07979／#5bc98b | — | — | hex | → css 找不到 #56a8ff；其餘對到 `--color-yellow`／`--color-red`／`--color-green` | 狀態燈、徽章 | 已核准（running 沒實作） |
| font / mono | 字型堆疊 | Segoe UI / Microsoft JhengHei；Cascadia Code / Consolas | — | — | — | → `--font-ui`／`--font-mono` | 全域文字、程式碼 | 已核准 |
| body_px / secondary_px / heading_px | 整數 | 14／12／18 | — | — | px | 只在 tokens；css 沒有對應變數 | 本文、次要文字、標題 | 已核准 |
| control_height_px | 整數 | 32 | — | — | px | 只在 tokens | 按鈕、輸入框高度 | 已核准 |
| radius_px | 整數 | 4 | — | — | px | css 是 `--radius-sm/md/lg`＝3/5/8 | 圓角 | 已核准（現況不一致） |
| spacing_px | 整數陣列 | [4, 8, 12, 16, 24] | 4 | 24 | px | 只在 tokens | 間距 | 已核准 |
| reference_canvas | 寬×高 | 1536×1024 | — | — | px | tokens | 設計稿基準 | 已核准 |
| min_window | 寬×高 | 1024×720 | 1024×720 | — | px | tokens；tauri.conf.json 是 `minWidth 960`／`minHeight 600` | 主視窗最小尺寸 | 已核准（現況不一致） |

#### 已核准

| 規則 ID | 規則 | 規格出處 | 核准依據 |
|---|---|---|---|
| R-UI-12 | 畫面的色彩 token 和 `tokens` 的色碼一致（每一個顏色都要有對應的 CSS 值） | ui-spec.json `tokens.background`…`tokens.complete` | 模組採納：ui-spec ALIGNED PROPOSAL（`docs/ui-design/verification.json:14` acceptance） |
| R-UI-13 | 字型與字級（本文 14、次要 12、標題 18 px）與 tokens 一致 | ui-spec.json `tokens.font`／`mono`／`body_px`／`secondary_px`／`heading_px` | 模組採納：ui-spec ALIGNED PROPOSAL（`docs/ui-design/verification.json:14` acceptance） |
| R-UI-14 | 控制項高度 32 px、圓角 4 px、間距只用 4/8/12/16/24 px | ui-spec.json `tokens.control_height_px`／`radius_px`／`spacing_px` | 模組採納：ui-spec ALIGNED PROPOSAL（`docs/ui-design/verification.json:14` acceptance） |
| R-UI-15 | 主視窗不可縮小到 1024×720 以下 | ui-spec.json `tokens.min_window` | 模組採納：ui-spec ALIGNED PROPOSAL（`docs/ui-design/verification.json:14` acceptance） |
| R-UI-16 | `screens/*.png` 與 mock 的綠燈只是示意，不可當產品 PASS 證據 | ui-spec.json `metadata.image_note`、`metadata.mock_as_product_pass=false`；docs/ui-design/README.md「圖稿非證據」 | 模組採納：ui-spec ALIGNED PROPOSAL（`docs/ui-design/verification.json:14` acceptance） |

> 注意：ui-spec `metadata.status`＝DESIGN ALIGNMENT，`verification.json.acceptance`＝ALIGNED PROPOSAL，README 也寫「不批准架構」。依 L3 決策 1，token 值列「已核准（模組採納）」，可寫成斷言；但 running 色、圓角、最小視窗三項和實作衝突，先暫不斷言（見 §7）。

#### 待決策

| 規則 ID | 卡在 | 目前選項 | 開發期處理 |
|---|---|---|---|
| — | 沒有規則依賴 G01–G04 | — | — |

### 2.3 UI Designer 元件屬性（無正式規格，全部待確認）

#### 參數表

存放位置有兩條，而且不一致：
- (A) `design/main.sgendesign`：經 `uidesign_save_design`。HOST 的 `DesignMeta` 只有 `title`／`updatedAt`／`targetStack`，`DesignNode` 也沒有 `scope`／`uiExclusive`／`properties`；serde 預設會**丟棄**沒宣告的欄位，所以 `meta.gridSize`、`meta.formSize`、`meta.guides`、`node.properties` 存檔後讀回可能遺失（M02 module-spec 決策 D2 也記錄「HOST DesignMeta 與 JS 擴充 metadata 未全對齊」）。
- (B) 場景套件 `scene/default.esui`（`scene_save`）：XML 屬性會寫出 `gridSize`、`formSize`。

| 參數 | 型別 | 預設 | 最小 | 最大 | 單位 | 存放位置 | 影響元件 | 狀態(已核准/待確認/待決策) |
|---|---|---|---|---|---|---|---|---|
| `meta.gridSize`（Grid 格距） | 整數 | 8 | 0（關）；1 會被改成 2 | 64（超過夾成 64） | px | (A) 會丟失／(B) | `#desGridSize`（選項 0/4/8/10/16/20/25/32）、`#designBoard` 的 `--grid-size` | 待確認 |
| 吸附距離 `DESIGN_SNAP_PX` | 常數 | 8 | — | — | px | 程式常數 | 拖曳吸附、對齊線 | 待確認 |
| `meta.formSize`／Form 根節點的 `w`、`h` | 整數 | 800×600 | 64（低於 64 會**重設成 800／600**，不是夾到 64） | 7680×4320 | px | (A) w/h 保留、formSize 會丟失／(B) | `#desFormSize`（9 個預設＋custom） | 待確認 |
| `props.x`／`props.y` | 數字 | 0（新放置的位置） | 0（拖曳與 Form 改尺寸時夾限；Inspector 直接輸入**不夾**） | Form 寬／高 − 節點寬／高 | px | (A)(B) | `#desX`／`#desY`、畫布位置 | 待確認 |
| `props.w`／`props.h` | 數字 | 依元件；畫面備用值 120×32 | 8 | 未定義 | px | (A)(B) | `#desW`／`#desH` | 待確認 |
| `props.zIndex` | 數字 | 0 | 未定義 | 未定義 | — | (A)(B) | `#desZ`、重疊順序 | 待確認 |
| `props.name` | 字串 | 元件類型名 | — | — | — | (A)(B) | `#desName`；Form 的名稱同時寫 `meta.title` | 待確認 |
| `props.layout`（只有 Form） | 列舉 none／hbox／vbox／grid | none | — | — | — | (A)(B) | `#desLayoutMode`；非 none 時不吸附 | 待確認 |
| `behaviorHints`／`bddHint`／`tddHint` | 字串陣列（逗號分隔）／字串 | 空 | — | — | — | (A)(B) | `#desBehavior`／`#desBdd`／`#desTdd` | 待確認 |
| `meta.guides.v`／`.h` | 數字陣列 | [] | — | — | px | (A) 會丟失 | 尺規拉出的參考線 | 待確認 |
| 畫布縮放 `designZoom` | 數字 | 1 | 0.4 | 2（每次 0.1） | 倍 | 不存檔 | `#designBoard` transform | 待確認 |
| UI 種類專屬屬性 `node.properties[*]`（約 80 種，例如 Slider 的 value/min/max/step、TextInput 的 maxLength、Overlay 的 zIndex） | 現況一律存字串 | "" | 未定義 | 未定義 | 依屬性 | (A) 會丟失 | `#desKindProps [data-ui-prop]` | 待確認（屬性名稱來自 UI-bhv.html §7，沒有型別和範圍） |
| `product_pass` | 布林（固定 false） | false | — | — | — | (A) | 存檔回應、預覽橫幅 | 待確認（HOST 拒絕 true；fixtures README 寫「不是驗收 PASS」） |

#### 已核准

| 規則 ID | 規則 | 規格出處 | 核准依據 |
|---|---|---|---|
| — | 沒有正式規格，沒有已核准規則 | — | — |

#### 待確認（只列現況，供 Owner 確認後才能轉成規則）

| 規則 ID | 現況行為 | 出處（程式） |
|---|---|---|
| R-UI-17 | Grid 格距 0＝關閉；1 改成 2；超過 64 夾成 64；非數字回到 8 | app.js `setDesignGridPx` |
| R-UI-18 | 拖曳時距離參考線 8 px 以內就吸附；沒有參考線時對齊 Grid | app.js `DESIGN_SNAP_PX`、`snapNodeToGuides` |
| R-UI-19 | Form 尺寸 64–7680 × 64–4320；低於 64 重設成 800×600；改 Form 尺寸時子元件夾回 Form 內 | app.js `setDesignFormSize`、`clampDesignNodeInForm` |
| R-UI-20 | x、y 在拖曳或 Form 改尺寸時夾在 Form 內；Inspector 輸入負數不夾 | app.js `clampDesignNodeInForm`、`applyPropsFromInputs` |
| R-UI-21 | w、h 最小 8；空白不改；輸入非數字會變成 NaN（`Math.max(8, NaN)`） | app.js `applyPropsFromInputs` |
| R-UI-22 | zIndex 任意數字，沒有上下限 | app.js `applyPropsFromInputs` |
| R-UI-23 | 縮放 0.4–2 倍，不存檔 | app.js `setDesignZoom` |
| R-UI-24 | UI 種類專屬屬性全部存成字串，沒有型別或範圍檢查 | app.js `ensureUiKindProperties`、`UI_BHV_SECTIONS` |
| R-UI-25 | Form 名稱同步成 `meta.title` | app.js `applyPropsFromInputs` |
| R-UI-26 | 設計檔 `product_pass` 只能是 false；載入 true 會被拒絕 | uidesign_doc.rs `validate` |
| R-UI-27 | 經 (A) 存檔再讀回時，JS 擴充的 meta／properties 是否保留——現況會丟失 | uidesign_doc.rs `DesignMeta`／`DesignNode`；commands.rs `uidesign_save_design` |

#### 待決策

| 規則 ID | 卡在 | 目前選項 | 開發期處理 |
|---|---|---|---|
| R-UI-28 | G02（Undo）＋G01（檔案與身分：設計檔權威是 .sgendesign 還是 .esui） | Undo：(a) 屬性修改進單文件 Undo；(b) 只有「清空」能還原（現況 `designRecoveryHistory`）。權威檔：(A) 或 (B) | 「存檔讀回一致」只能記錄現況，不寫 PASS 斷言；Undo 列待決策 |

### 2.4 架構 DAG Inspector 節點屬性（無正式規格，全部待確認）

#### 參數表

存放位置：場景套件 `scene/default.esml`（`scene_save`，XML，`archDocToXml`）；草稿另存瀏覽器 localStorage `sgenaxis.arch.draft.v1`。影響元件：Inspector `archNode*`／`archWi*`／`archDep*`／`archUi*`、畫布 `#archBoard`。

| 參數 | 型別 | 預設 | 最小 | 最大 | 單位 | 存放位置 | 影響元件 | 狀態(已核准/待確認/待決策) |
|---|---|---|---|---|---|---|---|---|
| `meta.gridSize`（架構 Grid） | 整數 | 8 | 0（關）；1 改成 2 | 64 | px | esml meta | `#archGridSize`（0/8/16/24） | 待確認 |
| 吸附距離 `ARCH_SNAP_PX` | 常數 | 8 | — | — | px | 常數 | 拖曳吸附 | 待確認 |
| `meta.formSize`（最小底板） | 寬×高 | 1280×720 | 320×240（低於就夾到這裡） | 未定義（Grid 無限延伸） | px | esml meta | `#archFormSize` | 待確認 |
| 縮放 `archZoom` | 數字 | 1 | 0.4 | 2 | 倍 | viewports（meta） | 畫布 | 待確認 |
| 節點 `x`／`y` | 數字 | 放置位置 | 0（負數夾成 0） | 未定義 | px | esml | 拖曳、吸附 | 待確認 |
| `name` | 字串 | 類別名 | 空白就保留舊名 | — | — | esml | `#archNodeName` | 待確認 |
| `kind` | 列舉 17 種（API…Layer） | 建立時決定 | — | — | — | esml | `#archNodeType`（唯讀，建立後不能改） | 待確認 |
| `packsKind`（Layer） | 列舉，由子物件推導 | — | — | — | — | esml | `#archNodePacksKind`（disabled） | 待確認 |
| `id`／`createdAt`／`updatedAt` | 字串（唯讀） | 系統產生 | — | — | — | esml | 唯讀欄位 | 待確認 |
| `description`／`contentHash` | 字串 | "" | — | — | — | contentHash 不在 esml 節點屬性清單裡 | `#archNodeDesc`／`#archNodeContentHash` | 待確認 |
| `schemaVersion` | 字串 | "1"（空白改成 "1"） | — | — | — | esml | `#archNodeSchemaVersion` | 待確認 |
| `dependencies`／`bddSpecs`／`tddSpecs` | 每行一筆 | [] | — | — | — | 節點 | textarea | 待確認 |
| `collapsed` | 布林 | false | — | — | — | esml | `#archNodeCollapsed` | 待確認（Node Spec：收合只改 UI Layout，不改架構關係） |
| `layoutOrder`（order） | 數字 | 空 | 未定義（step 1） | 未定義 | — | esml `order` | `#archNodeOrder`（只在節點有 moduleRef 時可改） | 待確認（Node Spec：視覺順序不是執行順序） |
| `width`／`height` | 數字或 ""（自動） | ""（自動） | HTML min=1（但輸入負數照存）；0 變成自動 | 未定義 | px | width／height 不在 esml 節點屬性清單裡 | `#archNodeWidth`／`#archNodeHeight` | 待確認 |
| WorkItem `inputTokens`／`outputTokens` | 數字 | 空 | HTML min=0 | 未定義 | token | 節點 | `#archWiInTok`／`#archWiOutTok` | 待確認 |
| WorkItem 列舉 | workflowStatus（7）／testStatus（6）／priority（low…critical） | 第一個選項 | — | — | — | 節點 | `#archWiWorkflow`／`#archWiTest`／`#archWiPriority`；`#archWiLamp` 推導、唯讀 | 待確認 |
| WorkItem 日期 | date | 空 | — | — | 日 | 節點 | build／modified／completed date | 待確認 |
| Deployment `timeoutSeconds` | 數字 | 空 | HTML min=0 | 未定義 | 秒 | 節點 | `#archDepTimeout` | 待確認 |
| Deployment 列舉 | deploymentType（6）／artifactType（4）／environment（3）／strategy（4）／executionStatus（6） | 第一個選項 | — | — | — | esml 只寫 deploymentType、targetRef | `#archDep*` | 待確認 |
| Deployment `secretRefs` | 字串（只存參照） | 空 | — | — | — | 節點 | `#archDepSecretRefs` | 待確認 |
| UI Layer `uiDefinitionRef`／`themeRef`／`rootNodeId`／`assetRefs` | 字串／每行一筆 | `design/main.sgendesign`／空 | — | — | — | esml | `#archUi*` | 待確認（屬性名稱見 UI-bhv.html §2.2） |

#### 已核准

| 規則 ID | 規則 | 規格出處 | 核准依據 |
|---|---|---|---|
| — | 沒有正式規格，沒有已核准規則 | — | — |

#### 待確認（只列現況）

| 規則 ID | 現況行為 | 出處（程式） |
|---|---|---|
| R-UI-29 | 架構 Grid：0 關、1 改成 2、超過 64 夾成 64、非數字回到 8 | app.js `setArchGridPx` |
| R-UI-30 | 底板最小 320×240，沒有上限；格式不是 `寬x高` 時忽略 | app.js `setArchFormSize` |
| R-UI-31 | 縮放 0.4–2 倍，非數字回到 1 | app.js `setArchZoom` |
| R-UI-32 | 拖曳吸附 8 px；沒命中時對齊 Grid；座標不可為負 | app.js `snapArchNode`、`snapInteriorCoord` |
| R-UI-33 | width／height 空白＝自動；0 或非數字＝自動；負數照存 | app.js `readArchCommonInspector` |
| R-UI-34 | order 只在有 moduleRef 時可改；非數字不改 | app.js `applyArchInspectorInputs` |
| R-UI-35 | name 空白保留舊名；schemaVersion 空白改成 "1" | 同上、`readArchCommonInspector` |
| R-UI-36 | kind 建立後不能改；Layer 的 packsKind 只從子物件推導 | app.js `applyArchInspectorInputs`、index.html `archNodeHint` |
| R-UI-37 | WorkItem tokens 非數字不改；負數只靠 HTML min=0，程式不擋 | app.js `applyArchInspectorInputs` |
| R-UI-38 | Deployment timeoutSeconds 同 R-UI-37 | 同上 |
| R-UI-39 | 列舉欄位只能選 index.html 列出的值；lamp 是推導值、不能手改 | index.html `archWi*`／`archDep*` |
| R-UI-40 | UI Layer 的 uiDefinitionRef 空白保留舊值 | app.js `applyArchInspectorInputs` |
| R-UI-41 | 寫入 esml 的節點屬性只有 id、name、kind、x、y、collapsed、order、schemaVersion、createdAt、updatedAt、UI Layer 與 deploymentType 等欄位；contentHash、width、height、WorkItem 大部分欄位不在這份清單裡（是否由子元素保存待確認） | app.js `archDocToXml` |

#### 待決策

| 規則 ID | 卡在 | 目前選項 | 開發期處理 |
|---|---|---|---|
| R-UI-42 | G02（Undo）＋G01（架構檔身分：localStorage 草稿與 scene/default.esml 誰是權威） | Undo：Ctrl+Z 現在走 `edit_undo → Core EditSession`（復原選取），不是 Inspector 屬性 Undo | 「Undo 還原」列待決策；「重開後保留」只記錄現況 |

## 3. 已有測試對照

| 規則 ID | 測試檔::函式 | 已涵蓋類別 | 缺口 |
|---|---|---|---|
| R-UI-01 | `APP/crates/sgenaxis-spec/tests/project_preferences.rs::presets_have_approved_limits_and_independent_custom_copies`；`APP/ui/project-preferences-ui.test.cjs::project controls produce exact v1 draft without credentials`（presetId＝custom） | 正常 | 沒有 UI 端「套用方案→改→保存→方案值不變」的整合測試 |
| R-UI-02 | spec::`zero_limits_and_concurrency_above_batch_are_rejected`、`negative_fractional_overflow_and_wrong_types_are_rejected`、`invalid_models_and_preferred_membership_are_rejected`；ui::`invalid numbers and unsafe JS integers cannot silently round`、`concurrency and membership rejected before command`；host `APP/crates/sgenaxis-host/tests/project_preferences.rs::invalid_root_and_invalid_draft_have_zero_writes` | 邊界、無效輸入 | 沒驗「顯示欄位原因」：狀態列只有一行通用訊息，沒有對應到欄位 |
| R-UI-03 | host::`save_reopen_and_project_isolation_use_exact_digest`；command `APP/src-tauri/tests/project_preferences_commands.rs::current_project_load_save_and_stale_digest` | 正常 | 原生 Tauri 重開 NOT RUN（RC-29 註記） |
| R-UI-04 | host::`stale_and_missing_digests_never_overwrite_existing_policy`、`externally_reformatted_bytes_invalidate_draft`；command::`current_project_load_save_and_stale_digest` | 失敗 | 沒有兩個視窗的 UI 測試 |
| R-UI-05 | host::`write_failure_preserves_prior_valid_document`、`successful_write_with_readback_failure_returns_storage_error`、`permission_read_failure_is_explicit_not_unconfigured` | 失敗 | UI 沒顯示失敗的測試 |
| R-UI-06 | host::`save_reopen_and_project_isolation_use_exact_digest` | 正常 | Settings 切換專案的 UI 測試沒有 |
| R-UI-07 | command::`unbound_or_stale_project_is_rejected_before_any_write` | 無效輸入 | UI 按鈕 disabled（`controls()`）沒有測試 |
| R-UI-08 | spec::`unknown_fields_at_every_level_including_secrets_are_rejected`；command::`imported_secret_field_is_rejected_without_source_mutation`、`presets_and_import_preview_reuse_validated_schema_without_writing` | 無效輸入、失敗 | 沒驗「機器路徑」排除 |
| R-UI-09 | spec::`unknown_format_version_mode_and_missing_required_data_are_rejected`、`invalid_text_and_duplicate_json_keys_are_rejected`；host::`malformed_existing_preferences_are_not_reset_or_overwritten` | 無效輸入 | UI 顯示原因沒測 |
| R-UI-10 | spec::`unconfigured_policy_is_preserved_without_invented_model_or_budget`；ui::`blank model budget remains unconfigured`；host::`missing_file_stays_unconfigured_and_does_not_write_defaults`；`APP/crates/sgenaxis-host/tests/project_preferences_creation.rs`（全檔） | 正常、邊界 | `chooseNewProject` 對話框沒有 UI 測試 |
| R-UI-11 | 無 | — | 待決策（G02） |
| R-UI-12～R-UI-15 | 無（`docs/verify_ui_design.py` 只驗文件結構；`verification.json` product_tests＝NOT RUN） | — | 沒有 token 對 CSS 的比對測試；running 色、radius、字級、最小視窗都已確認和實作不一致 |
| R-UI-16 | 無自動化 | — | 只能靠審查 |
| R-UI-17～R-UI-19 | `tests/test_pd_uidesigner_canvas_edit_01.py::test_grid_size_control_adjustable`、`test_form_size_presets_adjustable`、`test_drag_and_align_guide_logic`；`tests/test_pd_uidesigner_edit_p2.py::test_product_p2_controls` | 只檢查字串存在 | 沒有任何邊界值測試（2／64／7680／64 重設） |
| R-UI-20～R-UI-25 | `tests/test_pd_uidesigner_edit_p1.py::test_product_has_xy_delete_and_absolute_canvas`、`test_fixture_has_xy_geometry` | 只檢查字串存在 | 沒有行為測試 |
| R-UI-26 | `APP/crates/sgenaxis-host/src/uidesign_doc.rs` 內單元測試 `rejects_product_pass_true`、`rejects_wrong_format`、`roundtrip_sgendesign` | 無效輸入、正常 | — |
| R-UI-27 | `uidesign_doc.rs::roundtrip_sgendesign`、`save_load_via_fake_fs` | 正常（只測 HOST 已宣告的欄位） | 沒測 JS 擴充欄位經 HOST 存檔後讀回 |
| R-UI-29～R-UI-41 | `tests/test_pd_arch_dag_shell_01.py::test_arch_grid_infinite_extend`、`test_deployment_node_inspector_and_registry`、`test_workitem_node_lamp_and_event_log`、`test_collapse_and_ports_left_in_right_out`、`test_arch_middle_button_pan_and_wheel_zoom`、`test_strict_arch_node_kinds` | 只檢查字串存在 | 沒有 Inspector 數值邊界或 esml 存檔讀回的行為測試 |
| R-UI-28、R-UI-42 | 無 | — | 待決策（G01／G02） |

## 4. 測試矩陣

層：spec＝`sgenaxis-spec`；host＝`sgenaxis-host`；command＝`src-tauri/tests`；ui＝`ui/*.test.cjs` 或 Tauri 實機。
「待確認」參數的列只是預先寫好的案例，預期值是**現況**；Owner 確認前不得當驗收標準。

### 4.1 專案偏好設定

**數值參數代表列：`batch.maxTasks`**（同樣套用到 `budget.maxInputTokens`／`maxOutputTokens`／`maxWallTimeSeconds`，差別：預算欄空白＝null 未配置，maxTasks 空白要拒絕）

| 規則 ID | 類別 | 輸入 | 預期 | 層 |
|---|---|---|---|---|
| R-UI-02 | 邊界 min | tasks=`1`、concurrent=`1` | 接受，存成 1 | ui／spec |
| R-UI-02 | 邊界 min+1 | tasks=`2` | 接受 | ui／spec |
| R-UI-02 | 邊界 max−1（UI） | `9007199254740990` | 接受；上限取 JS 安全整數還是 u64 **暫不斷言（見 §7）** | ui |
| R-UI-02 | 邊界 max（UI） | `9007199254740991` | 接受；**暫不斷言（見 §7）** | ui |
| R-UI-02 | 邊界 max+1（UI） | `9007199254740992` | 拒絕，不送出指令（現況有測，只當回歸）；**暫不斷言（見 §7）** | ui |
| R-UI-02 | 邊界 max／max+1（Rust） | `18446744073709551615`／`18446744073709551616` | 前者接受，後者 InvalidDocument（現況，只當回歸）；**暫不斷言（見 §7）** | spec |
| R-UI-02 | 邊界 min−1 | `0` | 拒絕，保留原設定 | ui／spec |
| R-UI-02 | 空值 | tasks=`""` | 拒絕（Number("")＝0） | ui |
| R-UI-02 | 空值（預算） | input=`""` | 現況存成 null 未配置，和 SET02「儲存空白要拒絕」衝突；**暫不斷言（見 §7）** | ui |
| R-UI-02 | 錯型別 | `"abc"`、`"1.5"`、`"-1"`；JSON 裡是 `"100"`、`true`、`1.5` | 拒絕 | ui／spec |
| R-UI-02 | 失敗 | 已有有效設定，再存不合法值 | 檔案 bytes 不變，狀態列顯示「未保存：…」 | host／ui |
| 待確認 | 跨層落差 | 檔案中 `maxOutputTokens = 2^53+1` 經 IPC 載入 UI | 預期未定義：JS 會失去精度；載入後再存會被 UI 擋；**暫不斷言（見 §7）** | command／ui |

**`batch.maxConcurrent`（相對上限＝maxTasks；以 tasks=4 為例）**

| 規則 ID | 類別 | 輸入 | 預期 | 層 |
|---|---|---|---|---|
| R-UI-02 | 邊界 min／min+1 | concurrent=1／2 | 接受 | ui／spec |
| R-UI-02 | 邊界 max−1／max | concurrent=3／4 | 接受 | ui／spec |
| R-UI-02 | 邊界 max+1 | concurrent=5 | 拒絕「並行數不可超過每批 Task 上限」（規則本身待確認） | ui／spec |
| R-UI-02 | 空值／錯型別 | `""`／`"x"` | 拒絕 | ui |

**其他已核准規則（四類）**

| 規則 ID | 類別 | 輸入 | 預期 | 層 |
|---|---|---|---|---|
| R-UI-01 | 正常 | 套用「平衡」→ 把 tasks 改成 6 → 保存 | 存成 presetId=custom、maxTasks=6；再讀 `host_project_preferences_presets` 時平衡方案未被改寫（「平衡＝4/2」這個數值**暫不斷言（見 §7）**） | command／ui |
| R-UI-01 | 邊界 | 套用方案後不改就保存 | presetId=custom，數值等於方案 | ui |
| R-UI-01 | 無效輸入 | 未知方案 id `missing` | UnknownPreset，不用其他方案代替 | spec |
| R-UI-01 | 失敗 | 套用後保存失敗 | 系統方案與原檔都不變 | host |
| R-UI-03 | 正常 | 保存 → 關 app → 重開 → 開 Settings | 每個欄位都和保存時一樣，digest 相同 | ui（實機） |
| R-UI-03 | 邊界 | 全部預算空白並保存 | 現況：重開後仍是空白（未配置），不被填入預設；空白是否允許保存**暫不斷言（見 §7）** | host／ui |
| R-UI-03 | 無效輸入 | 在 app 外把檔案改壞再重開 | 顯示錯誤，不重設、不覆寫 | host |
| R-UI-03 | 失敗 | 讀回驗證失敗 | 回報 storage error，不宣稱成功 | host |
| R-UI-04 | 正常 | 單一視窗連續保存兩次 | 都成功，digest 更新 | host |
| R-UI-04 | 邊界 | 外部只改格式（同語意、bytes 不同） | 草稿失效，要求重新載入 | host |
| R-UI-04 | 無效輸入 | digest 缺漏 | 拒絕，零寫入 | host |
| R-UI-04 | 失敗 | 兩個視窗，第二個用舊 digest 保存 | 衝突，不覆寫 | host／ui |
| R-UI-05 | 正常 | 正常寫入 | 成功 | host |
| R-UI-05 | 邊界 | 寫入成功但讀回不一致 | 回報衝突 | host |
| R-UI-05 | 無效輸入 | 沒有讀取權限 | 明確錯誤，不當成「未配置」 | host |
| R-UI-05 | 失敗 | 寫入失敗 | 原檔仍有效，UI 顯示「未保存」 | host／ui |
| R-UI-06 | 正常 | A 存 4/2，B 存 8/4，切換 | 各自顯示自己的值 | host／ui |
| R-UI-06 | 邊界 | B 從未配置 | 切到 B 時欄位是空白／預設，不顯示 A 的值 | ui |
| R-UI-06 | 無效輸入 | 用 B 的 root 帶 A 的 digest 保存 | 拒絕 | command |
| R-UI-06 | 失敗 | 載入時切換專案（請求還在跑） | 舊回應被丟棄（epoch） | ui |
| R-UI-07 | 正常 | 已開專案 | 保存可按 | ui |
| R-UI-07 | 邊界 | 剛關閉專案 | 除「重新載入」外全部 disabled | ui |
| R-UI-07 | 無效輸入 | 不綁定專案直接呼叫 save | 拒絕，零寫入 | command |
| R-UI-07 | 失敗 | 綁定的 root 已經失效 | 拒絕，零寫入 | command |
| R-UI-08 | 正常 | 匯入有效偏好檔 | 新專案得到副本，來源 bytes 不變 | command |
| R-UI-08 | 邊界 | 匯入檔只有必填欄位 | 接受 | spec |
| R-UI-08 | 無效輸入 | 匯入檔帶 `apiKey` 等未知欄位 | 拒絕，來源不變 | spec／command |
| R-UI-08 | 失敗 | 取消檔案選擇 | 「已取消匯入」，不改草稿 | ui |
| R-UI-09 | 正常 | formatVersion=1 | 接受 | spec |
| R-UI-09 | 邊界 | formatVersion=2 | UnsupportedVersion | spec |
| R-UI-09 | 無效輸入 | 非 UTF-8、JSON 有重複 key、format 字串錯誤 | 拒絕 | spec |
| R-UI-09 | 失敗 | 新建時匯入壞檔 | 跳出「偏好檔無法套用」，不建立偏好 | ui |
| R-UI-10 | 正常 | 新建時選「保守」 | 建立後偏好的 presetId 對應保守方案、來源方案不變（「保守＝1/1」**暫不斷言（見 §7）**） | host／ui |
| R-UI-10 | 邊界 | 選「暫不套用」 | 沒有 preferences.json，Settings 顯示「尚未配置」 | host／ui |
| R-UI-10 | 無效輸入 | 同時傳入方案與匯入 | 拒絕（legacy_conflicting_choices…） | command |
| R-UI-10 | 失敗 | 對話框按「取消建立」 | 不建立專案 | ui |

**持久化三項（偏好）**

| 規則 ID | 類別 | 輸入 | 預期 | 層 |
|---|---|---|---|---|
| R-UI-03 | 重開後保留 | 改 tasks=6、concurrent=3、output=1000 → 保存 → 重開 app | 三個值都保留 | ui（實機） |
| R-UI-03 | 存檔讀回一致 | 保存後直接讀 `.sgenaxis/preferences.json` | JSON 跟 UI 顯示一致，沒有憑證欄位 | host |
| R-UI-11 | Undo 還原 | 改值後按 Ctrl+Z | **待決策（G02）**，只記錄現況，不判定 | ui |

### 4.2 設計 tokens

tokens 沒有使用者可調的值，所以「min／max／空值」只適用 `min_window`；其餘 token 只驗「實際算出的 CSS 值等於 tokens」。

| 規則 ID | 類別 | 輸入 | 預期 | 層 |
|---|---|---|---|---|
| R-UI-12 | 正常 | 在實機用 getComputedStyle 讀 `--bg-window`、`--bg-panel`…（共 12 色） | 等於 ui-spec 色碼 | ui |
| R-UI-12 | 邊界 | `running` #56a8ff | 現況 CSS 沒有；**暫不斷言（見 §7）** | ui |
| R-UI-12 | 無效輸入 | `muted` 對應 `--text-muted`（#6e7681） | 和 tokens 不符 → 先確認對應關係 | ui |
| R-UI-12 | 失敗 | 主題 CSS 沒有載入 | 畫面不可出現預設白底卻判 PASS | ui |
| R-UI-13 | 正常／邊界／無效／失敗 | 量本文、次要、標題的 font-size；字型缺 Segoe UI 時改用 JhengHei | 14／12／18 px；有備援字型；字型檔遺失時仍可閱讀 | ui |
| R-UI-14 | 正常 | 量按鈕、輸入框高度與圓角 | 高度 32 px；圓角 4 px（現況 3/5/8）**暫不斷言（見 §7）** | ui |
| R-UI-14 | 邊界／無效／失敗 | 抽查間距 | 只出現 4/8/12/16/24；其他值記為缺口 | ui |
| R-UI-15 | 邊界 min−1 | 視窗拖到 1023×719 | 規格：不可再縮（現況 960×600）；**暫不斷言（見 §7）** | ui（實機） |
| R-UI-15 | 邊界 min | 1024×720 | 可以，版面不破；**暫不斷言（見 §7）** | ui |
| R-UI-15 | 邊界 min+1 | 1025×721 | 可以；**暫不斷言（見 §7）** | ui |
| R-UI-15 | 正常 | 預設 1280×800 開啟 | 正常 | ui |
| R-UI-16 | 正常／無效 | 驗收報告附 `docs/ui-design/screens/*.png` | 不可當證據；只接受實機截圖 | 審查 |
| 持久化 | 重開後保留／存檔讀回／Undo | — | 不適用（tokens 是建置常數，沒有使用者狀態） | — |

### 4.3 UI Designer（全部待確認；預期＝現況）

**數值參數代表列：`meta.gridSize`**（同樣套用到架構 Grid R-UI-29，差別：架構選項是 0/8/16/24）。透過載入含 gridSize 的 `.esui`／recovery，或直接呼叫 `setDesignGridPx` 測試，因為下拉只能選固定值。

| 規則 ID | 類別 | 輸入 | 預期（現況） | 層 |
|---|---|---|---|---|
| R-UI-17 | 邊界 min | 0 | Grid 關閉（`is-grid-off`） | ui |
| R-UI-17 | 邊界 min+1 | 1 | 改成 2 | ui |
| R-UI-17 | 邊界 max−1 | 63 | 63 | ui |
| R-UI-17 | 邊界 max | 64 | 64 | ui |
| R-UI-17 | 邊界 max+1 | 65 | 夾成 64 | ui |
| R-UI-17 | 空值 | `""` | 0（關閉）——要確認是否合理 | ui |
| R-UI-17 | 錯型別 | `"abc"`、-1 | 8 | ui |

**`Form w×h`（R-UI-19；寬、高分開測，上限 7680／4320）**

| 規則 ID | 類別 | 輸入 | 預期（現況） | 層 |
|---|---|---|---|---|
| R-UI-19 | 邊界 min−1 | w=63 | **重設成 800**（不是夾到 64） | ui |
| R-UI-19 | 邊界 min／min+1 | 64／65 | 原值 | ui |
| R-UI-19 | 邊界 max−1／max | 7679／7680（h：4319／4320） | 原值 | ui |
| R-UI-19 | 邊界 max+1 | 7681（h：4321） | 夾成 7680（h：4320） | ui |
| R-UI-19 | 空值／錯型別 | `""`／`"abc"` | 800×600 | ui |
| R-UI-19 | 正常 | 選 1920×1080 後子元件超出 | 子元件夾回 Form 內 | ui |

**元件 `w`／`h`（R-UI-21；代表套用所有 Inspector 數值欄 x／y／zIndex，各欄的最小值不同：w/h=8，x/y=0，zIndex 沒有）**

| 規則 ID | 類別 | 輸入 | 預期（現況） | 層 |
|---|---|---|---|---|
| R-UI-21 | 邊界 min−1 | 7 | 8 | ui |
| R-UI-21 | 邊界 min／min+1 | 8／9 | 原值 | ui |
| R-UI-21 | 邊界 max−1／max／max+1 | 上限未定義 | 記錄為缺口；建議 Owner 決定是否以 Form 尺寸為上限 | ui |
| R-UI-21 | 空值 | `""` | 不變更 | ui |
| R-UI-21 | 錯型別 | 用程式把 value 設成 `"abc"` | 現況存成 NaN → 記錄為缺陷候選 | ui |
| R-UI-20 | 邊界 | Inspector 輸入 x=-50 | 現況不夾（拖曳時才夾）→ 記錄 | ui |
| R-UI-18 | 正常 | 拖曳到離參考線 8 px／9 px | 8 px 吸附，9 px 對齊 Grid | ui（錄影） |
| R-UI-23 | 邊界 | 縮放到 0.3／0.4／2／2.1 | 0.4／0.4／2／2 | ui |
| R-UI-24 | 代表列 | Slider 的 `min` 填 `"abc"`、`max` 小於 `min` | 現況照存字串；沒有規格 → 待確認 | ui |
| R-UI-26 | 無效輸入 | 載入 `product_pass:true` | 拒絕 | host |

**持久化三項（Designer）**

| 規則 ID | 類別 | 輸入 | 預期 | 層 |
|---|---|---|---|---|
| R-UI-27 | 重開後保留 | gridSize=16、formSize=1280×720、Button w=96 → 存 → 重開 | 現況：經 (A) gridSize／formSize 回到預設、w=96 保留；經 (B) 保留 → 記錄差異，不判 PASS；**暫不斷言（見 §7）** | ui（實機） |
| R-UI-27 | 存檔讀回一致 | 讀 `design/main.sgendesign` 的 JSON | 比對 meta／properties 是否遺失；**暫不斷言（見 §7）** | host／command |
| R-UI-28 | Undo 還原 | 改 w 後 Ctrl+Z | **待決策（G02）** | ui |

### 4.4 架構 DAG Inspector（全部待確認；預期＝現況）

**數值參數代表列：節點 `width`（套用 `height`；WorkItem tokens、Deployment timeoutSeconds 規則類似，但最小值是 HTML min=0，0 會被保留）**

| 規則 ID | 類別 | 輸入 | 預期（現況） | 層 |
|---|---|---|---|---|
| R-UI-33 | 邊界 min−1 | 0 | 變成自動（""） | ui |
| R-UI-33 | 邊界 min／min+1 | 1／2 | 原值 | ui |
| R-UI-33 | 邊界 max−1／max／max+1 | 上限未定義 | 記錄為缺口 | ui |
| R-UI-33 | 空值 | `""` | 自動 | ui |
| R-UI-33 | 錯型別 | `"-5"`、`"abc"` | -5 照存（缺陷候選）；abc→自動 | ui |
| R-UI-30 | 邊界 | 底板 319×239／320×240／321×241 | 320×240／原值／原值 | ui |
| R-UI-31 | 邊界 | 縮放 0.3／0.4／2／2.1／"x" | 0.4／0.4／2／2／1 | ui |
| R-UI-32 | 正常／邊界 | 拖到 x=-10；離其他節點 8／9 px | x=0；8 吸附、9 對齊 Grid | ui（錄影） |
| R-UI-34 | 無效輸入 | 不在 Module 內的節點改 order | 欄位 disabled，不改 | ui |
| R-UI-35 | 空值 | name=`""`、schemaVersion=`""` | 保留舊名；"1" | ui |
| R-UI-36 | 無效輸入 | 嘗試改 kind、packsKind | 唯讀，不能改 | ui |
| R-UI-39 | 無效輸入 | 用程式把 select 設成不在清單的值 | 記錄現況 | ui |
| R-UI-29 | 代表 | 套用 4.3 gridSize 那七列 | 同 4.3 | ui |

**持久化三項（架構）**

| 規則 ID | 類別 | 輸入 | 預期 | 層 |
|---|---|---|---|---|
| R-UI-41 | 重開後保留 | 改 name、collapsed、order、width=200、contentHash → scene.save → 重開 | 現況：name／collapsed／order 保留；width／contentHash 要看是否另外存 → 記錄 | ui（實機） |
| R-UI-41 | 存檔讀回一致 | 比對 `scene/default.esml` 與 localStorage 草稿 | 兩邊的值一致；不一致就記錄 | ui |
| R-UI-42 | Undo 還原 | 改屬性後 Ctrl+Z | **待決策（G02）**；現況是走 edit_undo 復原選取 | ui |

## 5. 開發段（RED）

- 放置位置：
  - 偏好：`APP/crates/sgenaxis-spec/tests/project_preferences.rs`、`APP/crates/sgenaxis-host/tests/project_preferences.rs`、`APP/src-tauri/tests/project_preferences_commands.rs`、`APP/ui/project-preferences-ui.test.cjs`（只在既有檔案裡加 case；新檔要先拿到 envelope 核准，F02 卡目前是 BLOCKED_PENDING_APPROVED_ENVELOPE_AND_VALID_RED）。
  - tokens：建議新增 UI 層比對測試；放哪裡要等 F04 PREP 綁定 runner，**不可自己猜 cargo target**（F04 卡 tdd.command 寫明 BLOCKED）。
  - Designer／架構：只有在 Owner 把「待確認」轉成已核准後才可以寫 RED。現有 `tests/test_pd_uidesigner_*.py`、`tests/test_pd_arch_dag_shell_01.py` 只檢查字串存在，不可拿來當行為 RED。
- 先跑紅的指令與預期失敗關鍵字：
  - `node --test ui/project-preferences-ui.test.cjs`（在 `APP/` 下）：新 case 例如「欄位原因」，預期 assert 找不到欄位對應訊息（`AssertionError`）。
  - `cargo test -p sgenaxis-spec --test project_preferences`、`cargo test -p sgenaxis-host --test project_preferences`、`cargo test -p sgenaxis-desktop --test project_preferences_commands`（package 名稱以 `APP/src-tauri/Cargo.toml` 為準）：預期失敗訊息 `assertion`／`left != right`；不可以是編譯錯誤或 fixture 錯誤（那不算有效 RED）。
  - tokens：其他 token 的比對可以寫 RED；`#56a8ff`、`radius 4px`、`minWidth 1024` 三項屬 §7 已知衝突，看板決策卡裁定前不寫斷言。
- 禁止事項：
  - 不可修改規格、ui-spec.json 或 RC-29 的 SET 文字來配合現況。
  - 不可把 R-UI-11／R-UI-28／R-UI-42（G01／G02）寫成斷言。
  - 不可把「待確認」的現況數值（例如 64、7680、0.4–2、1/1/4/2/8/4）寫成已核准斷言。
  - 不可弱化既有斷言，例如把 `assert.throws` 改成 warning，或拿掉 `9007199254740992`。
  - §7 列的已知衝突（預算空白、u64／JS 上限、方案數值、running 色、圓角、最小視窗、Designer HOST 存檔丟欄位）要先由看板決策卡裁定，不可自己選一邊。

## 6. 驗證段

> 執行者不可以是寫這段程式的代理。

- 重跑指令（在 `APP/` 下）：
  - `node --test ui/project-preferences-ui.test.cjs`（本次唯讀確認：4/4 pass）
  - `cargo test -p sgenaxis-spec --test project_preferences`
  - `cargo test -p sgenaxis-host --test project_preferences`
  - `cargo test -p sgenaxis-host --test project_preferences_creation`
  - `cargo test -p <src-tauri package> --test project_preferences_commands`
  - `cargo test -p sgenaxis-host uidesign_doc`（Designer HOST 單元測試）
  - `python -m pytest tests/test_pd_uidesigner_canvas_edit_01.py tests/test_pd_arch_dag_shell_01.py`（repo 根；只當回歸，不算行為證據）
- 介面實測步驟（Tauri 應用，不可用瀏覽器模式；瀏覽器模式不會保存偏好，Designer 會顯示 NOT RUN）：
  1. **開**：啟動 Tauri app，開啟測試專案 A（專案要放在 repo 外的暫存目錄）。
  2. **改**：對每個參數設定測試矩陣的值（偏好：Settings 面板；Designer：UI 視窗 Inspector／工具列；架構：DAG Inspector／工具列）。
  3. **看畫面**：確認畫面、狀態列訊息與 Inspector 數值；被拒絕的輸入要看到原因。
  4. **重開**：保存（偏好按「儲存專案偏好」；Designer 走 uidesign 存檔與 scene.save 兩條路各測一次；架構走 scene.save），完全關閉 app，再啟動並開同一個專案。
  5. **再看**：確認值是否保留；偏好另外切到專案 B 確認隔離（R-UI-06）。
  6. tokens：在主視窗用 DevTools 或注入腳本讀 computed style；把視窗拖到 1023×719 與 1024×720 各截圖（running 色、圓角、最小視窗只記錄現況，判定記 `NOT RUN — 待看板決策卡`，見 §7）。
- 證據：放 `reports/dispatch-pd/<卡ID>-evidence/`（偏好用 `PD-P1-F02-DELIVERY-01`；tokens、Designer、架構用 `PD-P1-F04-DELIVERY-01`）。
  - 每個參數：改前截圖＋改後截圖（＋重開後截圖），檔名 `<規則ID>-<參數>-before.png`／`-after.png`／`-reopen.png`。
  - 拖曳／吸附（R-UI-18、R-UI-32）、縮放、視窗縮放（R-UI-15）要錄影：`<規則ID>-<動作>.mp4` 或 `.gif`。
  - 每條規則一筆紀錄：規則／指令／Exit code／輸出末段／介面證據／判定。
- 直接判 TDD_FAIL 的情況：
  - 任何「待確認」參數（2.3、2.4 全部，以及 2.1 標待確認的數值）被判成 TDD_PASS。
  - 依賴 G01／G02 的列（R-UI-11、R-UI-27 的權威檔判定、R-UI-28、R-UI-42）被寫成 PASS／FAIL 斷言。
  - 用 `docs/ui-design/screens/*.png`、mock 或瀏覽器模式截圖當證據（R-UI-16）。
  - 只有改後截圖、沒有改前截圖，或是拖曳／吸附沒有錄影。
  - 偏好重開後的值和保存時不同，或專案 B 看到 A 的值。
  - 不合法輸入被保存，或保存失敗後原檔被改。
  - 重跑指令 exit code ≠ 0，或測試數比基準少（被刪或被 skip）。
  - 驗證者和實作者是同一個代理。

## 7. 已知衝突

| 衝突 | 規格出處 | 實作出處 | 影響規則 ID | 處理 |
|---|---|---|---|---|
| 主視窗最小尺寸：規格 1024×720，實作 960×600 | `docs/ui-design/ui-spec.json:118-121`（`tokens.min_window`） | `APP/src-tauri/tauri.conf.json:18-19`（`minWidth 960`、`minHeight 600`） | R-UI-15 | 暫不斷言，待看板決策卡 |
| 圓角：規格 4 px，實作 3／5／8 px | `docs/ui-design/ui-spec.json:106`（`tokens.radius_px`） | `APP/ui/styles.css:36-38`（`--radius-sm/md/lg`） | R-UI-14 | 暫不斷言，待看板決策卡 |
| running 狀態色 #56a8ff 沒有實作 | `docs/ui-design/ui-spec.json:96`（`tokens.running`） | `APP/ui/styles.css:24-31`（`:root` 色彩變數，沒有 #56a8ff） | R-UI-12 | 暫不斷言，待看板決策卡 |
| 預算欄空白＝未配置（null），但 SET02 寫「儲存空白…要拒絕」 | `docs/requirements-confirmation/requirements.json:751` RC-29 SET02 | `APP/ui/project-preferences-ui.js:5`（預算空白回 null）；`APP/crates/sgenaxis-spec/src/project_preferences.rs:34-36`（`Option<u64>`） | R-UI-02、R-UI-03 | 暫不斷言，待看板決策卡 |
| 數值上限兩層不同：UI 用 JS 安全整數 2^53−1，Rust 用 u64 | 規格沒有數值上限（RC-29 SET02 只要求拒絕不合法上限） | `APP/ui/project-preferences-ui.js:7`（`Number.isSafeInteger`）；`APP/crates/sgenaxis-spec/src/project_preferences.rs:34-36`、`:42-43`（u64） | R-UI-02 | 暫不斷言，待看板決策卡 |
| Designer 經 HOST 存檔丟掉 `meta.gridSize`、`meta.formSize`、`meta.guides` 與節點 `properties` | `docs/requirements-confirmation/phase1-spec/tasks/M03/planning/c1-owner-packet/`（C1 保存契約，待 Owner）；現況重現 `.../M03/planning/roundtrip-evidence/semantic-diff.json` | `APP/crates/sgenaxis-host/src/uidesign_doc.rs:16-23`（`DesignMeta`）、`:30-44`（`DesignNode`）；`APP/src-tauri/src/commands.rs:4471`（`uidesign_save_design`）；JS 寫入端 `APP/ui/app.js:13346`、`:13366`、`:13457` | R-UI-27（待確認） | 暫不斷言，待看板決策卡 |
| 系統方案數值 保守 1/1、平衡 4/2、效率 8/4 沒有規格出處 | `docs/requirements-confirmation/requirements.json` RC-29 SET01（沒有數值）；`phase1-spec/index.html#defaults` D05（沒有數值） | `APP/crates/sgenaxis-spec/src/project_preferences.rs:119-121`（`preset()`）；`APP/ui/project-preferences-ui.js:46`、`:65`（選單文字） | R-UI-01、R-UI-10 | 暫不斷言，待看板決策卡 |
