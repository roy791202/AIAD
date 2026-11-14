# SGenAxis v0.1 reports／dispatch 索引

工項：`PD-REPORTS-INDEX-01` · BDD-PD-REPORTS-INDEX-01  
依賴：`PD-BR-FINAL-01`（軟）

本文件是 **路徑與用途索引**，方便查找 v0.1 主要報告落點。  
**列出路徑 ≠ 該項已 PASS。** 未列於本索引的報告／檢查項 **不得** 被解讀為已通過；缺檔必須標明，禁止用索引「補齊」成偽 PASS。

權威狀態語意：[`PRODUCT-DEVELOPMENT.md`](./PRODUCT-DEVELOPMENT.md) §6.5／§8（PASS｜FAIL｜PARTIAL｜NOT RUN｜BLOCKED）。  
各報告檔內的 Status／Verdict 才是該次產物的狀態；本索引不覆寫、不聚合放行。

---

## 0. 範圍與非宣稱

| 本文件**做** | 本文件**不做／不宣稱** |
|--------------|------------------------|
| 列出主要 `build`／`sbom`／`gonogo`／`dispatch-pd` 路徑與用途 | 暗示「索引有列＝已 PASS」 |
| 對預期／慣例檔名標 **存在** 或 **缺檔** | 刪改歷史報告內容 |
| 指向如何解讀狀態欄位 | 自動放行發布／Go |
| 說明目錄慣例 | 把未列項當成已完成 |

**禁止**：本索引存在、CI 綠、或目錄有檔 → 自動等於未列檢查 **PASS**。

---

## 1. Build Result（`reports/build-*`）

**用途：** 單次建置／掛接產物的結構化 Build Result（摘要、產物、驗證腿、簽章／sec／sbom 掛接狀態）。由 `tools/board/build_result.py` 等產生；狀態以檔內 **Status** 為準。

| 路徑／模式 | 用途 | 本機（寫索引時） |
|------------|------|------------------|
| `reports/build-0.1.0-*.md` / `.json` | v0.1.0 Build Result 系列（含 br-refresh、with-sbom、with-sec、verify-hang 等變體） | **存在**（多份） |
| `reports/build-0.1.0-br-refresh.md` | BR 刷新／掛接後常用引用本 | **存在** |
| `reports/build-0.1.0-with-sbom.md` | 附 SBOM 掛接示範／結果 | **存在** |
| `reports/build-0.1.0.md`（無後綴 canonical） | 若流程期望單一 canonical 名 | **缺檔**（以帶後綴檔為準；缺檔≠PASS） |

解讀：開啟對應 `.md`／`.json` 看 **Status**；`NOT RUN`／`PARTIAL` 不得改寫為 PASS。

---

## 2. SBOM（`reports/sbom-*`）

**用途：** 軟體物料清單產物與摘要（CycloneDX／SPDX＋機器可讀 JSON）。掛接 Build Result 時引用；**SBOM 成功不得偽造** Build Result PASS（見各 sbom 報告 Gate 段）。

| 路徑／模式 | 用途 | 本機（寫索引時） |
|------------|------|------------------|
| `reports/sbom-*.md` | SBOM 人讀摘要 | **存在**（例 `sbom-20261024T131100.md`） |
| `reports/sbom-*.json` | SBOM 機器摘要（aiad.sbom.v1） | **存在** |
| `reports/sbom-*.cdx.json` | CycloneDX JSON | **存在** |
| `reports/sbom-*.spdx.json` | SPDX JSON | **存在** |
| `reports/sbom-v0.1.0.md`（固定版號名） | 若流程期望固定檔名 | **缺檔**（以時間戳檔為準） |

---

## 3. Go／NoGo（`reports/gonogo-*`）

**用途：** 發布門檻聚合（legs：build_result／msi／elev／sec／sbom／signing／changelog 等）。Verdict 可能為 **Go-with-PARTIAL**；**Anti-forge**：NOT RUN 腿不得改寫為 PASS。

| 路徑／模式 | 用途 | 本機（寫索引時） |
|------------|------|------------------|
| `reports/gonogo-v0.1.0-*.md` / `.json` | v0.1.0 Go/NoGo 報告（時間戳變體） | **存在**（多份；以最新時間戳為準） |
| `reports/gonogo-v0.1.0.md`（無時間戳） | 固定 canonical 名 | **缺檔**（用帶時間戳檔；缺檔≠PASS） |

交叉：檢查清單 [`RELEASE-CHECKLIST-v0.1.md`](./RELEASE-CHECKLIST-v0.1.md)；里程碑 [`../reports/milestone-validation-v0.1.md`](../reports/milestone-validation-v0.1.md)（若存在）。

| 相關路徑 | 用途 | 本機 |
|----------|------|------|
| `reports/milestone-validation-v0.1.md` | 里程碑驗證摘要（≠ 自動 Go） | **存在** |

---

## 4. Dispatch-PD（`reports/dispatch-pd/`）

**用途：** 看板工項 `PD-*` 的實作／TDD 分派證據。慣例：

| 路徑／模式 | 用途 |
|------------|------|
| `reports/dispatch-pd/<ID>.md` | 實作 Agent 交件報告（含 READY_FOR_GREEN／zone yellow 等） |
| `reports/dispatch-pd/<ID>-TDD-REVIEW.md` | 獨立 TDD Agent 審查；`TDD_PASS`／`TDD_FAIL` |
| `reports/dispatch-pd/_tdd-*.txt`／`_tdd_*.py` | TDD／看板輔助腳本與跑測紀錄（非業務 PASS 證明） |

**本卡自身：** `reports/dispatch-pd/PD-REPORTS-INDEX-01.md`（實作報告；§7.1 燈維持黃）。

| 檢查 | 本機（寫索引時） |
|------|------------------|
| 目錄 `reports/dispatch-pd/` | **存在** |
| 至少一份 `PD-*.md` 交件報告 | **存在** |
| 本索引宣稱「全部 PD-* 已 TDD_PASS／全綠」 | **禁止**（未列／未審＝未知，≠ PASS） |

讀單一卡報告即可；**禁止**把目錄有檔解讀成全板 PASS。

---

## 5. 其他常見 reports（非本卡必列，僅防誤讀）

下列若存在，狀態仍以**各檔內文**為準；本節不完整枚舉、**未列≠PASS**：

- `reports/sec-scan-*` — 依存／秘密掃描
- `reports/verify-hang-*` — VERIFY hang／逾時摘要
- `reports/live-cli-target-result.json` — live CLI 目標探測

---

## 6. 缺檔與反偽 PASS（Anti-PASS-forge）

1. 上表標 **缺檔** 的項目＝寫索引時找不到該路徑；**缺檔不得當成 PASS**，也不得省略後暗示已完成。
2. **不得暗示未列項已 PASS** — 索引外的檢查／OS／簽章／演練維持未知或見其來源報告的 NOT RUN／PARTIAL。
3. 本文件標題含「索引」≠ Build Result／Go／TDD 聚合 **PASS**。
4. 更新本索引時：只改本檔與本卡測試／dispatch 報告；**不得刪改歷史報告內容**（本卡不做）。

---

## 7. 如何引用

- 引用具體證據時寫**完整相對路徑**（含時間戳後綴），不要只寫「見 reports 索引」。
- Owner／PM 改綠前：依 §7.1 等獨立 TDD／決策；本索引僅導覽。
