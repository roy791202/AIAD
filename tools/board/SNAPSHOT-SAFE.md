# PD-BOARD-SAFE-01 — 看板 snapshot 安全寫入

PM 流程（建工項／決策紅燈／派 subagent）見 **[PM-AGENT.md](./PM-AGENT.md)** 與 PRODUCT-DEVELOPMENT §7.3。

## 規則（硬）

- **只**替換 `docs/PROJECT-BOARD.html` 內 `#board-snapshot` 的 JSON。
- 寫後檔案必須仍含 `<!DOCTYPE html>` 與導覽（`.nav` / `<nav` / `導覽`）。
- **禁止**整檔覆寫 HTML（含只貼上 `<script id="board-snapshot">…`）。測到即 FAIL。

## Agent 怎麼寫

1. **首選** `python tools/board/board.py report <id> done|blocked --note "…"`  
   （內部走 `board_watch.HtmlSnapshotStore` → `snapshot_safe`）。
2. **只加 note、不改燈**（§7.1 不可自改綠）:
   ```python
   from pathlib import Path
   from board_core import snapshot_safe
   from board_core import usecases
   # 或直接:
   def add_note(data):
       for t in data["tasks"]:
           if t.get("id") == "PD-XXXX":
               t["note"] = (t.get("note") or "") + "\n[ts] one line"
               return t
       raise KeyError("card")
   snapshot_safe.mutate_snapshot_file(Path("docs/PROJECT-BOARD.html"), add_note)
   ```
3. **不要**用編輯器／`Write` 工具整份重寫 `PROJECT-BOARD.html`。

## 驗收

```text
python -m pytest tools/board/test_snapshot_safe.py -q
```

模組：`tools/board/board_core/snapshot_safe.py`  
`board_watch.mutate_html` 已接入同一路徑。
