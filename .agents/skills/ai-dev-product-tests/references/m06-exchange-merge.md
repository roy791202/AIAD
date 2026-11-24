# M06 交換與合併：測試參考

> 規格根目錄簡寫：`SPEC` = `docs/requirements-confirmation/phase1-spec/`；產品根目錄簡寫：`APP` = `apps/sgenaxis-desktop/`。
> 讀取基準：worktree `claude/skills-index-structure-f8398d`（HEAD `ef4896fa`），僅唯讀。
> 狀態提醒：三張交付卡皆為 `BLOCKED_PENDING_APPROVED_ENVELOPE_AND_VALID_RED`；M06 PREP `current-state.json` 為 `CX_REVISION_PENDING_OWNER`（M06-X1～X7、R1～R4 未採納）；G01、G02 仍是 `PENDING_ARCHITECTURE_REVIEW`。

## 1. 範圍與來源

| 功能 ID | 規格連結 | 交付卡 | BDD 場景 |
|---|---|---|---|
| F07 ESS 交換與 BIN 按需封裝 | `SPEC/index.html#F07`：作者只在明確要求時輸出 BIN，內容含專案資料與引用素材；需求 REQ-09，驗收 AC07 | `SPEC/tasks/PD-P1-F07-DELIVERY-01.json`（相依 M06-PREP、G01） | BDD-11、BDD-12（F07 精確映射見 `SPEC/tasks/F07/feature-trace-preparation/traceability.json`；BDD-09 屬 F08） |
| F08 匯入驗證與新專案副本 | `SPEC/index.html#F08`：預覽 BIN 後還原成獨立專案，或把 ESS 複製成副本；需求 REQ-06/10/13，驗收 AC08 | `SPEC/tasks/PD-P1-F08-DELIVERY-01.json`（相依 M06-PREP、G01、G02） | BDD-09、BDD-10、BDD-13、BDD-14（`SPEC/tasks/F08/feature-trace-review/review.json`） |
| F09 單文件合併與身分衝突 | `SPEC/index.html#F09`：從 BIN 選一份文件逐項採用，其他文件不變；需求 REQ-11/12/14，驗收 AC09 | `SPEC/tasks/PD-P1-F09-DELIVERY-01.json`（相依 M06-PREP、G01、G02） | BDD-15、BDD-16、BDD-17、BDD-18、BDD-19（BDD-21「合併 Undo」屬 M04） |

其他來源：
- BDD 原文：`SPEC/phase1.feature` 第 64～140 行（@BDD-09～@BDD-19 @M06）。
- 需求基線：`SPEC/index.html` 內嵌 JSON `baseline`（REQ-06、09～14 都是「已確認」）。
- 不變條件：內嵌 JSON `invariants` 的 INV01、INV03、INV07、INV08。已取代條文：`superseded` 的 S-03、S-07、S-08。
- 一致性表：`SPEC/index.html#consistency`，其中「缺引用 vs 拒絕匯入」一列說明：包內宣告的內部內容缺失屬於完整性錯誤。
- 額外義務 X06：`SPEC/index.html#tests`（壓縮包的路徑、大小寫碰撞、連結、解開炸彈等情況；取消、空間不足、來源不可讀）。
- 預設值 D09、D10：`SPEC/index.html#defaults`，全部尚未批准。
- 門檻 G01、G02：`SPEC/index.html#gates`、`SPEC/tasks/PD-P1-G01-DEC-01.json`、`SPEC/tasks/PD-P1-G02-DEC-01.json`。
- 模組規劃：
  - `SPEC/tasks/M06/planning/gap-matrix.json`
  - `SPEC/tasks/M06/planning/decision-request.json`（D1/D2/D5/D6）
  - `SPEC/tasks/M06/planning/envelope.json`（PROPOSED_NOT_APPROVED）
  - `SPEC/tasks/M06/planning/exchange-exact-design/review-request.json`（M06-X1～X7 PENDING_OWNER）
  - `SPEC/tasks/M06/planning/import-validation-review/module-review.json`（M06-GAP1～4）
- 檔案提交前置：`SPEC/tasks/IO-PREREQ/implementation/acceptance/verification.json`（`PASS_IMPLEMENTED_SCOPE_ONLY`；Windows11 與原生別名的門檻仍未完成）。
- UI：`docs/ui-design/ui-spec.json` 沒有 M06 的頁面或對話框（搜尋 BIN、import、merge、export 都是 0 筆）。介面驗收只能依各功能節的「UI schema 摘要」。

## 2. 業務規則

### 已核准

判定方式：這裡只收需求基線標成「已確認」的 REQ、BDD 原文、AC，以及功能節裡沒有標「建議」的條文。這些條文的可觀察結果不依賴 BIN 格式或 ID schema。凡是要用到格式、ID 或交易細節才能下斷言的，一律放到「待決策」。

| 規則 ID | 規則 | 規格出處 | 核准依據 |
|---|---|---|---|
| R-M06-01 | 新建專案或一般保存都不會自動輸出 BIN；只有明確的封裝操作才會輸出 | REQ-09；BDD-11；F07「邊界」：新建不自動輸出；AC07「只有明確操作才輸出」 | 正式核准 |
| R-M06-02 | 明確封裝的 BIN，內容須包含專案定義、ESS、UI 設計，以及全部被引用的素材 | REQ-09；BDD-12；F07「資料影響」中標「確認」的部分 | 正式核准 |
| R-M06-03 | BIN 的內容清單與實際內容一致；缺少被引用素材時，不得宣稱封裝完整 | AC07「內容清單與實際一致」；`F07/feature-trace-preparation/traceability.json` #04 | 正式核准 |
| R-M06-04 | 封裝前後，來源檔的 hash 不變（成功與失敗都一樣） | AC07「來源 hash 不變」 | 正式核准 |
| R-M06-05 | 取消封裝後，不會留下會被誤認為成功的包，也不會顯示成功結果 | AC07；F07「狀態」含取消 | 正式核准 |
| R-M06-06 | `.ess` 不會偷偷換成 BIN；BIN 不是可執行授權 | F07「邊界」 | 正式核准 |
| R-M06-07 | 匯入 ESS 會建立獨立副本；修改並保存副本，不影響來源 | REQ-06；BDD-09 | 正式核准 |
| R-M06-08 | 目標已有同名 ESS 時，提供「另存新名稱」「明確取代」「取消」三個選項，不自動覆寫 | REQ-06；BDD-10 | 正式核准 |
| R-M06-09 | 匯入 ESS 或 BIN 前，先檢查格式版本、完整性、引用與目標路徑安全；損毀、未知版本或路徑越界時，拒絕並說明原因，目標不變 | REQ-13；BDD-13；AC08 | 正式核准 |
| R-M06-10 | 匯入與預覽都不執行包內程式（不隱藏執行） | REQ-10；BDD-13「未執行包內程式」；F08「資料影響」中標「確認」的部分；INV08 | 正式核准 |
| R-M06-11 | 包只缺「明確宣告」的外部依賴時，須經使用者明確確認，才以不完整、待綁定狀態匯入；匯入後可檢視、可保存，但依賴它的執行或生成會被阻擋。包內宣告的內部內容缺失屬完整性錯誤，不能走這個例外 | REQ-13；BDD-14；S-07；一致性表「缺引用 vs 拒絕匯入」 | 正式核准 |
| R-M06-12 | BIN 可預覽，並還原成獨立的新專案副本；來源不變，副本不依賴作者的絕對路徑 | REQ-10；AC08；S-03 | 正式核准 |
| R-M06-13 | 新建目標發生衝突（同名或非空目錄）時，提供改名、另選位置、取消，不直接覆寫 | F08「失敗處理」；REQ-08 | 正式核准 |
| R-M06-14 | 匯入或還原失敗時，來源與既有目錄都保持不變 | F08「失敗處理」；INV01 | 正式核准 |
| R-M06-15 | 整包還原成新專案，與單文件合併是兩個不同流程；整包還原不取得跨文件 Undo | REQ-12；F08「邊界」 | 正式核准 |
| R-M06-16 | 一次合併只限一份目標文件，加上必要的素材與引用；若必須修改其他文件才能一致，就阻擋並說明前置條件，不擴大範圍，也不動其他文件 | REQ-12；BDD-15；INV03；F09「邊界」 | 正式核准 |
| R-M06-17 | 合併前先預覽新增、修改、刪除與衝突，逐項選擇「保留本機」「採用匯入」「另存副本」；採用刪除也必須明確選擇 | REQ-11；F09「操作流程」與「邊界」 | 正式核准 |
| R-M06-18 | 兩份內容沒有可靠的共同基準時，不自動合併，逐項提供三個選項 | REQ-11；BDD-16 | 正式核准 |
| R-M06-19 | 在確認套用前取消合併時，目標文件與來源 BIN 都不變，也不新增 Undo 紀錄 | REQ-11「取消…保留目標合併前完整狀態及來源 BIN」；REQ-15「取消／未套用失敗不入歷史」 | 正式核准 |

### 待決策

| 規則 ID | 卡在 | 目前選項 | 開發期處理 |
|---|---|---|---|
| R-M06-20 | G01（BIN 內部 schema）；D6；D10；M06-X1 | ① 版本化壓縮包加 manifest，以 ZIP 為候選（D6）；② 不壓縮、分框的 BIN-v1（X1）；③ 擴充舊 SGB1 三 entry 格式（D6 備選，需另做安全 parser） | 不寫任何 BIN 位元組 fixture，也不寫格式斷言；R-M06-02/03 的 RED 等這項批准後才寫 |
| R-M06-21 | G01；F07「邊界」：單獨 ESS 的依賴如何攜帶 | 獨立 ESS 自帶素材，或改要求 BIN（X1：ESS 含內部素材時須明確選擇 RequiresBin） | 不對「單獨 ESS 含素材」寫斷言 |
| R-M06-22 | G01（Project/Document/Asset 的 ID 與版本）；D09；M06-X4。**依任務指示，F09 身分衝突整體列為待決策** | REQ-14 與 BDD-17 的語意已確認：ID 相同但無法確認同源時，暫停受影響項目，提供略過或另副本，不猜測重綁。但「同源」的判定欄位與 ID 格式還沒定案 | 只能保留 `PLANNED_NOT_RUN` 的場景存根，不寫成可驗收斷言 |
| R-M06-23 | G01；S-08；M06-X4（FreshImportedIds） | REQ-14 與 BDD-18：先預覽新身分與引用調整，只改副本內可確定的引用，未解析的標成待處理。映射資料的結構還沒定案 | 同 R-M06-22 |
| R-M06-24 | G01；M06-X6；F08 中標「建議」的條文 | 新專案取得新 ID，並保留來源追溯 | 不對 ID 或追溯欄位下斷言 |
| R-M06-25 | G02（prepare/commit/rollback）；F09 trace 指出的衝突 | BDD-19 原文：任一提交階段失敗都要回到完整前狀態。交換提案另把「提交後」的失敗歸成 `MergeAppliedRetentionDeferred`。兩者須由 Owner 和 G02 調和（`F09/feature-trace-preparation/evidence-and-gaps.json` 的 transaction_conflict） | 不可把提交後失敗弱化成「已回復成功」；在調和前不寫失敗注入斷言 |
| R-M06-26 | G02；REQ-15；BDD-21（M04） | 一次成功套用只占一筆 Undo（M04 Merge/Undo，X4） | 交給 M04 協同；M06 不自己寫 Undo 帳務斷言 |
| R-M06-27 | G02/G03；M06-X5；F09 中標「建議」的條文 | 共用素材不就地替換；另建新內容版本，透過 M05 的 pins 管理 | 不寫素材版本斷言 |
| R-M06-28 | G02；INV07（標明為建議契約）；F09 中標「建議」的條文 | 方案綁定目標 revision 與素材版本；過期就重新預覽 | 不寫「過期」判定斷言 |
| R-M06-29 | G02；F08「邊界」；M06-X6 | 目錄部分失敗時要精確清理（先隔離區，再由 M01 Ready CAS 發布） | 只驗收 R-M06-14（既有內容不變），不驗收清理範圍 |
| R-M06-30 | Owner 未批准 F07 的「建議」；G01 | 內容清單是否含格式版本、雜湊、來源版本；是否排除憑證、快取與機器專屬設定 | 不寫斷言 |
| R-M06-31 | Owner 未批准 F07 的「建議」；M06-X2 | 必要內部素材缺失就阻擋完整封裝；失敗或取消時只清本次產物；既有目的檔要另行確認才取代 | R-M06-05 只驗「不像成功」，不驗清理與取代策略 |
| R-M06-32 | Owner 未批准 F08 的「建議」；M06-X2/X6 | 只在選定目錄寫入，並先在隔離區準備 | 不寫斷言 |
| R-M06-33 | D10（未批准）；G01；M06-X1/X7 | X06 的其餘情況：重複路徑、大小寫碰撞、連結、解開炸彈、空間不足、來源不可讀、每階段取消。建議限額為 2 GiB／10000 項，壓縮比也要設上限 | 父目錄穿越與未知版本已併入 R-M06-09；其餘只保留場景名稱，不寫門檻數值 |
| R-M06-34 | M06-X3（R1～R4 未採納）；`preflight-document-reacceptance/review.json` | 精確錯誤優先序：只有 F1～F3 在文件範圍內關閉，64 個 oracle 只是文件層驗證；純函式 `evaluate_import_preflight` 也還只是提案 | 不以提案的錯誤碼或優先序寫斷言 |

## 3. 已有測試對照

結論：沒有任何現有測試直接驅動 M06 的封裝、匯入或合併流程（`gap-matrix.json` 的 gaps 第 1 項同樣如此記錄）。下表的「涵蓋」都是相鄰模組的機制或間接類比，不能當作 M06 的驗收證據。`APP/crates/sgenaxis-host/tests/module_packet.rs` 歸 M06，但一律標「間接覆蓋」（測的是 ESS 模組封包，不是 BIN 封裝／匯入）；`identity_preview.rs` 是 G01 相鄰回歸，不計覆蓋。

| 規則 ID | 測試檔::函式 | 已涵蓋類別 | 缺口 |
|---|---|---|---|
| R-M06-01 | 無 | — | 沒有封裝入口，也沒有「一般保存後檔案系統差異」的 fixture |
| R-M06-02 | 無（`tests/test_pd_scene_sgb_01.py` 只是舊 SGB1 三 entry 的 roundtrip，F07 review 判為歷史或靜態證據） | — | 沒有新 BIN 格式，也沒有獨立 decoder |
| R-M06-03 | 無 | — | 同上 |
| R-M06-04 | `APP/crates/sgenaxis-host/tests/module_packet.rs::selected_module_preserves_facts_excludes_unrelated_and_never_grants_approval`（Fs 寫入即 panic）；`APP/src-tauri/tests/project_document_commands.rs::doc_e01_adopts_and_preserves_source` | 間接覆蓋（module_packet）：正常（類比） | 前者是 ESS 模組封包匯出，後者是文件登記，都不是 BIN 封裝；沒有失敗路徑下的來源 hash 對比 |
| R-M06-05 | 無 | — | 沒有封裝取消的 harness |
| R-M06-06 | 無 | — | — |
| R-M06-07 | 無 | — | 沒有 ESS 跨專案複製入口 |
| R-M06-08 | `APP/crates/sgenaxis-adapters/tests/phase1_file_commit.rs::io_02_existing_file_or_directory_is_never_replaced`、`::io_10_expected_presence_mismatch_never_overwrites`、`::io_09_stale_digest_rejects_without_changing_original`（IO-PREREQ） | 失敗、邊界（基礎設施層） | 只證明單檔提交不會覆寫；沒有三選 UI，也沒有 ESS 同名判定 |
| R-M06-09 | `module_packet.rs::malformed_dtd_utf8_and_versions`（formatVersion=99 → UNSUPPORTED_FORMAT）、`::invalid_paths_reject_before_io`（`../`、絕對路徑、ADS、UNC 在 IO 前拒絕）、`::membership_and_graph_references_reject`；`APP/crates/sgenaxis-host/tests/identity_preview.rs::invalid_ess_schema_and_duplicate_ids_are_rejected`、`::malformed_unknown_and_duplicate_designs_are_rejected`（G01 相鄰回歸） | 間接覆蓋（module_packet）：無效輸入（ESS 讀取層） | 都不是匯入流程；沒有 BIN 損毀、包內路徑越界，也沒有「目標不變」的斷言 |
| R-M06-10 | `module_packet.rs::malformed_dtd_utf8_and_versions`（XML_DTD_FORBIDDEN）、`::literal_dtd_text_inside_cdata_is_not_declaration` | 間接覆蓋（module_packet）：無效輸入（弱類比） | 只證明不展開 DTD 實體；沒有「包內程式未執行」的觀察點 |
| R-M06-11 | 無（preflight 只有 64 個文件 oracle，不是產品測試） | — | 沒有 Blocked 與 NeedsDependencyConfirmation 分流的產品實作（M06-GAP1） |
| R-M06-12 | 無 | — | 沒有 BIN 還原；「不依賴絕對路徑」也沒有 fixture |
| R-M06-13 | `phase1_file_commit.rs::io_02_existing_file_or_directory_is_never_replaced`、`::gap_11_existing_empty_dir`、`::gap_11_existing_nonempty_dir`、`::io_03_invalid_names_are_rejected_without_child_creation`（IO-PREREQ） | 失敗、邊界、無效輸入（基礎設施層） | 沒有改名、另選、取消的 UI 與命令 |
| R-M06-14 | `phase1_file_commit.rs::io_11_pre_publish_faults_leave_old_bytes_and_owned_diagnostics`、`::io_12_post_publish_failure_restores_old_before_ordinary_error`、`::gap_10_rollback_cleanup_preserves_preimage`（IO-PREREQ） | 失敗（單檔） | 只到單一檔案；目錄層與多檔還原都沒有涵蓋 |
| R-M06-15 | 無 | — | — |
| R-M06-16 | `APP/crates/sgenaxis-work/tests/phase1_document_history.rs::m04_ex04_plan_for_another_document_cannot_cross_the_mutation_boundary`（M04 共用） | 無效輸入（M04 層） | 沒有「需修改他文件 → 阻擋並說明前置條件」的 M06 預覽斷言 |
| R-M06-17 | 無 | — | 沒有差異預覽，也沒有逐項決策 |
| R-M06-18 | `APP/crates/sgenaxis-spec/tests/identity_preview.rs::base_reference_without_matching_bytes_is_not_ancestry`（BaseMissing）、`::matching_base_is_validated_but_unreferenced_bytes_are_not_a_base`（G01 相鄰回歸） | 無效輸入、邊界（基準判定） | 只判定有沒有基準；沒有「不自動合併、提供三選」的斷言 |
| R-M06-19 | `phase1_document_history.rs::m04_ex02_preparing_then_discarding_a_plan_does_not_mutate_or_add_history`（M04 共用） | 正常（M04 層） | 沒有 M06 取消入口，也沒有來源 BIN 不變的斷言 |
| R-M06-22（待決策，只供參考） | `APP/crates/sgenaxis-spec/tests/identity_preview.rs::legacy_is_derived_without_fabricating_identity`；host 版 `identity_preview.rs::display_path_does_not_change_explicit_identity`、`::legacy_both_formats_are_read_only_and_do_not_require_git`（G01 相鄰回歸） | — | G01 未定，不作驗收 |
| R-M06-25（待決策，只供參考） | `phase1_file_commit.rs::io_13_failed_restore_retains_versions_and_blocks_followup` | — | 單檔層；G02 未定 |
| R-M06-26／27（待決策，只供參考） | `phase1_document_history.rs::m04_ex01_clear_commit_creates_one_complete_history_entry`、`::m04_prepare_carries_asset_versions_needed_by_both_sides`、`::m04_missing_asset_retention_plan_rejects_before_history_mutation` | — | 屬 M04；G02 未定 |
| R-M06-28（待決策，只供參考） | `phase1_document_history.rs::m04_ex03_stale_plan_rejects_without_changing_content_or_history`；`module_packet.rs::source_staleness_change_and_freshness_binding`（間接覆蓋）；host 版 `identity_preview.rs::changed_source_never_publishes_preview` | — | G02 未定 |

`APP/crates/sgenaxis-host/tests/packet_admission.rs` 測的是 AI 任務封包的准入綁定，不對應任何 M06 規則。

## 4. 測試矩陣

層：spec = `sgenaxis-spec`；work = `sgenaxis-work`；host = `sgenaxis-host`；command = `src-tauri`；ui = `ui/*.test.cjs` 加 Windows 原生操作。
凡是需要 BIN 位元組的 fixture，都要等 R-M06-20 批准後才能具體化。下表只寫可觀察的預期。

| 規則 ID | 類別 | 輸入 | 預期 | 層 |
|---|---|---|---|---|
| R-M06-01 | 正常 | 已建立專案，執行一次一般保存 | 目的地檔案樹沒有任何新 BIN；封裝呼叫次數為 0 | host |
| R-M06-01 | 邊界 | 剛完成新建（建立成功的當下） | 不產生 BIN | host |
| R-M06-01 | 無效輸入 | 封裝命令缺少明確的使用者觸發（例如不受信任的呼叫端） | 拒絕，不輸出 | command |
| R-M06-01 | 失敗 | 一般保存失敗 | 不輸出 BIN，也不顯示封裝結果 | host |
| R-M06-02 | 正常 | 專案含定義、ESS、UI，以及 2 個被引用素材，明確封裝 | 包內有四類內容，素材完整 | host |
| R-M06-02 | 邊界 | 素材 0 個；或兩份引用指向同一 digest 的素材 | 素材 0 個時內容清單仍有定義、ESS、UI；共用素材只收一次，引用完整 | host |
| R-M06-02 | 無效輸入 | 另有一個未被引用的素材 | 該素材不視為必要內容（是否收入屬 R-M06-30，不斷言） | host |
| R-M06-02 | 失敗 | 被引用素材不可讀 | 不得回報「完整封裝成功」 | host |
| R-M06-03 | 正常 | 封裝成功後，用獨立 decoder 列出 entries | entry 集合、大小、digest 與內容清單一一相符 | host |
| R-M06-03 | 邊界 | 只有 1 個 entry 類別在最小值的專案 | 清單筆數等於實際筆數 | host |
| R-M06-03 | 無效輸入 | 被引用素材缺失 | 清單不得宣稱完整 | host |
| R-M06-03 | 失敗 | 寫入中途失敗 | 沒有和實際內容不符、卻標成完成的清單 | host |
| R-M06-04 | 正常 | 封裝成功前後，對來源（定義、ESS、UI、素材）取 raw bytes hash | 每個 hash 都相等 | host |
| R-M06-04 | 邊界 | 0 byte 的素材，或 CRLF 結尾的 ESS | hash 仍相等，不做換行正規化 | host |
| R-M06-04 | 無效輸入 | 目的地等於來源路徑 | 拒絕；來源 hash 不變 | host |
| R-M06-04 | 失敗 | 封裝失敗或取消 | 來源 hash 不變，也不會靜默保存回來源 | host |
| R-M06-05 | 正常 | 在預覽階段取消 | 沒有成功結果，也沒有新的包 | ui |
| R-M06-05 | 邊界 | 在每個可取消點取消，包含最後一步之前 | 都沒有「看起來完成」的包或成功提示 | host |
| R-M06-05 | 無效輸入 | 同一個取消重複送出 | 結果不變，不出現成功 | command |
| R-M06-05 | 失敗 | 取消後清理失敗 | 不顯示成功；結果明確是失敗或取消 | host |
| R-M06-06 | 正常 | 選「匯出 ESS」 | 產出的是 `.ess`，不是 BIN | host |
| R-M06-06 | 邊界 | 副檔名大小寫不同（`.ESS`） | 仍依使用者選的類型，不轉成 BIN | host |
| R-M06-06 | 無效輸入 | 把 BIN 當作執行授權來源，觸發生成或執行 | 不授權，也不執行 | host |
| R-M06-06 | 失敗 | ESS 匯出失敗 | 不改用 BIN 當替代產物 | host |
| R-M06-07 | 正常 | A 匯出的 ESS 匯入 B，修改並保存 B 的副本 | A 的 bytes 不變 | host |
| R-M06-07 | 邊界 | 立即保存，沒有任何修改 | A 不變 | host |
| R-M06-07 | 無效輸入 | 匯入的來源就在 B 專案內部 | 仍建立副本，不和來源共用寫入 | host |
| R-M06-07 | 失敗 | 保存 B 副本失敗 | A 不變；B 保留原有效檔 | host |
| R-M06-08 | 正常 | 目標已有同名 ESS，預覽匯入 | 提供三個選項，未覆寫 | ui |
| R-M06-08 | 邊界 | 只有大小寫不同的同名檔（Windows 路徑） | 視為同名，提供三個選項（大小寫判定規則屬 D09，未批准，只觀察「不覆寫」） | command |
| R-M06-08 | 無效輸入 | 沒有選任何選項就送出套用 | 拒絕；既有檔不變 | command |
| R-M06-08 | 失敗 | 選「明確取代」後寫入失敗 | 原有效檔不變 | host |
| R-M06-09 | 正常 | 版本、完整性、引用、路徑都合法的包 | 驗證通過，進入預覽 | host |
| R-M06-09 | 邊界 | 已知的最高 formatVersion 與 +1 | 前者通過，後者以未知版本拒絕 | spec |
| R-M06-09 | 無效輸入 | 損毀的包；entry 路徑含 `../`、絕對路徑、磁碟代號或 UNC | 拒絕並說明原因；目標目錄的 bytes 不變 | host |
| R-M06-09 | 失敗 | 驗證途中來源不可讀 | 拒絕，目標不變 | host |
| R-M06-10 | 正常 | 包內含可執行檔或腳本 entry，執行預覽與匯入 | 沒有任何程序被啟動 | host |
| R-M06-10 | 邊界 | 含 DTD 或實體宣告的 ESS | 不展開實體，以安全方式拒絕 | spec |
| R-M06-10 | 無效輸入 | manifest 宣告了自動執行的鉤子 | 忽略或拒絕，不執行 | host |
| R-M06-10 | 失敗 | 匯入失敗 | 失敗路徑上同樣沒有任何執行 | host |
| R-M06-11 | 正常 | 安全完整的包，只缺 1 個明確宣告的外部依賴，使用者確認以待綁定匯入 | 可檢視、可保存；依賴它的生成被阻擋 | host |
| R-M06-11 | 邊界 | 缺 0 個依賴 | 不出現待綁定確認，直接可匯入 | host |
| R-M06-11 | 無效輸入 | 缺的是包內宣告的「內部」內容，卻想走待綁定 | 以完整性錯誤拒絕，不提供確認 | host |
| R-M06-11 | 失敗 | 缺外部依賴，但使用者未確認 | 不匯入，目標不變 | ui |
| R-M06-12 | 正常 | 預覽 BIN 後在新位置還原 | 建立獨立專案，來源 BIN 的 bytes 不變 | host |
| R-M06-12 | 邊界 | 包內引用了作者機器上的絕對路徑 | 副本不依賴這個路徑；改放在新位置，或明示未解析 | host |
| R-M06-12 | 無效輸入 | 還原目標是來源 BIN 所在的目錄本身 | 拒絕，或依 R-M06-13 處理衝突；來源不變 | command |
| R-M06-12 | 失敗 | 還原途中失敗 | 來源不變（清理範圍屬 R-M06-29） | host |
| R-M06-13 | 正常 | 目標名稱與既有專案同名 | 提供改名、另選、取消 | ui |
| R-M06-13 | 邊界 | 目標是空目錄；或非空目錄 | 都不直接覆寫（空目錄是否允許依 REQ-08「非空」規定，只斷言非空目錄一定擋） | host |
| R-M06-13 | 無效輸入 | 名稱空白、Windows 保留名，或含分隔符號 | 拒絕，不建立任何子目錄 | host |
| R-M06-13 | 失敗 | 選取消 | 沒有新目錄，既有目錄不變 | ui |
| R-M06-14 | 正常 | 匯入成功 | 來源 bytes 不變 | host |
| R-M06-14 | 邊界 | 在第一個寫入之前就失敗 | 來源與既有目錄完全不變 | host |
| R-M06-14 | 無效輸入 | 驗證被拒絕 | 目標目錄沒有任何新增或修改 | host |
| R-M06-14 | 失敗 | 寫入中途發生 IO 錯誤 | 既有目錄裡原有檔案的 bytes 不變；來源不變 | host |
| R-M06-15 | 正常 | 整包還原成新專案 | 不在任何既有文件的 Undo 歷史裡加紀錄 | host |
| R-M06-15 | 邊界 | 還原後馬上 Undo | 不會撤回整個新專案 | work |
| R-M06-15 | 無效輸入 | 在「建立副本」流程呼叫合併入口 | 入口分開，拒絕混用 | command |
| R-M06-15 | 失敗 | 還原失敗 | 沒有產生跨文件 Undo | host |
| R-M06-16 | 正常 | 合併只改目標文件與其必要素材 | 允許進入確認；其他文件的 bytes 不變 | host |
| R-M06-16 | 邊界 | 只差「另一份文件的引用」必須同步才一致 | 阻擋，並說明前置條件 | work |
| R-M06-16 | 無效輸入 | 一次選兩份目標文件 | 拒絕，提示同包其他文件要分次處理 | command |
| R-M06-16 | 失敗 | 阻擋發生後 | 目標與其他文件都不變，範圍不擴大 | host |
| R-M06-17 | 正常 | 有新增、修改、刪除與衝突的匯入 | 每一項都顯示，可逐項選三種處理 | ui |
| R-M06-17 | 邊界 | 差異 0 項；或只有 1 項 | 0 項時不提供套用變更；1 項時顯示一列 | ui |
| R-M06-17 | 無效輸入 | 刪除項目沒有明確選擇 | 不套用該刪除；有未決項時說明原因並阻擋 | work |
| R-M06-17 | 失敗 | 預覽產生失敗 | 不進入可套用狀態，目標不變 | host |
| R-M06-18 | 正常 | 兩份內容沒有可靠的共同基準 | 不自動合併；逐項提供三個選項 | work |
| R-M06-18 | 邊界 | 宣告了基準 revision，但基準 bytes 不符 | 視為沒有可靠基準 | spec |
| R-M06-18 | 無效輸入 | 提供了基準 bytes，但沒有宣告引用 | 不算基準 | spec |
| R-M06-18 | 失敗 | 讀取基準失敗 | 不退回成自動合併 | host |
| R-M06-19 | 正常 | 預覽後按取消 | 目標文件與來源 BIN 的 bytes 不變；Undo 數不變 | host |
| R-M06-19 | 邊界 | 已逐項選完但還沒確認就取消 | 同上 | ui |
| R-M06-19 | 無效輸入 | 取消後重送舊的套用請求 | 拒絕，不套用 | command |
| R-M06-19 | 失敗 | 取消時剛好預覽仍在產生 | 結果丟棄，不入歷史 | command |

## 5. 開發段（RED）

> 目前**不能開工**：三張交付卡都要求先取得核准的 envelope 和有效 RED；M06 的 envelope 是 `PROPOSED_NOT_APPROVED`，X1～X7 仍是 `PENDING_OWNER`。以下只在 envelope 批准後才適用。

- 放置位置（只是 envelope 提案的候選，`SPEC/tasks/M06/planning/exchange-exact-design/module-spec.json`、`cx-exchange-revision-v3/module-spec.json`；批准後以批准版本為準）：
  - work：`APP/crates/sgenaxis-work/tests/phase1_import_preflight.rs`（R-M06-11、16、17、18 的純策略）
  - host：`APP/crates/sgenaxis-host/tests/phase1_exchange.rs`（R-M06-01～11、14、16、19）、`APP/crates/sgenaxis-host/tests/phase1_project_copy.rs`（R-M06-12～15）
  - adapters：`APP/crates/sgenaxis-adapters/tests/phase1_archive_exchange.rs`（R-M06-09、10 的解碼器；等 R-M06-20 批准）
  - command：`APP/src-tauri/tests/phase1_exchange_commands.rs`（R-M06-01、05、08、13、15、16、19 的命令與呼叫端檢查）
  - ui：目前沒有提案檔名，也沒有 `ui-spec.json` 頁面；要先補 UI schema 的審查，再依 `APP/ui/project-document-ui.test.cjs` 的寫法另立檔案
- 先跑紅的指令（在 `APP` 目錄執行，加 `--locked`）：
  - `cargo test -p sgenaxis-work --test phase1_import_preflight --locked`
  - `cargo test -p sgenaxis-host --test phase1_exchange --locked`
  - `cargo test -p sgenaxis-host --test phase1_project_copy --locked`
  - `cargo test -p sgenaxis-adapters --test phase1_archive_exchange --locked`
  - `cargo test --manifest-path src-tauri/Cargo.toml --test phase1_exchange_commands --locked`
- 預期失敗關鍵字：
  - 有效 RED：`assertion` 失敗、`panicked at` 斷言訊息，且訊息要指向缺少的行為，例如「BIN written on ordinary save」「source hash changed」「target modified after rejected import」「auto-merged without base」。
  - 無效 RED：`error[E0432]`、`error[E0425]`、`unresolved import`、`FIXTURE_SETUP`、找不到 helper。這些是編譯、fixture 或環境失敗（交付卡 tdd.valid_red 的定義）。
- 回歸基線（RED 前後都要綠）：
  - `cargo test -p sgenaxis-host --test module_packet`
  - `cargo test -p sgenaxis-host --test identity_preview`
  - `cargo test -p sgenaxis-spec --test identity_preview`
  - `cargo test -p sgenaxis-work --test phase1_document_history`
  - `cargo test --manifest-path src-tauri/Cargo.toml --test project_document_commands`
  - `cargo test -p sgenaxis-adapters --test phase1_file_commit --locked -- --test-threads=1`
    - 這個要先 `cargo build -p sgenaxis-adapters --example file_commit_probe --locked`。
    - 再設 `FILE_COMMIT_PROBE_PATH`、`FILE_COMMIT_CHECKPOINT_PROBE_PATH`，依 `SPEC/tasks/IO-PREREQ/implementation/acceptance/independent-helper.json`、`independent-checkpoint.json`。
- 禁止事項：
  - 不改 `SPEC/**`、`phase1.feature` 或交付卡。
  - 不把 R-M06-20～34 寫成斷言，包括 ID 同源判定、新 ID 格式、BIN 位元組格式、提交後失敗分類、限額數值、錯誤碼優先序。
  - 不弱化斷言：例如把 BDD-19 改成「提交後失敗也算回復」，或用 `#[ignore]`、縮小 fixture。
  - 不刪除或修改既有測試，包括 IO-PREREQ 的 196 個原案例前綴，必須逐 byte 保留。
  - 不把 M04 的 `phase1_document_history.rs`、G01 相鄰回歸的 `identity_preview.rs` 改寫成 M06 測試。
  - 不加新依賴，例如 ZIP crate（envelope 的 new_dependency_cost 說明未批准）。
  - 不把舊 SGB1 三 entry 格式當成 BIN。

## 6. 驗證段

> 執行者不可以是寫這段程式的代理。

- 重跑指令（在 `APP` 目錄）：
  - `cargo test -p sgenaxis-work --test phase1_import_preflight --locked`
  - `cargo test -p sgenaxis-host --test phase1_exchange --locked`
  - `cargo test -p sgenaxis-host --test phase1_project_copy --locked`
  - `cargo test -p sgenaxis-adapters --test phase1_archive_exchange --locked`
  - `cargo test --manifest-path src-tauri/Cargo.toml --test phase1_exchange_commands --locked`
  - `node --test ui/<批准後的 M06 UI 測試檔>.test.cjs`
  - 第 5 段的全部回歸基線
- 介面實測步驟（Windows 原生 app；正式平台是 Windows11 x64，在 Windows10 跑的結果只能標成 NOT RUN 或替代，不可冒充）：
  1. 開啟含 UI 與 2 個被引用素材的專案，按一般保存，確認目的地沒有 BIN（R-M06-01）。
  2. 選「封裝 BIN」，確認摘要列出內容類別、引用素材、排除項、外部依賴與限制；選位置後輸出，並記錄結果（R-M06-02、03）。
  3. 重做步驟 2，在預覽及輸出進度中按取消，確認沒有成功提示，也沒有可被誤認的包（R-M06-05）。
  4. 在另一專案匯入同名 ESS，確認出現三個選項，選取消後既有檔不變（R-M06-08）。
  5. 匯入損毀或含 `../` 路徑的測試包，確認拒絕原因可讀、目標目錄不變、工作管理員中沒有新程序（R-M06-09、10）。
  6. 匯入只缺外部依賴的包：先不確認（應不匯入），再確認（可保存、生成按鈕被阻擋並說明原因）（R-M06-11）。
  7. 建立副本到同名或非空目錄，確認出現改名、另選、取消（R-M06-13）。
  8. 從 BIN 選兩份目標文件，確認只能選一份；若需要修改其他文件，確認被阻擋並說明前置條件（R-M06-16）。
  9. 在合併差異畫面逐項檢視；確認刪除項未選時不能套用；按取消後目標文件與 Undo 數都不變（R-M06-17、19）。
- 證據放置：
  - `reports/dispatch-pd/PD-P1-F07-DELIVERY-01-evidence/`（R-M06-01～06）
  - `reports/dispatch-pd/PD-P1-F08-DELIVERY-01-evidence/`（R-M06-07～15）
  - `reports/dispatch-pd/PD-P1-F09-DELIVERY-01-evidence/`（R-M06-16～19）
  - 每條規則一筆，欄位：`規則`／`指令`／`Exit code`／`輸出末段`（至少最後 20 行，含 `test result:`）／`介面證據`（截圖或錄影路徑，沒有介面時寫 N/A）／`判定`（PASS／FAIL／NOT RUN）。
  - 另記 HEAD SHA、OS 版本、`cargo --version`、fixture hash。
- 直接判 TDD_FAIL 的情況：
  - 任一條已核准規則缺少四類中的任一類測試，或那一類被 `#[ignore]` 或略過。
  - 測試斷言了 R-M06-20～34 的未決內容（格式位元組、ID 格式或同源判定、限額數值、提交後失敗分類、錯誤碼優先序）。
  - RED 證據只有編譯、fixture 或環境失敗，沒有行為斷言失敗；或沒有保留原始 RED log。
  - 既有回歸（module_packet、identity_preview×2、phase1_document_history、project_document_commands、phase1_file_commit）任何一個變紅，或原測試被修改或刪除。
  - 來源 hash 在任何封裝、匯入、合併路徑上改變；被拒絕的匯入改到了目標；取消後出現成功結果或像成功的包。
  - 合併改到了目標以外的文件；或在沒有可靠基準時自動合併。
  - 把舊 SGB1 roundtrip、文件 oracle（64 個或 184 個）、元件或靜態結果當成原生 UI 或功能完成的證據。
  - 驗證者與實作者是同一代理。

## 7. 已知衝突

| 衝突 | 規格出處 | 實作出處 | 影響規則 ID | 處理 |
|---|---|---|---|---|
| 目前無 | — | — | — | — |
