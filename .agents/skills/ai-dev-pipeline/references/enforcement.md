# 強制機制（四層）

| 層 | 機制 | 擋什麼 | 繞過時 |
|---|---|---|---|
| 1 規則 | 本 skill 組、`AGENTS.md`、`CLAUDE.md` 等 | 讓 AI 知道流程 | 只靠自律，所以需要下面三層 |
| 2 AI Hooks | `.ai-hooks/ai-hook.ps1`（Claude Code、Cursor 等） | 危險指令、讀機密檔；board.json 不合規則（`validate-board.ps1`）；開發代理設 Done／藍燈／Released／`approvedBy`；改 `.feature`、hook、CI 設定；`--no-verify`、改 `core.hooksPath`；改了檔案卻沒更新卡片 | board 檢查本身出錯一律阻擋（fail closed） |
| 3 Git Hooks + CI | `.githooks`（pre-commit、commit-msg）、`.github/workflows/*` | 看板規則、Conventional Commits、新增 skip/only/`#[ignore]`、版本不同步、PR 沒對應 In Review＋TDD Green 的 Task、未經 spec-change 標籤改 `.feature`、發版沒改 CHANGELOG；跑測試 | 本機 `--no-verify` 可跳過 Git Hooks，但 CI 一定跑 |
| 4 分支保護 | GitHub 分支保護＋CODEOWNERS | 直推 main、必要檢查沒過就合併、`.feature`／hook／CI 修改未經核准、force push | 管理員也不可略過 |

## AI Hooks 的時機
- **執行指令前**：擋 `rm -rf /`、`git push --force`、`git reset --hard`、`format`、`del /s`、`curl … | sh`、讀 `.env`；推送、遞迴刪除、發布套件要使用者確認。
- **讀檔前**：禁止讀機密檔（`.env`、`*.pem`、`id_rsa` 等）。
- **改檔後**：只對該檔跑 formatter／linter，並檢查產品程式的 `unwrap()`／`expect()`、`console.log`、寫死的機密。
- **結束前**：本輪有改檔就跑測試（失敗會要求繼續修）；`role=dev-agent` 時要求更新自己的看板卡。

## 規則
- hook 擋下或回報問題時，**修正程式或改用安全做法**；不准停用、修改、略過 hook 或 `config.json`，也不准改寫指令繞過。確實需要危險操作就交給使用者手動執行。
- hook 通過只代表自動檢查通過，**不等於驗收**。
- 角色由啟動 AI 的人設定（`.ai-hooks/config.json` 的 `role` 或 `AI_AGENT_ROLE`），預設 `dev-agent`；AI 不可自己改。
- PR 不得修改或停用 `.ai-hooks/`、`.githooks/`、`.github/workflows/`、`.claude/settings.json`（除非卡片本身就是改這些，且有 guard-change 標籤與核准）。審查時查 `.ai-hooks/logs/hooks.log`，被擋的指令與未修正的發現都要有交代。

## 看板伺服器（若有安裝）
- 只聽 localhost；帳號分 viewer／dev-agent／verifier／high-tier／admin，密碼雜湊存在不進 git 的使用者檔（雜湊規則見 [readiness.md](readiness.md) 的例外條款）。
- 每個帳號預設看不到任何專案（admin 除外），需授權。
- board.json 存檔後自動 commit；遠端同步只 `pull --ff-only` 與一般 push，衝突就停下顯示，絕不 force push。
- GitHub Token 只從環境變數 `GITHUB_TOKEN` 讀。
- 看板不提供線上編輯；代理照舊改 `docs/board.json`，由 git 記錄誰改了什麼。
