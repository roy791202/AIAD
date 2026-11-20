# SGenAxis 產品開發說明

| 欄位 | 內容 |
|------|------|
| 文件版本 | 0.2 · 2026-10-23 |
| 狀態 | **已拍板技術棧與製作流程**；產品實作尚未開工 |
| 產品名稱 | SGenAxis（工作台原型／文案；看板工具側曾用 VGenAxIs） |
| UI 原型 | `git_workbench_interactive.html` |
| PM 看板 | `docs/PROJECT-BOARD.html` + `docs/start-board-watch.cmd` → `http://127.0.0.1:28789/` |
| 舊規畫 | `docs/product-plan/`（Electron + React **已廢止**，僅供模組／工項語意參考） |

---

## 1. 產品定位

SGenAxis 是**本機優先的跨平台桌機**「自動化開發控制中心」：

- 人選專案、審工項、核准意圖與驗收
- 系統派本機 Agent CLI、收集證據、管理 Git 與（後期）部署
- 體感目標：**ComfyUI 式輕盈**（薄殼 + Web UI），但是**正式桌機 App**，不是純瀏覽器工具

### 1.1 使用者旅程（首版）

1. 開啟桌機 App → 選／開專案  
2. 看工項燈號看板 → 篩選紅／黃／灰  
3. 指派 Agent → 看 Run／Log  
4. 檢視 Git 變更 →（後期）核准提交／發布  

**操作步驟（開專案／DryRun／設定、埠 28789 與 `:8788` 禁區）：**  
`apps/sgenaxis-desktop/README.md`「使用說明」· 索引 `docs/DESKTOP-APP-USAGE.md`（PD-README-APP-01）。

### 1.2 範圍與非目標

| 首版範圍 | 非目標（暫不做） |
|----------|------------------|
| Windows／macOS／Linux 桌機 | 多租戶 RBAC、雲端 worker |
| 單個同時執行的 Agent | 多 Agent 並行調度 |
| Git CLI 讀取為主，寫入需閘門 | 任意外掛市場 |
| 本機專案根目錄綁定 | 把 HoneyBadger mailbox `:8788` 當產品通道 |

---

## 2. 已拍板技術棧

| 層 | 選型 | 授權／備註 |
|----|------|------------|
| 桌機殼 | **Tauri 2** | MIT／Apache-2.0；跨平台；無框架授權費 |
| Web UI | **Vanilla HTML／CSS／JS** | 對齊現有原型；要元件化時可局部加 Svelte（次選） |
| 核心 | **Rust Core** | `Property + Dirty + Evaluation` 髒更新 |
| OS 邊界 | **Ports + 跨平台 Adapters** | Core 不直接依賴 OS／CLI |
| 不做預設 | Electron、React 全家桶、egui／iced 當主 UI、Slint | 與「輕盈／開源不收費」衝突或過重 |

**授權結論：** 產品棧本身無「商用必須付費」隱憂；簽章憑證、商店帳號屬發行成本，與框架無關。

---

## 3. 系統架構

```
Vanilla Web UI  ──Tauri command／事件──►  Rust Core
                                              │
                         Property · Dirty · Evaluation
                                              │
                                         Ports（介面）
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
            FileSystemPort              ProcessPort                  GitPort
            PathPort                    DialogPort（可選）            …
                    │                         │                         │
                    └──────────► Win／macOS／Linux Adapters ◄───────────┘
                                              │
                                         OS／CLI／FS
```

### 3.1 依賴規則

- 箭頭（控制流）可向下；**編譯依賴向內指向 Core**
- UI **只**發 command／訂閱狀態投影，不直撞 Adapter
- Core／領域測試使用 **fake adapter**，不綁單一 OS
- Tauri 負責視窗與 IPC，**禁止**把業務 OS 邏輯堆在 command 閉包裡

### 3.2 跨平台適配器（Ports 示例）

| Port | 職責 |
|------|------|
| `FileSystemPort` | 讀寫、原子寫入、路徑存在性 |
| `PathPort` | 設定／快取／專案慣例目錄（各 OS） |
| `ProcessPort` | 啟動／監看 Agent CLI、結束碼、取消 |
| `GitPort` | status／log／diff（先讀後寫） |
| `DialogPort` | 原生開檔／選目錄（經 Tauri） |

---

## 4. 製作流程（強制順序）

| 階段 | 名稱 | 做什麼 | 退出條件 |
|------|------|--------|----------|
| **1** | 先搭好 UI | Tauri 殼載入 Vanilla 工作台；選單／側欄／主區／空狀態可點 | 無真資料可走完主路徑 |
| **2** | 核心髒更新 | Rust：`Property + Dirty + Evaluation`；假資料驅動 UI 刷新 | 改一處 → 該亮的投影都更新 |
| **2.5** | 跨平台適配器 | 定義 Ports；stub → 真 Win／macOS／Linux 實作 | Contract 測試綠；fake／真可切換 |
| **3** | 功能 | 依模組切片實作（只依賴 Port） | 每片有可測行為與證據位 |
| **4** | UI 接 command | 按鈕／選單 → Tauri command → Core；畫面只吃髒更新結果 | UI 無直接 OS／CLI 呼叫 |

不可顛倒：沒有髒更新管線就堆真功能；沒有 Port 就寫死 OS。

---

## 5. UI 說明

### 5.1 設計來源與原則

- **視覺／資訊架構權威：** `git_workbench_interactive.html`
- **風格：** 深色 DCC 工作台；側欄 + 主看板 + Inspector；燈號不靠顏色 alone（需文字／圖示）
- **體感：** Comfy 式輕盈——少依賴、快啟動、本機優先
- **無障礙底線：** 可讀標籤、鍵盤焦點、危險操作標明專案／路徑

### 5.2 視窗結構

| 區域 | 內容 |
|------|------|
| 選單列 | 檔案／編輯／專案／模組／工項／視窗／說明 |
| 工具列 | 作用中專案、路徑、分支、常用動作 |
| 左側欄 | Agent 派工、Tasks Status、佈版、模組架構圖、UI 設計工具入口 |
| 主區 | 工項看板（紅／黃／灰／已驗收）、Git 工作台、架構 DAG、UI 設計總覽 |
| Inspector | 選中工項／模組詳情、下一步、證據摘要 |
| 狀態列 | 專案、連線／Agent、簡短訊息 |

### 5.3 主要畫面

| 畫面 | 用途 | 空／錯誤／停用 |
|------|------|----------------|
| **工項看板** | 四態燈號、篩選、搜尋、新增／切燈、派工入口 | 無結果可清除篩選；載入失敗不顯示他專案殘影 |
| **Agent 派工** | 依優先序（紅 > 黃 > 灰）啟動本機 CLI；看進行中 Run | Provider 缺失時停用並說明原因 |
| **Git 工作台** | 變更列表、diff、分支摘要；寫入操作獨立閘門 | dirty／diverged／租約衝突需明示 |
| **模組架構圖** | 模組 DAG、選取高亮、開啟模組規格 | 循環列路徑；無證據不標綠 |
| **UI 設計工具** | 頁面總覽／設計對照（開發期） | 可不進首版發布範圍 |
| **佈版／部署** | 部署設定與狀態（後期） | 未接 Adapter 顯示未支援 |
| **設定** | Agent 路徑、模式（DryRun／真啟動）、專案根 | 路徑無效不可存為作用中 |

### 5.4 選單與 command 對應（摘要）

| 選單 | 代表動作 → 未來 command |
|------|-------------------------|
| 檔案 | 新增／開啟專案、儲存、結束 |
| 編輯 | 復原／重做、全選變更、清除選取 |
| 專案 | 切換專案、重新掃描儲存庫 |
| 模組 | 切到 Git／架構圖／UI 設計、Ports 檢視 |
| 工項 | 新增工項、指派 Agent、批次 BDD／TDD 標籤 |
| 視窗 | 重設佈局、顯隱 Inspector／分支樹 |
| 說明 | 關於、架構說明 |

UI 事件只呼叫 **command 名稱 + 參數**；副作用全部在 Core／Adapter。

### 5.5 燈號語意（產品）

| 燈 | 含義 |
|----|------|
| 灰 | 未開始／等依賴 |
| 藍 | 執行中（有活動 Run） |
| 黃 | 待核准／待處理／過期／待對帳 |
| 紅 | 失敗／阻塞（需原因與證據） |
| 綠 | 核准範圍內驗收完成（**≠** 已正式發布） |

> 開發用 `PROJECT-BOARD.html` 燈號是 PM 切片狀態，勿與產品內工項健康混為同一權威。

---

## 6. 功能說明（模組）

功能依領域模組切片；實作時只依賴 Port。下表延續 product-plan 責任劃分，但 **宿主改為 Tauri，UI 改為 Vanilla**。

| 模組 | 名稱 | 功能摘要 |
|------|------|----------|
| **HOST** | 桌面宿主與建置 | App 生命週期、composition root、Tauri IPC、設定儲存；不擁有業務狀態 |
| **UI** | 工程控制台 | 畫面與互動；狀態投影；所有 mutation 經 command |
| **WORK** | 專案工作區 | 專案 ID、root 綁定、切換與租約；執行中拒重綁 |
| **SPEC** | 工程規格 | ModuleSpec、契約、BDD／TDD 定義；核准後不原地竄改 |
| **FLOW** | 流程與核准 | 工項階段、核准閘門、合法狀態轉移 |
| **EXEC** | Agent 執行 | Run、生命週期、取消；**兩種 Provider：CLI／本機 MCP**（見 §6.3） |
| **GUARD** | 開發邊界 | 封包完整性、允許／保護路徑、未核准不得實作 |
| **EVID** | 驗證證據 | 測試結果不可變紀錄、有效 RED／GREEN、版本綁定 |
| **GIT** | 版本控管 | clone／fetch／pull／commit／push（寫入需閘門）；Git 為歷史權威 |
| **REL** | 部署與發布 | 部署設定、打包／安裝驗證、發布核准與回滾（後期）；**Windows 安裝包走 WiX**（開源） |
| **REPORT** | 報告投影 | 模組／系統 HTML 報告；只讀規格與證據 |

### 6.1 首版功能優先（建議）

1. HOST + UI 空殼（階段 1）  
2. 髒更新 + WORK 投影（階段 2）  
3. Path／FS／Process stub→真適配器（階段 2.5）  
4. FLOW 燈號狀態 + EXEC DryRun→真 CLI + GIT 唯讀（階段 3）  
5. 看板／選單全面接 command（階段 4）  
6. GUARD／EVID／SPEC 加深 → REL／REPORT  

### 6.2 Agent 執行規則（功能約束）

- Run 必須綁定：專案 root、規格／工項 ID、工作樹指紋  
- Provider「說完成」≠ 工項綠燈；需 EVID／FLOW 閘門  
- 取消與崩潰要對帳，禁止盲目重跑 mutation  
- 首版預設**單一**進行中 Agent  
- UI／FLOW 只選 **Provider 種類 + 設定**；不直撞 CLI 或 MCP  

### 6.3 Agent 兩種接入（已拍板）

同一 `AgentPort`（或 EXEC Provider 介面），兩套 Adapter，**共用 Run 事件流**（started／chunk／progress／exited／failed）：

| 模式 | 名稱 | 做法 | 適用 |
|------|------|------|------|
| **A. CLI** | 原設計 | `ProcessPort` 啟動本機 CLI（Claude／cursor-agent／Codex／Antigravity 等），讀 stdout／stderr／結束碼 | 現有腳本化、可離線重現命令列 |
| **B. MCP** | 地端 Agent | 經 **MCP** 連本機／區網 Agent（stdio 或本機 HTTP／SSE，視宿主而定），工具呼叫與訊息走 MCP 協定 | 與已開的地端 Agent／IDE MCP 宿主對接，少一層「再包一層 CLI」 |

```
UI「指派 Agent」
  → command: start_run { provider: Cli | Mcp, … }
    → EXEC 選 Adapter
        ├─ CliAgentAdapter  → ProcessPort → 子行程
        └─ McpAgentAdapter  → MCP client  → 地端 Agent
    → 統一 Domain Event → Dirty → 投影（Run log／燈號）
```

**規則**
- 兩種模式都要能：**啟動、串流輸出、取消、結束對帳、錯誤分類**  
- 設定頁分開：「CLI 路徑／參數」與「MCP 端點／伺服器名稱／核准工具表」  
- DryRun 兩種皆可模擬事件，不真連、不真起程  
- 不強制一個 Run 同時走 CLI + MCP；並行屬後續（非首版）  
- MCP **只連使用者明示的地端／本機目標**，不當成雲端任意閘道；秘密與 token 不進 UI 投影  

**監聽（接續）**  
- CLI：pipe 監聽行程輸出  
- MCP：訂閱 MCP 通知／串流訊息，轉成同一套 `ProcessChunk` 類事件（名稱可為 `AgentChunk`）

### 6.4 佈版工具（已拍板）

| 項 | 定案 |
|----|------|
| Windows 安裝包 | **WiX**（開源、不收費） |
| 產物形態 | MSI（必要時 Bundle／burn 另評） |
| 驗證 | 靜默安裝／卸載、檔案與捷徑、回滾紀錄（對齊 VERIFY-INSTALL） |
| 與 Tauri | Tauri 建出應用本體後，由 WiX 包成安裝程式；不改用 Electron 安裝器 |
| 非本拍板 | NSIS、Inno、僅 portable zip 當唯一正式管道 |
| 後續 | macOS／Linux 安裝包屬 **M4**，不硬套 WiX |

派工卡：`PD-REL-01`（M3，不插隊 M1／M2）。

### 6.5 M4 包裝範圍與限制（已拍板 · BDD-PD-M4-DOC-01）

**邊界（硬）**

| 面 | 定案 |
|----|------|
| **Windows（M3）** | 正式安裝包管道＝**WiX → MSI**；Tauri 建本體後由 WiX 包安裝程式 |
| **M4 包裝** | macOS／Linux **契約／stub／文件／CI 矩陣占位**；可重跑、可標狀態；**不**硬套 WiX |
| **非 M4 包裝** | SSH／容器／DCC 宿主另案；不併入「跨平台安裝包已完成」；SSH／遠端／容器開題見 [`docs/SSH-REMOTE-CONTAINER-EPIC-SCOPE.md`](./SSH-REMOTE-CONTAINER-EPIC-SCOPE.md)（**未接通**；禁止暗示已接通） |

**M4 做什麼／不做什麼**

| 做 | 不做（禁止暗示已完成） |
|----|------------------------|
| PackSpec 產物欄位（os／arch／path／sha256／status）與 Build Result／releases 可掛接 | 宣稱已完整跨平台發行、商店上架、或全 OS 靜默裝卸皆綠 |
| macOS／Linux 包裝入口 stub（無對應主機 → **NOT RUN**） | 強制 notarize／stapling／App Store／發行版商店必過 |
| CI／文件列出 windows／macos／linux 占位；缺 runner → **NOT RUN** | 購買付費 mac runner 才算 M4 過關 |
| 文件寫清 WiX 僅涵蓋 Windows | 把 WiX MSI 成功寫成「三平台已發行」 |

**Build Result／PackSpec 狀態語意（含 NOT RUN）**

允許狀態僅：`PASS`｜`FAIL`｜`BLOCKED`｜`NOT RUN`｜`PARTIAL`。

| 狀態 | 何時使用 |
|------|----------|
| **NOT RUN** | 主機 OS ≠ 目標（例：在 Windows 跑 mac／linux stub）、缺 CI runner、elevated／notarize／真機裝卸**未執行**；**exit 可為 0，但不得記成 PASS** |
| **PARTIAL** | 契約／stub／文件到位，但真機驗證或簽章未跑（常見於 v0.1 候選） |
| **PASS** | 該列目標上之驗證**實際跑過且通過**；不可用「腳本存在」代替 |
| **FAIL**／**BLOCKED** | 已跑失敗／被決策或環境阻塞 |

**禁止偽綠／偽完整發行**
- Stub 腳本存在、文件勾選、或 Windows WiX 建出 MSI ≠ 跨平台發行完成  
- 缺 runner／非目標 OS → 必須 **NOT RUN**（或 PARTIAL），禁止改寫為 PASS  
- 行銷／對外文案不得暗示「已完整支援 macOS／Linux 安裝發行」；權威以本節與桌機 README 為準  

對照：`docs/CI-OS-MATRIX.md`（矩陣占位）；派工 epic `PRODUCT-M4-*`／`PD-M4-*`。

---

## 7. 開發期工具（非產品殼）

開發看板的唯一權威是 **`docs/board.json`**，格式與規則由 `.ai-hooks/validate-board.ps1` 強制（hook、Git hook、CI 跑同一支）。完整規則：`.agents/skills/ai-dev-pipeline/references/board-and-lights.md`（看板、層級、燈號、讀取範圍）與 `roles-and-gates.md`（角色、PR、Done 條件）；本節為摘要，兩者衝突時以 references 為準。

| 工具 | 位址／入口 | 用途 |
|------|------------|------|
| 開發看板 | `docs/board.json`（驗證：`.ai-hooks/validate-board.ps1`） | 開發本產品用的工作卡與燈號；每張卡含 `id`／`level`／`parentId`／`status`／`light`／`notes`／`history` |
| 派工清單 | Epic `PRODUCT-DEV-20261023`＋其下 `PD-*` 卡 | **首版切片**（流程骨架＋模組），不是全產品／不是 VGenAxIs 歷史全量；含 `PD-EXEC-CLI`／`PD-EXEC-MCP` |
| **Done 規則（硬性）** | 見 §7.1 | **產出＋獨立 `TDD_PASS`＋PR 已合併 → 才可設 Done／Blue** |
| **PM Agent 必作** | 見 §7.3；詳 `tools/board/PM-AGENT.md` | **建卡 → 決策紅燈 → 派 subagent**；不可只在對話開工 |
| 禁止占用 | `:8788` HoneyBadger mailbox、使用者指定勿動之 `:8787` | 不可當 SGenAxis 通道 |

產品發行走 **Tauri 桌機**；開發看板是內部 PM 資料，不等同產品 UI（產品內燈號語意見 §5.5，勿混用）。

**燈號（`light`，每張卡必填）**

| 燈 | 含義 |
|----|------|
| Gray | 未開始／暫停（暫停須寫原因） |
| Green | 進行順利（**不代表完成**） |
| Yellow | 有風險（必填 `lightReason`） |
| Red | 卡住或待決策（必填 `lightReason`；待決策時以「待決策：」開頭） |
| Blue | 完成（只在 `status=Done`／Released） |

### 7.1 Done（藍燈）規則（硬性 · 已拍板）

卡片設 `status=Done`、`light=Blue` 必須**三項同時成立**：

| # | 條件 | 不合格例 |
|---|------|----------|
| 1 | **有產出** | 可指認的原始碼／報告／產物路徑；空承諾、只改 `notes` → **不可 Done** |
| 2 | **獨立 `TDD_PASS`** | 由**獨立 TDD 代理**（驗證者 ≠ 開發者）親跑測試並回報 PASS；必要時高階審查也通過 | `PENDING_TDD_PACKET`、開發代理自測自報、未跑測、弱化 assertion → **不可 Done** |
| 3 | **PR 已合併** | 沒有 PR 的純文件／決策卡免此項，須在 `notes` 註明 | PR 仍 open／draft → **不可 Done** |

綠燈只表示進行順利；開發中、In Review 的卡都是 Green（或依風險 Yellow／Red），**不可**用 Green 表示完成。

**角色分離（硬性）**
| 角色 | 可做 | 不可做 |
|------|------|--------|
| **開發代理** | 寫碼、寫測試、交 `reports/dispatch-pd/<ID>.md`、開 draft PR、標 `READY_FOR_TDD`（卡最多移到 `In Review`） | 設 Done／Blue、宣稱 TDD PASS、弱化已核准斷言、驗收自己的卡 |
| **TDD 代理**（獨立） | 核對 TDD 封包、親跑測試、寫 `reports/dispatch-pd/<ID>-TDD-REVIEW.md`、回報 `TDD_PASS`／`TDD_FAIL` | 改產品程式；設 Done／Blue |
| **高階模型（PM／架構師）／使用者** | **僅在三項條件成立時** 設 Done／Blue、合併 PR | 僅憑開發代理口頭完成就設 Done；實作自己規劃的卡又自己驗收 |

**禁止**
- 排程／腳本／輪詢批次設 Done／Blue
- 開發代理自測通過就設 Done（必須另起獨立 TDD 代理）
- 以 PARTIAL、口頭完成、文件勾選代替 `TDD_PASS`

工具：`tools/board/poll_extinguish.py` 保留為**拒絕**批次結案的安全鎖；`tools/board/poll_next_work.py` 只列待做、不改燈（目前仍讀已停用的舊看板，見 PM-AGENT.md「已知落差」）。

### 7.2 領取範圍／讀取範圍（硬性 · 省 token）

Subagent **只處理自己領取的那一張卡**；禁止為「了解全貌」讀整份 `docs/board.json` 或其他卡。

| 角色 | 可讀 | 禁止（除非該卡 AC 明示） |
|------|------|---------------------------|
| **派工者（PM／母對話）** | 只把該卡 `id`／`title`／`bdd`（或 `scenarioIds`）／TDD 封包／允許·保護範圍與相關路徑寫進 prompt | 叫子代理讀整份 `docs/board.json`、掃全部 `reports/dispatch-pd/*`、整份 PRODUCT-DEVELOPMENT |
| **開發代理** | Prompt 摘錄；`reports/dispatch-pd/<本卡ID>.md`；本卡允許路徑內檔案 | 讀其他 `PD-*` 卡或報告／無關 crate；整板搜尋 |
| **TDD 代理** | 佇列內各卡的報告＋對應測試指令；寫 `<ID>-TDD-REVIEW.md` | 一次載入全部卡的 `notes` 當上下文 |

看板回寫：只改**本卡**——更新 `updatedAt`、在 `history` 追加 `{at, from, to, by, note}`、在 `notes` 追加 `{at, by, text}`（只追加不改舊紀錄）；**禁止**整檔重寫 `docs/board.json` 或用過期副本覆蓋。改完跑 `.ai-hooks/validate-board.ps1`。

### 7.3 PM Agent 必作事項（硬性 · 已拍板）

母對話／PM Agent 安排工作時，下列為**必作**（細節與檢查清單：`tools/board/PM-AGENT.md`）：

| # | 必作 | 不合格 |
|---|------|--------|
| 1 | **建卡**：下一批工作先寫入 `docs/board.json`（`level=Task`／Story，`parentId` 指向上層，`status=Todo`、`light=Gray`；BDD／允許範圍／AC 寫進卡） | 只在聊天列清單、不建卡就派工 |
| 2 | **決策 → 紅燈**：待核准／範圍未決／REPLAN／SPEC_CONFLICT／發布門檻未定 → `light=Red`，`lightReason` 以「待決策：」開頭，`notes` 條列每項決策（問題／選項／影響卡 ID／建議） | 決策未決就開工；紅燈無待決策清單 |
| 3 | **分派 subagent**：決策清後 `Todo`→`In Progress`、`light=Green`；一卡一開發代理＋獨立 TDD Gate；prompt 僅該卡（§7.2）；三項條件成立後才由高階模型／使用者設 Done／Blue（§7.1） | 跳過 TDD；開發代理自設 Done；整板塞進 prompt |

自動派工一律跳過待決策紅燈卡（由 PM／owner 處理）。

**禁止**：無建卡派工；決策紅燈未關就派依賴它的卡；用腳本批次設 Done／Blue。

---

## 8. 里程碑（對齊製作流程）

| 里程碑 | 目標 | 對應階段 |
|--------|------|----------|
| **M0** | 本說明與棧／流程核准（本文件） | — |
| **M1** | Tauri + Vanilla 可開；髒更新 + Ports stub | 1 → 2 → 2.5 |
| **M2** | 真 Agent CLI + 看板／Git 讀取閉環 | 3 → 4 |
| **M3** | 證據閘門、審核式 Git 寫入、**WiX** 打包／靜默安裝驗證 | 3 加深 + REL |
| **M4** | macOS／Linux **包裝契約／stub／文件／CI 占位**；SSH／容器／DCC **另案** | 可選；**WiX 僅 Windows**；**≠ 已完整跨平台發行**（詳 §6.5） |

每次建置應留下 Build Result（PASS／FAIL／BLOCKED／NOT RUN／PARTIAL）。**NOT RUN**＝該檢查未執行（非失敗、亦非通過）；見 §6.5。

---

## 9. 相關路徑

| 路徑 | 角色 |
|------|------|
| `git_workbench_interactive.html` | 產品 UI 原型 |
| `docs/PRODUCT-DEVELOPMENT.md` | 本說明（Markdown） |
| `docs/PRODUCT-DEVELOPMENT.html` | 本說明（HTML，可雙擊開啟） |
| `docs/PROJECT-BOARD.html` | 開發看板資料與 UI |
| `tools/board/PM-AGENT.md` | **PM Agent 必作**：建工項、決策紅燈、分派 subagent |
| `docs/start-board-watch.cmd` | 看板服務啟動（埠 **28789**） |
| `apps/sgenaxis-desktop/README.md` | 桌機 App 使用說明（開專案／DryRun／設定；埠禁區） |
| `docs/VERIFY-ELEVATED-AND-LIVE-SMOKE.md` | elevated VERIFY-INSTALL／Live CLI 冒煙操作、風險、NOT RUN（PD-VERIFY-DOC-01） |
| `docs/RELEASE-CHECKLIST-v0.1.md` | v0.1 發布檢查清單（MSI／elev／sec／SBOM／簽章／CHANGELOG；PASS｜FAIL｜NOT RUN｜PARTIAL）（PD-REL-CHECKLIST-01） |
| `docs/ROLLBACK-v0.1.md` | v0.1 MSI 靜默卸載／失敗復原／風險；未真跑＝NOT RUN；禁止暗示已完成正式發布回滾演練（PD-ROLLBACK-DOC-01） |
| `docs/SSH-REMOTE-CONTAINER-EPIC-SCOPE.md` | SSH／遠端／容器**另案**範圍一頁；**未接通**；本頁無客戶端；禁止暗示遠端已接通（PD-REMAIN-SSH-EPIC-01） |
| `docs/DESKTOP-APP-USAGE.md` | 桌機使用說明索引（指向 README） |
| `reports/gonogo-v0.1.0-*.md` | Rel-Freeze Go／NoGo／**Go-with-PARTIAL** 結案報告（PD-REL-GONOGO-01）；非正式商店發布 |
| `reports/milestone-validation-v0.1.md` | Rel-Freeze 里程碑驗收（M0–M4＋Rel-Candidate；可 PARTIAL）（PD-MILESTONE-VAL-01） |
| `reports/dispatch-pd/` | 派工證據目錄（含 Rel-Freeze／Post-Freeze 各卡） |
| `docs/product-plan/` | 舊 Electron／React 規畫；模組語意可參考，技術選型以本文件為準 |
| `docs/architecture/index.html` | 既有架構筆記（實作時需對齊本文件改寫） |

**Post-Freeze／Rel-Freeze 結案語意（BDD-PD-PRODUCT-DOC-CLOSE-01）**

- Rel-Freeze 結案 verdict 可為 **Go-with-PARTIAL**（對齊 V01-GATE）；**不是**正式商店發布完成。
- **DCC／SSH／商店上架**＝**另案**；不併入本文件已決棧或「已發行」宣稱。SSH／遠端／容器開題權威：`docs/SSH-REMOTE-CONTAINER-EPIC-SCOPE.md`（**未接通**）。
- **禁止暗示完整跨平台發行已完成**（WiX MSI／stub／文件到位 ≠ 三平台已發行）；權威仍見 §6.5。

---

## 10. 變更紀錄

| 日期 | 說明 |
|------|------|
| 2026-10-24 | PD-REMAIN-SSH-EPIC-01：`docs/SSH-REMOTE-CONTAINER-EPIC-SCOPE.md` SSH／遠端／容器另案範圍一頁；未接通；禁止暗示遠端已接通；無客戶端實作 |
| 2026-10-24 | PD-PRODUCT-DOC-CLOSE-01（Post-Freeze）：§9／§10 記入 Rel-Freeze 結案與 **Go-with-PARTIAL**；明示 DCC／SSH／商店另案；禁止暗示完整跨平台發行已完成 |
| 2026-10-24 | PD-ROLLBACK-DOC-01：`docs/ROLLBACK-v0.1.md` 靜默卸載／失敗復原／風險；未真跑＝NOT RUN；禁止暗示正式發布回滾演練已完成 |
| 2026-10-24 | PD-REL-CHECKLIST-01：`docs/RELEASE-CHECKLIST-v0.1.md` 發布前可勾選項（MSI／elev／sec／SBOM／簽章／CHANGELOG）＋狀態語意 |
| 2026-10-24 | PD-M4-DOC-01：§6.5 M4 包裝範圍／NOT RUN 語意／WiX 僅 Windows；禁止暗示已完整跨平台發行；桌機 README 對齊 |
| 2026-10-24 | PD-README-APP-01：桌機使用說明（README＋`DESKTOP-APP-USAGE.md`）；明確 28789／`:8788` 禁區 |
| 2026-10-23 | 初版：拍板 Tauri 2 + Vanilla + Rust Core；製作流程 1→2→2.5→3→4；看板埠 28789；廢止 Electron／React 為產品棧 |
| 2026-10-23 | EXEC：Agent 分為 CLI 與地端 MCP 兩種 Provider，共用 Run 事件流 |
| 2026-10-23 | 看板寫入派工清單：`PRODUCT-DEV-20261023`＋`PD-DOC/UI/DIRTY/ADAPT/EXEC-CLI/EXEC-MCP/CMD` |
| 2026-10-23 | REL／佈版：Windows 安裝包拍板 **WiX**（M3；macOS／Linux 另案） |
| 2026-10-24 | §7.3 PM Agent 必作：建工項、決策紅燈＋待決策事項、分派 subagent；`tools/board/PM-AGENT.md`；`skip_kinds`+`decision` |
| 2026-10-24 | **滅燈規則**：未產出且 TDD 未過關不可滅工項；禁止排程直接改綠 |
| 2026-10-24 | **TDD Agent 閘門**：另起獨立 TDD Agent 測過（`TDD_PASS`）才可由母對話標綠；實作代理不可改綠 |
| 2026-10-24 | **§7.2 領取讀取範圍**：subagent 只讀自己領取工項；禁止讀整板／全部報告（省 token） |
