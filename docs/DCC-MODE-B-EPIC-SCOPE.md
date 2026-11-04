# DCC 宿主另案範圍一頁（Mode B · attach／env）

工項：`PD-REMAIN-DCC-EPIC-01` · BDD-PD-REMAIN-DCC-EPIC-01  
依賴：[`PRODUCT-DEVELOPMENT.md`](./PRODUCT-DEVELOPMENT.md) §6.5（DCC＝**非 M4 包裝**／**另案**）

**本頁＝開題／範圍契約，不是實作、不是接通證明。**  
**Status：** 另案 · **非首版（v0.1）** · DCC **未接通** · 驗證列＝**NOT RUN**（本卡無插件碼）。

---

## 1. 斷言（硬 · 禁止偽接通）

| 斷言 | 必須成立 |
|------|----------|
| **另案** | DCC 宿主整合**不**併入 M3／M4／Rel-Freeze「已決棧」或「已發行」宣稱（§6.5／§9） |
| **非首版** | v0.1 候選／Go-with-PARTIAL **不含** Maya／Houdini／其他 DCC 插件交付 |
| **未接通** | 本倉**無**已驗過的 DCC load／menu／shelf／env 接通；禁止文案暗示「已支援 DCC」或「DCC wired」 |
| **本卡不實作** | **禁止**新增／修改 Maya／Houdini／Blender 等插件程式、module、`.mod`、shelf 腳本 |
| **狀態語意** | 任何 DCC VERIFY／宿主 smoke 未真跑 → **NOT RUN**（或決策 **BLOCKED**）；不可偽 **PASS** |

---

## 2. 架構定位：Mode B（Plugin in host）

SGenAxis 桌機產品＝**獨立殼**（Tauri／本機看板）。DCC 另案若開做，採 **Mode B**：插件掛進既有宿主，**Core 不依賴宿主 API**。

```
UI (Qt/PySide in host) → App/Use-Case → ★ CORE（純／可測）★
                              ▲ via Ports
        DccHostPort adapter ──┘   OS ports（fs／env／proc）
              → DCC host → OS
```

- **兩條邊界分開：** `DccHostPort`（宿主 API）≠ OS／檔案／環境 ports。  
- **UI 不直呼** cmds／OpenMaya／hou；只經 Use-Case → Port。  
- **執行緒：** 宿主場景讀寫＝**宿主主執行緒**；長 IO／網路＝worker，再 marshal 回主執行緒。

本頁只定 **attach／env** 契約列；其餘 Domain／UI 細節留待未來 epic 開工後再拆卡。

---

## 3. Integration Schema（本頁範圍＝attach／env）

### 3.1 Host／DCC targets（占位 · 未選定＝未開工）

| 列 | 內容 | 本卡狀態 |
|----|------|----------|
| 目標宿主 | 例：Maya／Houdini（版本矩陣未拍板） | **未決** · 另案 |
| Python／Qt | 隨宿主版本（PySide2／6 等） | **未決** |
| 首版是否納入 | **否** | 固定 |

### 3.2 Attach surface（掛載面 · 未來實作才填路徑）

| 列 | Mode B 預期 | 本卡 |
|----|-------------|------|
| Module／plugin 檔 | 宿主可發現的 module／plug-in 入口 | **未實作** |
| Load／unload | 可重入載入、可乾淨卸載 | **未實作** |
| Startup hooks | 啟動時註冊（若需要） | **未實作** |
| Menu／shelf | 選單或 shelf 命令入口 | **未實作** |
| Command entry | 對應 Use-Case 的命令名 | **未實作** |

### 3.3 Environment contract（環境契約 · 未來實作才綁值）

| 列 | 常見宿主變數（例） | 本卡 |
|----|-------------------|------|
| Module path | `MAYA_MODULE_PATH` 等 | **未綁定** |
| Script path | `MAYA_SCRIPT_PATH` 等 | **未綁定** |
| Python path | `PYTHONPATH`（慎用、可追溯） | **未綁定** |
| PATH | 僅在必要且可卸載時追加 | **未綁定** |
| User-pref | **禁止污染**使用者偏好；註冊須可冪等還原 | **契約要求**（未來實作必須遵守） |

### 3.4 本頁明確不做（屬未來卡／禁止本卡擴 scope）

- 任何 DCC 插件原始碼、編譯、打包進 MSI  
- VERIFY-DCC 真機矩陣、宿主版本表綠燈  
- 把桌機 Agent／看板「看起來像 DCC」寫成「已整合 DCC」

---

## 4. BDD 對照（可驗收 · 文件層）

**Feature：** DCC 另案開題（Mode B scope）  
**Background：** Rel-Freeze／M4 已將 DCC 標為另案；本卡僅 docs。

| Scenario | Given / When / Then |
|----------|---------------------|
| 範圍一頁存在 | Given 倉庫有本文件；When 開啟本頁；Then 可見 Mode B＋attach／env 列與「未接通」斷言 |
| 非首版 | Given §6.5／§9；When 讀本頁 §1；Then 明示 v0.1 **不含** DCC 交付 |
| 無插件碼 | Given 本卡允許範圍＝`docs`；When 檢視本卡 diff；Then **無** Maya／Houdini／插件實作檔 |
| 禁止偽接通 | Given 對外或內部狀態表；When 描述 DCC；Then 必須用 **另案／未接通／NOT RUN**，不得寫成已支援或 PASS |

**Tag：** `BDD-PD-REMAIN-DCC-EPIC-01` · `integration:attach-env` · `status:NOT_RUN`

---

## 5. 後續（非本卡）

若 owner 核准開 DCC epic：另建決策紅燈（宿主／版本／是否進里程碑）→ 再灰燈拆 `PD-DCC-*`（Port／adapter／VERIFY-DCC）。**在此之前本頁維持「開題 only」。**

---

## 變更紀錄

| 日期 | 說明 |
|------|------|
| 2026-10-24 | PD-REMAIN-DCC-EPIC-01：初版一頁；Mode B attach／env；斷言未接通／非首版／不實作插件 |
