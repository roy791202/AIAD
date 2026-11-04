# SGenAxis Portable Harness（免安裝）

不經 **MSI／msiexec**，在本機開桌機 UI + **Mock Tauri IPC**，供 TDD Agent／人工：

1. 對照 [`git_workbench_interactive.html`](../../../git_workbench_interactive.html) 逐項驗證  
2. 用**假資訊**做壓力（大量工項／事件），確認不白屏、不未捕捉崩死  

**假資料 ≠ 產品證據 ≠ 正式發布 PASS。**

## 開通測試硬閘（必跑）

Owner：**必須開啟程式＋壓力測試通過才能 PASS**。

```powershell
cd D:\AIAD
python tools/harness/portable/open_stress_gate.py --stress 500
python -m pytest tests/test_pd_open_launch_01.py tests/test_pd_open_func_01.py tests/test_pd_open_stress_gate_01.py -q
```

無 `reports/dispatch-pd/PD-OPEN-*-evidence.json` 或 `ok!=true` → pytest FAIL → **禁止 TDD_PASS／綠燈**。假資料 ≠ 產品 PASS。

工項：`PRODUCT-OPEN-STRESS-20261024` · `PD-OPEN-LAUNCH-01` · `PD-OPEN-FUNC-01` · `PD-OPEN-STRESS-GATE-01`。

## 一鍵啟動

```powershell
cd D:\AIAD
python tools/harness/portable/serve.py
# 或
.\tools\harness\portable\run.ps1
# 壓力 500 假工項：
.\tools\harness\portable\run.ps1 -Stress 500
```

| URL | 內容 |
|-----|------|
| http://127.0.0.1:28790/ | UI + mock bridge（黃橫幅） |
| http://127.0.0.1:28790/workbench/ | Workbench IA 對照 |
| http://127.0.0.1:28790/harness/checklist-workbench.md | 逐項清單 |

埠 **28790**（避開看板 28789、禁用 8788）。

## TDD Agent 用法

1. 啟動 `serve.py`（可加 `--stress 500`）  
2. 開 UI + Workbench 並排  
3. 依 `checklist-workbench.md` 勾選；結果只許 PASS｜FAIL｜NOT RUN｜PARTIAL  
4. 另跑：`python -m pytest tests/test_pd_harness_portable_01.py tests/test_pd_harness_mock_01.py tests/test_pd_harness_checklist_01.py tests/test_pd_harness_stress_01.py -q`  
5. 產出報告引用 checklist／pytest；**禁止**把 harness 假投影寫進正式 Build Result 為產品 PASS  

## 可選：真 Tauri（仍免 MSI）

```powershell
cd D:\AIAD\apps\sgenaxis-desktop
npm run dev
```

需本機 Rust／WebView2；與 mock portable **分開**記錄。

## 檔案

| 路徑 | 角色 |
|------|------|
| `serve.py` | HTTP 注入 mock、掛 UI／Workbench |
| `run.ps1` | 包裝啟動 |
| `mock_tauri_bridge.js` | 假 `invoke` |
| `checklist-workbench.md` | 對照清單 |
| `stress_gen.py` | 產生假 board JSON |
| `open_stress_gate.py` | 開程＋壓力硬閘（寫 evidence；未過不得 PASS） |

## 工項

`PRODUCT-HARNESS-PORTABLE-20261024` · `PD-HARNESS-PORTABLE-01` · `MOCK` · `CHECKLIST` · `STRESS`
