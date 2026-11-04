# SGenAxis v0.1 發布檢查清單（可勾選）

工項：`PD-REL-CHECKLIST-01` · BDD-PD-REL-CHECKLIST-01  
填寫：`PD-CHECKLIST-FILL-01` · BDD-PD-CHECKLIST-FILL-01（2026-10-24）  
用途：發布前（或 Build Result 掛接前）逐項勾選並填入**狀態語意**；禁止把未跑項寫成 PASS。

權威狀態集合見 [`PRODUCT-DEVELOPMENT.md`](./PRODUCT-DEVELOPMENT.md) §6.5／§8。本清單要求每項標註其一：

| 狀態 | 語意（本清單） |
|------|----------------|
| **PASS** | 該檢查**已實際執行且通過**；有可引用證據（報告路徑／產物／簽章輸出） |
| **FAIL** | 已執行但失敗（建置／掃描／驗證錯誤）；不得略過後宣稱可發 |
| **NOT RUN** | **未執行**（缺憑證、未提權、決策未批、非目標 OS、缺 runner 等）；exit 可為 0，**禁止**改寫為 PASS |
| **PARTIAL** | 契約／腳本／文件／stub 到位，但真跑或關鍵子項未完成（常見於 v0.1 候選） |

**禁止**：腳本存在、文件勾選、CI 綠、stub 產出 → 自動等於該項 **PASS**。無憑證之簽章維持 **NOT RUN**（見 Rel-Candidate 決策）。  
**本文件不自動放行發布**（PD-CHECKLIST-FILL-01 不做自動放行）。

---

## 如何使用

1. 複製下表「狀態」欄，或在本檔直接改勾選與狀態字串。
2. 每列填：`[x]`／`[ ]`、狀態=`PASS|FAIL|NOT RUN|PARTIAL`、證據路徑（報告／產物）。
3. 將結果掛入 Build Result／releases 列；整體門檻由 owner／PM 依未決決策決定，**本文件不自動放行**。

---

## 檢查項

### 1. MSI（Windows 安裝包）

- [x] **MSI 建置／產物** — WiX → MSI 可重跑產出；路徑／sha256 可掛 PackSpec／Build Result  
  - 狀態：`PASS`（PASS｜FAIL｜NOT RUN｜PARTIAL）  
  - 證據：`packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi`；`packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi.sha256`；`reports/build-0.1.0-br-refresh.md`（MSI-ARTIFACT PASS；sha256=`facbfc8112991929b9142514cbea43903d270c4d04cc86715d805eec690ff5fb`）  
  - 參考：`packaging/windows/wix/`、桌機 `npm run tauri build` → WiX  
  - 語意提示：僅「有 WiX 腳本」→ **NOT RUN**／**PARTIAL**；真產出且對帳通過 → **PASS**；建置失敗 → **FAIL**

### 2. Elev（elevated VERIFY-INSTALL）

- [x] **Elevated 靜默裝／卸** — 提升權限下 VERIFY-INSTALL（`/qn` 裝卸對帳）  
  - 狀態：`PASS`（PASS｜FAIL｜NOT RUN｜PARTIAL）  
  - 證據：`packaging/windows/wix/out/verify-install-result.json`（`overall=PASS`，`live_executed=true`，`elevated_process=true`）；`reports/build-0.1.0-br-refresh.md`（ELEV-VERIFY PASS）  
  - 參考：[`VERIFY-ELEVATED-AND-LIVE-SMOKE.md`](./VERIFY-ELEVATED-AND-LIVE-SMOKE.md)  
  - 語意提示：未提權／未核准／未真跑 → **NOT RUN**（整體常 **PARTIAL**）；真跑通過 → **PASS**；對帳失敗 → **FAIL**

### 3. Sec（依存／秘密掃描）

- [x] **安全掃描** — 依存 CVE／秘密掃描已跑；高危已分流或明確阻擋  
  - 狀態：`PARTIAL`（PASS｜FAIL｜NOT RUN｜PARTIAL）
  - 證據：`reports/sec-scan-20261024T120542.md`（overall=PARTIAL；secret-scan=PASS；cve-scan=PARTIAL；untriagedHigh=0）；`reports/sec-triage-v0.1.md`（高危分流／剩餘風險；未分流高危不得暗示整體安全 PASS）；`reports/build-0.1.0-br-refresh.md`／`reports/build-0.1.0-with-sec.md`
  - 參考：硬化批 `PD-SEC-SCAN-01`；分流說明 `PD-SEC-TRIAGE-01` → [`reports/sec-triage-v0.1.md`](../reports/sec-triage-v0.1.md)
  - 語意提示：未跑掃描 → **NOT RUN**；工具失敗或高危未分流 → **FAIL**／**PARTIAL**；已跑且政策通過 → **PASS**。**禁止**因缺掃而偽造成整體 PASS。
  - 誠實註記：SEC-GATE 無未分流高危，但 cve 腿仍 PARTIAL（1 medium）→ 本列 **PARTIAL**，不得偽造成 PASS。

### 4. SBOM

- [x] **SBOM 產出** — CycloneDX 或 SPDX 檔可重跑；可被 sec／Build Result 引用  
  - 狀態：`PASS`（PASS｜FAIL｜NOT RUN｜PARTIAL）  
  - 證據：`reports/sbom-20261024T131100.cdx.json`；`reports/sbom-20261024T131100.spdx.json`；`reports/sbom-20261024T131100.md`；掛接：`reports/build-0.1.0-with-sbom.md`（SBOM-GATE PASS）  
  - 參考：Rel-Candidate `PD-SBOM-01` 產物路徑  
  - 語意提示：產出失敗明示 → **FAIL**；未跑 → **NOT RUN**；檔在但未掛報告 → **PARTIAL**；產出＋掛接成功 → **PASS**

### 5. 簽章（Authenticode／簽章 stub／live）

- [x] **程式碼簽章** — Windows Authenticode（stub 或 live 流程）  
  - 狀態：`NOT RUN`（PASS｜FAIL｜NOT RUN｜PARTIAL｜BLOCKED）  
  - 證據：`packaging/windows/out/sign-authenticode-result.json`（無憑證時 `certConfigured=false`，`status=NOT RUN`，`signed=false`）；`reports/build-0.1.0-br-refresh.md`（SIGNING NOT RUN）  
  - 參考：`packaging/windows/sign_live.py`（`PD-REMAIN-SIGN-LIVE-01` 真簽＋verify）；stub：`sign_authenticode.py`；無憑證時**必須** **NOT RUN**（決策：不強制買證、禁偽造 PASS）  
  - 語意提示：無憑證／未跑 → **NOT RUN**；live 成功（sign+verify+timestamp）→ **PASS**；簽／驗失敗 → **FAIL**；dry-cert 於 live → **BLOCKED**

### 6. CHANGELOG

- [x] **CHANGELOG／SemVer** — 倉庫 `CHANGELOG.md`（或等價）記載 v0.1.x 摘要，可與 Build Result／releases 對照  
  - 狀態：`PASS`（PASS｜FAIL｜NOT RUN｜PARTIAL）  
  - 證據：`CHANGELOG.md`（`## [0.1.0] — 2026-10-24`；SemVer／MSI／sha256／Build Result 路徑）；對照 `reports/build-0.1.0-br-refresh.md`  
  - 參考：根目錄 [`CHANGELOG.md`](../CHANGELOG.md)；工項 `PD-CHANGELOG-01`  
  - 語意提示：缺版本段或無法對照 → **FAIL**／**PARTIAL**；未檢查 → **NOT RUN**；摘要與產物可對照 → **PASS**  
  - 誠實註記：CHANGELOG 內 elev 欄仍寫 NOT RUN（較舊候選敘述）；產物／SemVer／sha256 可對照 → 本列 **PASS**（不以 CHANGELOG 舊 elev 敘述偽造 elev 列）。

---

## 彙總（發布前填）

| # | 項 | 狀態 | 證據（路徑） |
|---|----|------|--------------|
| 1 | MSI | PASS | packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi；reports/build-0.1.0-br-refresh.md |
| 2 | Elev | PASS | packaging/windows/wix/out/verify-install-result.json；reports/build-0.1.0-br-refresh.md |
| 3 | Sec | PARTIAL | reports/sec-scan-20261024T120542.md；reports/sec-triage-v0.1.md；reports/build-0.1.0-with-sec.md |
| 4 | SBOM | PASS | reports/sbom-20261024T131100.cdx.json；reports/sbom-20261024T131100.spdx.json；reports/build-0.1.0-with-sbom.md |
| 5 | 簽章 | NOT RUN | packaging/windows/out/sign-authenticode-result.json；reports/build-0.1.0-br-refresh.md |
| 6 | CHANGELOG | PASS | CHANGELOG.md；reports/build-0.1.0-br-refresh.md |

**彙總備註**（選填）：六項皆已填狀態＋可引用證據；簽章無憑證維持 **NOT RUN**；Sec 誠實 **PARTIAL**。整體仍為 Rel-Candidate／**不自動放行** — 由 owner 決定是否可 tag。任一關鍵項 **FAIL** 或未分流高危 → 不得暗示已可正式對外發佈。

| 欄位 | 值 |
|------|-----|
| 填寫者／日期 | PD-CHECKLIST-FILL-01 / 2026-10-24 |
| 對應 Build Result | `reports/build-0.1.0-br-refresh.md`（另見 `reports/build-0.1.0-with-sbom.md`、`reports/build-0.1.0-with-sec.md`） |
| 版本標的 | v0.1.0 |

---

## 交叉連結

| 文件 | 角色 |
|------|------|
| [`PRODUCT-DEVELOPMENT.md`](./PRODUCT-DEVELOPMENT.md) §6.5／§8 | NOT RUN／Build Result 權威語意 |
| [`VERIFY-ELEVATED-AND-LIVE-SMOKE.md`](./VERIFY-ELEVATED-AND-LIVE-SMOKE.md) | Elev／Live 操作與風險 |
| [`ROLLBACK-v0.1.md`](./ROLLBACK-v0.1.md) | v0.1 靜默卸載／失敗復原／風險；未真跑＝NOT RUN（PD-ROLLBACK-DOC-01） |
| [`DESKTOP-APP-USAGE.md`](./DESKTOP-APP-USAGE.md) | 桌機使用索引 |
| [`apps/sgenaxis-desktop/README.md`](../apps/sgenaxis-desktop/README.md) | 桌機 README（包裝／NOT RUN） |
| [`CHANGELOG.md`](../CHANGELOG.md) | v0.1 變更摘要 |
| [`CI-OS-MATRIX.md`](./CI-OS-MATRIX.md) | OS 矩陣占位（M4；非本清單必過） |

---

## 驗收對照（BDD-PD-REL-CHECKLIST-01／BDD-PD-CHECKLIST-FILL-01）

| Given／Then | 本文件 |
|-------------|--------|
| 列出發布前檢查項 MSI／elev／sec／SBOM／簽章／CHANGELOG | §檢查項 1–6 |
| 每項對應狀態語意 PASS｜FAIL｜NOT RUN｜PARTIAL | 文首狀態表＋每項「狀態」欄＋彙總表 |
| 六項皆有非空白狀態＋可引用證據路徑 | §彙總表（PD-CHECKLIST-FILL-01） |
| 缺證不得寫 PASS；SBOM 缺產物 → NOT RUN／PARTIAL | 本填寫依現有 reports／產物；SBOM 產物已就緒故 PASS |
| 可勾選 | Markdown `- [x]`／`- [ ]` 核取方塊 |
| 不自動放行發布 | 文首／彙總備註明示 |
