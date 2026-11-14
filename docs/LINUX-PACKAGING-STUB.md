# PD-M4-LINUX-STUB-01 — Linux packaging stub

BDD-PD-M4-LINUX-STUB-01：提供 linux 包裝入口（**AppImage** stub；未選 deb）；**非 Linux 主機明確 NOT RUN**；**不得偽造 PASS**。不做發行版商店上架。

## 入口

| 檔案 | 用途 |
|------|------|
| `packaging/linux/build_linux_stub.py` | 可重跑主入口（Windows／macOS／Linux 皆可呼叫） |
| `packaging/linux/build-linux-stub.py` | 連字號別名（轉呼叫上者） |
| `packaging/linux/build-appimage-stub.sh` | Linux shell 包裝，轉呼叫主入口 |
| `packaging/linux/contract_selftest.py` | 契約斷言（NOT RUN ≠ PASS；Linux→PARTIAL） |
| `packaging/linux/README.md` | 目錄說明 |

## 本機指令

```powershell
# 非 Linux（例如本機 Windows）→ status=NOT RUN，exit 0
python packaging/linux/build_linux_stub.py

# 契約自測
python packaging/linux/contract_selftest.py
```

產物：`packaging/linux/out/linux-stub-result.json`。

## PackSpec 欄位（與 PD-M4-PACK-SPEC-01 對齊）

`os`／`arch`／`path`／`sha256`／`status`，其中 `status∈PASS｜FAIL｜BLOCKED｜NOT RUN｜PARTIAL`。

- 非 Linux：`status=NOT RUN`，`path`／`sha256` 為 null。
- Linux stub 寫入：`status=PARTIAL`（占位 AppImage，非商店／非完整發行 PASS）。

## 與 Windows WiX 邊界

Windows 正式安裝包見 `packaging/windows/wix`（MSI）。本 stub **不**宣稱三平台已發行；權威語意見 `docs/PRODUCT-DEVELOPMENT.md` M4 節。

## 依賴

- `PD-M4-PACK-SPEC-01`（平行可）— 產物狀態集合與欄位語意
