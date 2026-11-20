# 上線就緒標準（路由）

內容已拆成主索引底下的參考文件，只讀你現在需要的那一份：

| 主題 | 參考 |
|---|---|
| 測試策略、交易與併發、日誌與 Trace ID、安全分層防禦、密碼與機密、記憶體與資源 | [readiness.md](../.agents/skills/ai-dev-pipeline/references/readiness.md) |
| 效能預算、複雜度上限、benchmark 回歸、演算法選擇 | [performance.md](../.agents/skills/ai-dev-pipeline/references/performance.md) |
| 版本、CHANGELOG、發布前檢查、回滾、選用的放量機制 | [release.md](../.agents/skills/ai-dev-pipeline/references/release.md) |

原則：一律以需求為準，不過度設計；單機桌面 App 不必硬上分散式交易、APM 或 JWT。本專案適用範圍見 [project.md](../.agents/skills/ai-dev-pipeline/references/project.md)。
