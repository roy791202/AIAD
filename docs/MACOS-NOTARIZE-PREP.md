# PD-NOTARY-PREP-01 — macOS notarize／stapling 預留說明（不實跑）

**BDD:** `BDD-PD-NOTARY-PREP-01` — 文件說明 notarize 步驟與本機限制；**標明目前 NOT RUN**；**禁止暗示已完成 Apple 公證**。

| 欄位 | 值 |
|------|-----|
| 狀態（本卡／本機） | **NOT RUN** |
| 是否已完成 Apple notarization | **否**（未提交、未通過、未 staple） |
| 是否可宣稱發行級 macOS 簽章／公證 | **否** |

> **硬禁令：** 本文件、`packaging/macos` stub、任何 Build Result／看板 note **不得**把「文件存在」或「腳本存在」寫成 notarize／stapling **PASS**，亦不得暗示「已完成 Apple 公證」。

---

## 目的與邊界

| 做 | 不做 |
|----|------|
| 預留步驟清單、工具名、前置條件、本機限制 | 在本機或 CI **實跑** `notarytool`／`altool`／`stapler` |
| 標明狀態 **NOT RUN**（未執行 ≠ 失敗） | 購買／配置 Apple Developer 憑證作為本卡過關條件 |
| 指向既有 macOS packaging stub | 把 Darwin stub **PARTIAL** 升級成公證 **PASS** |
| 說明未來真機跑完後如何記狀態 | App Store／TestFlight／商店上架 |

相關 stub（**非**公證）：[`MACOS-PACKAGING-STUB.md`](./MACOS-PACKAGING-STUB.md)、[`packaging/macos/README.md`](../packaging/macos/README.md)。  
產物契約：`notarize`／`stapling` 欄位目前為 `false`；Darwin stub → `PARTIAL`（見 `packaging/macos/packaging.manifest.json`）。

---

## 目前狀態（權威）

| 檢查項 | 狀態 | 說明 |
|--------|------|------|
| Apple Developer ID Application／Installer 憑證 | **NOT RUN**／未在本卡驗證 | 本卡不查 keychain、不簽碼 |
| `codesign` 正式簽章 | **NOT RUN** | stub `.stub` 明示不可公證／出貨 |
| `xcrun notarytool submit`（或舊 `altool`） | **NOT RUN** | **未提交**任何 archive／pkg／dmg |
| Notary service 審核結果 | **NOT RUN** | 無 UUID／無 Accepted |
| `xcrun stapler staple` | **NOT RUN** | 無 staple 票據 |
| Gatekeeper／`spctl` 驗證 | **NOT RUN** | 未跑 |

**本機（常見 Windows 開發機）：** 無 Darwin、無 Xcode CLT、無 Apple notary 連線 → 上述列必須維持 **NOT RUN**；exit 0 或文件齊全 **≠ PASS**。

---

## 預留步驟（未來真機；本卡不執行）

僅供日後在 **macOS + 有效 Developer 帳密／API key** 上執行。下列命令為說明用；**本卡派工禁止實跑**。

### 0. 前置條件（缺一則仍為 NOT RUN／BLOCKED）

1. Darwin 主機 + Xcode Command Line Tools  
2. Apple Developer Program 會員  
3. Developer ID Application（app）與／或 Developer ID Installer（pkg）憑證已匯入 keychain  
4. App Store Connect API key（或 app-specific password）已設定給 `notarytool`  
5. 待公證產物為**真實** `.app`／`.pkg`／`.dmg`（**不是** `packaging/macos` 的 `.stub`）

### 1. 簽章（codesign）— 預留

```bash
# 範例（占位；勿在本卡環境執行）
codesign --deep --force --options runtime \
  --sign "Developer ID Application: <Team Name> (<TEAM_ID>)" \
  /path/to/YourApp.app
codesign --verify --verbose=2 /path/to/YourApp.app
```

### 2. 打包提交物 — 預留

常見：對 `.app` 打 zip，或使用已簽的 `.pkg`／`.dmg`。

```bash
ditto -c -k --keepParent YourApp.app YourApp.zip
```

### 3. 提交公證（notarytool）— 預留

```bash
xcrun notarytool submit YourApp.zip \
  --key <AuthKey_XXX.p8> --key-id <KEY_ID> --issuer <ISSUER_UUID> \
  --wait
# 成功時 notary 回報 status: Accepted —— 僅在真實 Accepted 後才可記 PASS
```

舊路徑 `xcrun altool --notarize-app` 已淘汰取向；新專案應以 `notarytool` 為準。

### 4. Stapling — 預留

```bash
xcrun stapler staple YourApp.app
# 或對 .pkg / .dmg
xcrun stapler validate YourApp.app
```

### 5. Gatekeeper 抽樣 — 預留

```bash
spctl --assess --type execute -vv YourApp.app
```

---

## 狀態語意（與 PackSpec／Build Result 對齊）

| 狀態 | 何時使用（公證列） |
|------|-------------------|
| **NOT RUN** | 未在具備憑證的 Darwin 上執行 submit／staple（**目前預設**） |
| **BLOCKED** | 決策禁止、缺憑證且已決定不買證、或環境明確不可跑 |
| **PARTIAL** | 僅有 stub／文件／契約（如 Darwin packaging stub）；**尚未** Accepted＋staple |
| **PASS** | 真實產物已 **Accepted** 且 **staple／驗證通過**（證據：notary UUID、stapler validate、spctl） |
| **FAIL** | 已跑但拒簽、逾時、staple 失敗 |

**偽綠禁令：** 「README 有 notarize 章節」「腳本會印 notarize: false」「曾在某台 Mac 手動試過但無證據」→ 皆 **不得** 記 **PASS**。

---

## 本機限制（PD-NOTARY-PREP-01 驗收語境）

- 允許範圍僅 **文件**＋`packaging/macos` README；**禁止**實跑公證。  
- 開發主機若為 Windows／Linux：整條公證鏈 **NOT RUN**。  
- 即使在 Darwin：本卡仍 **不** 執行 submit；狀態維持 **NOT RUN** 直至另案真機卡帶證據。  
- `packaging/macos/out/macos-pack-result.json` 的 `notarize: false`／`stapling: false` 表示**未公證**，不是「公證失敗」。

---

## 依賴與後續另案

- 上游 stub：`PD-M4-MAC-STUB-01`（app-stub；非公證）  
- 狀態集合：`PD-M4-PACK-SPEC-01`  
- 產品語意：`docs/PRODUCT-DEVELOPMENT.md`（M4：不做強制 notarize 硬閘）  
- **另案：** 真實 Developer ID 簽章、notary submit、stapler、Gatekeeper 矩陣、商店上架

---

## 變更紀錄

| 日期 | 說明 |
|------|------|
| 2026-10-24 | `PD-NOTARY-PREP-01`：初版預留說明；狀態 **NOT RUN**；未實跑 Apple 公證 |
