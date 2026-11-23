# M04 文件與單文件歷史：測試參考

> 規格根目錄 `docs/requirements-confirmation/phase1-spec/`（以下簡稱 `SPEC/`）；產品根目錄 `apps/sgenaxis-desktop/`（以下簡稱 `APP/`）。
> 本檔只讀取來源整理，未修改 repo，未執行任何產品測試（全部 NOT RUN）。

## 1. 範圍與來源

| 功能 ID | 規格連結 | 交付卡 | BDD 場景 |
|---|---|---|---|
| F05 ESS編輯、正式保存與專案切換 | `SPEC/index.html#F05`（使用情境／資料影響／失敗處理／邊界／AC05／UI schema 摘要）；`SPEC/index.html#features` 基線 REQ-07；追溯配方 `SPEC/tasks/F05/feature-trace-correction/module-spec.json` `trace[]`（F05-P01～P05、F05-R20/R21；為 preparation 版的更正版，取代 `feature-trace-preparation/module-spec.json` 的 BDD 對應） | `SPEC/tasks/PD-P1-F05-DELIVERY-01.json`（BLOCKED_PENDING_APPROVED_ENVELOPE_AND_VALID_RED；依賴 M04-PREP、G01、G02） | `SPEC/phase1.feature` @BDD-07（保存失敗不離開）、@BDD-08（取消離開）；BDD-20/21 僅為共用回歸義務 |
| F10 清空與複合Undo | `SPEC/index.html#F10`（資料影響／失敗處理／邊界／AC10／UI schema 摘要）；基線 REQ-15、REQ-16；`SPEC/tasks/F10/feature-trace-preparation/trace.json`、`pending-recipes.json`（F10-T01～T08） | `SPEC/tasks/PD-P1-F10-DELIVERY-01.json`（BLOCKED…；依賴 M04-PREP、G02、G03） | @BDD-20（清空Undo）、@BDD-21（合併Undo）；@BDD-19、BDD-26、BDD-31 為跨模組共用回歸 |
| 模組準備卡 | `SPEC/tasks/PD-P1-M04-PREP-01.json`；`SPEC/tasks/M04/planning/`（test-plan.json、gap-matrix.json） | — | 同上 |
| 決策門檻 | `SPEC/tasks/PD-P1-G01-DEC-01.json`、`PD-P1-G02-DEC-01.json`、`PD-P1-G03-DEC-01.json`（均 PENDING_ARCHITECTURE_REVIEW）；`SPEC/index.html#gates`、`#defaults` D11 | — | — |
| 補充案例 | `SPEC/index.html#tests` X04：保存／另存／取代每一步故障、退出三種選擇、Undo 連續操作、關閉重開不保留歷史 | — | — |

## 2. 業務規則

### 已核准

| 規則 ID | 規則 | 規格出處 | 核准依據 |
|---|---|---|---|
| R-M04-01 | 有未保存修改時，關閉文件、切換專案、退出程式都要提示「保存／不保存／取消」三種選擇。 | `SPEC/index.html#features` REQ-07；`#F05` 操作流程、UI schema 摘要 | 正式核准 |
| R-M04-02 | 在提示中選「取消」就不離開：文件與內容保持原樣，仍然開啟。 | `SPEC/phase1.feature` @BDD-08；`#F05` 失敗處理「取消不離開」 | 正式核准 |
| R-M04-03 | 選「保存」但保存失敗時不關閉也不切換：留在原文件，保留目前修改、dirty 與目前專案，並持續顯示失敗原因。（原檔位元組在各階段故障下的保全另見 R-M04-10） | @BDD-07；REQ-07「選擇保存後必須成功才繼續離開」；`#F05` 失敗處理、AC05「保存未成功不關閉／切換」、UI schema「錯誤持續可見」 | 正式核准 |
| R-M04-04 | 選「不保存」只捨棄本次修改，不清除復原快照。 | `#F05` 失敗處理 | 正式核准 |
| R-M04-05 | 只有保存成功才更新正式基準；保存失敗、內容不符或過期的確認都不得改變正式基準與目前內容。 | `#F05` 資料影響（確認部分）；AC05「失敗保留原檔與dirty」 | 正式核准 |
| R-M04-06 | 正式保存不改快照基準，正式基準與快照基準彼此獨立。 | `#F05` 邊界；`#F11` 資料影響、邊界「保存正式檔不改快照基準」 | 正式核准 |
| R-M04-07 | 文件列顯示文件名、位置與修改標記；編輯後出現修改標記，保存成功後消失，保存失敗仍保留。 | `#F05` UI schema 摘要、狀態列表；AC05「失敗保留…dirty」 | 正式核准 |
| R-M04-08 | A/B 內容隔離：對文件／專案 A 的編輯、保存與遲到回應，不得改變 B 的內容或狀態。（可信保存目標身分的契約另見 R-M04-12） | `#F05` AC05「A/B內容隔離」；`F05/feature-trace-correction/module-spec.json` trace F05-P04 | 正式核准 |

### 待決策

| 規則 ID | 卡在 | 目前選項 | 開發期處理 |
|---|---|---|---|
| R-M04-09 重開內容等於成功保存的內容；重開後沒有 Undo 歷史（AC05、X04） | G01（ESS／UI 設計 schema、codec、身分） | M03 保存契約提案 `SPEC/tasks/M03/planning/preservation-contract/codec-contract.json`；CXv3 typed identities（`M04/planning/cx-revision-v3/shared-contract.json`）；均未採納 | 只保留配方 F05-P01，不寫斷言；既有 `scene_doc.rs::roundtrip_ess_text` 只當回歸觀察 |
| R-M04-10 保存／另存／明確取代在 encode、reserve、precommit、replace、提交不確定各階段故障時，原有效檔與模型的保全（REQ-07、BDD-07「原有效檔保留」、X04） | G02（prepare/validate/commit/rollback 協定）＋G01 | G02 recommendation：先暫存、保持原檔可恢復、提交後統一發布；現有 host `write_atomic` 不代表此路徑（F05-P02、E-UI） | 已提交或不確定的情況不得斷言「舊檔未變」；先只做 BDD-07 的不離開部分（R-M04-03） |
| R-M04-11 保存收據 → 根轉移 → 語意 ACK 的精確順序；Unknown／Deferred 時保持 Held、不 ACK | G02＋save-retention Owner G1～G4 | `M04/planning/save-response-review/review.json`、`save-retention-observation-review/review.json`（僅文件模型） | 配方 F05-P05；不以模型布林值當原生 oracle |
| R-M04-12 保存目標可信身分（Project/Document UUID、session、generation）與換 owner 後不得送達 ACK | G01 | F05-P04：可信 target/provider＋owner generation seam；不接受 UI 提供的可信布林 | R-M04-08 只用既有 session／文件 UUID 隔離驗證 |
| R-M04-13 開啟時先驗證再替換目前文件 | Owner 尚未採納（`#F05` 資料影響標「建議」） | 採納／不採納 | 不寫斷言 |
| R-M04-14 沒有變更時不出現 dirty 提示 | Owner 尚未採納（`#F05` 資料影響標「建議」） | 採納／不採納 | R-M04-01 的乾淨文件邊界只記觀察，不判通過／失敗 |
| R-M04-15 清空目前文件是一筆完整 Undo；一次 Undo 完整還原內容、階層、關係、引用、綁定與限制，只撤回這次操作（REQ-15、BDD-20、AC10） | G02（Undo 歷史何時入帳、交易邊界；G02 impact「阻擋…清空與Undo實作」） | F10-T01 配方；D11 沿用既有文件內歷史 | 既有 S1 純元件測試只當歷史證據，不當 F10 驗收 |
| R-M04-16 單文件合併（含待綁定）一筆 Undo 還原整次變更與綁定限制，不刪來源或共用素材（REQ-15/16、BDD-21） | G02＋M06 合併整合（MH1～MH6 待 Owner） | F10-T02 配方 | 不寫斷言 |
| R-M04-17 取消不入歷史；部分套用失敗要先完整回復、不新增 Undo（REQ-15、BDD-19 共用） | G02 | F10-T03：列舉所有提交階段，不得只挑部分模型案例 | 不寫斷言；不弱化「完整回復」 |
| R-M04-18 Undo 只回收本次新增且已無引用的素材（REQ-16） | G02＋G03（引用根判定） | F10-T04：M05 roots 提案 | 不授權實體清理 |
| R-M04-19 Undo 算內容變更，觸發快照重新評估；擷取要等清空／合併／Undo 完成或完全回復（REQ-16、REQ-20、AC10、BDD-26） | G03（＋G02） | F10-T06、F10-T07 | 不新增 timer／provider 語意 |
| R-M04-20 Undo 範圍限目前文件與這次開啟期間；不含跨文件、關閉重開、焦點、滑鼠、播放進度（REQ-15、`#F10` 邊界、X04） | G02（＋G01 才能驗證重開） | — | 不寫斷言 |
| R-M04-21 Undo 失敗不消耗歷史、保留可回復狀態 | G02（`#F10` 失敗處理明言「此為G02失敗協定一部分」，且標「建議」） | 採納／修訂 | 不寫斷言 |
| R-M04-22 Redo 語意 | `#defaults` D11 建議；`#F10` 邊界「Redo規格另列建議，不當已批准」 | 沿用既有 Redo／另定 | 既有 `undo` 會推入 `redo` 的行為不得寫成驗收斷言 |

## 3. 已有測試對照

測試路徑相對 `APP/`。純元件測試（`phase1_document_history.rs`）是歷史 S1 證據（`F05/feature-trace-correction/module-spec.json` evidence E-S1），沒有檔案系統、重開、UI 或 owner handoff。

| 規則 ID | 測試檔::函式 | 已涵蓋類別 | 缺口 |
|---|---|---|---|
| R-M04-01 | 無 | — | `ui/app.js:513 confirmLeaveSceneIfDirty` 只有切換專案用兩個 `confirm()` 拼出三選，沒有測試；關閉文件、退出程式找不到 dirty 攔截（app.js 沒有 beforeunload 或 CloseRequested 處理） |
| R-M04-02 | 無 | — | 取消分支（第二個 confirm 回 false → "abort"）只有原始碼，沒有測試；也沒有關閉提示 |
| R-M04-03 | 無 | — | `saveSceneSgsToProject` 失敗時在 `clearSceneDirty` 前丟例外，只有原始碼觀察；失敗原因只用 toast，「持續可見」未驗證 |
| R-M04-04 | 無 | — | 不保存只呼叫 `clearSceneDirty()`；「不清復原快照」沒有任何測試 |
| R-M04-05 | `crates/sgenaxis-work/tests/phase1_document_history.rs::m04_ex08_formal_ack_does_not_reset_the_recovery_baseline`、`::m04_ex09_late_formal_ack_preserves_newer_edits_as_dirty`、`::m04_editing_during_save_remains_possible_and_late_ack_leaves_new_content_dirty`、`::m04_conflicting_digest_for_current_revision_cannot_replace_a_baseline`、`::m04_future_ack_cannot_change_either_baseline`、`::m04_old_ack_cannot_rewind_an_already_newer_baseline` | 正常、邊界、無效輸入（work 層） | 沒有「保存失敗 → 不呼叫 ACK」的 host/command 測試；UI 端 `clearSceneDirty` 時序沒有測試 |
| R-M04-06 | `phase1_document_history.rs::m04_ex08_formal_ack_does_not_reset_the_recovery_baseline`、`::m04_recovery_ack_does_not_reset_the_formal_baseline`、`::m04_ex06_undo_advances_revision_but_can_return_to_a_clean_formal_content`（snapshot_baseline 不變） | 正常、邊界（work 層） | 失敗類別（ACK 被拒時兩個基準都不動）只有 R-M04-05 的測試間接涵蓋；沒有和 M07 快照儲存的整合 |
| R-M04-07 | 無 | — | `markSceneDirty`／`clearSceneDirty`（app.js:452/458）沒有 UI 測試 |
| R-M04-08 | `phase1_document_history.rs::m04_ex04_plan_for_another_document_cannot_cross_the_mutation_boundary`、`::m04_plan_for_another_session_cannot_commit`；`src-tauri/tests/project_document_commands.rs::doc_e02_unbound_and_stale_projects_reject_before_reads`、`::ui02_sibling_and_drive_mismatch_still_reject_before_reads`；`ui/project-document-ui.test.cjs` 測試「late prepare result cannot bind another project」、「late adoption response and double click cannot update B or replay request」 | 無效輸入、失敗（work 層；command／ui 層只涵蓋文件「納入」，不涵蓋保存） | 沒有「保存 A 期間切到 B，A 的遲到保存回應不得改 B」的測試 |
| R-M04-09（待決策） | `crates/sgenaxis-host/src/scene_doc.rs` 單元測試 `roundtrip_ess_text` | 只供參考 | 不算驗收覆蓋 |
| R-M04-10（待決策） | `scene_doc.rs::invalid_scene_paths_preserve_existing_document`；`project_document_commands.rs::doc_e04_atomic_failure_preserves_manifest`、`::doc_e05_readback_failure_reports_uncertain_commit`（manifest，不是 ESS 保存） | 只供參考 | 不算驗收覆蓋 |
| R-M04-15（待決策） | `phase1_document_history.rs::m04_ex01_clear_commit_creates_one_complete_history_entry`、`::m04_ex01_undo_restores_content_refs_bindings_and_restrictions`、`::m04_empty_history_undo_reports_no_undo_and_preserves_state`、`::m04_revision_overflow_cannot_wrap_or_add_a_history_entry` | 只供參考（歷史 S1） | 不算 F10 驗收覆蓋（F10-T01 gap） |
| R-M04-15／22（待決策；F10 實作缺口，自 M07 移入） | `APP/ui/uidesign_recovery.js`（UI 設計文件「清空＋Undo／Redo」checkpoint，對應 REQ-15／F10；檔名雖有 recovery，但不是 M07 的復原快照） | 無測試 | 全缺：沒有任何 `*.test.cjs` 載入它；G02 未定前只記缺口，不當 F10 驗收，也不把它的 redo 行為寫成 R-M04-22 斷言 |
| R-M04-16／17／18（待決策） | `::m04_prepare_carries_asset_versions_needed_by_both_sides`、`::m04_ex02_preparing_then_discarding_a_plan_does_not_mutate_or_add_history`、`::m04_ex03_stale_plan_rejects_without_changing_content_or_history`、`::m04_missing_asset_retention_plan_rejects_before_history_mutation` | 只供參考 | 沒有真實合併或素材根整合 |

沒對應到任何規則的既有測試：`::m04_ex05_same_semantic_content_is_not_a_new_content_edit`（和 R-M04-14 建議相關，但不能當驗收）、`::m04_ex07_*`（擷取，屬 M07/G03）、`::m04_closed_session_rejects_mutation_and_capture`、`::m04_matching_revision_does_not_authorize_a_forged_before_payload`、`::m04_late_recovery_ack_cannot_swallow_a_newer_content_revision`。

## 4. 測試矩陣

| 規則 ID | 類別 | 輸入 | 預期 | 層 |
|---|---|---|---|---|
| R-M04-01 | 正常 | 文件 A 有未保存修改，分別觸發關閉文件、切換專案、退出程式 | 每個入口都出現同一個三選對話框（保存／不保存／取消），選之前不離開 | ui |
| R-M04-01 | 邊界 | 只改一個欄位後馬上觸發切換；乾淨文件觸發切換 | 有修改時要提示；乾淨文件是否提示屬 R-M04-14 待決策，只記錄觀察，不判 | ui |
| R-M04-01 | 無效輸入 | 對話框以 Esc 或視窗關閉鈕關掉（不是三個按鈕之一） | 不可當成「不保存」；要嘛視同取消，要嘛不離開（判定只看「沒有離開、沒有捨棄」） | ui |
| R-M04-01 | 失敗 | 退出過程中 host 回應錯誤或逾時 | 不在未選擇時靜默退出或丟掉修改 | ui／command |
| R-M04-02 | 正常 | 未保存的 A，在關閉提示選取消 | A 仍開啟，內容位元組／語意摘要與操作前相同，dirty 仍為 true | ui／work |
| R-M04-02 | 邊界 | 在切換專案提示選取消；連按兩次取消 | 專案根不變，B 沒有載入，不重複送出請求 | ui |
| R-M04-02 | 無效輸入 | 取消後馬上送出 B 的遲到載入結果 | 遲到結果被丟棄，A 不變 | ui |
| R-M04-02 | 失敗 | 取消當下 host 正在忙（Busy） | 仍留在 A，不因錯誤改成離開 | ui／command |
| R-M04-03 | 正常 | dirty 的 A，保存被注入失敗，在切換提示選保存 | 不切換；A 的修改與 dirty 保留；目前專案仍是 A；錯誤訊息持續可見 | ui／command |
| R-M04-03 | 邊界 | 關閉與退出入口各做一次保存失敗 | 三個入口結果一致：都不離開 | ui |
| R-M04-03 | 無效輸入 | 保存目標路徑不合法（例如超出 scene/） | 回傳型別化錯誤，不離開，dirty 保留 | host／ui |
| R-M04-03 | 失敗 | 保存失敗後使用者再選保存並成功 | 第二次成功後才離開；失敗那次不得已清掉 dirty | ui |
| R-M04-04 | 正常 | dirty 的 A 已有一份復原快照，在切換提示選不保存 | 切換成功，A 本次修改被捨棄；復原快照檔案與索引不變 | ui／work |
| R-M04-04 | 邊界 | 沒有任何快照時選不保存；快照正在寫入時選不保存 | 前者只捨棄修改；後者不刪除、不截斷快照 | work |
| R-M04-04 | 無效輸入 | 不保存後送入舊 session 的保存 ACK | ACK 被拒，正式基準不變 | work |
| R-M04-04 | 失敗 | 捨棄過程中專案 B 開啟失敗 | 不得順便清快照；A 的狀態依實際結果如實回報 | ui／command |
| R-M04-05 | 正常 | revision R 保存成功並以 (R, digest(R)) ACK | 正式基準 = (R, digest)；dirty=false | work |
| R-M04-05 | 邊界 | 保存中編輯到 R+1，之後才收到 R 的 ACK | 正式基準 = R；R+1 仍為 dirty（既有 ex09） | work |
| R-M04-05 | 無效輸入 | ACK 的 digest 與 revision 不符；ACK 指向未來或更舊的 revision | 回傳 RevisionConflict，狀態完全不變 | work |
| R-M04-05 | 失敗 | 保存寫入失敗 | 不送 ACK；正式基準不變；UI 不清 dirty | command／ui |
| R-M04-06 | 正常 | 正式保存成功 | 快照基準不變 | work |
| R-M04-06 | 邊界 | 正式與快照基準一開始指向同一 revision，之後只 ACK 正式 | 只有正式基準前進 | work |
| R-M04-06 | 無效輸入 | 快照 ACK 帶正式 revision 的 digest | 正式基準不變 | work |
| R-M04-06 | 失敗 | 正式保存失敗 | 兩個基準都不變 | work |
| R-M04-07 | 正常 | 編輯一次 → 保存成功 | 先出現修改標記，保存後消失；文件名與位置正確 | ui |
| R-M04-07 | 邊界 | 開啟後未編輯；編輯後再改回原值 | 未編輯時沒有標記；改回原值是否清標記屬 R-M04-14，只記錄觀察 | ui |
| R-M04-07 | 無效輸入 | 沒綁定專案時嘗試保存 | 標記保留，顯示需要綁定專案 | ui |
| R-M04-07 | 失敗 | 保存失敗 | 標記保留，錯誤可見 | ui |
| R-M04-08 | 正常 | A、B 兩專案有相同相對檔名；編輯 A 並保存 | B 的檔案位元組與 UI 狀態不變 | command／ui |
| R-M04-08 | 邊界 | 保存 A 期間切換到 B，A 的保存回應遲到 | 回應不得更新 B 的 dirty／狀態列 | ui |
| R-M04-08 | 無效輸入 | 計畫的 document_uuid 或 session_uuid 屬於另一文件 | InvalidInput 或拒絕，狀態不變（既有 ex04） | work |
| R-M04-08 | 失敗 | B 開啟失敗 | A 的已保存內容不受影響 | command |

## 5. 開發段（RED）

- 前置：兩張交付卡目前都是 BLOCKED_PENDING_APPROVED_ENVELOPE_AND_VALID_RED，卡上 `protected_files` 寫明「all product source/tests until exact envelope approved」。exact envelope 與 Skeleton 獲批准之前，不得新增產品測試；下面的位置只是候選。
- 放置位置（候選，以批准的 envelope 為準）：
  - work 層（R-M04-05、06、08 的無效輸入，及 R-M04-04 的基準部分）：`APP/crates/sgenaxis-work/tests/phase1_document_history.rs` 追加，或另開同 crate 的新測試檔；fixture 沿用檔內「plain values、不 stub」的方式。
  - command 層（R-M04-03、05 的失敗、R-M04-08）：`APP/src-tauri/tests/` 新檔，仿照 `project_document_commands.rs` 的 `Fs` 故障注入假檔案系統。
  - ui 層（R-M04-01～04、07、08）：`APP/ui/<新檔>.test.cjs`，仿照 `project-document-ui.test.cjs` 以控制器區段載入。目前 `confirmLeaveSceneIfDirty` 不在可抽出的區段內，需要先批准 Skeleton 才能測。
- 先跑紅（在 `APP/` 執行）：
  - `cargo test -p sgenaxis-work --test phase1_document_history`
  - `cargo test -p <envelope 指定 crate> --test <envelope 指定檔名>`（卡上 tdd.command 寫明「no guessed cargo target」，不得自行猜）
  - `node --test ui/<新檔>.test.cjs`
- 有效 RED 的失敗關鍵字：Rust 要先編譯成功，再出現 `panicked at` 或 `assertion \`left == right\` failed`，且失敗點是目標行為的斷言；Node 要出現 `not ok` 或 `AssertionError`。出現 `error[E0`（編譯錯誤）、fixture 讀不到、環境錯誤，都不算 RED（卡上 tdd.valid_red）。既有測試原本就 GREEN，或歷史 RED log，都不算這次的 RED。
- 禁止事項：
  - 不改規格、BDD、交付卡、決策卡。
  - 不把 R-M04-09～22 寫成斷言（包括「舊檔各階段不變」「一次 Undo 完整還原」「Redo 存在」）。
  - 不弱化斷言：例如不得把「完整回復」縮成「部分欄位相同」，也不得把 BDD-07 的「不離開」改成只檢查 toast。
  - 不宣稱關閉／切換有跨文件原子交易（`#F05` 邊界）。
  - 不新增 Port、owner、timer 或 provider 語意。

## 6. 驗證段

> 執行者不可以是寫這段程式的代理。

- 重跑指令（在 `APP/` 執行）：
  - `cargo test -p sgenaxis-work --test phase1_document_history`
  - `cargo test -p <envelope 指定 crate> --test <envelope 指定檔名>`（command 層新檔）
  - `node --test ui/project-document-ui.test.cjs`（相鄰回歸）
  - `node --test ui/<新檔>.test.cjs`
- 介面實測步驟（Windows 11 x64 免安裝版；做不到就記 NOT RUN，不得以元件測試代替）：
  1. 綁定專案 A，編輯場景，確認文件列出現修改標記（R-M04-07）。
  2. 切換到專案 B → 出現三選對話框；選取消，確認仍在 A 且內容不變（R-M04-01、02）。
  3. 以批准的故障注入 seam 讓保存失敗，選保存 → 確認沒有切換、修改標記仍在、錯誤持續可見（R-M04-03）；沒有批准的 seam 時，此步記 NOT RUN。
  4. 選不保存 → 切換到 B；檢查 `%LOCALAPPDATA%\EuSlot\Recovery\<ProjectID>\<SessionID>\` 內的快照在操作前後相同（R-M04-04）。
  5. 關閉文件與退出程式各重複一次步驟 2～3（R-M04-01）。
  6. A、B 相同相對檔名：保存 A 後比對 B 檔案的雜湊（R-M04-08）。
  - 每一步都要截圖；步驟 2～4 另外錄影。
- 證據：`reports/dispatch-pd/PD-P1-F05-DELIVERY-01-evidence/`（F10 待決策解除後用 `reports/dispatch-pd/PD-P1-F10-DELIVERY-01-evidence/`）。每條規則一筆，欄位為：規則／指令／Exit code／輸出末段／介面證據（截圖或錄影檔名）／判定。另外記錄 source SHA、fixture、未跑的層級。
- 直接判 TDD_FAIL 的情況：
  - 任一重跑指令 exit code 不是 0，或有測試被 `#[ignore]`、`skip`、`todo` 跳過。
  - 斷言比 §4 預期弱，或改了規格、BDD、交付卡。
  - 把待決策規則（R-M04-09～22）寫成通過斷言或拿來宣稱 PASS。
  - 有 UI 的規則（R-M04-01～04、07、08）缺介面證據，卻判 PASS。
  - 把編譯／環境失敗當成 RED，或拿歷史 S1 log 當這次的證據。
  - 驗證者與實作者是同一個代理。
  - 以靜態或元件結果冒充原生 UI 或整體完成。

## 7. 已知衝突

| 衝突 | 規格出處 | 實作出處 | 影響規則 ID | 處理 |
|---|---|---|---|---|
| 目前無 | — | — | — | — |
