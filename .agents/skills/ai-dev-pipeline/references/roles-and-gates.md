# 角色與關卡

## 角色
| 角色 | 模型 | 可做 | 不可做 |
|---|---|---|---|
| 高階模型（架構師／PM） | 高階 | 預製期全部產出；派工；處理 `SPEC_CONFLICT`／`REPLAN_REQUIRED`／`RESLICE_REQUIRED`；改 `.feature`（需記理由）；合併 PR；設 Done／藍燈 | 實作自己規劃的卡又自己驗收 |
| 開發代理 | 中低階 | 依 TDD 封包寫測試程式碼與產品程式；開 draft PR；標 `READY_FOR_TDD`；卡最多移到 In Review | 改 `.feature`、削弱斷言、skip；設 Done／藍燈／Released／`approvedBy`；驗收自己的卡 |
| 獨立 TDD 代理（驗證者） | 中低階 | 核對測試與 TDD 封包一致；親跑測試；依步驟實際操作介面並截圖錄影；寫驗收報告；回報 `TDD_PASS`／`TDD_FAIL` | 改產品程式；改測試斷言（測試基礎設施壞掉除外，需註明）；採信開發代理「已測過」的說法 |
| 獨立高階審查代理 | 高階 | 架構、分層、安全、品質審查；退回 | 改產品程式 |
| 使用者／Owner | — | 核准預製期產出；最終拍板；可代行高階模型的所有權限 | — |

- 開發、驗證、審查是**各自獨立啟動**的代理，不共用對話或工作階段。
- 代理的角色由啟動它的人設定（`.ai-hooks/config.json` 的 `role` 或環境變數 `AI_AGENT_ROLE`），AI 不可自己改。

## 什麼時候必須另起高階審查
預設只需獨立 TDD 代理；符合下列任一項時，高階審查為必要：
- 卡片動到 Port 介面、跨層、架構或新相依套件。
- 涉及安全（認證授權、外部輸入、機密、指令執行、路徑處理）。
- 同一張卡已被退回兩次以上。
- 發版（RC 或正式版）或 Hotfix。
其他情況可選用；不另起時，驗證報告要寫明「未經高階審查，理由：…」。

## PR 的生命週期
1. 開發代理在標 `READY_FOR_TDD` 時開 **draft PR**（分支 `feature/<task-id>-<slug>`，一個 Task 一個 PR），填 `prUrl`。
2. 驗證代理（必要時加審查代理）只讀 PR 與證據，不改程式；FAIL 就附證據退回。
3. 通過後由高階模型／Owner 把 PR 轉成 ready、合併（Squash and Merge）。

## Done（藍燈）條件 —— 三項同時成立
1. **有產出**：可指認的原始碼／報告／產物路徑；只改備註不算。
2. **獨立 `TDD_PASS`**：驗證者 ≠ 開發者，親跑通過；必要時審查也通過。
3. **PR 已合併**（沒有 PR 的純文件／決策卡免此項，需註明）。
只有高階模型或使用者能設 Done／藍燈；排程、腳本、輪詢一律不得批次改 Done。

## 結案 PR（設 Done）
- **只改 `docs/board.json`**；改到其他檔案，CI guard 直接失敗（不會退回一般 PR 的檢查）。
- 由 **Owner 加 `board-closeout` 標籤**，而且要在**推送前**加好：guard 讀的是觸發事件當下的標籤，推送後才加可能被取消的那一輪蓋掉（見 `docs/LESSONS.md` 2026-11-25 一則）。
- 一個結案 PR 可以結多張卡。guard 只檢查有變更的卡：必須是 Task 或 Story；base 為 In Review 且 `tdd` Green；結案後為 Done 並填 `completedAt`。
- 只可改 `status`、`light`、`updatedAt`、`completedAt`、`ci`、`approvedBy`、`lightReason`；`notes`、`history` 只能追加。不可新增或刪除卡片。
- 看板最上層只可改 `updatedAt`；`version`、`project`、`migration` 等其他最上層欄位不可新增、刪除或修改。

## 驗收紀錄必填
開發代理身分、驗證代理身分（審查代理身分）、BDD ID、執行的指令與結果、截圖錄影路徑、`TDD_PASS`／`TDD_FAIL`、NOT RUN 清單與原因。
