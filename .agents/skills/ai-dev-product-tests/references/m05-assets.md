# M05 素材：測試參考

> 規格根目錄簡寫：`SPEC` = `docs/requirements-confirmation/phase1-spec/`；`APP` = `apps/sgenaxis-desktop/`。
> 讀取基準：worktree `claude/skills-index-structure-f8398d`（HEAD `ef4896fa`）。`cargo test -p sgenaxis-work --test phase1_asset_roots --locked` 唯讀重跑：41 passed / 0 failed（2026-11-22）。

## 1. 範圍與來源
| 功能 ID | 規格連結 | 交付卡 | BDD 場景 |
|---|---|---|---|
| F06 素材管理與引用 | `SPEC/index.html`「F06 素材管理與引用」段（M05，建議採用，局部確認）；需求 REQ-16、REQ-18；不變條件 INV04；X05；決策表 D03、D08 | `SPEC/tasks/PD-P1-F06-DELIVERY-01.json`（BLOCKED_PENDING_APPROVED_ENVELOPE_AND_VALID_RED；依賴 M05-PREP、G01、G03、G04） | `SPEC/phase1.feature` `@BDD-31 @M05 @REQ-16`「快照仍引用素材」 |
| F06（M05-S1 切片） | `SPEC/tasks/M05/planning/pure-policy-design/module-spec.json`（純保留判定設計）；`SPEC/tasks/M05/s1/adoption.json`（Owner 採納 M05-R1～R4） | `SPEC/tasks/PD-P1-M05-PREP-01.json`；S1 驗收 `SPEC/tasks/M05/s1/green/acceptance/review.json`（IMPLEMENTATION_ACCEPTANCE_PASS_SLICE_ONLY） | `SPEC/tasks/M05/s1/module.feature`（3 個 Skeleton 場景：快照根缺失、完整且無引用、共用素材仍被引用） |
| F06 追溯 | `SPEC/tasks/F06/feature-trace-preparation/module-spec.json`（F06-TRACE-01～05） | 同上 | BDD-31；AC06 為提案，無核准 BDD |

## 2. 業務規則
### 已核准
| 規則 ID | 規則 | 規格出處 | 核准依據 |
|---|---|---|---|
| R-M05-01 | Undo 不得刪除共用素材（仍被其他文件／Undo／Redo 引用者必須保留）。 | `SPEC/index.html` REQ-16（已確認）；F06「資料影響」中「確認：共用素材不能被Undo誤刪」 | 正式核准 |
| R-M05-02 | 被保留中（含未處理）的復原快照引用的素材必須保留，即使活文件已撤回引用。 | `SPEC/index.html` REQ-18（已確認）；`SPEC/phase1.feature` BDD-31 結果句；S1 `module-spec.json` cases M05-ROOT-R05/R06 | 正式核准 |
| R-M05-03 | 五類引用根（LiveDocuments、UndoHistory、RedoHistory、RecoverySnapshots、InFlightTransactions）必須全部明確出現且為 Complete；缺任一類或 Unknown 一律 Retain(RootsIncomplete)，不得視為「完整且空」。 | `pure-policy-design/module-spec.json` contracts.order[2]；`adoption.json` M05-R1/R2；`s1/module.feature` Rule 1；`SPEC/index.html` X05「引用根不明時不清理」、D03「未知引用視為仍使用」 | 模組採納：M05-R1、R2（`SPEC/tasks/M05/s1/adoption.json`） |
| R-M05-04 | 根的 revision 與預期 revision 不符（或預期 revision 缺漏）時 Retain(StaleRoots)。 | `module-spec.json` contracts.order[2]；`s1/green/acceptance/review.json` contracts_reviewed[0]「missing/unknown/absent expected revision retains」 | 模組採納：M05-R1～R4（pure-policy-design）（`SPEC/tasks/M05/s1/adoption.json`） |
| R-M05-05 | 任一根中 asset_id＋digest 完全相符的引用即 Retain(Referenced{kind, owner_id})；LiveDocuments 涵蓋專案內所有文件，不只目前文件；其他素材的引用不影響候選。 | `module-spec.json` contracts.order[3]、contracts.identity；M05-R1 | 模組採納：M05-R1（`SPEC/tasks/M05/s1/adoption.json`） |
| R-M05-06 | 同 asset_id 但 digest 不同時 Retain(IdentityConflict)，不猜來源。 | `module-spec.json` contracts.order[3]；M05-R2 | 模組採納：M05-R2（`SPEC/tasks/M05/s1/adoption.json`） |
| R-M05-07 | 候選只有在 owned_by_operation 等於本次 operation_id 時才可能可清理；否則 Retain(NotOwnedByOperation)。 | `module-spec.json` contracts.order[4]；REQ-16「僅移除本次新增」 | 模組採納：M05-R1～R4（pure-policy-design）（`SPEC/tasks/M05/s1/adoption.json`） |
| R-M05-08 | 保留理由去重並依固定順序排序（根類順序→理由種類→owner_id 位元組序），與輸入順序無關。 | `module-spec.json` contracts.output；M05-R2 | 模組採納：M05-R2（`SPEC/tasks/M05/s1/adoption.json`） |
| R-M05-09 | 輸入有界驗證：識別字串 1～256 UTF-8 bytes 且無 NUL；digest 為 `sha256:`＋64 小寫 hex；每類引用 ≤4096、總數 ≤16384；重複根類或重複預期 revision 皆回 InvalidInput；超限不截斷；判定不改動輸入。 | `module-spec.json` limits_proposed_not_confirmed＋contracts.order[0]、failure；M05-R3（採納「Bounded inputs」） | 模組採納：M05-R3（`SPEC/tasks/M05/s1/adoption.json`） |
| R-M05-10 | EligibleForCleanup 只帶 asset_id＋content_digest，不含路徑或刪除權；任何結果都不得直接觸發實體刪除。 | `module-spec.json` architecture.transaction、contracts.output；M05-R4；`s1/module.feature` 場景 2「no file is deleted」 | 模組採納：M05-R4（`SPEC/tasks/M05/s1/adoption.json`） |
| R-M05-11 | RootSnapshot 的 project_id／session_id 與 EvaluationContext 不符時回 InvalidInput。 | `module-spec.json` contracts.identity | 模組採納：M05-R1～R4（pure-policy-design）（`SPEC/tasks/M05/s1/adoption.json`） |

### 待決策
| 規則 ID | 卡在 | 目前選項 | 開發期處理 |
|---|---|---|---|
| R-M05-12 | G01（Asset ID 與版本格式）、G03 | 建議：穩定 Asset ID 指向不可變內容版本；複製來源、不偷偷轉換；大型素材按內容共用快取（F06「資料影響」建議部分） | 不寫斷言；只可在 planning 記錄候選 fixture |
| R-M05-13 | G04（素材格式矩陣） | D08：首批 PNG/JPEG＋受限靜態 SVG；動圖／影片只顯示類型與未支援提示；拒 SVG 腳本與任意外部資源 | 不寫格式白名單斷言；文件參考四類媒體需求不得縮減 |
| R-M05-14 | G04 | X05：0 byte／超限／損毀／未知媒體的處理；AC06（提案）「未知格式明示」；容量上限未批准 | 待矩陣批准後才定輸入與預期 |
| R-M05-15 | G04 | F06「失敗處理」：讀取／解碼／轉換失敗保留元件與引用並說明；播放受限提供手動入口，不假稱素材遺失 | 屬建議採用段落；不寫成驗收斷言 |
| R-M05-16 | G01、G02 | AC06（提案）：重命名不斷引用；替換影響先預覽；共用素材不就地替換，建立新內容版本（`SPEC/index.html` F08 邊界句） | 不建 Skeleton；只列 PLAN-F06-03 對照 |
| R-M05-17 | G03 | AC06（提案）：跨版本快照仍可讀舊素材 | 不寫斷言；依 F06-TRACE-04 |
| R-M05-18 | G02、G03 | REQ-16 已確認「僅移除本次新增且已無引用的素材」，但 INV04 引用根集合與實體清理交易「待G02/G03批准」；D03 清理時機只在使用者明確清理或批准的維護流程 | 只可測「判定」（R-M05-03～10），不可測或實作實體刪除 |
| R-M05-19 | G01～G04 | BDD-31 端到端（合併新增素材→成功快照→Undo 合併→清理評估）；`SPEC/fixtures.json` id 31 fixture「pending G01-G04」 | 不以 S1 純策略測試冒充 BDD-31 綁定（F06-TRACE-01 已標缺口） |
| R-M05-20 | G01（交換格式） | UX31～34「素材引用納入交換與復原已確認」；BIN 含引用素材；schema 未定 | 需求已確認但格式未定；不寫序列化斷言 |
| R-M05-21 | G04、UI schema 未批准 | F06 狀態：可用／缺失／未支援／待驗證／替換預覽／使用中／候選回收；素材面板名稱／類型／縮圖／容量／使用位置／缺失 | `docs/ui-design/ui-spec.json` 目前無素材面板；不寫 UI 斷言 |

## 3. 已有測試對照
檔案：`APP/crates/sgenaxis-work/tests/phase1_asset_roots.rs`（41 個，全部 PASS）；相鄰：`APP/crates/sgenaxis-work/tests/phase1_document_history.rs`。

| 規則 ID | 測試檔::函式 | 已涵蓋類別 | 缺口 |
|---|---|---|---|
| R-M05-01 | phase1_asset_roots::m05_other_document_reference_retains、m05_undo_history_retains、m05_redo_history_retains；phase1_document_history::m04_prepare_carries_asset_versions_needed_by_both_sides、m04_missing_asset_retention_plan_rejects_before_history_mutation | 正常、失敗（M04 側） | 邊界（同一素材同時被 Undo 與 Redo 持有）、無效輸入（Undo 根 Unknown 時 Undo 後評估）在 M05 側沒有以「Undo 後」語意命名的案例；無 host/command 層 |
| R-M05-02 | m05_retained_snapshot_retains、m05_unprocessed_snapshot_retains、m05_unknown_snapshot_retains、m05_missing_provider_is_not_complete_empty | 正常、失敗、無效輸入 | 邊界（活文件已撤回、只剩快照引用的組合）；BDD-31 未綁定 |
| R-M05-03 | m05_unknown_live_documents_retains、m05_unknown_undo_retains、m05_unknown_redo_retains、m05_unknown_snapshot_retains、m05_unknown_transaction_retains、m05_missing_provider_is_not_complete_empty、m05_empty_complete_roots_yield_identity_only_eligibility | 正常、失敗、無效輸入 | 邊界：observations 為空（0 類）、多類同時 Unknown 的理由合併順序 |
| R-M05-04 | m05_stale_root_revision_retains | 失敗 | 「預期 revision 缺漏某類」與「預期 revision 多出不存在的根」未測；邊界與無效輸入缺 |
| R-M05-05 | root_retains!(7 個：live/other/undo/redo/retained snapshot/unprocessed snapshot/inflight)、m05_other_asset_does_not_pin_candidate | 正常、邊界 | 無效輸入（引用的 owner_id 空白、引用 digest 格式錯）未測 |
| R-M05-06 | m05_same_asset_id_conflicting_digest_retains | 正常 | 衝突出現在非 LiveDocuments 根、衝突與正常引用並存時的理由組合；邊界缺 |
| R-M05-07 | m05_unowned_candidate_retains、m05_other_operation_candidate_retains | 正常、失敗 | 邊界（operation_id 大小寫或前後空白差異）、無效輸入（owned_by_operation 為空字串）未測 |
| R-M05-08 | m05_reasons_sorted_by_root_then_owner_and_deduplicated | 正常、邊界（輸入反序） | 不同理由種類混合（Referenced＋StaleRoots＋NotOwnedByOperation＋IdentityConflict）的排序未測 |
| R-M05-09 | invalid!(11 個)、valid_id!(3 個)、count_boundary!(4095/4096/4097)、total_boundary!(16383/16384/16385) | 正常、邊界、無效輸入 | 未測：operation_id／owner_id／revision 空白、revision 257 bytes、revision 含 NUL、引用中 digest 非法；失敗類（拒絕後輸入不變）只在 invalid! 內檢查，計數超限案例未檢查輸入不變 |
| R-M05-10 | m05_empty_complete_roots_yield_identity_only_eligibility、m05_other_asset_does_not_pin_candidate、valid_id! | 正常 | 型別層面保證；無 host/command 層確認「沒有任何刪除入口接受 Eligible」 |
| R-M05-11 | invalid!(m05_project_identity_mismatch)、invalid!(m05_session_identity_mismatch) | 無效輸入 | 正常（相符才通過已由 fixture 隱含）、邊界（大小寫差異）未明測 |

## 4. 測試矩陣
| 規則 ID | 類別 | 輸入 | 預期 | 層 |
|---|---|---|---|---|
| R-M05-01 | 正常 | 候選被 UndoHistory 的 owner `history-undo` 引用 | Retain[Referenced{UndoHistory, history-undo}] | work |
| R-M05-01 | 邊界 | 同一素材同時在 UndoHistory 與 RedoHistory | Retain 兩條理由，Undo 在前 | work |
| R-M05-01 | 無效輸入 | UndoHistory 根 completeness=Unknown | Retain[RootsIncomplete{UndoHistory}]，非 Eligible | work |
| R-M05-01 | 失敗 | M04 operation 的 required_asset_versions 被清空 | M04 拒絕且歷史不變（既有 m04 測試） | work |
| R-M05-02 | 正常 | 只有 RecoverySnapshots 引用候選 | Retain[Referenced{RecoverySnapshots, owner}] | work |
| R-M05-02 | 邊界 | LiveDocuments 無引用、RecoverySnapshots 引用 `snapshot-unprocessed` | 仍 Retain | work |
| R-M05-02 | 無效輸入 | 移除 RecoverySnapshots 觀測 | Retain[RootsIncomplete{RecoverySnapshots}] | work |
| R-M05-02 | 失敗 | RecoverySnapshots=Unknown | Retain[RootsIncomplete{RecoverySnapshots}] | work |
| R-M05-03 | 正常 | 五類皆 Complete 且無引用、候選屬本 operation | EligibleForCleanup{asset_id, digest} | work |
| R-M05-03 | 邊界 | observations 為空 vec | Retain，五條 RootsIncomplete 依固定根序 | work |
| R-M05-03 | 無效輸入 | 缺任一類觀測（逐類 5 案） | Retain[RootsIncomplete{該類}] | work |
| R-M05-03 | 失敗 | 兩類同時 Unknown（Live＋Transaction） | Retain 兩條 RootsIncomplete，Live 在前 | work |
| R-M05-04 | 正常 | 五類 revision 全等於預期 | 不出現 StaleRoots | work |
| R-M05-04 | 邊界 | expected_root_revisions 缺 UndoHistory 一筆 | Retain（含 UndoHistory 不可確認之理由），非 Eligible | work |
| R-M05-04 | 無效輸入 | 預期 revision 重複同一類 | Err(InvalidInput) | work |
| R-M05-04 | 失敗 | UndoHistory revision=`revision-2`，預期 `revision-1` | Retain[StaleRoots{UndoHistory}] | work |
| R-M05-05 | 正常 | LiveDocuments 引用 owner `document-other` | Retain[Referenced{LiveDocuments, document-other}] | work |
| R-M05-05 | 邊界 | 引用 asset_id=`other-asset` | Eligible（不受他素材影響） | work |
| R-M05-05 | 無效輸入 | 引用的 owner_id 為空字串 | Err(InvalidInput{field 非空}) | work |
| R-M05-05 | 失敗 | 引用 content_digest=`bad` | Err(InvalidInput)，不得 Eligible | work |
| R-M05-06 | 正常 | Live 中同 asset_id、digest `b…` | Retain[IdentityConflict{asset-1}] | work |
| R-M05-06 | 邊界 | 衝突出現在 RecoverySnapshots | Retain[IdentityConflict] | work |
| R-M05-06 | 無效輸入 | 衝突引用的 digest 為大寫 hex | Err(InvalidInput) | work |
| R-M05-06 | 失敗 | 同根同時有正確引用與衝突引用 | Retain，兩種理由皆列且順序穩定 | work |
| R-M05-07 | 正常 | owned_by_operation=Some(operation-1)＝context | 可 Eligible | work |
| R-M05-07 | 邊界 | owned_by_operation=Some("Operation-1")（大小寫不同） | Retain[NotOwnedByOperation] | work |
| R-M05-07 | 無效輸入 | owned_by_operation=Some("") | Err(InvalidInput) | work |
| R-M05-07 | 失敗 | owned_by_operation=None | Retain[NotOwnedByOperation] | work |
| R-M05-08 | 正常 | Live 引用 z-document、a-document | 依 owner 位元組序 a→z | work |
| R-M05-08 | 邊界 | observations 反序輸入 | 結果與正序完全相同 | work |
| R-M05-08 | 無效輸入 | 同一引用重複三次 | 只出現一條理由 | work |
| R-M05-08 | 失敗 | 混合 Referenced＋StaleRoots＋NotOwnedByOperation＋IdentityConflict | 依根序再依理由種類固定排序，兩次呼叫結果相同 | work |
| R-M05-09 | 正常 | asset_id 1 byte、256 bytes、128 個 `é`（256 bytes） | Eligible | work |
| R-M05-09 | 邊界 | 單類引用 4095／4096／4097；總數 16383／16384／16385 | 前兩者 Eligible，第三者 InvalidInput | work |
| R-M05-09 | 無效輸入 | asset_id 空、257 bytes、含 NUL；digest `bad`／大寫；revision 空或 257 bytes；operation_id 空 | Err(InvalidInput{field, reason 皆非空}) | work |
| R-M05-09 | 失敗 | 任一 InvalidInput 案例 | 呼叫前後 candidate/roots/context 完全相等 | work |
| R-M05-10 | 正常 | 五類 Complete 無引用、屬本 operation | Eligible 只含 asset_id＋content_digest | work |
| R-M05-10 | 邊界 | 同上但候選 asset_id 為 256 bytes | Eligible 原樣帶回 256 bytes，不截斷 | work |
| R-M05-10 | 無效輸入 | 任一根 Unknown | 不得回 Eligible | work |
| R-M05-10 | 失敗 | 呼叫 evaluate 後檢查專案暫存目錄 | 無任何檔案被刪除；host/command 無接受 Eligible 的刪除入口（待 G02/G03 後才補 host 案） | work |
| R-M05-11 | 正常 | project/session 相符 | 正常判定 | work |
| R-M05-11 | 邊界 | project_id 只差大小寫（`Project-1`） | Err(InvalidInput)（位元組相等才相符） | work |
| R-M05-11 | 無效輸入 | RootSnapshot.project_id=`other-project` | Err(InvalidInput) | work |
| R-M05-11 | 失敗 | RootSnapshot.session_id=`other-session` | Err(InvalidInput)，輸入不變 | work |

> 邊界列「大小寫不同」「observations 為空」「預期 revision 缺漏」的預期是依 contracts 的「equals／Exactly five／absent expected revision retains」推得，規格未逐例列出；若實際行為不同，回報規格不符，不得改預期遷就實作。

## 5. 開發段（RED）
- 放置位置：既有 `APP/crates/sgenaxis-work/tests/phase1_asset_roots.rs` 已被 S1 鎖定（`s1/green/authorization.json`「public_contracts_tests_dependencies: Locked」），不可直接修改。缺口案例建議新增 `APP/crates/sgenaxis-work/tests/phase1_asset_roots_gaps.rs`，需先取得 Owner 對此檔的 envelope 批准（交付卡 allowed_files 目前只到 planning/evidence）。
- 先跑紅的指令：`cargo test -p sgenaxis-work --test phase1_asset_roots_gaps --locked`（在 `apps/sgenaxis-desktop` 下）。
- 預期失敗關鍵字：`assertion \`left == right\` failed` 或 `expected typed malformed-input rejection`；有效 RED 只能是可編譯、fixture 成功、斷言失敗。`error[E…]` 編譯錯誤、`could not compile`、fixture panic 都不是 RED。S1 已 GREEN，新案例若第一次就 PASS，記為「既有行為已涵蓋」，不是 RED，也不得刪掉。
- 回歸：`cargo test -p sgenaxis-work --locked`（S1 驗收基準 222 PASS）與 `cargo test -p sgenaxis-host --lib --locked`。
- 禁止事項：不改規格與 S1 已採納型別／列舉／函式簽名；不把第 2 段待決策（R-M05-12～21）寫成斷言；不弱化或刪除既有 41 個斷言；不新增 Port、crate、實體刪除、catalog 持久化；不以 S1 純策略測試宣稱 BDD-31 完成。

## 6. 驗證段
> 執行者不可以是寫這段程式的代理。
- 重跑指令（於 `apps/sgenaxis-desktop`）：
  - `cargo test -p sgenaxis-work --test phase1_asset_roots --locked`（預期 41 passed）
  - `cargo test -p sgenaxis-work --test phase1_asset_roots_gaps --locked`（批准新增後）
  - `cargo test -p sgenaxis-work --test phase1_document_history --locked`（R-M05-01 相鄰）
  - `cargo test -p sgenaxis-work --locked`、`cargo test -p sgenaxis-host --lib --locked`（回歸）
- 介面實測步驟：目前無素材介面（`docs/ui-design/ui-spec.json` 無素材面板；`APP/ui/app.js` 僅序列化 `assetRefs` 字串）。素材面板屬 R-M05-21 待決策，本輪不做介面實測，證據欄標「N/A：無介面」。
- 證據：放 `reports/dispatch-pd/PD-P1-F06-DELIVERY-01-evidence/`；每條規則一筆：規則／指令／Exit code／輸出末段（含 `test result:` 行）／介面證據／判定。另記 HEAD SHA 與測試檔 hash。
- 直接判 TDD_FAIL 的情況：
  - 任一既有 41 個測試失敗、被刪、被 `#[ignore]` 或斷言被放寬。
  - 任一根 Unknown／缺失／stale 時回 EligibleForCleanup。
  - EligibleForCleanup 帶出路徑或觸發任何實體刪除。
  - InvalidInput 後輸入被改動，或超限被截斷而非拒絕。
  - 待決策規則被寫成可驗收斷言，或以 S1 測試冒充 BDD-31／AC06 通過。
  - 驗證者與實作者為同一代理，或證據缺 Exit code／輸出末段。

## 7. 已知衝突

| 衝突 | 規格出處 | 實作出處 | 影響規則 ID | 處理 |
|---|---|---|---|---|
| 目前無 | — | — | — | — |
