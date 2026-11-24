# M01 專案定義與新建：測試參考

> 草稿。只讀 repo 產生，未修改任何檔案。路徑前綴：`SPEC=docs/requirements-confirmation/phase1-spec`，`APP=apps/sgenaxis-desktop`，`M01P=$SPEC/tasks/M01/planning`。

## 1. 範圍與來源

| 功能 ID | 規格連結 | 交付卡 | BDD 場景 |
|---|---|---|---|
| F01 六步新建與草稿 | `$SPEC/index.html`「F01 六步新建與草稿」節（作者還沒選框架，先存需求與交付方向，之後再填）；REQ-03、REQ-08；TDD 段 X01；附錄 D04 | `$SPEC/tasks/PD-P1-F01-DELIVERY-01.json`（狀態 `BLOCKED_PENDING_APPROVED_ENVELOPE_AND_VALID_RED`；依賴 PD-P1-M01-PREP-01、PD-P1-G01-DEC-01） | `$SPEC/phase1.feature` @BDD-01「保存未完成精靈」、@BDD-02「非空目錄」 |
| （模組現況） | `$M01P/current-state.json`：M01-S2 已 GREEN_SCOPED_ACCEPTED；S3（UI/IPC/owner/冪等）是 `EXACT_PROPOSAL_PENDING_ONE_OWNER_CONFIRMATION` | `$SPEC/tasks/PD-P1-M01-PREP-01.json` | `$M01P/s2-green/module-spec.json#/baseline`（已確認、不再問的基線） |

## 2. 業務規則

### 已核准

| 規則 ID | 規則 | 規格出處 | 核准依據 |
|---|---|---|---|
| R-M01-01 | 新建專案用六步精靈，順序是：基本資料、交付環境、運作方式、工具需求、技術與 UI UX、預覽與建立 | `$SPEC/index.html` REQ-03（已確認） | 正式核准 |
| R-M01-02 | 可以保存還沒填完的定義；重新開啟後，已保存的欄位和未決事項都還在 | REQ-03；@BDD-01；`PD-P1-F01-DELIVERY-01.json#/acceptance/0`（AC01：「六步可保存重開」）；`$M01P/s2-green/module-spec.json#/baseline/items/2` | 正式核准 |
| R-M01-03 | 保存定義不等於批准生成：草稿不生成未確認的部分；草稿值不能被當成已批准；要列出缺少哪些決策 | F01「邊界」的確認句（草稿可以缺技術，生成時不得把草稿值當成已批准）；@BDD-01 的「那麼」；`$M01P/exact-design/module-spec.json#/plan/cases`（TDD-M01-EX-02、EX-05，已在 M01-S1 驗收） | 正式核准 |
| R-M01-04 | 生成被阻擋時，定義仍然可以保存 | AC01（「生成被阻擋時仍可保存」）；REQ-04 | 正式核准 |
| R-M01-05 | 目標同名、目標是既有檔案、或目標是空或非空的既有目錄：都不覆寫，原內容逐位元不變，不刪任何檔案 | REQ-08；@BDD-02；F01「失敗處理」的確認句；AC01（「衝突的既有目錄逐位元不變」）；EX-07、EX-08；`$M01P/s2-green/module-spec.json#/failure_matrix`（M01-S2 已採納） | 正式核准 |
| R-M01-06 | 發生 R-M01-05 的衝突時，提供三個選擇：修改名稱、另選位置、取消 | REQ-08；@BDD-02 的「那麼」；`$M01P/s2-green/module-spec.json#/baseline/items/3` | 正式核准 |
| R-M01-07 | 名稱驗證：空字串或只有空白要拒絕；Windows 保留名（CON、NUL、COM1…）、路徑分隔符、結尾句點、NUL 字元要拒絕；長度 1 到 120 字合法 | `$SPEC/index.html` TDD 段 X01（名稱空白、Windows 保留名）；長度上限出自 `$M01P/exact-design/module-spec.json#/schema/properties/name`，經 M01-S1 驗收及 M01-S2-D3 採納（見第 6 節的不確定說明） | 模組採納：M01-S2-D3（`$M01P/s2-exact-design/decisions.json`；120 字上限出自 M01-S1 exact-design schema） |
| R-M01-08 | 遇到不可寫路徑、重複按建立、取消草稿再重開這三種情況時，六步裡各自填的值都要保留 | `$SPEC/index.html` X01（「六步各自值保全」） | 正式核准 |
| R-M01-09 | 連續按兩次「建立」，不會建立第二個專案，也不會覆寫第一次的結果 | X01（「重複按建立」）；REQ-08 | 正式核准 |
| R-M01-10 | 取消精靈不寫入任何檔案，也不建立目錄 | X01（「草稿取消」）；`$M01P/s2-green/module-spec.json#/failure_matrix`（preflight 失敗不改任何東西） | 正式核准 |
| R-M01-11 | 舊的三個新建入口（`create_new_project_root`、`create_new_project_under`、`host_new_project_directory` 系）收到合法請求時，一律先回 `WIZARD_REQUIRED`，在任何檔案系統呼叫（含讀取）之前就回 | `$M01P/s2-exact-design/decisions.json` M01-S2-D6；`$M01P/s2-green/verification.json#/approved_decisions` | 模組採納：M01-S2-D6（`$M01P/s2-exact-design/decisions.json`） |
| R-M01-12 | 用過期的 revision 保存要回 RevisionConflict，原定義不變；revision 溢位時不回繞 | `$M01P/exact-design/module-spec.json` TDD-M01-EX-04（M01-S1 已驗收，見 `$M01P/s2-green/module-spec.json#/baseline/items/0`） | 模組採納：M01-S1 驗收（TDD-M01-EX-04；`$M01P/s2-green/module-spec.json#/baseline/items/0`） |
| R-M01-17（原列待決策） | 建立過程遇到權限、空間或原生拒絕等錯誤時，回 PartialProjectCreated 並列出這次已產生的項目（progress）；只清理能證明是這次新增的檔案；需人工處理時回 RecoveryRequired。UI「保留表單」仍屬 F01 建議，不在本條斷言範圍 | F01「失敗處理」；M01-S2-D2、D5（`$M01P/s2-exact-design/decisions.json`）；`$M01P/s2-green/module-spec.json#/failure_matrix` | 模組採納：M01-S2-D2、D5（`$M01P/s2-exact-design/decisions.json`）。F01 不在 G02／G03 的 `affected_features`，內容不直接依賴其未決部分 |

### 待決策

| 規則 ID | 卡在 | 目前選項 | 開發期處理 |
|---|---|---|---|
| R-M01-13 | G01（檔案與身分契約，`PD-P1-G01-DEC-01.json` 狀態 PENDING_ARCHITECTURE_REVIEW） | 定義檔放在 `.sgenaxis/project-definition.json`，schema `eluslot.project-definition` v1；持久 projectUuid 加 legacy root key 別名；codec 上限 16MiB、深度 64、10 萬節點、單字串 1MiB、數字 4096（M01-S2-D3/D4 在模組內採納，但 G01 全域尚未批准） | 既有 codec／store 測試只當回歸保留，不再新增依賴這些格式細節的驗收斷言 |
| R-M01-14 | F01「資料影響」標為建議；`lastSavedStep` 欄位格式受 G01 約束 | 按返回不清除已填值；重開時回到上次已保存的步驟 | 只能寫成 `#[ignore]` 待決測試或註記，不寫成必過斷言 |
| R-M01-15 | F01「資料影響」標為建議 | 不同交付目標各自獨立記錄（目前 bridge 只支援一個 target，id 就是 project uuid） | 不寫斷言；記錄現況限制 |
| R-M01-16 | 附錄 D04（「欄位與 schema 需整體批准」）；S-02 | 草稿只有名稱與位置必填，目的、偏好、技術可以暫定；名稱先修剪前後空白再驗證 | 修剪行為不寫斷言；R-M01-07 不受影響 |
| R-M01-18 | 附錄 D05（「沿用既有能力，先核對差額」） | 偏好可選 skip、preset、import；import 是獨立副本 | 既有 t051–t061 與 legacy 測試保留為回歸 |
| R-M01-19 | `$SPEC/index.html`「狀態與 UI schema 均作本次整體審查內容」；`docs/ui-design/ui-spec.json` 沒有精靈畫面 | 七個狀態：空白、編輯中、草稿已保存、有待決策、建立中、建立成功、失敗；UI 有「保存草稿」鈕、預覽完整路徑、錯誤摘要定位到欄位、可用鍵盤操作 | UI 測試只驗已核准規則（R-01/02/06/08/09/10），不驗狀態名稱或版面 |
| R-M01-20 | M01-S3-D1～D8 待 Owner 確認（`$M01P/s3-exact-design/`；`s3-reconcile-20261115/TDD-REVIEW.md` 列 D1、D3、native、S3-G1 為 OPEN） | caller／owner 視窗授權、同一 request_id 的冪等處理、晚到回應不得改新專案、native 選擇器 | `phase2_project_wizard.rs` 只當骨架回歸；不新增 S3 契約斷言 |
| R-M01-21 | G01 | 開啟既有專案或採用 legacy 專案時，只新增定義檔，不改 ESS、manifest、既有偏好（`s2-green` 基線已確認語意，但檔案契約歸 G01） | 既有 t070–t077 保留為回歸 |

## 3. 已有測試對照

| 規則 ID | 測試檔::函式 | 已涵蓋類別 | 缺口 |
|---|---|---|---|
| R-M01-01 | `sgenaxis-host/tests/phase1_project_definition_codec.rs::t001_basics…t001_preview` | 正常（work/codec） | UI 的 `STEPS` 標題是「交付目標／專案結構／需求」，跟 REQ-03 的名稱不一致；UI 沒有任何測試；缺第 0 步與第 7 步的邊界 |
| R-M01-02 | `sgenaxis-work/tests/phase1_project_definition.rs::m01_ex02_incomplete_draft_is_valid_without_generating_anything`；codec `t002_draft`；`phase2_project_wizard.rs::wizard_bridge_new_project_commit_persists_definition` | 正常 | 精靈中途沒有「保存草稿」，只有第 6 步能 commit；`wizard_begin` 不會載入已存的定義（existing 只是 location，draft 一律新建空白）；沒有「保存後重開續填」的 host、command 或 UI 測試；AC01 目前做不到 |
| R-M01-03 | work `m01_ex05_generation_gate_lists_concrete_missing_decisions`、`m01_changed_definition_invalidates_old_approval_references`、`m01_confirmed_target_still_requires_concrete_language_and_toolchain`、`m01_complete_trusted_definition_has_no_missing_core_fields` | 正常／邊界／無效 | host／command 層沒有斷言 commit 後檔案樹裡只有定義檔、沒有骨架；UI 的 `previewText` 沒有測試 |
| R-M01-04 | 間接涵蓋：`phase2_project_wizard.rs::wizard_bridge_new_project_commit_persists_definition`（欄位不齊時仍 commit） | 正常（間接） | 沒有明確斷言「missing 不是空的，commit 仍然成功」 |
| R-M01-05 | host `phase1_project_definition.rs::t057_file`、`t058_empty`、`t059_nonempty`、`t060_race`、`t087_duplicate_request`、`existing_file_is_not_deleted_and_existing_directory_is_not_adopted` | 正常／邊界／失敗（Port 假 FS） | bridge（`wizard_commit`）、command、UI 層都沒有 ExistingTarget 測試；Windows 原生 FS 未測 |
| R-M01-06 | 無 | — | 最大缺口：UI 只顯示「步驟失敗：…」，沒有改名、另選位置、取消三個選項；location 在 `wizard_begin` 就固定了，第 1 步改名不會改目標目錄 |
| R-M01-07 | work `m01_ex01_empty_and_whitespace_names_report_the_name_field`、`m01_name_length_one_and_120_are_valid_boundaries`、`m01_121_character_name_is_rejected_before_apply`、`m01_windows_reserved_names_and_separators_are_invalid`；`phase2_project_wizard.rs::wizard_apply_step_rejects_invalid_name`；legacy `t100_name_0..2` | 正常／邊界／無效 | UI 沒有測「名稱錯誤時停在第 1 步並指出欄位」；command 層沒有測試 |
| R-M01-08 | 無直接測試（`wizard_commit` 原始碼註解說被拒時保留 session，但沒有測試） | — | 缺：commit 失敗後 token 仍有效、六步值仍在；UI 按返回後值仍在 |
| R-M01-09 | host `t087_duplicate_request`（store 層第二次回 ExistingTarget）；`phase2_project_wizard.rs::wizard_commit_clears_token_and_rejects_reuse` | 正常／無效 | UI 的 busy 防重送沒有測試；command 層沒有測並行兩次 commit |
| R-M01-10 | `phase2_project_wizard.rs::wizard_cancel_drops_in_flight_session` | 正常 | 缺斷言「取消前後 FS 樹相同」；UI 的 Esc／取消鈕沒有測試 |
| R-M01-11 | `phase1_project_creation_legacy.rs::t091_deprecated…t099_deprecated`、`t100_demo`；`src-tauri/tests/project_preferences_commands.rs::legacy_*_requires_wizard_before_any_fs_access` | 正常／無效／失敗 | 大致齊全 |
| R-M01-12 | work `m01_ex04_stale_revision_is_a_conflict_and_preserves_current_value`、`m01_revision_overflow_does_not_wrap_or_mutate`、`m01_ex03_apply_advances_revision_and_preserves_identity_and_legacy_aliases` | 正常／邊界／失敗 | 精靈 bridge 不經過 revision 檢查（begin 一律從 revision 0 開始） |
| R-M01-17 | host `phase1_project_definition.rs::t078_failure`、`t079_failure`、`t080_failure`、`t081_failure`（PartialProjectCreated）、`t082_recovery`、`t083_recovery`（RecoveryRequired） | 邊界／無效／失敗（Port 假 FS） | 沒有「無錯誤時不觸發清理」的明確斷言；bridge（`wizard_commit`）、command 層沒有測試；Windows 原生 FS 未測 |

13 條已核准規則中有 11 條有測試（R-M01-06、R-M01-08 完全沒有）；只有 R-M01-11 算完整涵蓋。

## 4. 測試矩陣

| 規則 ID | 類別 | 輸入 | 預期 | 層 |
|---|---|---|---|---|
| R-M01-01 | 正常 | 從頭依序走完六步 | 共六步、順序固定；步驟名稱與 REQ-03 是否一致**暫不斷言（見 §7）**，只記錄現況 | ui |
| R-M01-01 | 邊界 | 在第 1 步按上一步；在第 6 步看按鈕 | 第 1 步的上一步是 disabled；第 6 步的主按鈕是「建立」 | ui |
| R-M01-01 | 無效輸入 | `wizard_apply_step` 收到不存在的 step 字串 | 反序列化拒絕，draft 不變 | command |
| R-M01-01 | 失敗 | apply_step 在 IPC 失敗 | 停在原步驟，不前進 | ui |
| R-M01-02 | 正常 | 填完第 1–2 步，框架留空；保存，再重開 | 名稱、目的、交付值、openDecisions 都在 | host |
| R-M01-02 | 邊界 | 只填名稱（其他步都空）就保存再重開 | 讀回的定義相等，mode 是 draft | work、host |
| R-M01-02 | 無效輸入 | 用不存在或已清掉的 token 續填 | 回 UnknownToken，FS 不變 | command |
| R-M01-02 | 失敗 | 保存時寫入失敗 | 回錯誤；記憶體中的 draft 保留、可以重試 | host |
| R-M01-03 | 正常 | 未決的草稿 commit | FS 樹只多 `.sgenaxis/` 定義（加選擇的偏好），沒有骨架檔 | host |
| R-M01-03 | 邊界 | 所有核心欄位都齊，但 approvalRefs 是空的 | missing 含 approvalRefs；mode 不會自動變成 defined | work |
| R-M01-03 | 無效輸入 | caller 在 patch 裡夾帶 approvalRefs 或 mode=defined | 欄位被拒或忽略，不能取得批准 | command |
| R-M01-03 | 失敗 | 改了已批准定義的內容 | 舊的 approvalRefs 失效 | work |
| R-M01-04 | 正常 | missing 不是空的時候 commit | 成功，receipt 有 revision；預覽列出缺少的決策 | host、ui |
| R-M01-04 | 邊界 | missing 只差 1 項 | 照樣可以保存 | host |
| R-M01-04 | 無效輸入 | 名稱不合法，同時 missing 不是空的 | 擋在名稱驗證，不寫檔 | host |
| R-M01-04 | 失敗 | 偏好準備失敗 | 不建立目錄；可以改用 skip 重試 | host |
| R-M01-05 | 正常 | 目標不存在 | 用 exclusive 方式建立 | host |
| R-M01-05 | 邊界 | 目標是空目錄；目標是一般檔案；建立前一刻被別人建立（race） | 都回 ExistingTarget；原 bytes 和樹不變 | host |
| R-M01-05 | 無效輸入 | 目標是非空目錄（內有 keep.ess） | 回 ExistingTarget；keep.ess 的雜湊不變 | host、command |
| R-M01-05 | 失敗 | 經 `wizard_commit` 碰到既有目錄 | 回 Commit/ExistingTarget；沒有 remove_file 或覆寫；session 保留 | host（bridge） |
| R-M01-06 | 正常 | 衝突後選「修改名稱」，改成新名字再建立 | 用新名字建立；舊目錄不變 | command、ui |
| R-M01-06 | 邊界 | 衝突後選「另選位置」 | 改到新父路徑後建立成功；六步值不變 | command、ui |
| R-M01-06 | 無效輸入 | 改名後的新名字也衝突，或是保留名 | 再顯示一次三個選擇或名稱錯誤；不寫檔 | ui |
| R-M01-06 | 失敗 | 衝突後選「取消」 | 釋放 token；FS 不變；不顯示成功 | ui、command |
| R-M01-07 | 正常 | 名稱 `Project-A` | validation.ok | work |
| R-M01-07 | 邊界 | 長度 1、2、119、120 合法；121 拒絕 | 合法的通過；121 回 name 欄位錯誤 | work |
| R-M01-07 | 無效輸入 | `""`、`" "`、`CON`、`con.txt`、`a/b`、`a\b`、`a:b`、`name.`、含 `\0` | InvalidInput{field:"name"}；UI 停在第 1 步並指出名稱欄 | work、host、ui |
| R-M01-07 | 失敗 | 名稱不合法卻直接呼叫 commit | 拒絕，沒有任何 FS 呼叫 | host |
| R-M01-08 | 正常 | 在第 3 步按上一步，再按下一步 | 第 1–3 步的值都在 | ui |
| R-M01-08 | 邊界 | 在第 6 步 commit 被拒 | token 仍有效，六步的值都在，可以重試 | host |
| R-M01-08 | 無效輸入 | 父路徑不可寫或不存在 | 回錯誤、不是成功；draft 保留 | host、command |
| R-M01-08 | 失敗 | 存了草稿、取消、再重開 | 回到已保存的值；沒保存的值不會冒出來 | host、ui |
| R-M01-09 | 正常 | 按一次建立 | 產生一個專案、一張 receipt | host |
| R-M01-09 | 邊界 | 在 busy 期間連點兩下 | 只送出一次 `wizard_commit` | ui |
| R-M01-09 | 無效輸入 | commit 成功後用同一個 token 再 commit | 回 UnknownToken，FS 不變 | host |
| R-M01-09 | 失敗 | 兩個 commit 並行搶同一個目標 | 只有一個成功；另一個回 ExistingTarget，第一個的結果不被覆寫 | command |
| R-M01-10 | 正常 | 在任何一步取消 | `wizard_cancel` 被呼叫；FS 樹不變 | host、ui |
| R-M01-10 | 邊界 | 在第 6 步的偏好選擇器按取消 | 不建立專案；顯示「尚未建立專案」 | ui |
| R-M01-10 | 無效輸入 | 用未知 token 取消 | 回 UnknownToken，無副作用 | host |
| R-M01-10 | 失敗 | 取消時 IPC 失敗 | 對話框照樣關閉，沒有任何寫檔 | ui |
| R-M01-11 | 正常 | 三個舊入口收到合法請求 | 回 `WIZARD_REQUIRED:`；零 FS 呼叫 | host |
| R-M01-11 | 邊界 | 目標已有檔案 | bytes 不變，不刪除 | host |
| R-M01-11 | 無效輸入 | 名稱是空、`..`、`a/b`，或根目錄不是絕對路徑 | 回一般設定錯誤（不是 WIZARD_REQUIRED）；零 FS 呼叫 | host |
| R-M01-11 | 失敗 | 從 command 層呼叫舊偏好建立入口 | 在任何 FS 動作前回 WIZARD_REQUIRED | command |
| R-M01-12 | 正常 | expected revision 等於目前 | revision 加 1；身分與別名保留 | work |
| R-M01-12 | 邊界 | revision 已是 u64::MAX | 拒絕，不回繞也不改值 | work |
| R-M01-12 | 無效輸入 | 不合法的持久身分 | 拒絕套用 | work |
| R-M01-12 | 失敗 | 用舊 revision 保存 | RevisionConflict；目前值不變 | work、host |
| R-M01-17 | 正常 | 建立成功（不注入任何錯誤） | 不回 PartialProjectCreated／RecoveryRequired；沒有任何清理呼叫 | host |
| R-M01-17 | 邊界 | 根目錄已建立，之後的步驟才失敗 | PartialProjectCreated，progress 標 `root_created=true` 並列出本次產生的項目；非本次建立的項目不刪 | host |
| R-M01-17 | 無效輸入 | 建立根目錄後原生層拒絕路徑（InvalidLocation） | PartialProjectCreated{cause: InvalidLocation}，帶 path 與 reason；不碰既有檔 | host |
| R-M01-17 | 失敗 | 建立根目錄時權限失敗；或寫入後狀態無法確認 | 前者不留下任何本次產物、回錯誤；後者回 RecoveryRequired，不自動刪除；既有檔 bytes 不變 | host |

## 5. 開發段（RED）

- 放置位置（新增，不動既有檔）：
  - host bridge：`$APP/crates/sgenaxis-host/tests/phase2_project_wizard.rs` 補 R-05/06/08/09/10 的 bridge 案例。這個檔案有 `#![cfg(windows)]`，必須在 Windows 跑。
  - command：`$APP/src-tauri/tests/project_wizard_commands.rs`（新檔），放 R-01、R-02、R-06、R-09 的 command 層案例。
  - ui：`$APP/ui/project-wizard-ui.test.cjs`（新檔），用 node:test 加假 `__TAURI__.core.invoke` 和最小 DOM stub，放 R-01/06/07/08/09/10 的 UI 案例。
  - work 層的缺口很少；只在 `$APP/crates/sgenaxis-work/tests/phase1_project_definition.rs` 補缺的邊界。
- 先跑紅（cwd `$APP`）：
  - `cargo test -p sgenaxis-host --test phase2_project_wizard`：預期失敗訊息含 `ExistingTarget`、`UnknownToken`，或 assert 訊息「六步值未保全」。不可以是編譯錯誤或 fixture 錯誤。
  - `cargo test -p sgenaxis-tauri --test project_wizard_commands`（crate 名以 `src-tauri/Cargo.toml` 為準）：預期 assert 失敗，訊息含「rename/relocate/cancel」選項缺失。
  - `node --test ui/project-wizard-ui.test.cjs`：預期 `AssertionError`，例如沒有「保存草稿」或衝突三選項、按兩下送出兩次 commit（步驟標題與 REQ-03 的差異暫不斷言，見 §7）。
- 有效 RED：測試可編譯，且只因為目標行為缺失而失敗。缺依賴、壞 fixture、編譯失敗、skip、非 Windows 跳過，都不算 RED（依據：`$SPEC/index.html` TDD 段、`PD-P1-F01-DELIVERY-01.json#/tdd/valid_red`）。
- 禁止：
  - 不改 `$SPEC/**` 規格、BDD、交付卡。
  - 不把待決策 R-M01-13～16、18～21 寫成必過斷言，最多 `#[ignore = "PENDING G0x/S3"]` 加註記。
  - 不對 §7 已知衝突寫斷言（目前是步驟名稱）。
  - 不刪除或弱化既有 t0xx、m01_* 斷言；舊預期要遷移時，必須有明文核准的遷移紀錄。
  - 不新增 crate 或依賴；UI 不得直接碰 FS。

## 6. 驗證段

> 執行者不可以是寫這段程式的代理。

- 重跑指令（cwd `$APP`；host 的 phase1/phase2 檔只在 Windows 編譯）：
  - `cargo test -p sgenaxis-work --test phase1_project_definition`
  - `cargo test -p sgenaxis-host --test phase1_project_definition`
  - `cargo test -p sgenaxis-host --test phase1_project_definition_codec`
  - `cargo test -p sgenaxis-host --test phase1_project_creation_legacy`
  - `cargo test -p sgenaxis-host --test phase2_project_wizard`
  - `cargo test -p <src-tauri crate> --test project_preferences_commands`、`--test project_wizard_commands`
  - `node --test ui/project-wizard-ui.test.cjs`
  - 回歸：`cargo test -p sgenaxis-host --locked -- --test-threads=1`、`cargo test -p sgenaxis-work --locked`
- 介面實測步驟（Windows 11 x64 免安裝版，依 REQ-01）：
  1. 新增專案，依序走六步，截圖記錄步驟名稱（名稱暫不判定，見 §7）。在第 3 步按上一步再下一步，值都在（R-01、R-08）。
  2. 名稱輸入 `CON` 或空白，確認停在第 1 步並指出名稱欄（R-07）。
  3. 框架留空走到第 6 步，預覽列出缺少的決策，按建立後成功；檔案總管裡只有 `.sgenaxis/`，沒有骨架（R-03、R-04）。
  4. 保存草稿，關閉，重開續填，確認值與未決事項都在（R-02，目前預期 FAIL）。
  5. 先在目標位置放一個非空目錄並記下檔案雜湊，再建立同名專案。確認雜湊不變，且出現修改名稱、另選位置、取消三個選擇，三個都要實際點過（R-05、R-06）。
  6. 快速連點兩下建立，只產生一個專案（R-09）。在各步按取消或 Esc，FS 不變（R-10）。
  7. 每一步都截圖，全程錄影。
- 證據：放 `reports/dispatch-pd/PD-P1-F01-DELIVERY-01-evidence/`。每條規則一筆，欄位是：規則／指令／Exit code／輸出末段（`test result:` 行）／介面證據（截圖或錄影檔名＋FS 雜湊前後對照）／判定。
- 直接判 TDD_FAIL 的情況：
  - 任一已核准規則的測試失敗，或被 `#[ignore]`、刪除、弱化。
  - 衝突後既有目錄的 bytes 或雜湊有變。
  - 草稿被當成已批准，或 commit 產生了骨架。
  - 用非 Windows 跳過（cfg(windows)）冒充 PASS。
  - 用元件或靜態結果冒充原生 UI PASS。
  - 把待決策規則當驗收依據。
  - 驗證者就是實作者。
  - 證據缺 Exit code 或輸出末段。
- 不確定的出處：
  - R-M01-07 的 120 字上限，只追到 exact-design 的 schema，加上 M01-S1 驗收與 M01-S2-D3 採納，`$SPEC/index.html` 本文沒有寫數字；依 L3 決策 1 列為「模組採納」。
  - M01-S2 的 D1～D7 依 L3 決策 1 視為已核准（模組採納）；其中直接牽涉 G01 檔案格式與身分的 R-M01-13、R-M01-21 仍留待決策。
  - `project_wizard.rs` 與 `commands.rs` 的 wizard bridge 已經存在，但 S3 決策還沒批准。這段程式的授權來源沒有找到。

## 7. 已知衝突

| 衝突 | 規格出處 | 實作出處 | 影響規則 ID | 處理 |
|---|---|---|---|---|
| 精靈步驟名稱和 REQ-03 不一致（規格：基本資料、交付環境、運作方式、工具需求、技術與 UI UX、預覽與建立；實作：基本資料、交付目標、專案結構、需求、技術與 UI、預覽與建立） | `$SPEC/index.html` 需求基線 REQ-03（已確認） | `$APP/ui/project-wizard-ui.js:21`（`STEPS`）；標題在第 32 行「2／6 交付目標」、43 行「3／6 專案結構」、48 行「4／6 需求」、56 行「5／6 技術與 UI」 | R-M01-01 | 暫不斷言，待看板決策卡 |
