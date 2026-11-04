# SGenAxis v0.1 回滾／靜默卸載復原說明

工項：`PD-ROLLBACK-DOC-01` · BDD-PD-ROLLBACK-DOC-01  
依賴：`PD-REL-03`（WiX VERIFY-INSTALL）、`PD-VERIFY-DOC-01`（elevated 操作語意）

本文件說明 **v0.1 Windows MSI** 的靜默卸載、失敗後復原步驟與風險，以及如何標註 **NOT RUN**。  
**本文件是操作／復原說明，不是正式發布回滾演練紀錄。** 未在本機 elevated 真跑的步驟必須標 **NOT RUN**；禁止暗示「已完成正式發布回滾演練」或把文件／契約通過寫成演練 **PASS**。

權威狀態集合：[`PRODUCT-DEVELOPMENT.md`](./PRODUCT-DEVELOPMENT.md) §6.5。  
Elevated 裝／卸操作細節：[`VERIFY-ELEVATED-AND-LIVE-SMOKE.md`](./VERIFY-ELEVATED-AND-LIVE-SMOKE.md)。  
WiX／`verify-install.ps1` 契約：[`packaging/windows/wix/README.md`](../packaging/windows/wix/README.md)。

---

## 1. 範圍與非宣稱

| 本文件**做** | 本文件**不做／不宣稱** |
|--------------|------------------------|
| 說明 MSI **silent uninstall**（`msiexec /x … /qn`）步驟 | 強制本機 elevated 卸載演練（本卡不做） |
| 失敗復原步驟與風險表 | 把「文件寫完」當成回滾演練 **PASS** |
| 未真跑項標 **NOT RUN** | 暗示已完成正式發布回滾演練 |
| 與 VERIFY／PD-REL-03 交叉連結 | macOS／Linux 卸載（M4 → **NOT RUN**） |

本卡產出＝文件＋契約 assert；**elevated 真卸載**若未跑 → 回滾演練列＝**NOT RUN**（常見 **PARTIAL** 文件就緒）。

---

## 2. MSI 靜默卸載（silent uninstall）

### 2.1 前置

| 前置 | 說明 |
|------|------|
| OS | **Windows x64**；非 Windows → **NOT RUN** |
| 產物 | 已建 MSI：`packaging/windows/wix/out/SGenAxis-*-windows-x64.msi` |
| 權限 | **已提升** PowerShell（系統管理員）。腳本／本說明**不會**自行 UAC 提權 |
| 決策 | 若組織要求先批 elevated（如 `PD-DEC-ELEV-01`），未批 → **NOT RUN**／**BLOCKED**，勿偽 PASS |

### 2.2 建議路徑（契約腳本）

不需管理員的 dry／契約（卸載列維持 **NOT RUN**）：

```powershell
cd D:\AIAD\packaging\windows\wix
.\verify-install.ps1
# → out\verify-install-result.json；elevated 卸載列 status=NOT RUN
```

已核准且 **已 elevated** 時，真靜默裝＋卸（含 silent uninstall）：

```powershell
cd D:\AIAD\packaging\windows\wix
.\verify-install.ps1 -RunElevated
# → msiexec /qn 安裝後再 msiexec /x /qn 卸載；寫 log＋result JSON
```

細節見 [`VERIFY-ELEVATED-AND-LIVE-SMOKE.md`](./VERIFY-ELEVATED-AND-LIVE-SMOKE.md) §2。

### 2.3 手動 silent uninstall（等價）

僅在已 elevated、且確知要從本機移除已安裝產品時：

```powershell
# 以實際 MSI 檔名為準（例 0.1.0）
$msi = "D:\AIAD\packaging\windows\wix\out\SGenAxis-0.1.0-windows-x64.msi"
msiexec /x $msi /qn /norestart /l*v D:\AIAD\packaging\windows\wix\out\rollback-uninstall.log
```

卸載後對帳（應為不存在）：

```powershell
Test-Path "${env:ProgramFiles}\SGenAxis\SGenAxis.exe"   # expect False
Test-Path "${env:ProgramData}\Microsoft\Windows\Start Menu\Programs\SGenAxis\SGenAxis.lnk"  # expect False
```

亦可用產品碼：`msiexec /x {PRODUCT-CODE} /qn /norestart`（從安裝 log／登錄查；本文件不強制寫死 GUID）。

---

## 3. 失敗復原步驟

當 silent uninstall **失敗**（msiexec 非零、檔案／捷徑殘留、或部分寫入）時，依序：

1. **保留證據** — 複製 `rollback-uninstall.log`／`verify-install-uninstall.log` 與 `verify-install-result.json`；狀態記 **FAIL**（已跑失敗）或 **PARTIAL**（部分對帳失敗），**禁止**改成 NOT RUN 掩飾。
2. **重試一次 elevated `/x /qn`** — 同一 MSI；仍失敗則勿循環盲跑。
3. **對帳殘留** — 手動確認 `%ProgramFiles%\SGenAxis`、開始功能表 `SGenAxis` 捷徑；殘留則在 elevated 下刪除空目錄／捷徑（僅本產品路徑；勿掃全碟）。
4. **必要時重裝再卸** — 若產品處於「半安裝」：先 elevated `msiexec /i … /qn`，再 `/x … /qn`（見 VERIFY §2.3）。
5. **機器還原** — 建議在可還原 VM／快照上回滾整機；生產桌面無快照時停止並升級為 **BLOCKED**／人工處理，勿宣稱演練 PASS。
6. **記錄** — Build Result／報告寫明：步驟、exit、log 路徑、最終狀態（FAIL｜PARTIAL｜NOT RUN）。

未執行上述任一步 → 該步標 **NOT RUN**。

---

## 4. 風險

| 風險 | 說明 |
|------|------|
| 系統變更 | `/qn` 卸載會移除 `%ProgramFiles%\SGenAxis` 與開始功能表捷徑；失敗可能留下殘檔 |
| 需管理員 | 非 elevated 不得偽造成功；未提權＝**NOT RUN** |
| 錯 MSI／錯版本 | `/x` 錯檔可能卸到非預期產品列；確認檔名／版本與已安裝一致 |
| 機器選擇 | 優先可還原 VM；勿在未備份生產機盲跑 |
| 與「正式回滾演練」混淆 | **文件／assert 通過 ≠ 已完成正式發布回滾演練** |
| CI | 預設不強制 elevated 卸載才綠；未跑＝**NOT RUN**／**PARTIAL** |
| 禁區 | 不觸碰 `:8788`／`:8787`；非正式管道勿用 NSIS／Inno 當主通道 |

---

## 5. NOT RUN 速查（本文件）

| 情境 | 應記 |
|------|------|
| 只寫了本說明／單元 assert 通過，未 elevated `/x` | 回滾演練／真卸載＝**NOT RUN** |
| 只跑 `.\verify-install.ps1`（無 `-RunElevated`） | elevated 卸載列 **NOT RUN**；overall 常 **PARTIAL** |
| 決策未批 elevated | **NOT RUN** 或 **BLOCKED** |
| macOS／Linux 主機 | Windows MSI 回滾＝**NOT RUN** |
| elevated `/x /qn` 真跑且對帳通過 | 該項才可 **PASS**（仍≠「正式發布回滾演練已完成」除非 owner 另開演練卡並掛證據） |
| 真跑失敗 | **FAIL**／**PARTIAL**，禁止改寫 NOT RUN |

---

## 6. 交叉連結

| 文件／入口 | 用途 |
|------------|------|
| [`VERIFY-ELEVATED-AND-LIVE-SMOKE.md`](./VERIFY-ELEVATED-AND-LIVE-SMOKE.md) | elevated 靜默裝／卸操作與 NOT RUN |
| [`packaging/windows/wix/README.md`](../packaging/windows/wix/README.md) | PD-REL-03 VERIFY-INSTALL、`verify-install.ps1` |
| [`RELEASE-CHECKLIST-v0.1.md`](./RELEASE-CHECKLIST-v0.1.md) | 發布前 Elev 檢查項 |
| [`PRODUCT-DEVELOPMENT.md`](./PRODUCT-DEVELOPMENT.md) §6.4–§6.5 | VERIFY-INSTALL／狀態語意 |
| [`DESKTOP-APP-USAGE.md`](./DESKTOP-APP-USAGE.md) | 桌機使用索引 |

---

## 7. BDD 對照（BDD-PD-ROLLBACK-DOC-01）

| Given／When | Then |
|-------------|------|
| 讀本文件 §2 | 說明 MSI **silent uninstall**（`msiexec /x`／`/qn`）步驟 |
| 讀 §3 | 失敗復原步驟可依序執行／記錄 |
| 讀 §4 | **風險**表清楚（權限、殘留、錯版、與演練混淆） |
| 未真跑 elevated 卸載 | 標 **NOT RUN**；不得暗示已完成正式發布回滾演練 |
| 契約 assert | 必要標題／片語存在（見 `tests/test_pd_rollback_doc_01.py`） |
