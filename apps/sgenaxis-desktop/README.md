# SGenAxis Desktop — 使用說明與開發備註

Tauri 2 + Vanilla HTML/CSS/JS 桌機殼。  
權威規格：`docs/PRODUCT-DEVELOPMENT.md`  
**新使用者請先讀下方「使用說明」**（BDD-PD-README-APP-01）。

---

## 使用說明（開專案／DryRun／設定）

### 埠與禁區（必讀）

| 用途 | 位址／入口 | 說明 |
|------|------------|------|
| **開發看板（PM）** | `http://127.0.0.1:28789/` | 雙擊 `docs/start-board-watch.cmd`；寫回 `docs/PROJECT-BOARD.html` |
| **產品桌機** | `npm run tauri dev`（本目錄） | 正式使用路徑；**不是**瀏覽器開看板埠 |
| **禁止** | `:8788` | HoneyBadger mailbox — **不可**當 SGenAxis／Agent／看板通道 |
| **禁止** | `:8787` | 使用者指定勿動 |
| **已讓出** | `:18789` | 舊看板埠；勿再寫回腳本 |

桌機設定裡的「看板／專案根路徑」必須是**本機檔案路徑**（例如 `docs/PROJECT-BOARD.html`），**禁止**填 `http://…`、`:8788`、`:8787`。無效路徑／禁區埠**不可**存為 Live（作用中）。

### 1）啟動桌機

前置：Rust stable + Cargo、[Tauri 系統依賴](https://v2.tauri.app/start/prerequisites/)（Windows 需 WebView2）、Node.js 18+（建議）。

```powershell
cd D:\AIAD\apps\sgenaxis-desktop
npm install
npm run tauri dev
```

成功時會開出桌機視窗（選單列、側欄、主區、狀態列）。  
僅瀏覽器開 `ui/index.html` 可做導覽 QA，**無 Tauri IPC** → 無法真開專案設定持久化／無法跑 DryRun。

### 2）開專案／綁定看板路徑

1. 側欄點 **設定**（或選單切到設定面板）。
2. 在「看板／專案根路徑（本機檔；非 URL）」填入倉庫內看板檔，例如：  
   `D:\AIAD\docs\PROJECT-BOARD.html`（相對路徑亦可，視 host 解析）。
3. 按 **僅存草稿（DryRun）** 先持久化；確認路徑不含 `:8788`／`:8787`／`http`。
4. 狀態列應反映專案／設定已載入；工具列「開啟專案…」若仍標示意，以**設定面板路徑**為準。

開發期若要同時看燈號板：另開 `docs/start-board-watch.cmd` → **只**用 `http://127.0.0.1:28789/`，**不要**連 `:8788`。

### 3）跑 DryRun（不真起程／不真連 MCP）

1. 設定面板確認模式為 **DryRun**（或按「切回 DryRun」／「僅存草稿」）。
2. 側欄開 **Agent**（或工具列「Agent 派工」／「DryRun 派工」）。
3. 選 Provider：**Cli** 或 **Mcp**。
4. 按 **DryRun 派工** → 經 `start_run`（`dry_run: true`）模擬 Run 事件；Log／串流會更新。
5. 可 **取消** 進行中的 Run（有 `run_id` 時）。

DryRun **不會**真啟動 CLI、**不會**真連地端 MCP。Live 需在設定填有效 CLI 路徑或 MCP 端點後按「存為作用中（Live）」；端點仍**禁止** `:8788`／`:8787`。

**Elevated VERIFY／Live CLI 冒煙（可選）** — 靜默 MSI 裝卸、真 CLI start→chunk→exit、權限風險與 **NOT RUN** 語意：見 [`docs/VERIFY-ELEVATED-AND-LIVE-SMOKE.md`](../../docs/VERIFY-ELEVATED-AND-LIVE-SMOKE.md)（BDD-PD-VERIFY-DOC-01）。主路徑 DryRun smoke（`scripts/pd_smoke_01.py`）**不**取代該文件。

### 4）設定（CLI／MCP／模式）

| 區塊 | 做什麼 |
|------|--------|
| 執行模式 | DryRun＝模擬；Live＝核准真啟動（路徑／端點須有效） |
| 看板／專案根 | 本機檔路徑；非 URL；禁 `:8788`／`:8787` |
| CLI（Provider A） | 選 Claude／cursor-agent／Codex／Antigravity + 可執行檔路徑 |
| MCP（Provider B） | 傳輸、伺服器名、端點、核准工具表；secret 只存本機、不進投影 |
| 存為作用中 | Live；無效／禁區埠會被拒 |
| 僅存草稿／切回 DryRun | 持久化但 `agent_active=false` |
| 檢視投影 | 看無 secret 的投影（僅 `has_secret`） |

### 5）工項看板（桌機內）

- **新增工項** → `upsert_task`（需 Tauri）。
- 桌機讀本機 `#board-snapshot`／設定之路徑；**不**依賴 HoneyBadger `:8788` 寫回。
- 開發用 HTTP 看板僅 **28789**（見上表）。

### 驗收對照（BDD-PD-README-APP-01）

| Given／When | Then |
|-------------|------|
| 新使用者依本節啟動 | 可 `tauri dev` 開桌機 |
| 依本節設專案／看板路徑 | 本機路徑可存；`:8788`／URL 被拒說明清楚 |
| 依本節 DryRun | Agent 面板可啟動模擬 Run |
| 讀埠表 | **28789**＝看板；**:8788**＝禁區 |

---

## 範圍與不做

- 可開的 Tauri 殼載入 Vanilla 工作台；IPC → Core／EXEC／HOST
- **不做**：把 `:8788` 當產品通道；行銷網站；Electron／React／egui 主 UI

## 包裝／發行邊界（M3／M4 · BDD-PD-M4-DOC-01）

權威細節：`docs/PRODUCT-DEVELOPMENT.md` §6.4–§6.5。本節僅摘要，**禁止**解讀為已完整跨平台發行。

| 里程碑 | 範圍 | 邊界 |
|--------|------|------|
| **M3（Windows）** | **WiX → MSI** 為正式 Windows 安裝包管道；`npm run tauri build` 產出本體後由 WiX 包安裝程式 | **不是** NSIS／Inno 正式管道；WiX **不**涵蓋 macOS／Linux |
| **M4** | macOS／Linux **包裝契約／stub／文件／CI 矩陣占位**（可重跑、可標狀態） | **≠** notarize／商店上架／三平台靜默裝卸皆綠；SSH／容器／DCC **另案** |

**NOT RUN 語意（Build Result／PackSpec）**

狀態僅：`PASS`｜`FAIL`｜`BLOCKED`｜`NOT RUN`｜`PARTIAL`。

- **NOT RUN**：目前主機不是目標 OS、缺 CI runner、或 elevated／notarize／真機裝卸**未跑** → 可結束但不偽造成 **PASS**
- **PARTIAL**：stub／文件／契約到位，真機驗證未跑（常見）
- **PASS**：該 OS 目標上驗證**實際跑過且通過**；「有腳本／有 README」不算 PASS

`tauri build` 在本機成功、或 Windows WiX MSI 建出，**都不代表** macOS／Linux 安裝包已發行。矩陣占位見 `docs/CI-OS-MATRIX.md`。

**Elevated／Live 補充：** 未提升權限的 VERIFY-INSTALL、未核准或無本機 CLI 的 Live 冒煙 → **NOT RUN**（可 PARTIAL）；操作步驟見 [`docs/VERIFY-ELEVATED-AND-LIVE-SMOKE.md`](../../docs/VERIFY-ELEVATED-AND-LIVE-SMOKE.md)。

**v0.1 發布檢查清單：** 發布前可勾選 MSI／elev／sec／SBOM／簽章／CHANGELOG，每項標 **PASS｜FAIL｜NOT RUN｜PARTIAL** — [`docs/RELEASE-CHECKLIST-v0.1.md`](../../docs/RELEASE-CHECKLIST-v0.1.md)（PD-REL-CHECKLIST-01）。

## 目錄

```
apps/sgenaxis-desktop/
  ui/                   # Vanilla 前端
  crates/               # core／ports／adapters／exec／listen／guard／evid／spec／work／host
  src-tauri/            # Tauri 2 host
  package.json
  README.md             # 本檔
```

## 前置依賴（摘要）

| 工具 | 用途 |
|------|------|
| [Rust](https://rustup.rs/) stable + Cargo | 編譯 `src-tauri` |
| [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/) | WebView2（Windows）等 |
| Node.js 18+（建議） | `npm i` → `@tauri-apps/cli` |

```powershell
winget install Rustlang.Rustup
# 重開終端：rustup default stable
cd D:\AIAD\apps\sgenaxis-desktop
npm install
```

## 瀏覽器暫行 QA（無 Rust 時）

```powershell
cd D:\AIAD\apps\sgenaxis-desktop
npx --yes serve ui -l 1420
# http://127.0.0.1:1420 — 僅導覽；無 DryRun IPC
```

## 測試／建置

```powershell
cd D:\AIAD\apps\sgenaxis-desktop\src-tauri
cargo test --lib

cd D:\AIAD\apps\sgenaxis-desktop
npm run tauri build
```

## 授權

產品棧：Tauri MIT／Apache-2.0；本目錄骨架隨倉庫授權。
