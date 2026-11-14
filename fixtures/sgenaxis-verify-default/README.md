# SGenAxis 驗證預設專案

假資料看板，供**已安裝版**／`tauri dev` 功能對照。

**假資料 ≠ 產品證據 ≠ 正式 PASS。**

## 一鍵植入並開啟

```powershell
cd D:\AIAD
python tools/verify/seed_default_data.py --launch
```

1. App 啟動後狀態列應顯示已綁定 `fixtures\sgenaxis-verify-default`
2. 工項看板按 **載入本機看板** → 應見 `VF-*` 樣本工項（灰／藍／黃／紅／綠）
3. 可再驗：側欄、新增專案、Agent DryRun、UI 設計工具

壓力硬閘另跑：

```powershell
python tools/harness/portable/open_stress_gate.py --stress 500
```
