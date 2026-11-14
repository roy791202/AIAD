# SSH／遠端／容器 — 另案範圍一頁

**Card:** `PD-REMAIN-SSH-EPIC-01` · **BDD:** `BDD-PD-REMAIN-SSH-EPIC-01`  
**Authority parent:** [`PRODUCT-DEVELOPMENT.md`](./PRODUCT-DEVELOPMENT.md) §6.5（非 M4 包裝）  
**Status of this page:** **scope / open-topic only** — **not** an implementation plan that implies wiring exists.

---

## 1. Verdict（硬）

| Claim | Truth |
|-------|--------|
| SSH／遠端宿主／容器執行是否已接通產品？ | **否** — **未接通**；現況＝**另案未實作** |
| 本頁是否交付 SSH 客戶端或連線程式？ | **否** — **禁止**本卡／本頁附帶客戶端程式碼 |
| 可否對外寫「已支援遠端／SSH／容器跑 FLOW」？ | **否** — **禁止暗示遠端已接通** |
| 與 M4／v0.1 發行的關係 | **獨立另案**；不併入「跨平台安裝包已完成」或 Rel-Freeze 已決棧 |

**一句話：** 本文件只框定未來 SSH／遠端／容器 epic 的**範圍邊界**；產品目前**沒有**遠端連線能力。

---

## 2. In scope（未來另案可討論／建卡的主題）

僅列主題邊界，**不**等於已開工或已接通：

1. **SSH 遠端宿主** — 透過 SSH 在遠端機器執行／觀測工作（認證、跳板、連線生命週期）屬另案。
2. **容器遠端／隔離執行** — 以容器作為執行環境（映像、掛載、網路隔離）屬另案。
3. **與現有本機棧的邊界** — 產品今日權威路徑仍為本機：UI → Tauri Command → DispatchHost → Core／FLOW／EXEC／WORK／EVID → Ports（見 PRODUCT-DEVELOPMENT）；遠端若未來引入，須另定 Port／adapter，**不得**暗示現有 adapter 已接遠端。
4. **文件／決策／驗收語意** — 任何遠端卡必須可標 `NOT RUN`／`BLOCKED`／未接通，禁止用「文件存在」偽綠。

---

## 3. Out of scope（本卡硬禁）

| 不做 | 理由 |
|------|------|
| SSH／SFTP／遠端 shell **客戶端實作** | 卡面「不做」；允許範圍僅 `docs` |
| 容器 runtime 整合（Docker／Podman／k8s 等）程式 | 屬另案實作卡，非本開題頁 |
| UI／Command／DispatchHost 遠端連線按鈕或設定面板 | 會暗示已接通 |
| 宣稱 Live／E2E／冒煙「已在遠端跑過」 | 無證據；須 **NOT RUN** |
| 把本頁寫進「已發行能力」或商店文案 | 違反 §6.5／Post-Freeze 另案語意 |

---

## 4. 斷言（可核對 · BDD-PD-REMAIN-SSH-EPIC-01）

以下語句為本卡**必須成立**的文件斷言（TDD 可 grep；實作代理不自改綠）：

1. 本頁明示產品 SSH／遠端／容器為 **另案**，且現況 **未接通**。
2. 本頁明示 **禁止暗示遠端已接通**（含「已支援遠端執行」「SSH 已可用」等僞完整宣稱）。
3. 本頁明示本卡 **不實作連線**、**無客戶端程式碼**交付。
4. 本頁交叉引用 §6.5：SSH／容器 **不**併入 M4「跨平台安裝包已完成」。
5. Rel-Freeze／v0.1 **Go-with-PARTIAL** ≠ SSH／遠端已交付。

**禁止出現於本頁的僞綠措辭（反例）：**「遠端已接通」「SSH client ready」「container execution wired」「production remote host live」。

---

## 5. 建議後續（僅開題，不派實作）

Owner／PM 若要真做遠端，另建卡並先過決策紅燈，例如：

- 遠端 Port 契約（與本機 EXEC／WORK 邊界）
- 認證與祕密存放（禁止寫死金鑰進 repo）
- 驗收：真機／真容器矩陣列與 `NOT RUN` 規則
- 獨立 epic ID（勿掛在 M4 包裝完成之下）

在決策與實作卡成立前，本頁維持 **scope-only**；狀態語意等同能力 **未交付**。

---

## 6. 相關路徑

| 路徑 | 角色 |
|------|------|
| `docs/PRODUCT-DEVELOPMENT.md` §6.5／§9 | 包裝邊界；另案權威 |
| `docs/RELEASE-NOTES-v0.1.md` §4 | SSH／遠端宿主＝**未做另案** |
| `reports/dispatch-pd/PD-REMAIN-SSH-EPIC-01.md` | 本卡派工證據 |

*End of one-pager · PD-REMAIN-SSH-EPIC-01*
