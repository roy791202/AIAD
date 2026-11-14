# SGenAxis v0.1 佈版說明（Go-with-PARTIAL）

| Field | Value |
|-------|--------|
| Card | `PD-REL-NOTES-01` → **`PD-REL-NOTES-POST-01`**（佈版刷新） |
| BDD | `BDD-PD-REL-NOTES-01`；刷新 `BDD-PD-REL-NOTES-POST-01` |
| When | 2026-10-24（POST 刷新同日） |
| Posture | **Go-with-PARTIAL**（非正式商店／對外 GA） |
| Related | `PD-REL-GONOGO-01` → `reports/gonogo-v0.1.0-20261024T131414.md`；`PD-SPRINT-CLOSE-01` → `reports/sprint-close-v0.1.md`；Remain backlog 批次 `PD-REMAIN-*` |

---

## 1. 本佈版範圍（Scope）

本文件是 **v0.1 Rel-Freeze／Post-Freeze 佈版說明**，說明目前內部候選佈版**做到哪裡、沒做到哪裡**。

**In scope（本佈版）：**

- Windows MSI 候選產物與 Rel-Freeze 證據鏈（checklist／Build Result／GoNoGo）。
- 看板 sprint 路徑 DEV → HARDEN → M4 → VERIFY → REL-CAND → FREEZE 的結案姿勢收斂。
- 誠實標註整體姿勢為 **Go-with-PARTIAL**（對齊 `PD-DEC-V01-GATE-01`）。
- **POST 刷新：** Remain backlog（`PD-REMAIN-*`）**已關**後的範圍對照（見 §1.1）；姿勢**仍**為 Go-with-PARTIAL。

**Out of scope（本文件不做）：**

- 行銷網站／對外商店上架文案。
- **禁止**宣稱已正式商店發布或對外 GA。
- 強制買證、真 git tag 放行、開 DCC／SSH 新 epic（未做另案；見 §4）。

### 1.1 佈版刷新範圍（PD-REL-NOTES-POST-01）

本刷新**只**補寫下列事實，**不**改變發布姿勢：

| Item | Reading |
|------|---------|
| Remain backlog | **已關**（`PD-REMAIN-*` 批次結案／範圍文件落地；≠ 正式發行 PASS） |
| 簽章（Authenticode） | **仍 NOT RUN**（未買證；禁偽 PASS） |
| git tag | **未 tag**（無正式 SemVer tag 放行） |
| 買證 | **未買證**（故 signing 維持 NOT RUN） |
| 發布姿勢 | **仍 Go-with-PARTIAL**（≠ 正式商店／對外 GA） |

**Forbidden / false:** 把「Remain 已關」寫成「v0.1 正式 GA／已 tag／已簽章放行」。  
**True:** Remain backlog closed as deferred-work closure; candidate posture remains **Go-with-PARTIAL**.

---

## 2. Go-with-PARTIAL（發布姿勢）

v0.1 的 Go/NoGo 結案 verdict 為 **Go-with-PARTIAL**，**不是**完整 **Go**，也**不是**正式對外發行 PASS。

| Source | Result |
|--------|--------|
| Go/NoGo（`PD-REL-GONOGO-01`） | **Verdict: Go-with-PARTIAL** |
| Gate（`PD-DEC-V01-GATE-01`） | BR PARTIAL + elev／sign soft → Go-with-PARTIAL；**never** NOT RUN → PASS |
| POST（Remain 已關後） | **仍** Go-with-PARTIAL；Remain 關閉**不**升級為正式 GA |

Go-with-PARTIAL ＝ 內部 Rel-Freeze 可收斂的候選姿勢；**≠** 正式商店／對外 GA。

---

## 3. 簽章 NOT RUN

| Leg | Status | Reading |
|-----|--------|---------|
| signing（Authenticode） | **NOT RUN** | 無購買／未掛正式憑證；**禁止**改寫為 PASS |
| POST 刷新後 | **仍 NOT RUN** | Remain 已關**不**等於已簽章；**未買證** |
| 其他腿（摘要） | 見 GoNoGo 報告 | msi／changelog 等可為 PASS；build_result／sec 可為 PARTIAL |

**誠實原則：** NOT RUN 腿維持 **NOT RUN**。本佈版說明**不**把簽章 stub 或文件存在偽造成已簽章放行。

---

## 4. 未做另案

| Item | Status |
|------|--------|
| DCC 宿主整合 | **未做另案**（範圍見 `docs/DCC-MODE-B-EPIC-SCOPE.md`；未接通） |
| SSH／遠端宿主 | **未做另案**（範圍見 `docs/SSH-REMOTE-CONTAINER-EPIC-SCOPE.md`；未接通） |
| 買證（Authenticode 憑證採購） | **未做另案**／**未買證**（故 signing = **NOT RUN**） |
| 正式 SemVer git tag | **未 tag**（tag apply gate 另議；本佈版未放行） |
| 正式商店上架／對外 GA | **未做**／另議 |
| 行銷網站 | **不做**（本卡硬範圍外） |

Remain backlog **已關**＝該批 deferred 工項／範圍文件結案；**≠** 上表「未做另案」自動變成已接通或已放行。

---

## 5. Anti-forge（BDD-PD-REL-NOTES-01／POST-01）

| Forbidden claim | Correct reading |
|-----------------|-----------------|
| 「已正式商店發布」／「已正式對外 GA」／「v0.1 GA 已上線」 | **禁止**。本文件＝佈版範圍說明，**不是**商店／對外 GA |
| Go-with-PARTIAL＝正式發行 PASS | **禁止**。Verdict 維持 **Go-with-PARTIAL**；signing 為 **NOT RUN** |
| Remain 已關＝正式 GA／已 tag／已簽章 | **禁止**。Remain 關閉後姿勢**仍** Go-with-PARTIAL；**未 tag**、**未買證**、signing **仍 NOT RUN** |
| 本文件＝行銷網站／商店上架完成 | **禁止**。行銷網站本卡不做 |

**Forbidden / false:** “v0.1 is formally released to the store / external GA.”  
**True:** Layout notes for an internal **Go-with-PARTIAL** candidate; Remain backlog **closed**; signing **still NOT RUN**; **未 tag**／**未買證**; DCC／SSH／商店 remain **未做另案**.

---

## 6. What this document is / is not

### Is

- Short layout／release-notes for v0.1 scope + **Go-with-PARTIAL**.
- POST refresh after Remain backlog **已關**: refresh scope only; posture unchanged.
- Explicit record that **signing = NOT RUN**（仍）, **未 tag**, **未買證**, and deferred host work is **未做另案**.

### Is not

- Formal store publication or external GA announcement.
- Marketing website copy.
- Auto-approval to buy certificates, apply git tag, or ship to stores.
- A claim that closing Remain upgrades the release to formal GA.
