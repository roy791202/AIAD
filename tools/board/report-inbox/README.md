# tools/board/report-inbox — 派工 Agent 回報檔收件匣

BOARD-DISPATCH-01 §3.11（INV-BD-43..47）。每張派出去的卡，Agent 完工時用檔案編輯工具寫：

```
tools/board/report-inbox/<runId>.json
{"card": "<卡號>", "run": "<runId>", "outcome": "done" | "blocked", "note": "<一行說明>"}
```

確切路徑與內容會寫在該輪的 prompt 裡（也在環境變數 `HB_DISPATCH_REPORT_FILE`）。看板伺服器大約每秒檢查一次：
- **有效**的回報檔視同 `board.py report`（by=agent），處理後**移到** `tools/board/runtime/reports/processed/`；
- **無效**的會留在這裡，等 Agent 修正，同時在 Log 頁顯示原因；輪次結束時移到 `runtime/reports/rejected/`；
- 已經用其他管道回報過的，移到 `runtime/reports/ignored/`。

檔案只會被移動，不會被刪除。這個資料夾**刻意不放進 .gitignore**：有些 Agent IDE（例如 Antigravity 預設的
「gitignore access」）不允許編輯被 git 忽略的路徑。檔案通常只在這裡停留約一秒。請勿手動放檔案進來。

Port is 18789 (vg-board). Never use 8788 (HoneyBadgerCreator mailbox).
