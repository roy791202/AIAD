# 本專案事實：SGenAxis（AIAD）

> 只寫已拍板的事實與路徑；細節以連結的文件為準。通用 skill 與這裡衝突時，**以這裡為準**，並在回報中指出衝突。

## 技術棧（已拍板，見 `docs/PRODUCT-DEVELOPMENT.md` §2）
- 桌面殼 **Tauri 2**；UI **Vanilla HTML／CSS／JS**（不用 React 全家桶、Electron、egui/iced、Slint；需元件化時可局部用 Svelte）。
- 核心 **Rust**（`apps/sgenaxis-desktop/crates/*`），以 `Property + Dirty + Evaluation` 做髒更新。
- OS 邊界：Ports（`FileSystemPort`、`PathPort`、`ProcessPort`、`GitPort`、`DialogPort`）＋各平台 Adapter；Tauri command 閉包內不得堆業務 OS 邏輯。
- 開發工具與 CI 腳本：Python（`tools/`、`scripts/`）。
- `PYSIDE_CPP_ARCHITECTURE.md`（Qt／PySide6）是**另案草稿，未拍板**，不得當作現行架構依據。

## 製作順序（強制，見 PRODUCT-DEVELOPMENT §4）
1 先搭 UI 殼 → 2 核心髒更新（假資料）→ 2.5 定義 Ports（stub → 真實作，contract 測試綠）→ 3 功能切片（只依賴 Port）→ 4 UI 接 command。不可顛倒。

## 看板
- 權威：`docs/board.json`，以 `.ai-hooks/validate-board.ps1` 驗證。舊 `PROJECT-BOARD.html`、`#board-snapshot`、`zone` 已停用（只剩 `.bak`）。
- 卡片 ID 慣例：`PD-<模組>-<名稱>-NN`。

## BDD、證據與報告
- BDD：`docs/bdd/<卡 ID>.feature`（例：`docs/bdd/PD-GIT-ADD-REMOTE-01.feature`），情境 ID `<卡 ID>-<序號>`。
- 開發報告：`reports/dispatch-pd/<ID>.md`（含 RED 指令與失敗輸出、GREEN 輸出）。
- 驗收報告：`reports/dispatch-pd/<ID>-TDD-REVIEW.md`，結論 `TDD_PASS`／`TDD_FAIL`。
- `reports/` 不進 git（本機證據）；需要留存的結論寫進卡片 `notes` 或 PR 描述。
- 建置結果用 PASS／FAIL／BLOCKED／NOT RUN／PARTIAL。

## 測試與 CI
- PR 閘門：`python scripts/pd_ci_pr_gate.py`（說明見 `docs/CI-PR-GATE.md`）。
- Rust：在 `apps/sgenaxis-desktop` 跑 `cargo test`；CI 另有 `rust-gate.yml`、`ai-dev-guard.yml`、`os-matrix-stub.yml`。

## 發布
- Windows：WiX → MSI（`packaging/windows/wix/`），規格 SSOT `packaging/pack-spec.v1.json`；發布檢查見 `docs/RELEASE-CHECKLIST-v0.1.md`、回滾見 `docs/ROLLBACK-v0.1.md`。
- macOS／Linux 目前只有包裝契約與 stub（M4），**不等於已跨平台發行**。
- 無服務端、無 updater 放量 → [release.md](release.md) 的「選用」段落目前不適用。

## 其他
- `AI_INSTRUCTIONS/` 是**凍結的需求快照**（`docs/requirements-confirmation/requirements.json` 以 sha256 引用），不是代理要讀的 skill，不要同步或修改。
- 失敗經驗文件：`docs/LESSONS.md`（新紀錄加在最上面）。
- 禁用埠：`:8788`、`:8787`。
