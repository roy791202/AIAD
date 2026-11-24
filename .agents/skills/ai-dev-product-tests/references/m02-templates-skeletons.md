# M02 模板與雙骨架：測試參考

> 範圍：只寫業務邏輯（模板選擇、偏好規則、骨架產生）。偏好參數的 UI/UX 調整驗證由 `ui-parameters.md` 負責，本檔不重複。
> 路徑前綴：規格 `docs/requirements-confirmation/phase1-spec/`（下稱 `SPEC/`）；產品 `apps/sgenaxis-desktop/`（下稱 `APP/`）。
> 盤點基準：worktree `claude/skills-index-structure-f8398d`，HEAD `ef4896fa`；僅靜態閱讀，另跑 `node --test ui/project-preferences-ui.test.cjs`（4/4 pass）確認名稱，未跑 cargo（避免寫入 `target/`）。

## 1. 範圍與來源

| 功能 ID | 規格連結 | 交付卡 | BDD 場景 |
|---|---|---|---|
| F02 產品模板與偏好 | `SPEC/index.html#F02`：狀態「建議採用」。模板只產生專案副本、更新不自動覆寫、偏好排除憑證，整段都還是提案；`SPEC/index.html#defaults` 的 D05、D06 也都還沒批准 | `SPEC/tasks/PD-P1-F02-DELIVERY-01.json`（BLOCKED_PENDING_APPROVED_ENVELOPE_AND_VALID_RED，依賴 M02-PREP、G04） | BDD-03、BDD-04 只是共用回歸義務。`SPEC/tasks/F02/feature-trace-preparation/trace.json` 的 `trace_integrity` 寫明，這兩個場景不能直接證明 AC02 |
| F03 架構與程式/UI 雙骨架 | `SPEC/index.html#F03`：狀態「已確認」，但局部仍是提案。對應的確認需求是 `SPEC/index.html#baseline` 的 REQ-04 | `SPEC/tasks/PD-P1-F03-DELIVERY-01.json`（BLOCKED…，依賴 M02-PREP、G01、G04） | `SPEC/phase1.feature` 的 @BDD-03「生成條件不足」、@BDD-04「生成雙骨架」 |
| M02-S1 純計畫切片（F03 子集） | `SPEC/tasks/M02/planning/exact-design/module-spec.json`：Owner 已採納 DX1～DX7（見 `SPEC/tasks/M02/s1/adoption.json`），但授權範圍只到 S1 Skeleton 加 RED | 同 F03 卡；S1 的驗收見 `SPEC/tasks/M02/s1/` | `SPEC/tasks/M02/s1/module.feature` 的 @M02-T01～T10 |
| 專案偏好（歷史卡，F02「偏好」的既有能力） | `docs/board.json` 裡 PD-ELU-SET-PREFERENCES-S0-01、PD-ELU-SET-PREFERENCES-S1-01、PD-ELU-PROJECT-PREFERENCES-S2-01 三張卡的 `legacyTask.bdd`，都是歷史綠燈 | 同上三卡；F02 交付卡沒有引用它們 | 三卡 `legacyTask.bdd` 各一條（Given/When/Then 句） |
| 模板支援矩陣（阻擋項） | `SPEC/tasks/PD-P1-G04-DEC-01.json`：PENDING_ARCHITECTURE_REVIEW，阻擋 F02、F03、F04、F06 | — | — |

## 2. 業務規則

### 已核准

| 規則 ID | 規則 | 規格出處 | 核准依據 |
|---|---|---|---|
| R-M02-01 | 必要架構、契約或批准不齊時只回 SaveDefinitionOnly，不產生計畫也不寫檔。缺項清單要排序並去重；未定的 topology／hasUi／toolchain、tentative 或 unresolved 需求、空白 intent、缺 acceptance、open_decisions 都要列入 | `SPEC/index.html#baseline` REQ-04；`SPEC/phase1.feature` @BDD-03；`exact-design/module-spec.json` 的 `pure_C_contract.order`、`pure_C_contract.requirements`；`s1/module.feature` @M02-T02 | 正式核准 |
| R-M02-02 | 條件齊備時，計畫必須同時含 Program 與 UiUx 兩類產物意圖；只有其中一類或零產物都要拒絕 | REQ-04；@BDD-04；`pure_C_contract.order`（Prepared 必含 program 與 ui_ux）；@M02-T01、@M02-T08 | 正式核准 |
| R-M02-03 | approval 參照字串本身不算批准，必須經 HOST 核實（required_approvals_satisfied）才放行；核實過的參照若不符，回 ApprovalMismatch | `pure_C_contract.types.GenerationPolicyContext`；@M02-T03；`decision_batch` M02-DX1 | 模組採納：M02-DX1（`SPEC/tasks/M02/s1/adoption.json`） |
| R-M02-04 | 模板 id、version、source_digest 與 context 綁定只要一項不符，就回 TemplateMismatch，不產生計畫 | `pure_C_contract.types.GenerationBinding`；@M02-T04 | 模組採納：M02-S1 exact-design（`SPEC/tasks/M02/s1/adoption.json`，DX1～DX7） |
| R-M02-05 | 產物相對路徑要拒絕以下情況：空字串、`..`、絕對路徑、反斜線、磁碟代號、Windows 保留名、結尾點、空或 `.` 元件、NUL、非 ASCII；大小寫碰撞與檔案／目錄前綴碰撞也要拒絕 | `wire_contracts.common`（UTF8/ASCII 路徑）；@M02-T06；M02-DX4 | 模組採納：M02-DX4（`SPEC/tasks/M02/s1/adoption.json`） |
| R-M02-06 | 上限：產物 1～128 筆；路徑 ≤240 bytes、單一元件 ≤64、元件數 ≤16；digest 格式為 `sha256:` 加 64 個小寫 hex | `wire_contracts.limits_proposed`、`wire_contracts.hashes`（M02-DX4 已採納）；@M02-T08 | 模組採納：M02-DX4（`SPEC/tasks/M02/s1/adoption.json`） |
| R-M02-07 | project_uuid 不合法或不一致、definition_revision 不符、target 或 requirement ID 重複，都回 InvalidInput，不依名稱猜測 | `pure_C_contract.order`；@M02-T09 | 模組採納：M02-S1 exact-design（`SPEC/tasks/M02/s1/adoption.json`，DX1～DX7） |
| R-M02-08 | 計畫綁定的 9 個欄位（project、revision、definition digest、target、template id/version/digest、approval、base activation）任一變更時，`validate_plan_binding` 回 StaleBinding 並指出欄位；綁定相同則通過 | `pure_C_contract.public_functions_proposed`；@M02-T07；M02-DX1 | 模組採納：M02-DX1（`SPEC/tasks/M02/s1/adoption.json`） |
| R-M02-09 | 同一組輸入重複準備，結果要相同；產物依 relative_path 升冪排序；準備前後不得改動任何輸入 | `pure_C_contract.types.GenerationPlan`；@M02-T10、@M02-T01 | 模組採納：M02-S1 exact-design（`SPEC/tasks/M02/s1/adoption.json`，DX1～DX7） |
| R-M02-10 | 錯誤優先序：身分、型別、重複 ID、模板、路徑這類結構錯誤，先於 SaveOnly 缺項回報 | `pure_C_contract.order`（先拒壞身份…再合併 missing） | 模組採納：M02-S1 exact-design（`SPEC/tasks/M02/s1/adoption.json`，DX1～DX7） |
| R-M02-11 | 生成邊界：不啟動 AI、建置、外部程式、安裝或發布，也不實作未確認的業務功能；模板 manifest 不允許 commands、install、scripts 欄位 | `SPEC/index.html#F03`「邊界」（無「建議」字樣）；REQ-23；`exact-design/module-spec.json` 的 `confirmed[2]` 與 `wire_contracts.template_manifest` | 正式核准 |
| R-M02-12 | 偏好文件 v1 嚴格解析。任何一層出現未知欄位都拒絕，包含 token 這類憑證欄位；formatVersion 不支援回 UnsupportedVersion；format 不符、無效 UTF-8、重複 JSON key、負數、小數、溢位、型別錯誤、缺必要區塊，都回 InvalidDocument | `docs/board.json` PD-ELU-SET-PREFERENCES-S0-01 的 `legacyTask.bdd`（reject invalid/unknown/secret fields） | 正式核准（`docs/board.json` 歷史卡 legacyTask.bdd） |
| R-M02-13 | 偏好政策不變量：allowedModelIds 不重複且不空白；preferredModelId 必須在清單內；maxTasks、maxConcurrent 都大於 0 且 maxConcurrent ≤ maxTasks；預算為正整數或 null（未配置）；直接用 struct 也不能繞過驗證 | 同上 S0（enforce schema/model/budget/batch invariants） | 正式核准（`docs/board.json` 歷史卡 legacyTask.bdd） |
| R-M02-14 | 系統方案只是建議。未知方案回 UnknownPreset，不替代；套用後得到的是可獨立修改的副本，不影響原方案；未配置時不發明模型或預算；batch.mode 只接受 suggest，不授予自動執行 | 同上 S0（suggestion-only preset IDs… owned preset… do not grant IO/UI/automatic-run authority） | 正式核准（`docs/board.json` 歷史卡 legacyTask.bdd） |
| R-M02-15 | HOST 偏好的載入與保存。缺檔視為未配置，不寫預設；專案之間互相隔離；digest 過期或缺漏回 Conflict，原檔不變；既有檔損壞時不重設；讀取權限失敗明確報錯，不當成未配置；寫入失敗保留先前的有效文件；回讀不一致回 Conflict | `docs/board.json` PD-ELU-SET-PREFERENCES-S1-01 的 `legacyTask.bdd` | 正式核准（`docs/board.json` 歷史卡 legacyTask.bdd） |
| R-M02-16 | 匯入偏好檔只做預覽：不寫入、不改來源，含憑證欄位就拒絕；未綁定或已過期的專案在任何寫入前就要拒絕 | `docs/board.json` PD-ELU-PROJECT-PREFERENCES-S2-01 的 `legacyTask.bdd`（validate before…, copy independent preference values）；S0 的 reject secret | 正式核准（`docs/board.json` 歷史卡 legacyTask.bdd） |
| R-M02-17（原列待決策） | 第一個模板是 `local-tauri-vanilla` 1.0.0，只支援 desktop/windows-x64/rust/tauri2+vanilla/has_ui=true；其他組合（含 has_ui=false）回 UnsupportedTarget，不靜默丟掉 UiUx 產物，也不擴充支援組合。G04 的整體支援矩陣（其他框架、版本）仍待決策，不從本條推論 | `exact-design/module-spec.json#first_template`；M02-DX6；`s1/module.feature` @M02-T05 | 模組採納：M02-DX6（`SPEC/tasks/M02/s1/adoption.json`） |

### 待決策

| 規則 ID | 卡在 | 目前選項 | 開發期處理 |
|---|---|---|---|
| R-M02-18 | G04；F02 整段是提案（`SPEC/index.html#F02`，AC02 標「提案」） | 修改模板副本不影響來源（`F02/feature-trace-preparation/trace.json` 的 F02-PROP-T01 recipe） | 只保留 PLANNED_NOT_RUN 配方，不寫 RED |
| R-M02-19 | G04；F02 與 F03「再生成先預覽差異」都是建議 | 模板更新或再生成時先看差異，不自動覆寫（F02-PROP-T02） | 同上 |
| R-M02-20 | G04；F02 AC02 是提案；X02 | 不增加需求以外的模組，也不能排除必要模組（F02-PROP-T03；`SPEC/index.html#tests` 的 X02） | 同上 |
| R-M02-21 | G04；F02「失敗處理」是提案 | 模板來源不可用時保留已存副本；相容性未知時標「未驗證」；不自動安裝依賴 | 同上；R-M02-11 只涵蓋已確認的「不安裝」邊界 |
| R-M02-22 | G04（模板版本、生成框架、UI 設計 schema）；S2 渲染與 golden14 還沒授權（`M02/planning/current-state.json` 的 `remaining`） | BDD-04：生成後的程式樹與 UI 樹，在路徑和 bytes 上都要等於預覽（F03-TDD-AC03-02） | 純計畫層由 R-M02-02 驗證；實際產物 oracle 不寫斷言 |
| R-M02-23 | G04（UI schema、模板 golden） | AC03「未實作區明示」，要有可見標記與 golden 比對（F03-TDD-AC03-03）。需求本身已確認，但標記格式還沒定 | 不以 ArtifactProduct 判別值代替可見標記 |
| R-M02-24 | G01 檔案與身分契約；DX5 原生多檔交易還沒驗證（`F03/feature-trace-preparation/feature-trace.json` F03-TDD-AC03-04） | 生成失敗不破壞原有效內容、已有檔案衝突不覆寫、列出殘留。已採納的失敗表見 `exact-design/module-spec.json#failure_matrix` | 不寫原生或 adapter 斷言；等 S2、S3 envelope 核准 |
| R-M02-25 | D05 還沒批准（`SPEC/index.html#defaults`）；F02 是「建議」 | 偏好預設不套用；主題與語言可沿用；技術與工具鏈要重新驗證；機器路徑、憑證不帶入 | 現有偏好 schema 沒有主題、語言、工具鏈欄位，不新增 |
| R-M02-26 | M01 精靈契約對齊（`docs/ci/wizard-contract-alignment/module-spec.json`：FULL_REGRESSION_BLOCKED） | 新建時套用偏好的三條成功路徑 WIZARD-01、02、03（略過、方案、矛盾選擇），要經精靈完成 | 屬 M01。M02 只把 legacy_* 拒絕測試當作回歸，不把拒絕當成功覆蓋 |

## 3. 已有測試對照

測試檔：W = `APP/crates/sgenaxis-work/tests/phase1_generation_plan.rs`，共 73 個測試；S = `APP/crates/sgenaxis-spec/tests/project_preferences.rs`；H = `APP/crates/sgenaxis-host/tests/project_preferences.rs`；HC = `APP/crates/sgenaxis-host/tests/project_preferences_creation.rs`；C = `APP/src-tauri/tests/project_preferences_commands.rs`。

| 規則 ID | 測試檔::函式 | 已涵蓋類別 | 缺口 |
|---|---|---|---|
| R-M02-01 | W::m02_t02_missing_topology / tentative_requirement / unresolved_requirement / empty_requirement_intent / missing_acceptance / open_decision / missing_toolchain / unresolved_ui；W::m02_t02_missing_projection_includes_topology_and_is_sorted_unique；W::oracle_missing_causes_* | 正常、無效、邊界（重複項去重） | 失敗類：「只保存定義」只是純值，沒有 HOST 實際保存與 UI 拒絕生成的證據（F03-TDD-AC03-01 gap） |
| R-M02-02 | W::m02_t01_complete_definition_yields_both_intents_without_mutation；W::m02_t08_artifacts_zero / one_lacks_ui / only_ui_product_rejected / artifacts_128_accepted | 正常、邊界、無效 | 失敗類：沒有實際產物 |
| R-M02-03 | W::m02_t03_unverified_approval_is_not_authority；W::m02_t03_verified_approval_identity_mismatch | 正常（SaveOnly）、無效 | 邊界：沒有「多個 approval 只滿足一部分」的測試 |
| R-M02-04 | W::m02_t04_template_id_mismatch / version_mismatch / digest_mismatch / context_template_mismatch / unknown_target_identity | 無效、正常（由 T01 涵蓋） | 邊界：沒有「version 只差大小寫或空白」的測試 |
| R-M02-05 | W::m02_t06_path_*（11 種）；W::m02_t06_casefold_collision_rejected；W::m02_t06_file_directory_prefix_collision_rejected；W::m02_t06_prefix_collision_with_intervening_sibling_is_rejected | 無效、邊界 | 無 |
| R-M02-06 | W::m02_t08_path_one_byte / 239 / 240 / 241_bytes / component_64 / 65 / 16 / 17_components / artifacts_129；W::m02_t08_invalid_definition_digest / approval_digest / base_digest | 邊界、無效、正常 | 無 |
| R-M02-07 | W::m02_t09_invalid_project_uuid / project_identity_mismatch / definition_revision_mismatch / duplicate_target_id / duplicate_requirement_id | 無效 | 邊界：沒有大小寫不同的 UUID |
| R-M02-08 | W::m02_t07_stale_*（9 種）；W::m02_t07_same_binding_is_valid | 正常、無效 | 邊界：沒有「base 從 None 變成 Some」的測試 |
| R-M02-09 | W::m02_t10_repeated_preparation_is_deterministic_and_sorted；T01 的不變性斷言 | 正常、邊界（反序輸入） | — |
| R-M02-10 | W::m02_f2_unsafe_path_precedes_missing_approval / invalid_identity_precedes_missing_topology / duplicate_target_precedes_unresolved_requirement | 正常、無效 | 邊界：沒有「兩種結構錯誤同時出現」時的優先序測試 |
| R-M02-11 | 無 | — | 全部缺：沒有任何測試證明生成不啟動外部程式，或模板 manifest 會拒絕 commands/install/scripts |
| R-M02-12 | S::unknown_fields_at_every_level_including_secrets_are_rejected；S::unknown_format_version_mode_and_missing_required_data_are_rejected；S::invalid_text_and_duplicate_json_keys_are_rejected；S::negative_fractional_overflow_and_wrong_types_are_rejected | 無效、邊界（u64 溢位）、正常（fixture） | — |
| R-M02-13 | S::invalid_models_and_preferred_membership_are_rejected；S::zero_limits_and_concurrency_above_batch_are_rejected；S::accepts_explicit_models_and_positive_budgets_without_normalizing_source；S::direct_struct_validation_cannot_bypass_policy_checks | 正常、邊界（1、u64::MAX）、無效 | 邊界：缺 maxConcurrent 等於 maxTasks 的測試 |
| R-M02-14 | S::presets_have_approved_limits_and_independent_custom_copies；S::unknown_preset_is_not_silently_substituted；S::unconfigured_policy_is_preserved_without_invented_model_or_budget；C::presets_and_import_preview_reuse_validated_schema_without_writing | 正常、無效 | 方案數值 1/1、4/2、8/4 只在測試裡找得到，沒有規格欄位出處 |
| R-M02-15 | H::missing_file_stays_unconfigured_and_does_not_write_defaults；save_reopen_and_project_isolation_use_exact_digest；stale_and_missing_digests_never_overwrite_existing_policy；externally_reformatted_bytes_invalidate_draft；invalid_root_and_invalid_draft_have_zero_writes；malformed_existing_preferences_are_not_reset_or_overwritten；permission_read_failure_is_explicit_not_unconfigured；write_failure_preserves_prior_valid_document；successful_write_with_mismatched_readback_returns_conflict；successful_write_with_readback_failure_returns_storage_error；HC::real_filesystem_project_preference_roundtrip；C::current_project_load_save_and_stale_digest | 正常、邊界（多一個 `\n`）、無效、失敗 | 原生測試只有 HC 一條 roundtrip |
| R-M02-16 | C::presets_and_import_preview_reuse_validated_schema_without_writing；C::imported_secret_field_is_rejected_without_source_mutation；C::unbound_or_stale_project_is_rejected_before_any_write | 正常、無效、失敗 | 邊界：沒有空檔或超大匯入檔的測試 |
| R-M02-17 | W::m02_t05_unsupported_platform、W::m02_t05_no_ui_does_not_silently_drop_ui_product、W::m02_t05_unsupported_framework；正常由 W::m02_t01_complete_definition_yields_both_intents_without_mutation 涵蓋 | 正常、邊界、無效 | 失敗類只靠 `reject!` 巨集的輸入不變檢查；沒有 architecture 或 language 不符的組合 |

（待決策 R-M02-18～26 不列可驗收對照。R-M02-26 的 C::legacy_* 三個測試只當作回歸保留。）

## 4. 測試矩陣

| 規則 ID | 類別 | 輸入 | 預期 | 層 |
|---|---|---|---|---|
| R-M02-01 | 正常 | 完整定義，只把 topology 改成 Unresolved | SaveDefinitionOnly{missing:["topology"]}，輸入不變 | work |
| R-M02-01 | 邊界 | open_decisions 為 ["topology","topology"]，另缺 approval | 缺項恰好是 ["approvalRefs","topology"]（已排序、已去重） | work |
| R-M02-01 | 無效輸入 | requirements[0].intent 為 " " | 缺項為 ["requirements[0].intent"] | work |
| R-M02-01 | 失敗 | 條件不足時呼叫 HOST 的 prepare（S2 核准後） | 不建立 `.sgenaxis/generated/`，寫入次數為 0，回 DefinitionOnly{missing} | host |
| R-M02-02 | 正常 | 完整 fixture | Prepared 同時含 Program 與 UiUx | work |
| R-M02-02 | 邊界 | 128 筆產物，或 1 筆 Program 加 1 筆 UiUx | 都接受 | work |
| R-M02-02 | 無效輸入 | 產物只有 UiUx，或只有 1 筆 Program | 拒絕，不產生計畫 | work |
| R-M02-02 | 失敗 | 0 筆，或 129 筆產物 | 回型別化錯誤，輸入不變 | work |
| R-M02-03 | 正常 | required_approvals_satisfied=true 且參照相符 | 放行並產生 Prepared | work |
| R-M02-03 | 邊界 | 有 approval 參照字串，但 satisfied=false | SaveOnly，缺項含 approvalRefs | work |
| R-M02-03 | 無效輸入 | verified_approval_refs 為 ["OTHER@1"] | ApprovalMismatch | work |
| R-M02-03 | 失敗 | 參照清空且未核實 | 不產生計畫，輸入不變 | work |
| R-M02-04 | 正常 | 模板與綁定完全一致 | Prepared | work |
| R-M02-04 | 邊界 | 只差 source_digest 的最後一個 hex 字元 | TemplateMismatch | work |
| R-M02-04 | 無效輸入 | template_ref.version 為 "2.0.0" | TemplateMismatch | work |
| R-M02-04 | 失敗 | context 的 template id 為 "other" | TemplateMismatch，不產生計畫，輸入不變 | work |
| R-M02-05 | 正常 | "program/src/main.rs" | 接受 | work |
| R-M02-05 | 邊界 | "PROGRAM/MAIN.RS" 與 "program/main.rs" 並存 | DuplicateArtifact（大小寫不敏感） | work |
| R-M02-05 | 無效輸入 | "../escape.rs"、"C:/x"、"program\\main.rs"、"program/CON.txt"、"program/name." | InvalidArtifactPath，帶 path 與非空的 reason | work |
| R-M02-05 | 失敗 | 檔案 "a" 與目錄前綴 "a/b" 衝突 | 拒絕，輸入不變 | work |
| R-M02-06 | 正常 | 路徑長 1 byte | 接受 | work |
| R-M02-06 | 邊界 | 240 bytes、元件 64、16 個元件 | 接受；241、65、17 則拒絕 | work |
| R-M02-06 | 無效輸入 | definition_digest 為 "sha256:Z"，approval_digest 為 "" | InvalidInput | work |
| R-M02-06 | 失敗 | base_activation_digest 為 Some("bad") | InvalidInput，不產生計畫 | work |
| R-M02-07 | 正常 | 合法的 v4 UUID，revision 一致 | Prepared | work |
| R-M02-07 | 邊界 | 兩個 target 同名但 ID 不同 | 接受，不依名稱合併 | work |
| R-M02-07 | 無效輸入 | project_uuid 為 "bad" | InvalidInput{field:"projectUuid"} | work |
| R-M02-07 | 失敗 | target 重複 | InvalidInput{field:"deliveryTargets[1].id"} | work |
| R-M02-08 | 正常 | 綁定相同 | Ok(()) | work |
| R-M02-08 | 邊界 | base_activation_digest 由 None 變成 Some(digest) | StaleBinding{field:"base_activation_digest"} | work |
| R-M02-08 | 無效輸入 | definition_revision 變成 2 | StaleBinding{field:"definition_revision"} | work |
| R-M02-08 | 失敗 | approval_digest 已變更，之後再確認生成（S2 核准後） | 拒絕確認，寫入次數為 0 | host |
| R-M02-09 | 正常 | 同一組輸入準備兩次 | 兩次結果相同 | work |
| R-M02-09 | 邊界 | 產物順序反轉 | 輸出依 relative_path 升冪 | work |
| R-M02-09 | 無效輸入 | 會觸發錯誤的輸入 | 錯誤發生後，輸入與錯誤前逐值相等 | work |
| R-M02-09 | 失敗 | 重複呼叫中第二次碰到 stale | 第一次的計畫不受影響 | work |
| R-M02-10 | 正常 | 路徑不安全，同時缺 approval | 先回 InvalidArtifactPath | work |
| R-M02-10 | 邊界 | UUID 無效，同時缺 topology | 先回 InvalidInput{projectUuid} | work |
| R-M02-10 | 無效輸入 | target 重複，同時有 Unresolved 需求 | 先回 InvalidInput，不回 SaveOnly | work |
| R-M02-10 | 失敗 | 同時有兩種結構錯誤 | 依 `pure_C_contract.order` 只回第一個（缺口，需補） | work |
| R-M02-11 | 正常 | 合法模板 manifest | 準備與生成都不呼叫行程、網路或安裝類 Port（用 spy 計數為 0） | host |
| R-M02-11 | 邊界 | manifest 帶空的 "scripts":[] | 拒絕（不允許這個欄位） | spec |
| R-M02-11 | 無效輸入 | manifest 帶 "commands" 或 "install" | 拒絕，來源 bytes 不變 | spec |
| R-M02-11 | 失敗 | 模板宣告依賴但本機沒有 | 不下載不安裝，回明確錯誤或缺項 | host |
| R-M02-12 | 正常 | 合法的 v1 fixture | 解析成功 | spec |
| R-M02-12 | 邊界 | maxInputTokens 為 18446744073709551616 | InvalidDocument（上限落在 u64 或 JS 安全整數**暫不斷言，見 §7**；現有測試只當回歸） | spec |
| R-M02-12 | 無效輸入 | 任何一層加 "token" | InvalidDocument | spec |
| R-M02-12 | 失敗 | formatVersion=2、重複 key、0xff bytes | 依序回 UnsupportedVersion、InvalidDocument、InvalidDocument | spec |
| R-M02-13 | 正常 | ["Model-A","Model-B"]，preferred 為 B，預算為 1 與 u64::MAX | 接受，來源 bytes 不變（u64::MAX 與「null＝未配置」兩點**暫不斷言，見 §7**） | spec |
| R-M02-13 | 邊界 | maxConcurrent 等於 maxTasks | 接受（缺口，需補） | spec |
| R-M02-13 | 無效輸入 | ["a","a"]、[" "]、preferred 不在清單、preferred 為 "" | InvalidPolicy | spec |
| R-M02-13 | 失敗 | 直接用 struct 把 max_tasks 設成 0 再呼叫 validate | InvalidPolicy | spec |
| R-M02-14 | 正常 | preset("balanced") | 回副本；改成 custom 並修改後，原方案不變（方案的具體數值**暫不斷言，見 §7**） | spec |
| R-M02-14 | 邊界 | 未配置的 fixture | 模型清單為空，mode 為 Suggest，confirmBeforeRun 為 true；「三項預算都是 None＝未配置」**暫不斷言（見 §7）** | spec |
| R-M02-14 | 無效輸入 | preset("missing") | UnknownPreset | spec |
| R-M02-14 | 失敗 | batch.mode 為 "automatic" | InvalidDocument | spec |
| R-M02-15 | 正常 | A、B 兩專案各自保存後重開 | 各自讀回，digest 等於檔案 bytes 的 sha256 | host |
| R-M02-15 | 邊界 | 外部在檔尾多加一個 "\n" | 拿舊 digest 保存回 Conflict | host |
| R-M02-15 | 無效輸入 | expected digest 為 None 或 "wrong" | Conflict，原 bytes 不變 | host |
| R-M02-15 | 失敗 | 注入寫入或讀取權限失敗 | 保留先前的有效文件；讀取失敗不當成未配置 | host |
| R-M02-16 | 正常 | 匯入合法的 balanced JSON | status 為 ok，寫入次數不變，來源 bytes 不變 | command |
| R-M02-16 | 邊界 | 匯入 0 byte 的檔案 | 拒絕且零寫入（缺口，需補） | command |
| R-M02-16 | 無效輸入 | 匯入含 "token" 欄位 | Err，來源不變 | command |
| R-M02-16 | 失敗 | 用 "/A" 對未綁定的 "/B" 保存 | Err，寫入次數為 0 | command |
| R-M02-17 | 正常 | 完整 fixture（desktop/windows-x64/rust/tauri2+vanilla/has_ui=true），綁 `local-tauri-vanilla` 1.0.0 | Prepared，同時含 Program 與 UiUx | work |
| R-M02-17 | 邊界 | 其他欄位相同，只把 has_ui 改成 false | UnsupportedTarget；不產生只剩 Program 的計畫 | work |
| R-M02-17 | 無效輸入 | platform 為 "linux-x64"；或 framework 為 "qt" | UnsupportedTarget | work |
| R-M02-17 | 失敗 | 任一不支援組合被拒之後 | 不產生計畫，definition／template／context 與呼叫前逐值相等 | work |

## 5. 開發段（RED）

- 前置條件：F02 與 F03 交付卡都還是 BLOCKED_PENDING_APPROVED_ENVELOPE_AND_VALID_RED。補任何測試前，要先取得 Owner 核准的精確 envelope；S1 的授權只涵蓋 `generation_plan.rs`、`lib.rs`、`phase1_generation_plan.rs` 三個檔（`SPEC/tasks/M02/s1/adoption.json` 的 `scope`）。
- 放置位置：
  - R-M02-01～10、17 的邊界缺口，補在 `APP/crates/sgenaxis-work/tests/phase1_generation_plan.rs`，沿用 `reject!`、`stale!`、`invalid_path!` 這幾個 macro。
  - R-M02-12～14 補在 `APP/crates/sgenaxis-spec/tests/project_preferences.rs`。
  - R-M02-15 補在 `APP/crates/sgenaxis-host/tests/project_preferences.rs`。
  - R-M02-16 補在 `APP/src-tauri/tests/project_preferences_commands.rs`。
  - R-M02-11 與 R-M02-01、08 的 host 失敗列，要等 S2 HOST envelope 核准後才寫；確切檔名由 envelope 指定，不要自己猜一個新的 cargo target。
- 先跑紅的指令：
  - `cargo test -p sgenaxis-work --test phase1_generation_plan --locked <新測試名>`，預期關鍵字為 `typed rejection required` 或 `assertion`…`left == right`，exit 101。
  - `cargo test -p sgenaxis-spec --test project_preferences --locked <新測試名>`，預期 `assertion failed`，exit 101。
  - 有效 RED 的條件：必須能編譯，fixture 自檢通過，然後因為行為缺失讓斷言失敗。編譯錯誤、fixture 錯誤、環境錯誤、逾時都不算 RED（`PD-P1-F03-DELIVERY-01.json` 的 `tdd.valid_red`）。
  - 注意：若補的邊界測試一跑就 GREEN（現有實作已經支援），要記錄為「回歸補強，非 RED」，不能宣稱是 RED。
- 禁止事項：
  - 不改規格、BDD、交付卡、決策卡。
  - 不把 R-M02-18～26 寫成可驗收斷言，也不擴充 UnsupportedTarget 的支援組合（R-M02-17 只認 DX6 的單一組合）。
  - 不對 §7 已知衝突寫斷言（方案數值、預算空白語意、u64 與 JS 上限）。
  - 不弱化或刪除既有的 73 個 W 測試與偏好測試的斷言，也不改 macro 的判定方式。
  - 不把 legacy_* 拒絕測試當成 WIZARD 成功路徑的覆蓋。
  - 不新增主題、語言、工具鏈這些偏好欄位（D05 還沒批准）。
  - 不 commit、不 push，不自行轉綠。

## 6. 驗證段

> 執行者不可以是寫這段程式的代理。

- 重跑指令（cwd 為 `apps/sgenaxis-desktop`）：
  - `cargo test -p sgenaxis-work --test phase1_generation_plan --locked`（基準 73 個，加上新增的測試）
  - `cargo test -p sgenaxis-spec --test project_preferences --locked`
  - `cargo test -p sgenaxis-host --test project_preferences --locked`
  - `cargo test -p sgenaxis-host --test project_preferences_creation --locked`（真實檔案系統，要在 Windows 上跑）
  - `cargo test -p sgenaxis-desktop --test project_preferences_commands --locked`
  - 相鄰回歸：`cargo test -p sgenaxis-work --test phase1_project_definition --locked`
- 介面實測步驟：本檔的規則都屬業務邏輯層，沒有自己的介面步驟。偏好面板與新建偏好對話框的操作驗證，請看 `ui-parameters.md`。生成預覽與生成按鈕的停用原因，要等 S2/S4 與 G04 核准後才有介面可測，目前記為 NOT RUN。
- 證據放置：
  - F03 相關的 R-M02-01～11、17 放 `reports/dispatch-pd/PD-P1-F03-DELIVERY-01-evidence/`。
  - F02 相關的 R-M02-12～16 放 `reports/dispatch-pd/PD-P1-F02-DELIVERY-01-evidence/`。
  - 每條規則記一筆，欄位為：規則／指令／Exit code／輸出末段（含 `test result:` 行）／介面證據（本檔一律寫 N/A）／判定。
  - 待決策的 R-M02-18～26 每條記為 `NOT RUN — 待決策`，不判 PASS；§7 標「暫不斷言」的列記為 `NOT RUN — 待看板決策卡`。
- 直接判 TDD_FAIL 的情況：
  - 任一既有測試被刪除、改名而沒有對照，或斷言被放寬（例如 `matches!` 改成 `is_err()`）。
  - 新測試把 G04、G01、D05 的待決內容寫成斷言，例如 DX6 以外的框架組合、模板副本 diff、主題欄位。
  - RED 證據其實是編譯、fixture 或環境錯誤，或者沒有原始 log、指令、exit code。
  - 執行驗證的代理就是寫程式的代理。
  - 拿純計畫層的 PASS 宣稱「骨架已生成」「UI 已驗證」或 F02/F03 整卡完成。
  - 修改了規格、決策卡或 envelope 以外的產品檔案。

## 7. 已知衝突

| 衝突 | 規格出處 | 實作出處 | 影響規則 ID | 處理 |
|---|---|---|---|---|
| 系統方案數值 保守 1/1、平衡 4/2、效率 8/4 沒有規格出處 | `docs/requirements-confirmation/requirements.json` RC-29 SET01（只講複製方案後調整，沒有數值）；`SPEC/index.html#defaults` D05 也沒有數值 | `APP/crates/sgenaxis-spec/src/project_preferences.rs:119-121`（`preset()`）；`APP/ui/project-preferences-ui.js:46`、`:65`（方案選單文字） | R-M02-14 | 暫不斷言，待看板決策卡 |
| 預算欄空白＝未配置（null），但 SET02 寫「儲存空白…要拒絕」 | `docs/requirements-confirmation/requirements.json:751` RC-29 SET02 | `APP/ui/project-preferences-ui.js:5`（預算空白回 null）；`APP/crates/sgenaxis-spec/src/project_preferences.rs:34-36`（`Option<u64>`，None 視為未配置） | R-M02-13、R-M02-14 | 暫不斷言，待看板決策卡 |
| 數值上限兩層不同：UI 用 JS 安全整數 2^53−1，Rust 用 u64 | 規格沒有數值上限（RC-29 SET02 只要求拒絕不合法上限） | `APP/ui/project-preferences-ui.js:7`（`Number.isSafeInteger`）；`APP/crates/sgenaxis-spec/src/project_preferences.rs:34-36`、`:42-43`（u64） | R-M02-12、R-M02-13 | 暫不斷言，待看板決策卡 |
