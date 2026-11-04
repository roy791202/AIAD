# PD-CI-01 — PR 閘門（lint＋測試子集）

BDD-PD-CI-01：PR 可跑固定指令（lint／單元或 smoke 子集）；**失敗不可視為綠**；本機等價命令如下。

## GitHub Actions

Workflow：`.github/workflows/pr-gate.yml`

- 觸發：`pull_request`、`workflow_dispatch`
- Runner：`ubuntu-latest`（免費 GitHub-hosted；**不**使用付費／專屬 runner）
- 步驟：安裝 `pytest==9.1.1` → `python scripts/pd_ci_pr_gate.py`
- **失敗 = 工作流紅燈**；不得當作合併／看板綠燈

建議依賴：`PD-SMOKE-01`（本機可另跑全量 smoke；PR 閘門固定為較輕的**單元子集**，不強制 cargo／全量 smoke）。

## 本機等價命令

於倉庫根目錄：

```powershell
# 一鍵（與 CI 相同入口）
python scripts/pd_ci_pr_gate.py

# 分步等價
python scripts/pd_ci_lint.py
python -m pytest tests/test_board_rules.py tests/test_board_files.py tests/test_stats.py tests/test_schedule.py tests/test_dispatcher.py -q --tb=short
```

前置：Python 3.10+；`pip install pytest==9.1.1`（見根目錄 `requirements.txt`）。

## 固定範圍

| 階段 | 指令／範圍 |
|------|------------|
| Lint | `scripts/pd_ci_lint.py` → `compileall`：`scripts/`、`sgenaxis/`、`tests/`、`tools/board/` |
| 測試子集 | 上表五個 `tests/test_*.py`（單元；無 elevated MSI、無付費 runner） |

任一非零退出 ⇒ **FAIL**（非綠）。

## 多 OS 矩陣占位（對照）

M4 矩陣 stub（windows／macos／linux job 占位；缺 runner → **NOT RUN**；無付費 mac 要求）見 [`docs/CI-OS-MATRIX.md`](./CI-OS-MATRIX.md) 與 `.github/workflows/os-matrix-stub.yml`。本機：`python scripts/pd_ci_os_matrix_stub.py`（啟用 cell 時呼叫本文件同一 `pd_ci_pr_gate.py`）。

## README 片段（可貼到專案 README）

```markdown
### PR gate (PD-CI-01)

CI: `.github/workflows/pr-gate.yml` (lint + unit subset on `ubuntu-latest`).
Local: `python scripts/pd_ci_pr_gate.py`
Details: `docs/CI-PR-GATE.md`. A failed gate is **not** green.
OS matrix stub: `docs/CI-OS-MATRIX.md` · `python scripts/pd_ci_os_matrix_stub.py`
```
