# Workbench 對照驗證清單（PD-HARNESS-CHECKLIST-01）

給 **TDD Agent／人工**：在 **免安裝 Portable Harness** 上逐項勾選。  
權威 IA：`git_workbench_interactive.html`（本機 `/workbench/`）。  
假資料／mock ≠ 產品證據；結果僅 `PASS`｜`FAIL`｜`NOT RUN`｜`PARTIAL`。

## 啟動

```powershell
cd D:\AIAD
python tools/harness/portable/serve.py
# 壓力：python tools/harness/portable/serve.py --stress 500
```

開：`http://127.0.0.1:28790/` 與並排 `/workbench/`。

| 環境 | 說明 |
|------|------|
| Portable mock | 本清單預設；`window.__SGENAXIS_HARNESS__` 存在 |
| Tauri dev | 可選；無 MSI，但需 Rust — 標 **NOT RUN** 若不跑 |

---

## A. 殼（對照 Workbench titlebar／toolbar／statusbar）

| # | 項 | When | Then | 結果 |
|---|----|------|------|------|
| A1 | 選單列可見 | 開啟 harness UI | 檔案／編輯／專案／模組／工項／視窗／說明 | ☐ |
| A2 | 工具列專案綁定 | 載入後 | 顯示假 `project_root` 或可讀未綁定 | ☐ |
| A3 | 狀態列 | 載入後 | 專案／Agent／訊息區存在 | ☐ |
| A4 | Harness 橫幅 | 載入後 | 可見 PORTABLE HARNESS；連到 Workbench | ☐ |

## B. 側欄主路徑（Workbench 順序）

| # | 項 | When | Then | 結果 |
|---|----|------|------|------|
| B1 | Agent 派工 | 點側欄 Agent | `panel-agent` 顯示；可 DryRun 假 start_run | ☐ |
| B2 | Tasks Status／看板 | 點看板／篩選 | `panel-board` 有假工項列；篩選不崩 | ☐ |
| B3 | 佈版 | 點佈版 | `panel-deploy`；未支援／空態可讀 | ☐ |
| B4 | 模組架構圖 | 點架構 | `panel-arch`；mock 投影或空態 | ☐ |
| B5 | UI 設計工具 | Workbench 有 | 桌機若缺視圖 → 本項 **NOT RUN／缺口**（屬 SHELL-FIDELITY） | ☐ |

## C. 次要面板（產品有、Workbench 選單有）

| # | 項 | When | Then | 結果 |
|---|----|------|------|------|
| C1 | Git 工作台 | 開 Git | 假 summary／diff；不直呼真 git | ☐ |
| C2 | 設定 | 開設定 | DryRun／路徑可讀；secrets 不出現 token | ☐ |
| C3 | Ports | 開 Ports | 假 ports 列表 | ☐ |
| C4 | Listen | 開 Listen | 空或假事件；標 harness | ☐ |

## D. 壓力（假資訊）

| # | 項 | When | Then | 結果 |
|---|----|------|------|------|
| D1 | stress=500 啟動 | `serve.py --stress 500` | 頁面載入無白屏；console 無未捕捉例外導致死頁 | ☐ |
| D2 | 切換面板 | 連續切 Agent／Board／Git／Arch | 不卡死；可回看板 | ☐ |
| D3 | 假 Run | Agent 啟動 DryRun | poll_chunks 有輸出；可取消 | ☐ |
| D4 | pytest stress | `pytest tests/test_pd_harness_stress_01.py` | 腳本 PASS（靜態／產生器）；≠ 產品效能 PASS | ☐ |

## 彙總

| 欄 | 值 |
|----|-----|
| 執行者 | |
| 日期 | |
| Portable mock | PASS／FAIL／PARTIAL |
| 壓力 | PASS／FAIL／NOT RUN／PARTIAL |
| 備註 | 假資料；不可寫入正式 BR／GA |
