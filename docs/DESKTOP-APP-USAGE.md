# 桌機 App 使用說明（索引）

**完整步驟（開專案／DryRun／設定／埠禁區）** 以桌機 README 為準：

→ [`apps/sgenaxis-desktop/README.md`](../apps/sgenaxis-desktop/README.md)（章節「使用說明」）

對應工項：`PD-README-APP-01` · BDD-PD-README-APP-01。

## 埠速查

| | |
|--|--|
| 開發看板 | `http://127.0.0.1:28789/`（`docs/start-board-watch.cmd`） |
| 產品桌機 | `apps/sgenaxis-desktop` → `npm run tauri dev` |
| **禁區** | `:8788`（HoneyBadger mailbox）、`:8787` |
| 已讓出 | `:18789`（勿寫回） |

權威產品說明：[`PRODUCT-DEVELOPMENT.md`](./PRODUCT-DEVELOPMENT.md) §1.1、§7。

Elevated VERIFY-INSTALL／Live CLI 冒煙（權限、風險、NOT RUN）：[`VERIFY-ELEVATED-AND-LIVE-SMOKE.md`](./VERIFY-ELEVATED-AND-LIVE-SMOKE.md)（PD-VERIFY-DOC-01）。

v0.1 發布前可勾選檢查清單（MSI／elev／sec／SBOM／簽章／CHANGELOG；狀態 PASS｜FAIL｜NOT RUN｜PARTIAL）：[`RELEASE-CHECKLIST-v0.1.md`](./RELEASE-CHECKLIST-v0.1.md)（PD-REL-CHECKLIST-01）。

v0.1 回滾／靜默卸載復原（失敗步驟、風險、未真跑＝**NOT RUN**；≠正式發布回滾演練）：[`ROLLBACK-v0.1.md`](./ROLLBACK-v0.1.md)（PD-ROLLBACK-DOC-01）。
