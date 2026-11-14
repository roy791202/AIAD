# PD-SHELL-AUDIT-01 — Workbench ↔ 桌機殼落差清單（v0.1）

**BDD:** `BDD-PD-SHELL-AUDIT-01`  
**IA SSOT:** `git_workbench_interactive.html`  
**Desktop UI:** `apps/sgenaxis-desktop/ui/`（`index.html` · `styles.css` · `app.js`）  
**ARCH:** UI → Command → DispatchHost → domain → Ports（本卡僅文件／斷言；不改產品碼）

> **明確聲明（v0.1）：** 本清單只記錄落差與優先級。**禁止暗示** MSI／安裝版視覺對齊業已完成。視覺對齊仍為未完成；後續 CHROME／SIDEBAR／BOARD／UIDESIGN-VIEW／CSS 卡才處理實作。

---

## 圖例

| 標籤 | 意義（v0.1） |
|------|----------------|
| **Must** | Shell-Fidelity 本批應對齊的 IA／殼體／主路徑密度 |
| **Should** | 明顯改善體感；可在本批或緊接迭代處理 |
| **Won't** | 本批不做（保留／降級／另案） |

勾選框 `[ ]` = 尚未對齊；實作卡完成後由後續卡勾選，本卡不宣稱完成。

---

## 1. 殼區（Chrome）

| # | 項 | Workbench 選擇器 | Desktop 路徑／選擇器 | 現況摘要 | 優先 | ☐ |
|---|-----|------------------|----------------------|----------|------|---|
| C1 | 選單列品牌＋七選單 | `#appTitlebar` `.desktop-menubar` `.menubar-brand`；選單 `data-menu`：file／edit／project／module／tasks／window／help | `apps/sgenaxis-desktop/ui/index.html` → `header.menubar` `.brand`；`data-menu`：檔案／編輯／專案／模組／工項／視窗／說明 | 選單語意大致對應；Workbench 內嵌視窗控制鈕 `.window-controls`，桌機依賴 OS 標題列 | Must | [ ] |
| C2 | 工具列專案列 | `.desktop-toolbar` `#projectCombo` `#repoPathBox` `#btnToggleBranchTree` | `.toolbar` `#project-bind-chip` `#project-path` | 桌機僅綁定／路徑 chip，缺專案 combo、分支盒、歷史／GIT 設定鈕密度 | Must | [ ] |
| C3 | 狀態列資訊層 | `.window-statusbar`（`--statusbar-h: 48px`） | `footer.statusbar`（`--statusbar-h: 28px`） | 桌機較扁；欄位較少（專案／Agent／msg） | Must | [ ] |
| C4 | Titlebar 合併高度 | `--titlebar-h: 74px`（menubar+toolbar 合一） | `--menubar-h: 30px` + `--toolbar-h: 40px` | 總高接近但分層／間距／視覺權重不同 | Should | [ ] |
| C5 | 原生窗控鈕 mock | `.window-controls` `.win-btn` | （無；Tauri 原生） | Won't：不仿造假窗控 | Won't | [ ] |
| C6 | Qt／PySide 對照鈕 | `#btnToggleArchitecture` | （無） | Won't：原型教學鈕，非產品殼 | Won't | [ ] |

---

## 2. 側欄（Sidebar IA）

Workbench 主路徑（SSOT 順序）：

1. `#secAgentDispatch` → Agent 派工  
2. `#secTasksStatus` → Tasks Status（`data-filter`：overview／gray／yellow／red／green／accepted）  
3. `#secDeployStats` → 佈版  
4. `#secArchDagModule` → 模組架構圖  
5. `#secUiDesignModule` → UI 設計工具  

| # | 項 | Workbench | Desktop | 現況 | 優先 | ☐ |
|---|-----|-----------|---------|------|------|---|
| S1 | 主路徑順序 Agent→Tasks→佈版→架構 | `#secAgentDispatch` … `#secArchDagModule` | `nav.sidebar` `#nav-agent` → `#sec-tasks-status` → `#nav-deploy` → `#nav-arch` | 順序已鏡像；視覺密度／徽章／收闔樣式仍偏簡 | Must | [ ] |
| S2 | Tasks Status 六篩＋計數 | `.status-list` `.status-item[data-filter]` `.counter-badge` | `#tasks-status-body` `.status-item[data-filter]` `[data-count-for]` | 篩選語意在；overview-dots／badge 樣式與 Workbench 有落差 | Must | [ ] |
| S3 | UI 設計工具側欄項 | `#secUiDesignModule` `#btnUiNav` | `#nav-uidesign` `data-panel="uidesign"`（stub／進行中） | 入口已現；視覺／主路徑密度與 Workbench 仍未對齊 | Must | [ ] |
| S4 | 側欄寬＋可拖曳 | `--sidebar-w: 240px`；`#sidebarResizer` | `--sidebar-w: 220px`；無 resizer | 寬度偏窄；無分隔拖曳 | Should | [ ] |
| S5 | 次要模組區（Git 等） | 多經選單／視圖切換；側欄主列偏精簡 | 「模組」區塊：`#nav-git` `#nav-spec` `#nav-report` `#nav-settings` `#nav-ports`；另有 `#nav-listen` | 桌機側欄較擠；Listen／Ports／Spec／Report 可降級但不刪 | Should | [ ] |
| S6 | Emoji／裝飾標題 | Agent 列含 emoji | 純文字 | Won't：不強制搬 emoji | Won't | [ ] |

---

## 3. 六視圖（Workbench `.view-content`）

| # | Workbench 視圖 id | 語意 | Desktop 對應 | 落差 | 優先 | ☐ |
|---|-------------------|------|--------------|------|------|---|
| V1 | `#viewTaskBoard` | 工項看板表 | `#panel-board` | 有；表密度／欄位／列高未對齊（見 §4） | Must | [ ] |
| V2 | `#viewAgentDispatch` | Agent 派工 | `#panel-agent` | 有；Run 工具列已接 Command，視覺密度不同 | Must | [ ] |
| V3 | `#viewRelease` | 佈版／部署 | `#panel-deploy` | 有；能力／產物投影在；原型統計徽章密度不同 | Must | [ ] |
| V4 | `#viewArchDag` | 模組架構圖 | `#panel-arch` | 有；空態／Command 投影；非 DAG 畫布密度 | Should | [ ] |
| V5 | `#viewGitWorkspace` | Git 工作台 | `#panel-git` | 有；Workbench 更完整的 Git 操作面板密度 | Should | [ ] |
| V6 | `#viewUiDesign` | UI 設計工具 | `#panel-uidesign`（stub／進行中；cite WB `viewUiDesign`） | 殼入口在；設計包嵌入／證據邊界／密度仍待 UIDESIGN-VIEW | Must | [ ] |

**Desktop 額外面板（相對六視圖）：** `#panel-listen` `#panel-spec` `#panel-report` `#panel-ports` `#panel-settings` — 保留功能；位置可次層（Won't 刪除）。

---

## 4. 密度（Density／Tokens）

| # | Token／區 | Workbench `:root` | Desktop `styles.css` `:root` | 落差 | 優先 | ☐ |
|---|-----------|-------------------|------------------------------|------|------|---|
| D1 | 側欄寬 | `--sidebar-w: 240px` | `220px` | 偏窄 | Must | [ ] |
| D2 | Inspector 寬 | `--inspector-w: 390px` | `280px` | 明顯偏窄 | Must | [ ] |
| D3 | 狀態列高 | `--statusbar-h: 48px` | `28px` | 明顯偏扁 | Must | [ ] |
| D4 | 色票／字級基線 | `--bg-*` `#101112`…；`font-size: 13px` | 同源色票；`13px` | 基線接近；細節控件 padding 仍偏「網頁表單」 | Should | [ ] |
| D5 | `data-ui`／`data-tone` 主題 | `html[data-ui]` `html[data-tone]` | 無對等屬性切換 | Won't（v0.1）：主題矩陣另案 | Won't | [ ] |
| D6 | 看板表列／欄 | `#viewTaskBoard` 表格列＋`board-section` | `#board-tasks` 列表式投影 | 非表格密度；欄位層級弱 | Must | [ ] |

---

## 5. 缺項總表（相對 SSOT）

| 缺項 | 引用 | 處置（v0.1） |
|------|------|----------------|
| UI 設計工具視圖完整度（嵌入／開啟／非產品證據） | WB `#viewUiDesign` `#secUiDesignModule`；desktop `#panel-uidesign` stub | **Must** → `PD-SHELL-UIDESIGN-VIEW-01` |
| 專案 combo／分支盒／工具列密度 | WB `.desktop-toolbar`；desktop `.toolbar` | **Must** → `PD-SHELL-CHROME-01` |
| Inspector 寬與分區（top／bottom collapsible） | WB `.inspector` `.inspector-top` `.inspector-bottom`；desktop `aside.inspector` 單欄 cards | **Must／Should** → `PD-SHELL-CSS-01` |
| 看板表結構 | WB `#viewTaskBoard`；desktop `#panel-board` | **Must** → `PD-SHELL-BOARD-01` |
| 側欄 UI 設計項＋Tasks 視覺 | WB 主路徑末段 | **Must** → `PD-SHELL-SIDEBAR-01` |
| 假窗控、Qt 對照鈕、emoji、完整 tone 主題 | — | **Won't** |
| 刪 Listen／Ports／Spec／Report | desktop 現有 panel | **Won't**（可降級位置） |

---

## 6. 路徑索引（證據）

| 角色 | 路徑 |
|------|------|
| IA SSOT | `git_workbench_interactive.html` |
| Desktop HTML | `apps/sgenaxis-desktop/ui/index.html` |
| Desktop CSS | `apps/sgenaxis-desktop/ui/styles.css` |
| Desktop JS | `apps/sgenaxis-desktop/ui/app.js` |
| 本清單 | `docs/shell-audit-PD-SHELL-AUDIT-01.md` |
| 卡報告 | `reports/dispatch-pd/PD-SHELL-AUDIT-01.md` |
| 斷言 | `tests/test_pd_shell_audit_01.py` |

---

## 7. 驗收備註

- 本卡 AC = **可勾選對照表存在** + Must／Should／Won't 標註 + 引用選擇器／路徑 + **禁止暗示** MSI／安裝版視覺對齊業已完成。  
- 勾選完成屬後續實作卡；本文件所有☐預設未勾。  
- **READY_FOR_GREEN** 僅表示本 DOC／測試就緒，**≠** 殼體視覺對齊業已完成，**≠** zone=green。
