# M07 復原與歷史入口：測試參考

> 規格根目錄簡稱 `SPEC` = `docs/requirements-confirmation/phase1-spec/`；產品根目錄簡稱 `APP` = `apps/sgenaxis-desktop/`。
> 規格文字只摘一句，細節以連結為準。G01／G02／G03 仍為 `PENDING_ARCHITECTURE_REVIEW`（`SPEC/tasks/PD-P1-G0x-DEC-01.json` 的 `status`）。

## 1. 範圍與來源

| 功能 ID | 規格連結 | 交付卡 | BDD 場景 |
|---|---|---|---|
| F11 定期復原快照 | `SPEC/index.html` 的「F11 定期復原快照」段（流程、資料影響、狀態、失敗處理、邊界、AC11、UI schema）；需求基線 REQ-17～21；不變條件 INV05；測試補充組 X07；測試層級 L0（計時 59/60/61） | `SPEC/tasks/PD-P1-F11-DELIVERY-01.json`（status `BLOCKED_PENDING_APPROVED_ENVELOPE_AND_VALID_RED`，依賴 M07-PREP、G01、G03） | `SPEC/phase1.feature` 的 BDD-22、23、24、25、26、27、30 |
| F12 歷史入口、復原與保留 | `SPEC/index.html` 的「F12 歷史入口、復原與保留」段（AC12、UI schema）；REQ-21、REQ-22；建議預設 D01／D02／D03／D12；X08 | `SPEC/tasks/PD-P1-F12-DELIVERY-01.json`（同上狀態與依賴） | `SPEC/phase1.feature` 的 BDD-27、28、29（BDD-32 屬 M08） |

補充來源：
- 模組準備卡 `SPEC/tasks/PD-P1-M07-PREP-01.json`；目前狀態 `SPEC/tasks/M07/planning/current-state.json`（S1 只做到純政策；OS 計時器、實際擷取、素材釘選、payload／索引持久化、復原 UI 都還沒做）。
- 已採納的 S1 純政策：`SPEC/tasks/M07/s1/adoption.json`（採納 M07-R1～R4）→ 設計 `SPEC/tasks/M07/planning/pure-policy-design/module-spec.json`；驗收 `SPEC/tasks/M07/s1/green/acceptance/`（`PASS_SLICE_ONLY`，`work-full.txt` 顯示 phase1_recovery_policy 35 passed）。
- 待 Owner 決定的 M07 精確設計：`SPEC/tasks/M07/planning/snapshot-exact-design/review-request.json`（M07-D1～D7 都是 `PENDING_OWNER`）；跨閘門建議 `SPEC/tasks/M07/planning/decision-request.json`（D1、D2、D4、D5、D6 都是 `PROPOSED_NOT_APPROVED`）。
- 產品原始碼：`APP/crates/sgenaxis-work/src/recovery_state.rs`（純函式 `transition_recovery`）。
- 測試 fixture：`SPEC/fixtures.json`（fixture:22～30；目前 `PLANNED_NOT_EXECUTED`）。

## 2. 業務規則

### 已核准

已核准包含兩類：需求基線標「已確認」的條文，以及已採納的 S1 純政策 M07-R1～R4。純政策的範圍是由 HOST 提供已經過時間、指紋與完成回條，政策只產生新狀態與動作，不做 IO。

| 規則 ID | 規則 | 規格出處 | 核准依據 |
|---|---|---|---|
| R-M07-01 | 每 60 秒檢查一次：距上次檢查不到 60000 ms 回 `NotDue`，滿 60000 ms 以上才可進入判斷；時間大跳躍只檢查一次，不補發漏掉的週期 | REQ-19；`index.html` 測試層級 L0「計時59/60/61邊界」；X07；S1 adoption → pure-policy-design `precise_transition_proposal` | 正式核准 |
| R-M07-02 | 內容和上次成功快照相同時不新增快照（`SkipUnchanged`） | REQ-19；BDD-22；AC11「無變更零新快照」 | 正式核准 |
| R-M07-03 | 沒有成功快照時，首次未保存內容必須納入（`RequestCapture`）。本條只管內容；素材部分見 R-M07-13 | REQ-19；BDD-23 | 正式核准 |
| R-M07-04 | 快照寫入不重疊：有寫入進行中或已請求擷取時，檢查回 `WaitInFlight`，不會再請求一次；已有進行中嘗試時不得再登記第二個 | REQ-20；BDD-25「不重疊啟動」；F11 邊界 | 正式核准 |
| R-M07-05 | 清空、匯入／合併、Undo 進行中不擷取中間狀態，延後到完成或完整回復後再檢查，且延後不消耗檢查期限 | REQ-20；BDD-26；`index.html` 跨功能一致性「Undo vs 快照」 | 正式核准 |
| R-M07-06 | 寫入期間的新變更留到下一輪：版本 R 成功只把基準推進到 R 的指紋，R+1 在下一次到期檢查時仍會被請求擷取 | REQ-20；BDD-24 | 正式核准 |
| R-M07-07 | 寫入失敗不更新基準、保留待保存狀態，下一輪重試 | REQ-20；BDD-25；F11 失敗處理 | 正式核准 |
| R-M07-08 | 以 ProjectID／SessionID 隔離：事件的 project 或 session 跟狀態不符就拒絕（`SessionMismatch`），狀態不變 | REQ-17；BDD-30；F11 資料影響 | 正式核准 |
| R-M07-09 | 工作階段關閉後，背景完成回報不得推進基準或寫錯文件（`IgnoreClosedCompletion`／`Closed`） | X07「session關閉時背景回報不得寫錯新文件」；S1 adoption | 正式核准 |
| R-M07-10 | 輸入不合法（ID 空白、超過 256 bytes、含 NUL；指紋不是小寫 `sha256:`+64 hex）、時間倒退、過期或不認得的 attempt、沒請求就開始：一律回明確錯誤，且呼叫端的輸入不被改動 | S1 adoption → pure-policy-design `public_boundary_proposed`、`precise_transition_proposal` | 模組採納：M07-R1～R4（`SPEC/tasks/M07/s1/adoption.json`） |
| R-M07-11 | 正式保存基準和快照基準互相獨立：正式保存成功不重設快照基準（只限基準層；「不刪既有快照」見 R-M07-17） | REQ-21；BDD-27 前半；INV05；F11 邊界「保存正式檔不改快照基準」 | 正式核准 |
| R-M07-12 | 復原狀態、最後成功時間、失敗原因持續可見；正式保存成功不得蓋掉快照失敗 | F11 UI schema 摘要；F11 狀態列舉；REQ-18「不假稱成功」 | 正式核准 |

### 待決策

| 規則 ID | 卡在 | 目前選項 | 開發期處理 |
|---|---|---|---|
| R-M07-13 | G03（另含 G01 schema） | 快照包含架構、UI 設計、互動設定、素材引用與未保存素材，且和素材完整性屬同一版本（REQ-18、F11 邊界）。選項是 M07-D2 自含 payload＋素材 bundle 搭配新的 RecoveryStoragePort（PENDING_OWNER） | 政策層只驗 `asset_manifest_digest` 的格式（R-M07-10），不寫「素材已納入」的斷言 |
| R-M07-14 | G03 | 先完成新快照再發布索引；索引前中斷時保留舊快照（REQ-18、AC11）。選項是 M07-D3 的 pin→objects→index→root-transfer→ACK 順序；G03 recommendation 是持久化完整後才發布 | `Published` 目前只是 HOST 給的受信回條，不能寫成持久化或中斷注入斷言 |
| R-M07-15 | G01＋G03 | 復原區放在 `%LOCALAPPDATA%\EuSlot\Recovery\<ProjectID>\<SessionID>\`，獨立於程式與原專案；多 session 實檔互不覆寫（REQ-17、BDD-30 檔案層）。穩定 ProjectID 的格式看 D1（G01） | 不建立實際目錄、不固定路徑格式；只保留政策層隔離（R-M07-08） |
| R-M07-16 | G03；D12 未採納 | 復原區不可寫時持續警告，並可選替代位置（REQ-18、F11 失敗處理）。D12 建議替代路徑綁本機使用者 | UI 測試可用注入狀態驗「不可寫警告」文字是否存在（R-M07-12）；替代位置的寫入流程不寫斷言 |
| R-M07-17 | G03 | 正式保存成功不立即清空既有快照；失敗保留既有快照與待保存狀態（REQ-21、BDD-27 後半、AC12「正式保存不抹快照」） | 快照儲存還不存在，不寫刪檔或保留斷言 |
| R-M07-18 | G03＋G01 | 歷史入口獨立標示復原版本，顯示專案名、快照時間、原始位置、素材完整性；以未保存狀態開啟，由人保存回原檔或另存；原磁碟離線也能另存（REQ-22、BDD-28、AC12）。選項是 M07-D5 預覽／確認後開為新的未保存文件 | 沒有歷史清單或讀取 schema，不建 UI 斷言 |
| R-M07-19 | G03 | 移除歷史紀錄不刪文件、快照或素材（REQ-22、BDD-29）。需求已確認，但歷史索引與儲存尚未批准 | 待索引與儲存批准後，才轉成「移除後檔案仍在」的實檔斷言 |
| R-M07-20 | G01＋G03 | 失效路徑保留並標原因，可重新定位、開啟可用的復原版本或移除紀錄（REQ-22、F12 狀態） | 不寫斷言 |
| R-M07-21 | G03 | 素材缺失時列明限制，不假稱完整恢復；保存失敗時保留快照與編輯內容（F12 失敗處理） | 不寫斷言 |
| R-M07-22 | G03＋D01／D02／D03／D12 待採納 | 保留期限、數量、容量與清理政策都未確認（REQ-21）。建議值：未處理快照不自動刪、已處理快照保留 30 天且至少 10 份、軟門檻 2 GiB、只在明確清理時清、歷史顯示 50 項（M07-D4、decision-request D6） | 不實作自動清理，不寫任何數值斷言 |
| R-M07-23 | G02＋G03 | 被保留快照引用的素材不可物理刪除（INV04、BDD-31 屬 M05、D03） | 屬 M05 交界，本模組不寫斷言 |
| R-M07-24 | G03＋M08 系統層 | 移動免安裝目錄不影響復原；強制終止後只能恢復已成功的快照（AC12、X08、F11 失敗處理） | 留給 L5 系統測試，現在不寫 |
| R-M07-25 | G02＋G03（D4） | 復原開啟後 Undo 歷史從空開始、只恢復內容（F12 邊界）；Undo 結果和成功快照相同就不新增（`index.html`「Undo vs 快照」）。M04 的 mutation 訊號怎麼接到 `mutation_in_progress` 也還沒定 | 政策層只驗布林延後（R-M07-05），不接 M04 的 mutation 訊號 |
| R-M07-26 | G03（M07-D1／D4） | 選取、滑鼠移動、播放進度不算內容變更（REQ-19）。指紋由 HOST 提供；穩定擷取與 SGA-RECOVERY-FP-v1 尚未採納 | 政策層把指紋當不透明值，不寫「選取不改指紋」的斷言 |

## 3. 已有測試對照

測試檔 `APP/crates/sgenaxis-work/tests/phase1_recovery_policy.rs`（以下簡稱 `rp`）；共 35 個 test，見 S1 驗收的 `work-full.txt`。

| 規則 ID | 測試檔::函式 | 已涵蓋類別 | 缺口 |
|---|---|---|---|
| R-M07-01 | `rp::m07_59000ms_is_not_due`、`m07_60000ms_requests_capture`、`m07_61000ms_requests_capture`（`due!` 巨集）、`m07_long_resume_requests_one_capture`、`m07_no_timer_backlog_after_large_jump`、`m07_max_elapsed_counter_uses_subtraction_without_wrap`、`m07_max_elapsed_due_counter_requests_capture` | 正常、邊界 | 59999 ms 沒測；沒有 HOST 實際時鐘接線測試；失敗類只靠 R-M07-10 的時間倒退 |
| R-M07-02 | `rp::m07_equal_content_skips_despite_elapsed_time` | 正常 | 邊界（相同內容但未到期時，應先回 `NotDue`）、連續兩輪都相同、略過後 `capture_requested` 仍為 false |
| R-M07-03 | `rp::m07_first_unsaved_content_requests_capture`；`m07_unknown_current_fingerprint_rejected` 間接涵蓋 | 正常、無效 | 首次內容遇到 mutation 時延後；首次快照失敗後重試（基準仍為 None） |
| R-M07-04 | `rp::m07_inflight_check_does_not_overlap`、`m07_pending_capture_check_does_not_request_twice` | 正常、邊界 | `AttemptAlreadyActive`（寫入進行中又 BeginAttempt）完全沒測 |
| R-M07-05 | `rp::m07_mutation_defers_without_consuming_deadline`、`m07_stable_same_time_check_after_defer_is_eligible` | 正常、邊界 | 寫入進行中加上 mutation 時哪個優先（目前程式回 `WaitInFlight`）；未到期又 mutation 時回 `NotDue` |
| R-M07-06 | `rp::m07_begin_records_actual_newer_captured_revision`、`m07_published_acknowledges_only_captured_fingerprint`、`m07_newer_edit_still_requests_capture_after_old_completion` | 正常、邊界 | 寫入中 R+1 的檢查與完成交錯；`captured_revision` 政策沒有檢查，規格也沒要求，不列斷言 |
| R-M07-07 | `rp::m07_failed_completion_keeps_previous_baseline`、`m07_next_due_check_retries_failed_capture` | 正常、失敗 | 連續多輪失敗；首次快照失敗 |
| R-M07-08 | `rp::m07_other_session_completion_rejected`、`m07_other_project_event_rejected` | 無效 | 兩個獨立 session 狀態並行、各自推進互不影響（BDD-30 政策層）；其他 session 的 Check 和 BeginAttempt；錯誤後狀態不變的斷言 |
| R-M07-09 | `rp::m07_close_clears_only_unstarted_capture_request`、`m07_closed_completion_cannot_advance_baseline` | 正常、失敗 | 關閉後 Check／BeginAttempt 回 `Closed` 沒測；關閉後 Failed 完成回報；重複 Close |
| R-M07-10 | `rp::m07_begin_requires_capture_request`、`m07_unknown_completion_is_stale`、`m07_mismatched_attempt_is_stale`、`m07_time_regression_rejected`（`exact_error!`）；`m07_unknown_current_fingerprint_rejected`、`m07_invalid_current_fingerprint_rejected`、`m07_invalid_saved_fingerprint_rejected`、`m07_empty_state_identity_rejected`、`m07_empty_attempt_id_rejected`、`m07_257_byte_attempt_id_rejected`、`m07_invalid_asset_digest_rejected`（`invalid!`）；`m07_256_byte_attempt_id_is_valid`、`fixture_has_distinct_current_baseline_and_capture_identities` | 邊界、無效、失敗 | event 端 ID 空白或含 NUL；BeginAttempt 的 `captured_fingerprint` 不合法；大寫 hex；state 內 inflight 不合法 |
| R-M07-11 | 無 | 無 | 全缺：沒有 HOST 或 M04 正式保存與 M07 狀態的接線測試 |
| R-M07-12 | 無 | 無 | 全缺：沒有復原狀態 UI 或 ui test |

## 4. 測試矩陣

層的意思：work＝`sgenaxis-work` 純政策；host＝`sgenaxis-host` 用例接線；ui＝`ui/*.test.cjs`。標「新」的是第 3 段的缺口。

| 規則 ID | 類別 | 輸入 | 預期 | 層 |
|---|---|---|---|---|
| R-M07-01 | 正常 | last=0、now=60000、指紋與基準不同 | `RequestCapture`，`last_check_ms`=60000 | work |
| R-M07-01 | 邊界 | now=59000、59999（新）、60000、61000；last=u64::MAX-60000 → now=u64::MAX | 59000／59999 回 `NotDue` 且狀態不變；其餘回 `RequestCapture` 且不溢位 | work |
| R-M07-01 | 無效輸入 | last=60000、now=59000 | `Err(TimeRegressed)`，輸入不變 | work |
| R-M07-01 | 失敗 | now 從 0 跳到 60000000，同一時間再檢查一次 | 第一次 `RequestCapture`，第二次 `NotDue`，沒有補發 | work |
| R-M07-02 | 正常 | 到期，指紋等於基準 | `SkipUnchanged`，`capture_requested`=false | work |
| R-M07-02 | 邊界 | 指紋等於基準且 now=59999（新）；連續兩次到期都相同（新） | 第一種回 `NotDue`；第二種兩次都 `SkipUnchanged` | work |
| R-M07-02 | 無效輸入 | 到期、`current_fingerprint`=None | `Err(InvalidInput{field:"current_fingerprint"})` | work |
| R-M07-02 | 失敗 | 到期、指紋＝"bad" | `Err(InvalidInput)`，狀態不變 | work |
| R-M07-03 | 正常 | 基準 None、到期、有指紋 | `RequestCapture` | work |
| R-M07-03 | 邊界 | 基準 None、到期、mutation=true（新） | `DeferMutation`，狀態不變 | work |
| R-M07-03 | 無效輸入 | 基準 None、指紋 None | `Err(InvalidInput)` | work |
| R-M07-03 | 失敗 | 基準 None，首次嘗試 Failed 後再到期（新） | `RetryPending` 後基準仍為 None，下一輪 `RequestCapture` | work |
| R-M07-04 | 正常 | inflight=Some、到期 | `WaitInFlight`，`last_check_ms` 更新，不請求擷取 | work |
| R-M07-04 | 邊界 | `capture_requested`=true、到期 | `WaitInFlight`，不重複請求 | work |
| R-M07-04 | 無效輸入 | inflight=Some 且 `capture_requested`=true，再 BeginAttempt（新） | `Err(AttemptAlreadyActive)`，狀態不變 | work |
| R-M07-04 | 失敗 | inflight 時再到期多次，然後 Complete Failed（新） | 每次都 `WaitInFlight`；完成後才回 `RetryPending` | work |
| R-M07-05 | 正常 | 到期、mutation=true | `DeferMutation`，`last_check_ms` 不變 | work |
| R-M07-05 | 邊界 | 延後後同一時間、mutation=false | `RequestCapture` | work |
| R-M07-05 | 無效輸入 | mutation=true、now 小於 last | `Err(TimeRegressed)` | work |
| R-M07-05 | 失敗 | inflight=Some 且 mutation=true（新） | `WaitInFlight`（依現行程式的優先序；規格只要求不擷取中間狀態，不得改成擷取） | work |
| R-M07-06 | 正常 | inflight R（指紋 b）、Published | 基準＝b、`BaselineAdvanced` | work |
| R-M07-06 | 邊界 | R Published 後到期，當前指紋 d（R+1） | `RequestCapture` | work |
| R-M07-06 | 無效輸入 | Complete 的 attempt_id 和 inflight 不符 | `Err(StaleAttempt)` | work |
| R-M07-06 | 失敗 | R 寫入中先 Check（R+1，回 `WaitInFlight`），再 Published R，再到期（新） | 基準＝R，R+1 被請求擷取，沒被吞掉 | work |
| R-M07-07 | 正常 | inflight、Failed | 基準不變、`RetryPending` | work |
| R-M07-07 | 邊界 | Failed 後下一次到期 | `RequestCapture` | work |
| R-M07-07 | 無效輸入 | 沒有 inflight 卻收到 Failed | `Err(StaleAttempt)` | work |
| R-M07-07 | 失敗 | 連續三輪 Begin 後 Failed（新） | 基準始終是原值，每輪都可重試 | work |
| R-M07-08 | 正常 | 同專案兩個 session 狀態各自 Check→Begin→Published（新） | 兩邊基準各自推進，互不影響 | work |
| R-M07-08 | 邊界 | session_id 長度 256 和 257（新） | 256 被接受；257 回 `Err(InvalidInput)` | work |
| R-M07-08 | 無效輸入 | 事件的 session_id 或 project_id 跟狀態不同 | `Err(SessionMismatch)`，狀態不變 | work |
| R-M07-08 | 失敗 | 其他 session 送 Complete Published | `Err(SessionMismatch)`，基準不變 | work |
| R-M07-09 | 正常 | `capture_requested`=true 時 Close | `closed`=true、`capture_requested`=false、`Closed` | work |
| R-M07-09 | 邊界 | 已關閉時再 Check、BeginAttempt、Close（新） | 都回 `Closed`，狀態不變 | work |
| R-M07-09 | 無效輸入 | 已關閉、Complete 的 attempt_id 不合法（空白） | `Err(InvalidInput)`，驗證先於關閉判斷 | work |
| R-M07-09 | 失敗 | 已關閉、inflight、Complete Published 或 Failed | `IgnoreClosedCompletion`，基準不變 | work |
| R-M07-10 | 正常 | attempt_id 長度 256 | `AttemptRegistered` | work |
| R-M07-10 | 邊界 | attempt_id 長度 257；指紋 hex 63 和 65 碼（新） | `Err(InvalidInput)` | work |
| R-M07-10 | 無效輸入 | 大寫 hex 指紋、含 NUL 的 ID、不合法的 `captured_fingerprint`（新） | `Err(InvalidInput)`，呼叫端輸入 clone 前後相等 | work |
| R-M07-10 | 失敗 | 沒請求就 BeginAttempt；不認得的 Complete | `CaptureNotRequested`／`StaleAttempt` | work |
| R-M07-11 | 正常 | 已有成功快照基準 S、有後續編輯，正式保存成功（新） | M07 狀態的 `successful_fingerprint` 仍是 S | host |
| R-M07-11 | 邊界 | 正式保存後同時到期，指紋與 S 不同（新） | `RequestCapture`；正式保存沒有吞掉快照需求 | host |
| R-M07-11 | 無效輸入 | 用其他 session 的事件試圖改基準（新） | `SessionMismatch`，基準不變 | host |
| R-M07-11 | 失敗 | 正式保存失敗（新） | 快照基準與 `capture_requested` 都不變 | host |
| R-M07-12 | 正常 | 注入「成功」狀態和最後成功時間（新） | 狀態區顯示成功和時間 | ui |
| R-M07-12 | 邊界 | 逐一注入 F11 列出的 7 種狀態（新） | 每種都有可見標示，不顯示空白 | ui |
| R-M07-12 | 無效輸入 | 注入未知狀態代碼（新） | 不顯示「成功」，以失敗或未知呈現 | ui |
| R-M07-12 | 失敗 | 快照「失敗待重試」同時正式保存成功（新） | 快照失敗原因仍可見，沒被保存成功的提示蓋掉 | ui |

待決策規則 R-M07-13～26 不列入矩陣；批准後才補四類測試。

## 5. 開發段（RED）

- 前置：兩張交付卡目前都是 `BLOCKED_PENDING_APPROVED_ENVELOPE_AND_VALID_RED`，卡上的 `tdd.command` 也是 BLOCKED，要求先由 PREP 綁定實際 runner。開工前必須先取得批准的 envelope 和測試目標，不可自己猜 cargo target。
- 放置位置（以批准的 envelope 為準）：
  - work 層補測（R-M07-01～10 的「新」項）：另開一個新檔放在 `APP/crates/sgenaxis-work/tests/`，不要改已驗收的 `phase1_recovery_policy.rs`（S1 受保護，見 M07-D6「S1 protected」）。
  - host 層（R-M07-11）：`APP/crates/sgenaxis-host/tests/` 新檔；要先有批准的 HOST recovery 用例骨架。
  - ui 層（R-M07-12）：`APP/ui/` 下新的 `*.test.cjs`；要先有批准的復原狀態 UI schema。
- 先跑紅：
  - `cargo test -p sgenaxis-work --test <新檔名>`：預期失敗關鍵字 `assertion `left == right` failed` 或 `panicked at`。
  - `cargo test -p sgenaxis-host --test <新檔名>`：預期同上。
  - `node --test ui/<新檔>.test.cjs`：預期 `AssertionError` 或 `not ok`。
- 有效 RED 的判定（依交付卡 `valid_red`）：測試必須能編譯，且因為缺少目標行為而失敗。編譯失敗、fixture 錯誤、環境錯誤都不算。R-M07-04、08、09、10 的「新」項多半是已實作行為的補測，第一次跑可能直接 PASS，這時要標成「特性補測，非 RED」，不能假造失敗。
- 禁止事項：
  - 不改規格、BDD、fixture，也不改已驗收的 S1 測試。
  - 不把 R-M07-13～26 寫成斷言，包括快照寫入、索引順序、復原路徑、清理數值、歷史 UI。
  - 不弱化斷言，例如不可把 `assert_transition` 的「輸入不變」檢查拿掉。
  - 不建立實際 `%LOCALAPPDATA%` 目錄，不接 OS 計時器。

## 6. 驗證段

> 執行者不可以是寫這段程式的代理。

- 重跑指令：
  - `cargo test -p sgenaxis-work --test phase1_recovery_policy --locked`：既有 35 個測試必須全部 PASS，作為回歸基線。
  - `cargo test -p sgenaxis-work --test <新 work 測試檔> --locked`
  - `cargo test -p sgenaxis-host --test <新 host 測試檔> --locked`（R-M07-11）
  - `node --test ui/<新 ui 測試檔>.test.cjs`（R-M07-12）
  - 相鄰回歸：`cargo test -p sgenaxis-work --locked`、`cargo test -p sgenaxis-host --lib --locked`（和 S1 驗收的 `commands.json` 相同）。
- 介面實測步驟（R-M07-12，UI 存在之後才做）：
  1. 開專案並編輯，不保存，確認狀態區顯示「待檢查」或「寫入中」。
  2. 注入或模擬快照失敗，確認顯示「失敗待重試」和原因。
  3. 執行正式保存成功，確認快照失敗訊息仍在。
  4. 每一步都截圖。
  - 歷史入口（F12）屬待決策，這輪不做介面實測，在證據裡標 `NOT RUN（G03）`。
- 證據：放在 `reports/dispatch-pd/PD-P1-F11-DELIVERY-01-evidence/`（R-M07-01～12）。F12 的規則全部屬待決策，`reports/dispatch-pd/PD-P1-F12-DELIVERY-01-evidence/` 只記 `NOT RUN` 和卡住的閘門。每條規則一筆，欄位為：規則／指令／Exit code／輸出末段／介面證據／判定。
- 直接判 TDD_FAIL 的情況：
  - 既有 `phase1_recovery_policy` 任何一個測試 FAIL，或測試數少於 35。
  - 新測試沒有有效 RED 紀錄，就直接宣稱 GREEN（特性補測要明確標示的除外）。
  - 有任何斷言涵蓋 R-M07-13～26（等於把待決策寫成已核准）。
  - 改了規格、BDD、fixture，或改了、刪了 S1 測試，或弱化了斷言。
  - 測試寫入真實 `%LOCALAPPDATA%` 或使用者資料，或用實際時間 sleep 代替注入時間。
  - 正式保存流程改動了快照基準（違反 R-M07-11），或 UI 以保存成功蓋掉快照失敗（違反 R-M07-12）。
  - 驗證者和實作者是同一個代理。

## 7. 已知衝突

| 衝突 | 規格出處 | 實作出處 | 影響規則 ID | 處理 |
|---|---|---|---|---|
| 目前無 | — | — | — | — |
