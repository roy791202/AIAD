# SGenAxis UI design — 規畫↔產品落差

## 權威順序（IA / 殼）

1. **`git_workbench_interactive.html`（Workbench）＝ IA／側欄主路徑 SSOT** — 殼、視圖切換、側欄順序以此為準。
2. PRODUCT-DEVELOPMENT §5（產品敘述）
3. `apps/sgenaxis-desktop` 現況（桌機 `data-panel`）
4. 本目錄 `ui-spec.json` 文字 schema（14 頁＋對話框；**不得以舊 14 頁導覽覆寫 Workbench**）
5. `screens/*.png`／圖稿 — **僅視覺示意，不是產品執行或驗收證據**

**圖稿非證據：** 截圖／mock 上的 PASS、完成態、Agent 結果一律不當成產品 verification。產品碼、真實 Agent、Git 突變、部署與測試結果是否落地，以桌機／契約／測試報告為準，不以本設計包圖面為準。

Open [`index.html`](index.html) locally. Schema: [`ui-spec.json`](ui-spec.json). Screens under `screens/`.

Regenerate: `python docs/build_ui_design.py`  
Validate: `python docs/verify_ui_design.py`

This design package does **not** approve architecture, new domain rules, or release／GA.

---

## 落差對照表（Workbench 為主欄）

主欄＝Workbench 殼／視圖；旁註＝`UI-xx`（ui-spec 頁）與桌機 `data-panel`。狀態語意：

| 標記 | 意涵 |
|------|------|
| MERGED | 規劃頁已併入／對應 Workbench 視圖（非獨立頂層導覽） |
| PARTIAL | 桌機有對應 panel／投影，能力未等同規格全文 |
| OUT_OF_SCOPE | Workbench 主路徑無此面；桌機有或僅規格提案 |
| DESIGN-ONLY | 僅設計包／稍後模組；桌機主路徑未掛 |

### 殼（Chrome）

| Workbench 殼 | 說明 | UI-xx（旁註） | 桌機 panel／表面（旁註） |
|--------------|------|---------------|-------------------------|
| `.desktop-menubar` | 品牌、檔案／檢視選單、開啟專案等 | UI-01（開專案入口）、UI-12（設定入口） | menubar；`settings` 視窗；OPEN 流程 |
| `aside.sidebar` | 左側主路徑：Agent → Tasks Status → 佈版 → 架構圖 → UI 設計工具 | （導覽本身非單頁） | `.sidebar` + `nav-item[data-panel]` |
| `main.workspace` | 中央 `view-content` 切換 | 見下表各 view | `#app` 內 `.panel[data-panel]` |
| Inspector／狀態列（原型） | 選中列／同步提示 | UI-02 部分欄位概念 | inspector；toast／status |

### 主視圖（側欄／選單可達）

| Workbench 視圖 / 側欄 | Workbench 角色 | UI-xx（旁註） | 桌機 `data-panel`（旁註） | 落差 |
|------------------------|----------------|---------------|---------------------------|------|
| `viewAgentDispatch` / 「Agent 派工」 | 派工與執行面 | UI-07 | `agent` | PARTIAL |
| `viewTaskBoard` / 「Tasks Status」 | 工項看板（預設中央） | UI-03；封包／排程概念見 UI-05、UI-06 | `board` | PARTIAL（UI-05／06 多為 MERGED／未獨立頂層） |
| `viewGitWorkspace`（選單「已驗收／分支與變更」等） | Git 工作台 | UI-08 | `git` | PARTIAL |
| `viewRelease` / 「佈版」 | 佈版／部署統計 | UI-09、UI-10 | `deploy` | PARTIAL |
| `viewArchDag` / 「模組架構圖」 | 模組 DAG（標「稍後」） | UI-04 | `arch` | PARTIAL |
| `viewUiDesign` / 「UI 設計工具」 | 設計工具面（標「稍後」） | （設計包自身；非產品主路徑） | *無* `ui-design` panel（桌機主路徑不掛） | DESIGN-ONLY |
| Settings overlay | 環境／偏好 | UI-12 | `settings` | PARTIAL |
| 開啟專案 overlay | 選資料夾／進專案 | UI-01；進專案後總覽概念 UI-02 | OPEN／專案切換（非獨立 panel id） | PARTIAL |

### 桌機有、Workbench 無獨立主視圖

| Workbench | UI-xx（旁註） | 桌機 `data-panel` | 落差 |
|-----------|---------------|-------------------|------|
| *無對應 view id* | UI-14（模組規格） | `spec` | OUT_OF_SCOPE（相對 Workbench 主路徑；桌機有） |
| *無對應 view id* | UI-11（模組報告） | `report` | OUT_OF_SCOPE（相對 Workbench 主路徑；桌機有） |
| *無對應 view id* | （規格未列獨立頁） | `listen` | OUT_OF_SCOPE — 僅註記於對齊 metadata／本表 |
| *無對應 view id* | （規格未列獨立頁） | `ports` | OUT_OF_SCOPE — 僅註記於對齊 metadata／本表 |

### 14 頁舊提案：相對 Workbench 的處置（勿當頂層導覽）

| UI-xx | 舊標題 | 相對 Workbench | 備註 |
|-------|--------|----------------|------|
| UI-01 | 專案管理 | MERGED → 開專案 overlay／選單 | 非側欄頂層頁 |
| UI-02 | 專案總覽 | MERGED → 殼／Inspector 概念 | 非側欄頂層頁 |
| UI-03 | 工項工作台 | → `viewTaskBoard` | 主路徑 |
| UI-04 | 模組架構 DAG | → `viewArchDag` | 主路徑（稍後） |
| UI-05 | 工項工程封包 | MERGED／提案残留於看板列細節 | 勿獨立導覽覆寫殼 |
| UI-06 | 工項依賴排程 | MERGED／提案残留 | 勿獨立導覽覆寫殼 |
| UI-07 | Agent 執行與證據 | → `viewAgentDispatch` | 主路徑 |
| UI-08 | Git 版本控管 | → `viewGitWorkspace` | 主路徑 |
| UI-09 | 部署設定與產物 | → `viewRelease` | 主路徑 |
| UI-10 | 部署執行與復原 | → `viewRelease` | 與 UI-09 同視圖旁註 |
| UI-11 | 模組報告與里程碑 | 無 WB view；桌機 `report` | OUT_OF_SCOPE @ WB 主路徑 |
| UI-12 | 環境與 Agent 設定 | → Settings overlay | 非側欄主項 |
| UI-13 | 核准與重新規劃 | 流程／對話提案 | 非 WB 獨立 view |
| UI-14 | 模組規格與修訂 | 無 WB view；桌機 `spec` | OUT_OF_SCOPE @ WB 主路徑 |

`ui-spec.json` 的 `implementation`／`product_panel` 欄位由 **PD-UIDESIGN-SPEC-01** 維護；本 README 在 SPEC 未齊時仍以 Workbench＋桌機已知映射為準，SPEC 落地後用語應對齊、不得顛倒權威。

---

## BDD

**BDD-PD-UIDESIGN-README-01：** README 對照表以 Workbench 殼／視圖為主欄，旁註 UI-xx 與桌機 panel；明示 Workbench＝IA SSOT、圖稿非證據。
