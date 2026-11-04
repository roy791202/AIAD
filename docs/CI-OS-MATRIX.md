# PD-M4-CI-MATRIX-01 — 多 OS CI 矩陣占位

BDD-PD-M4-CI-MATRIX-01：CI **或**文件列出 **windows／macos／linux** job 占位；**缺 runner → NOT RUN**；與 **PD-CI-01** 本機命令可對照。

**不做：** 購買付費／專屬 mac runner 才算過關。

## 矩陣表（占位）

| OS | Workflow job | Runner（預設） | 狀態語意 |
|----|--------------|----------------|----------|
| windows | `matrix-windows` | `windows-latest`（免費 GitHub-hosted） | 有 runner 時可跑 PD-CI-01 閘門；否則 **NOT RUN** |
| macos | `matrix-macos` | **預設不啟用** mac runner → 在 ubuntu 上記 **NOT RUN**；可選 repo variable `ENABLE_MACOS_MATRIX=true` 使用免費 `macos-latest`（仍非付費專屬 runner） | 缺／未啟用 → **NOT RUN**（不得偽造成 PASS） |
| linux | `matrix-linux` | `ubuntu-latest`（免費 GitHub-hosted） | 有 runner 時可跑 PD-CI-01 閘門；否則 **NOT RUN** |

允許狀態字串：`PASS`｜`FAIL`｜`BLOCKED`｜`NOT RUN`｜`PARTIAL`（與 PackSpec／Build Result 對齊；見依賴 `PD-M4-PACK-SPEC-01`）。

## GitHub Actions stub

Workflow：`.github/workflows/os-matrix-stub.yml`

- 觸發：`workflow_dispatch`（預設；可自行打開 `pull_request`）
- 三個命名 job：`matrix-windows`／`matrix-macos`／`matrix-linux`
- 實際步驟入口：`python scripts/pd_ci_os_matrix_stub.py --ci --os <windows|macos|linux>`
- **失敗 ≠ 看板綠燈**；本卡 §7.1 不自改綠

## 與 PD-CI-01 本機命令對照

權威 PR 閘門文件：[`docs/CI-PR-GATE.md`](./CI-PR-GATE.md)  
權威一鍵入口：

```powershell
# PD-CI-01 — 與 .github/workflows/pr-gate.yml 相同
python scripts/pd_ci_pr_gate.py

# 分步等價
python scripts/pd_ci_lint.py
python -m pytest tests/test_board_rules.py tests/test_board_files.py tests/test_stats.py tests/test_schedule.py tests/test_dispatcher.py -q --tb=short
```

矩陣 stub（本機 dry；非目前主機的 OS 列為 **NOT RUN**）：

```powershell
python scripts/pd_ci_os_matrix_stub.py
# 聚焦單一 cell：僅當本機／runner OS 與 cell 一致時才呼叫 PD-CI-01；否則該 cell = NOT RUN
python scripts/pd_ci_os_matrix_stub.py --ci --os windows   # 在 Windows 上 → 跑閘門
python scripts/pd_ci_os_matrix_stub.py --ci --os linux     # 在非 Linux 上 → linux=NOT RUN（不偽 PASS）
# mac：非 Darwin（且未在 macos-latest 上）→ NOT RUN（exit 0；無付費 mac 要求）
python scripts/pd_ci_os_matrix_stub.py --ci --os macos
```

| 本機／CI | PD-CI-01 | 矩陣 stub |
|----------|----------|-----------|
| 一鍵閘門 | `scripts/pd_ci_pr_gate.py` | stub 在啟用 cell 上 **呼叫同一腳本** |
| Workflow | `.github/workflows/pr-gate.yml`（ubuntu） | `.github/workflows/os-matrix-stub.yml`（三 OS 占位） |
| 文件 | `docs/CI-PR-GATE.md` | 本文件 `docs/CI-OS-MATRIX.md` |

## 依賴

- `PD-CI-01` — 固定 lint＋單元子集；本機等價命令見上表
- `PD-M4-PACK-SPEC-01` — 產物 `status∈PASS｜FAIL｜BLOCKED｜NOT RUN｜PARTIAL`；矩陣 cell 狀態沿用同一集合

## README 片段

```markdown
### OS matrix stub (PD-M4-CI-MATRIX-01)

Jobs: windows / macos / linux placeholders in `.github/workflows/os-matrix-stub.yml`.
Missing or disabled runners → **NOT RUN** (no paid mac required).
Local: `python scripts/pd_ci_os_matrix_stub.py`
Cross-ref PR gate: `python scripts/pd_ci_pr_gate.py` · `docs/CI-PR-GATE.md` · `docs/CI-OS-MATRIX.md`.
```
