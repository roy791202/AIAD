# Elevated VERIFY-INSTALL 與 Live CLI 冒煙 — 操作說明

工項：`PD-VERIFY-DOC-01` · BDD-PD-VERIFY-DOC-01  
Epic：`PRODUCT-VERIFY-20261024`  
對照實作卡：`PD-ELEV-VERIFY-01`、`PD-LIVE-CLI-SMOKE-01`（可選；須決策核准後才黃燈實跑）

本文件說明**如何人工跑** elevated 靜默裝／卸與真 CLI Live 冒煙、權限與風險，以及 **NOT RUN** 語意。  
權威產品邊界：[`PRODUCT-DEVELOPMENT.md`](./PRODUCT-DEVELOPMENT.md) §6.4–§6.5、§6.3。  
桌機日常使用（開專案／DryRun／埠禁區）：[`apps/sgenaxis-desktop/README.md`](../apps/sgenaxis-desktop/README.md)。

---

## 1. 狀態字串（硬）

允許狀態僅：`PASS`｜`FAIL`｜`BLOCKED`｜`NOT RUN`｜`PARTIAL`。

| 狀態 | 何時使用（本文件範圍） |
|------|------------------------|
| **NOT RUN** | 未提升權限、未核准決策、本機無目標 CLI、未實際執行 elevated `/qn` 或 Live start→exit；**exit 可為 0，不得記成 PASS** |
| **PARTIAL** | 契約／dry／文件到位，但 elevated 或 Live 真跑未做（常見） |
| **PASS** | 該檢查**實際跑過且通過**（elevated 裝卸對帳成功，或 Live start→chunk→exit 觀測成功） |
| **FAIL** | 已跑且失敗（msiexec 非零、檔案／捷徑缺失、CLI 異常結束等） |
| **BLOCKED** | 決策未批、環境禁止、或明確中止（非「沒跑」） |

**禁止**：把「腳本存在」「dry／契約通過」「CI 綠」改寫成 elevated／Live 的 **PASS**。

---

## 2. Elevated VERIFY-INSTALL（靜默裝／卸）

### 2.1 何時可跑

| 前置 | 說明 |
|------|------|
| 決策 | `PD-DEC-ELEV-01`／批級 `PD-DEC-VERIFY-GO-01` 已核准；未批 → 維持 **NOT RUN**／**BLOCKED**，勿黃燈實跑 |
| OS | **Windows x64**；macOS／Linux 裝卸屬 M4 stub → **NOT RUN** |
| 產物 | 已建 MSI：`packaging/windows/wix/out/SGenAxis-*-windows-x64.msi`（`.\build-msi.ps1`） |
| 權限 | **已提升**的 PowerShell（系統管理員）。腳本**不會**自行 UAC 提權 |

細節與契約：[`packaging/windows/wix/README.md`](../packaging/windows/wix/README.md)（PD-REL-03）。

### 2.2 契約／dry（預設 — 不裝系統）

不需管理員。elevated 列標記 **NOT RUN**，overall 常為 **PARTIAL**。

```powershell
cd D:\AIAD\packaging\windows\wix
.\verify-install.ps1
# → out\verify-install-result.json
# elevated 列 status=NOT RUN（不得偽造 PASS）
```

### 2.3 Live elevated（真靜默裝／卸）

**必須**已在「以系統管理員身分執行」的 PowerShell：

```powershell
cd D:\AIAD\packaging\windows\wix
.\verify-install.ps1 -RunElevated
# → msiexec /qn 安裝＋卸載；寫入 out\verify-install-*.log 與 verify-install-result.json
```

等價手動（仍須 elevated）：

```powershell
msiexec /i D:\AIAD\packaging\windows\wix\out\SGenAxis-0.1.0-windows-x64.msi /qn /norestart /l*v out\verify-install-install.log
Test-Path "${env:ProgramFiles}\SGenAxis\SGenAxis.exe"
Test-Path "${env:ProgramData}\Microsoft\Windows\Start Menu\Programs\SGenAxis\SGenAxis.lnk"
msiexec /x D:\AIAD\packaging\windows\wix\out\SGenAxis-0.1.0-windows-x64.msi /qn /norestart /l*v out\verify-install-uninstall.log
```

結果掛接：由 `PD-ELEV-VERIFY-01`／`PD-VERIFY-HANG-01` 寫入報告或 Build Result；本文件只定義操作與語意。

### 2.4 權限／風險

| 風險 | 說明 |
|------|------|
| 系統變更 | `/qn` 寫入 `%ProgramFiles%\SGenAxis`、開始功能表捷徑；卸載亦同 |
| 需管理員 | 非 elevated 時 `-RunElevated` **不得**偽造成功；列為 **NOT RUN** |
| 機器選擇 | 建議用可還原 VM／專用機；勿在未備份的生產桌面盲跑 |
| 禁區 | 不觸碰 `:8788`／`:8787`；非正式管道勿用 NSIS／Inno |
| CI | 預設 **不**強制 elevated 才算閘門綠；未跑＝**NOT RUN**／**PARTIAL** |

---

## 3. Live CLI 冒煙（真啟動，非 DryRun）

### 3.1 與 DryRun／主路徑 smoke 的差別

| 路徑 | 做什麼 | elevated？ |
|------|--------|------------|
| DryRun（桌機設定） | 模擬 Run 事件；**不**起真 CLI | 否 |
| `scripts/pd_smoke_01.py`（PD-SMOKE-01） | UI／專案／看板／DryRun 閉環 | 否；**不做** elevated MSI |
| **Live CLI 冒煙**（本節） | 核准後真 `start → chunk → exit`（或明確跳過） | 否（行程權限＝目前使用者） |

權威接入規則：[`PRODUCT-DEVELOPMENT.md`](./PRODUCT-DEVELOPMENT.md) §6.3；桌機步驟見 README「使用說明」。

### 3.2 何時可跑

| 前置 | 說明 |
|------|------|
| 決策 | `PD-DEC-LIVE-CLI-01`／批級核准；未批 → **NOT RUN**／**BLOCKED** |
| 目標 | 本機明示 CLI（如 `claude`／`cursor-agent`／`codex`）或設定中的可執行路徑；皆無 → **NOT RUN**（見 `PD-LIVE-TARGET-01`） |
| 模式 | 桌機設定為 **Live**（「存為作用中」）；路徑有效；**禁止** `:8788`／`:8787`／URL 當看板根 |
| 秘密 | token／API key **不進** UI／看板投影（僅得有 `has_secret` 類旗標） |

### 3.3 建議操作步驟（人工冒煙）

1. 啟動桌機：`cd apps/sgenaxis-desktop` → `npm run tauri dev`（見 README）。
2. 設定 → CLI Provider：選工具並填**本機可執行檔路徑**（勿填雲端任意閘道）。
3. 看板／專案根＝本機檔路徑（例：`docs/PROJECT-BOARD.html`）。
4. **存為作用中（Live）**；確認未被禁區埠／無效路徑拒絕。
5. Agent 面板 → Provider **Cli** → 啟動一次 Live 派工（非 DryRun）。
6. 觀測：Run **started** → 輸出 **chunk** → **exited**（結束碼可觀測）；可取消則再驗取消路徑。
7. 結束後可切回 DryRun（「僅存草稿／切回 DryRun」），避免後續誤觸真啟動。

自動化腳本／契約測試由 `PD-LIVE-CLI-SMOKE-01` 交付；本文件定義**操作與判定語意**，不強制本卡實作腳本。

### 3.4 權限／風險

| 風險 | 說明 |
|------|------|
| 真子行程 | Live 會啟動本機 Agent CLI，可能改工作樹／呼叫網路（視該 CLI） |
| 範圍 | 僅使用者明示的本機目標；**不做**雲端任意閘道 |
| 秘密外洩 | 投影／報告／看板 note **不得**貼 token；失敗日誌需脫敏 |
| 與 elevated 無關 | Live smoke **不**取代 VERIFY-INSTALL；未跑 elevated 仍記 **NOT RUN** |
| 失敗分類 | 無 CLI／未核准＝**NOT RUN** 或 **BLOCKED**；起程後異常＝**FAIL**（不得改成 NOT RUN 掩飾） |

---

## 4. NOT RUN 速查（驗收用）

| 情境 | 應記 |
|------|------|
| 未開 elevated PowerShell、只跑 `.\verify-install.ps1` | elevated 列 **NOT RUN**；overall 常 **PARTIAL** |
| 決策未批 elevated／Live | **NOT RUN** 或 **BLOCKED**（依決策卡），**非 PASS** |
| 本機無可用 CLI、探測失敗 | Live smoke **NOT RUN** |
| macOS／Linux 主機跑 Windows MSI elevated | **NOT RUN** |
| 契約測試通過、文件寫完 | **≠** elevated／Live **PASS** |
| elevated `/qn` 或 Live start→exit 真跑且通過 | 該項才可 **PASS** |

掛入 Build Result 時同樣遵守：缺跑 → **NOT RUN**；失敗 → **FAIL**／**PARTIAL**；禁止把 NOT RUN 寫成 PASS（`PD-VERIFY-HANG-01`）。

---

## 5. 交叉連結

| 文件／入口 | 用途 |
|------------|------|
| [`apps/sgenaxis-desktop/README.md`](../apps/sgenaxis-desktop/README.md) | 開專案／DryRun／Live 設定／埠禁區；本操作之桌機側入口 |
| [`packaging/windows/wix/README.md`](../packaging/windows/wix/README.md) | WiX MSI、`verify-install.ps1`、`-RunElevated` |
| [`ROLLBACK-v0.1.md`](./ROLLBACK-v0.1.md) | v0.1 靜默卸載／失敗復原／風險；未真跑＝**NOT RUN**（PD-ROLLBACK-DOC-01） |
| [`PRODUCT-DEVELOPMENT.md`](./PRODUCT-DEVELOPMENT.md) §6.3–§6.5 | Provider、VERIFY-INSTALL、NOT RUN 權威語意 |
| [`DESKTOP-APP-USAGE.md`](./DESKTOP-APP-USAGE.md) | 桌機使用說明索引 |
| `scripts/pd_smoke_01.py` | 主路徑 DryRun smoke（**非**本文件 Live／elevated） |

---

## 6. BDD 對照（BDD-PD-VERIFY-DOC-01）

| Given／When | Then |
|-------------|------|
| 操作者依 §2 跑 dry verify-install | 結果 JSON 存在；elevated 列為 **NOT RUN**（未提權時） |
| 已核准且 elevated 下跑 `-RunElevated` | 可完成靜默裝／卸對帳；狀態非偽 PASS |
| 操作者依 §3 在核准下跑 Live CLI | 可觀測 start→chunk→exit，或因無 CLI／未核准得 **NOT RUN**／明確跳過原因 |
| 讀 §1／§4 | 權限／風險與 **NOT RUN** 語意清楚；不得把未跑當成 PASS |
