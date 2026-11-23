# 失敗經驗（LESSONS）

> 卡關、退回、流程失誤的根因與防範。新紀錄加在最上面。格式：日期、卡片／PR、發生什麼、根因、防範。

## 2026-11-23：`gh pr merge --auto` 在必要檢查未設定時立即合併（PR #114）

- **卡片／PR**：PD-AIDEV-PRODUCT-TESTS-01，roy791202/AIAD#114。
- **發生什麼**：承諾「等 `guard` 轉綠再合併」，實際執行 `gh pr merge --squash --auto --match-head-commit <sha>`。
  四項檢查（`guard`、`rust-windows`、`tests`、`lint + test subset`）都還在跑，PR 就被立即合併（合併 commit `6a4af6e4`）。事後確認四項檢查最終都是 SUCCESS，沒有造成損害。
- **根因**：`--auto` 只會等「分支保護設為必要」的檢查；`main` 沒有把 `guard`、`rust-windows` 設成必要檢查，
  GitHub 視為可立即合併。執行前沒有確認分支保護設定。
- **防範**：
  1. 合併前先確認該 head sha 的**所有**檢查都是 SUCCESS（`gh pr view <n> --json statusCheckRollup`），再用
     `gh pr merge --squash --match-head-commit <sha>` 合併，不用 `--auto` 代替等待。
  2. 只有確認分支保護已把要等的檢查設成必要時，才可以用 `--auto`。
  3. 建議 Owner 在 `main` 分支保護把 `guard`、`lint + test subset`、`tests`、`rust-windows` 設為必要檢查（待決定）。
