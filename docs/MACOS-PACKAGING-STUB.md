# PD-M4-MAC-STUB-01 — macOS packaging stub

BDD-PD-M4-MAC-STUB-01：提供 mac 包裝入口腳本／文件（**app-stub**）；**非 Darwin 主機明確 NOT RUN**；**不得偽造 PASS**。不做 notarize／stapling 必過。

## 入口

| 檔案 | 用途 |
|------|------|
| `packaging/macos/build_macos_stub.py` | 可重跑主入口（Windows／Linux／macOS 皆可呼叫） |
| `packaging/macos/build_macos.py` | manifest 別名（轉呼叫上者） |
| `packaging/macos/build-macos-stub.py` | 連字號別名 |
| `packaging/macos/build-macos.sh` | Darwin shell 包裝，轉呼叫主入口 |
| `packaging/macos/contract_selftest.py` | 契約斷言（NOT RUN ≠ PASS；Darwin→PARTIAL） |
| `packaging/macos/packaging.manifest.json` | stub 契約（與 PackSpec 欄位對齊） |
| `packaging/macos/README.md` | 目錄說明 |

## 本機指令

```powershell
# 非 Darwin（例如本機 Windows）→ status=NOT RUN，exit 0
python packaging/macos/build_macos_stub.py

# 契約自測
python packaging/macos/contract_selftest.py
```

產物：`packaging/macos/out/macos-pack-result.json`。

## PackSpec 欄位（與 PD-M4-PACK-SPEC-01 對齊）

`os`／`arch`／`path`／`sha256`／`status`，其中 `status∈PASS｜FAIL｜BLOCKED｜NOT RUN｜PARTIAL`。

- 非 Darwin：`status=NOT RUN`，`path`／`sha256` 為 null。
- Darwin stub 寫入：`status=PARTIAL`（占位 `.stub`，無 notarize／stapling PASS）。

## 與 Windows WiX 邊界

Windows 正式安裝包見 `packaging/windows/wix`（MSI）。本 stub **不**宣稱三平台已發行；權威語意見 `docs/PRODUCT-DEVELOPMENT.md` M4 節。

## 依賴

- `PD-M4-PACK-SPEC-01`（平行可）— 產物狀態集合與欄位語意
