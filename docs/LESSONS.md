# 失敗經驗（LESSONS）

> 卡關、退回、流程失誤的根因與防範。新紀錄加在最上面。格式：日期、卡片／PR、發生什麼、根因、防範。

## 2026-11-25：推送後馬上加 `spec-change` 標籤，`guard` 仍判定缺標籤（PR #119）

- **卡片／PR**：PD-BOARD-GAPS-RELEASE-01，roy791202/AIAD#119。
- **發生什麼**：強制推送 rebase 後的 head `20358ca1`，接著馬上執行 `gh pr edit 119 --add-label spec-change`。
  這個 head 的 `guard` 結果是 FAILURE，錯誤是「修改了 BDD 情境…需要核准者加上 spec-change 標籤」，但 PR 上明明已經有這個標籤。
  有兩輪 `guard`：失敗的那一輪 log 裡 `PR_LABELS` 是空的；另一輪是 CANCELLED。重跑被取消的那一輪（run 45565769820）後，`PR_LABELS: spec-change`，結果通過。
- **根因**：
  1. `.github/workflows/ai-dev-guard.yml` 從事件內容取 `PR_LABELS`，也就是事件發生當下的標籤，不是 PR 現在的標籤。
     推送觸發的 `synchronize` 事件發生時還沒有標籤。
  2. 同一個 workflow 設了 `concurrency: cancel-in-progress: true`。PR 時間軸：強制推送 07:08:02Z，加標籤 07:08:04Z；
     但 run 45565769820（帶標籤）建立於 07:08:06Z，比 run 45565772015（無標籤）的 07:08:07Z 早。
     **推測**：帶標籤的 `labeled` 那一輪先建立，後被沒有標籤的 `synchronize` 那一輪取消，所以留下的是沒有標籤的失敗結果。
     兩輪在 API 上的事件都只顯示 `pull_request`，無法直接證明哪一輪是哪個事件。
  3. 依 GitHub 文件，重跑 run 會沿用原本的事件內容，所以重跑失敗的那一輪仍然讀不到標籤。
- **防範**：
  1. 需要 `spec-change`／`guard-change` 標籤的 PR，**先加標籤，再推送**。這樣之後每一輪都帶得到標籤。
  2. 標籤已在但 `guard` 說缺標籤時，先看失敗那一輪 log 的 `PR_LABELS`：
     - 是空的：重跑由 `labeled` 事件觸發、被取消的那一輪（`gh run rerun <id>`），不要重跑失敗的那一輪。
     - 找不到這一輪：移除標籤再加回去，觸發新的 `labeled` 事件。
  3. 合併前，以**最新一輪**有讀到標籤的 `guard` 為準；舊的 FAILURE 紀錄要確認唯一錯誤就是缺標籤。
  4. 建議（待 Owner 決定）：`guard` 改用 `gh pr view --json labels` 讀取 PR 現在的標籤，不從事件內容取。

## 2026-11-23：`gh pr merge --auto` 在必要檢查未設定時立即合併（PR #114）

- **卡片／PR**：PD-AIDEV-PRODUCT-TESTS-01，roy791202/AIAD#114。
- **發生什麼**：承諾「等 `guard` 轉綠再合併」，實際執行 `gh pr merge --squash --auto --match-head-commit <sha>`。
  四項檢查（`guard`、`rust-windows`、`tests`、`lint + test subset`）都還在跑，PR 就被立即合併（合併 commit `6a4af6e4`）。事後確認四項檢查最終都是 SUCCESS，沒有造成損害。
- **根因**：`--auto` 只會等「分支保護設為必要」的檢查；`main` 沒有任何分支保護（沒有必要檢查），
  GitHub 視為可立即合併。執行前沒有確認分支保護設定。
- **防範**：
  1. 合併前先確認該 head sha 的**所有**檢查都是 SUCCESS（`gh pr view <n> --json statusCheckRollup`），再用
     `gh pr merge --squash --match-head-commit <sha>` 合併，不用 `--auto` 代替等待。
  2. 只有確認分支保護已把要等的檢查設成必要時，才可以用 `--auto`。
  3. 建議 Owner 在 `main` 分支保護把 `guard`、`lint + test subset`、`tests`、`rust-windows` 設為必要檢查（待決定）。
