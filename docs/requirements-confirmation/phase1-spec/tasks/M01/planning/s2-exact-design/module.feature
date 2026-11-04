Feature: M01 safe definition persistence
  Background:
    Given a user explicitly selected an authorized local project operation
    And existing source files remain independent originals

  @M01-S2-B001 @M01-S2-T001
  Scenario: 六個步驟未完成草稿往返
    Given 每個步驟的合法未完成定義與extensions
    When 將定義保存表示再讀回
    Then 所有WORK欄位與步驟一致、不生成任何骨架

  @M01-S2-B002 @M01-S2-T002
  Scenario: mode_draft
    Given 合法mode=draft，尚有未決技術欄位
    When 讀回定義
    Then mode與未決值保留，不推定批准或執行生成

  @M01-S2-B003 @M01-S2-T003
  Scenario: mode_defined
    Given 合法mode=defined，尚有未決技術欄位
    When 讀回定義
    Then mode與未決值保留，不推定批准或執行生成

  @M01-S2-B004 @M01-S2-T004
  Scenario: revision_0
    Given definitionRevision為字串0
    When 讀回定義
    Then revision精確保留、不增量也不經浮點

  @M01-S2-B005 @M01-S2-T005
  Scenario: revision_18446744073709551615
    Given definitionRevision為字串18446744073709551615
    When 讀回定義
    Then revision精確保留、不增量也不經浮點

  @M01-S2-B006 @M01-S2-T006
  Scenario: 拒絕非法revision_01
    Given revision為'01'
    When 讀回定義
    Then 明確拒絕且不產生部分值

  @M01-S2-B007 @M01-S2-T007
  Scenario: 拒絕非法revision_+1
    Given revision為'+1'
    When 讀回定義
    Then 明確拒絕且不產生部分值

  @M01-S2-B008 @M01-S2-T008
  Scenario: 拒絕非法revision_-1
    Given revision為'-1'
    When 讀回定義
    Then 明確拒絕且不產生部分值

  @M01-S2-B009 @M01-S2-T009
  Scenario: 拒絕非法revision_18446744073709551616
    Given revision為'18446744073709551616'
    When 讀回定義
    Then 明確拒絕且不產生部分值

  @M01-S2-B010 @M01-S2-T010
  Scenario: 拒絕非法revision_1
    Given revision為1
    When 讀回定義
    Then 明確拒絕且不產生部分值

  @M01-S2-B011 @M01-S2-T011
  Scenario: FieldState保留_unresolved
    Given topology狀態與value有可表示組合
    When 往返定義
    Then 狀態/value精確保留；confirmed空字串仍可列缺決策

  @M01-S2-B012 @M01-S2-T012
  Scenario: FieldState保留_tentative
    Given topology狀態與value有可表示組合
    When 往返定義
    Then 狀態/value精確保留；confirmed空字串仍可列缺決策

  @M01-S2-B013 @M01-S2-T013
  Scenario: FieldState保留_confirmed
    Given topology狀態與value有可表示組合
    When 往返定義
    Then 狀態/value精確保留；confirmed空字串仍可列缺決策

  @M01-S2-B014 @M01-S2-T014
  Scenario: FieldState拒絕_unresolved
    Given 狀態與value不可表示
    When 讀回定義
    Then 拒絕而非丟value/自動補值

  @M01-S2-B015 @M01-S2-T015
  Scenario: FieldState拒絕_tentative
    Given 狀態與value不可表示
    When 讀回定義
    Then 拒絕而非丟value/自動補值

  @M01-S2-B016 @M01-S2-T016
  Scenario: FieldState拒絕_confirmed
    Given 狀態與value不可表示
    When 讀回定義
    Then 拒絕而非丟value/自動補值

  @M01-S2-B017 @M01-S2-T017
  Scenario: nullable_false_區分
    Given hasUi分別null或false，template為null
    When 往返定義
    Then None與Some(false)不混淆、template不補預設

  @M01-S2-B018 @M01-S2-T018
  Scenario: 完整target_requirement_template
    Given 含各FieldState、requirement、template與approvalRefs的定義
    When 往返定義
    Then 所有已定義欄位保留但不認證approvalRefs

  @M01-S2-B019 @M01-S2-T019
  Scenario: 保留數字token_-0
    Given extensions包含合法數字-0
    When 往返定義
    Then 數字token文字精確保留、不變成浮點近似或字串欄位

  @M01-S2-B020 @M01-S2-T020
  Scenario: 保留數字token_1.00
    Given extensions包含合法數字1.00
    When 往返定義
    Then 數字token文字精確保留、不變成浮點近似或字串欄位

  @M01-S2-B021 @M01-S2-T021
  Scenario: 保留數字token_1E+03
    Given extensions包含合法數字1E+03
    When 往返定義
    Then 數字token文字精確保留、不變成浮點近似或字串欄位

  @M01-S2-B022 @M01-S2-T022
  Scenario: 保留數字token_18446744073709551616
    Given extensions包含合法數字18446744073709551616
    When 往返定義
    Then 數字token文字精確保留、不變成浮點近似或字串欄位

  @M01-S2-B023 @M01-S2-T023
  Scenario: 保留數字token_0.123456789012345678901234567890
    Given extensions包含合法數字0.123456789012345678901234567890
    When 往返定義
    Then 數字token文字精確保留、不變成浮點近似或字串欄位

  @M01-S2-B024 @M01-S2-T024
  Scenario: extension_tree_private_key
    Given extensions有null/bool/string/array/object及名為$serde_json::private::Number的普通key
    When 往返定義
    Then 樹、順序與普通key保留、不誤當內部marker

  @M01-S2-B025 @M01-S2-T025
  Scenario: 拒未知欄位_futureRoot
    Given v1已知結構含額外欄位futureRoot
    When 讀回定義
    Then 明確拒絕、不靜默忽略

  @M01-S2-B026 @M01-S2-T026
  Scenario: 拒未知欄位_deliveryTargets[0].future
    Given v1已知結構含額外欄位deliveryTargets[0].future
    When 讀回定義
    Then 明確拒絕、不靜默忽略

  @M01-S2-B027 @M01-S2-T027
  Scenario: 拒未知欄位_template.future
    Given v1已知結構含額外欄位template.future
    When 讀回定義
    Then 明確拒絕、不靜默忽略

  @M01-S2-B028 @M01-S2-T028
  Scenario: 必填不得默認
    Given 每次移除一個v1必填欄位
    When 讀回定義
    Then MissingField，不能補預設而丟失來源意義

  @M01-S2-B029 @M01-S2-T029
  Scenario: 拒絕_bad_utf8
    Given 來源含bad_utf8
    When 讀回定義
    Then 精確錯誤分類且來源保持不變

  @M01-S2-B030 @M01-S2-T030
  Scenario: 拒絕_bom
    Given 來源含bom
    When 讀回定義
    Then 精確錯誤分類且來源保持不變

  @M01-S2-B031 @M01-S2-T031
  Scenario: 拒絕_malformed
    Given 來源含malformed
    When 讀回定義
    Then 精確錯誤分類且來源保持不變

  @M01-S2-B032 @M01-S2-T032
  Scenario: 拒絕_duplicate_root
    Given 來源含duplicate_root
    When 讀回定義
    Then 精確錯誤分類且來源保持不變

  @M01-S2-B033 @M01-S2-T033
  Scenario: 拒絕_duplicate_extensions
    Given 來源含duplicate_extensions
    When 讀回定義
    Then 精確錯誤分類且來源保持不變

  @M01-S2-B034 @M01-S2-T034
  Scenario: 拒絕_unsupported_version
    Given 來源含unsupported_version
    When 讀回定義
    Then 精確錯誤分類且來源保持不變

  @M01-S2-B035 @M01-S2-T035
  Scenario: 拒絕_unsupported_schema
    Given 來源含unsupported_schema
    When 讀回定義
    Then 精確錯誤分類且來源保持不變

  @M01-S2-B036 @M01-S2-T036
  Scenario: 驗證優先序
    Given future版本同時帶未知欄位；另一案future版本帶duplicate key
    When 讀回定義
    Then 前案UnsupportedSchema；後案DuplicateKey優先

  @M01-S2-B037 @M01-S2-T037
  Scenario: 界限_name_chars
    Given 以其他條件合法的定義分別到達[1, 120, 121]
    When 讀回定義
    Then 界內接受、界外明確ResourceLimit或InputTooLarge；不把fixture錯當RED

  @M01-S2-B038 @M01-S2-T038
  Scenario: 界限_input_bytes
    Given 以其他條件合法的定義分別到達[16777215, 16777216, 16777217]
    When 讀回定義
    Then 界內接受、界外明確ResourceLimit或InputTooLarge；不把fixture錯當RED

  @M01-S2-B039 @M01-S2-T039
  Scenario: 界限_json_depth
    Given 以其他條件合法的定義分別到達[63, 64, 65]
    When 讀回定義
    Then 界內接受、界外明確ResourceLimit或InputTooLarge；不把fixture錯當RED

  @M01-S2-B040 @M01-S2-T040
  Scenario: 界限_json_value_nodes
    Given 以其他條件合法的定義分別到達[99999, 100000, 100001]
    When 讀回定義
    Then 界內接受、界外明確ResourceLimit或InputTooLarge；不把fixture錯當RED

  @M01-S2-B041 @M01-S2-T041
  Scenario: 界限_decoded_string_bytes
    Given 以其他條件合法的定義分別到達[1048575, 1048576, 1048577]
    When 讀回定義
    Then 界內接受、界外明確ResourceLimit或InputTooLarge；不把fixture錯當RED

  @M01-S2-B042 @M01-S2-T042
  Scenario: 界限_number_token_bytes
    Given 以其他條件合法的定義分別到達[4095, 4096, 4097]
    When 讀回定義
    Then 界內接受、界外明確ResourceLimit或InputTooLarge；不把fixture錯當RED

  @M01-S2-B043 @M01-S2-T043
  Scenario: output_bytes界限
    Given 既有WORK樹可輸出剛好16MiB與多1byte
    When 保存為wire表示
    Then 到達界限仍合法，多1byte拒絕，不回部分bytes

  @M01-S2-B044 @M01-S2-T044
  Scenario: 候選拒絕_blank_name
    Given WORK候選或wire含blank_name
    When 要求編碼或讀回
    Then 精確欄位拒絕、輸入值不變

  @M01-S2-B045 @M01-S2-T045
  Scenario: 候選拒絕_invalid_project_uuid
    Given WORK候選或wire含invalid_project_uuid
    When 要求編碼或讀回
    Then 精確欄位拒絕、輸入值不變

  @M01-S2-B046 @M01-S2-T046
  Scenario: 候選拒絕_duplicate_target_uuid
    Given WORK候選或wire含duplicate_target_uuid
    When 要求編碼或讀回
    Then 精確欄位拒絕、輸入值不變

  @M01-S2-B047 @M01-S2-T047
  Scenario: 候選拒絕_blank_requirement_id
    Given WORK候選或wire含blank_requirement_id
    When 要求編碼或讀回
    Then 精確欄位拒絕、輸入值不變

  @M01-S2-B048 @M01-S2-T048
  Scenario: 候選拒絕_invalid_template_digest
    Given WORK候選或wire含invalid_template_digest
    When 要求編碼或讀回
    Then 精確欄位拒絕、輸入值不變

  @M01-S2-B049 @M01-S2-T049
  Scenario: 候選拒絕_absolute_legacy_alias
    Given WORK候選或wire含absolute_legacy_alias
    When 要求編碼或讀回
    Then 精確欄位拒絕、輸入值不變

  @M01-S2-B050 @M01-S2-T050
  Scenario: 候選拒絕_invalid_number_candidate
    Given WORK候選或wire含invalid_number_candidate
    When 要求編碼或讀回
    Then 精確欄位拒絕、輸入值不變

  @M01-S2-B051 @M01-S2-T051
  Scenario: 新建skip
    Given 新位置不存在、合法部分草稿、偏好Skip
    When 首次明確保存
    Then 獨佔建立root/metadata與完整definition；無prefs/生成/active bind

  @M01-S2-B052 @M01-S2-T052
  Scenario: 新建_preset
    Given 合法定義與已驗證preset偏好，來源有快照
    When 首次明確保存
    Then definition先提交，偏好後提交且可讀回；來源原樣

  @M01-S2-B053 @M01-S2-T053
  Scenario: 新建_imported_copy
    Given 合法定義與已驗證imported_copy偏好，來源有快照
    When 首次明確保存
    Then definition先提交，偏好後提交且可讀回；來源原樣

  @M01-S2-B054 @M01-S2-T054
  Scenario: 偏好預檢_unknown_preset
    Given 請求有unknown_preset
    When 準備偏好及保存
    Then 錯誤發生在任何目錄/lease寫入之前

  @M01-S2-B055 @M01-S2-T055
  Scenario: 偏好預檢_invalid_import
    Given 請求有invalid_import
    When 準備偏好及保存
    Then 錯誤發生在任何目錄/lease寫入之前

  @M01-S2-B056 @M01-S2-T056
  Scenario: 偏好預檢_plan_source_mismatch
    Given 請求有plan_source_mismatch
    When 準備偏好及保存
    Then 錯誤發生在任何目錄/lease寫入之前

  @M01-S2-B057 @M01-S2-T057
  Scenario: 不得覆寫_file
    Given 新建目標為file
    When 明確保存新專案
    Then ExistingTarget且完整原樹不變，競爭案在exclusive create發生

  @M01-S2-B058 @M01-S2-T058
  Scenario: 不得覆寫_empty_directory
    Given 新建目標為empty_directory
    When 明確保存新專案
    Then ExistingTarget且完整原樹不變，競爭案在exclusive create發生

  @M01-S2-B059 @M01-S2-T059
  Scenario: 不得覆寫_nonempty_directory
    Given 新建目標為nonempty_directory
    When 明確保存新專案
    Then ExistingTarget且完整原樹不變，競爭案在exclusive create發生

  @M01-S2-B060 @M01-S2-T060
  Scenario: 不得覆寫_race_created_target
    Given 新建目標為race_created_target
    When 明確保存新專案
    Then ExistingTarget且完整原樹不變，競爭案在exclusive create發生

  @M01-S2-B061 @M01-S2-T061
  Scenario: 更新existing
    Given 已保存definition與匹配raw digest，WORK已連續修改多次
    When 保存捕獲revision
    Then 提交捕獲內容與revision，不再加一，不改prefs/history

  @M01-S2-B062 @M01-S2-T062
  Scenario: 同revision無變更
    Given 捕獲內容與已存同revision完全語意一致
    When 再次明確保存
    Then 允許相同revision完整提交，receipt有新IO txid

  @M01-S2-B063 @M01-S2-T063
  Scenario: 同revision變更
    Given 內容改了但捕獲revision未前進
    When 要求保存
    Then 寫前拒絕RevisionNotAdvanced

  @M01-S2-B064 @M01-S2-T064
  Scenario: 較舊revision
    Given 捕獲revision低於opened baseline
    When 要求保存
    Then 寫前拒絕且不清baseline

  @M01-S2-B065 @M01-S2-T065
  Scenario: 格式外部修改
    Given 磁碟只有格式/空白變更，語意仍相同
    When 以舊raw digest保存
    Then 仍RevisionConflict，不以重編碼digest放行

  @M01-S2-B066 @M01-S2-T066
  Scenario: 存在性_expected_present_now_absent
    Given 存在性與expected不符
    When 要求保存
    Then 不覆寫或建立正式目標

  @M01-S2-B067 @M01-S2-T067
  Scenario: 存在性_expected_absent_now_present
    Given 存在性與expected不符
    When 要求保存
    Then 不覆寫或建立正式目標

  @M01-S2-B068 @M01-S2-T068
  Scenario: expected參數不可越權
    Given 呼叫者expected digest與私有binding baseline不一致
    When 要求保存
    Then 在任何IO寫前拒絕

  @M01-S2-B069 @M01-S2-T069
  Scenario: UUID不可換
    Given 捕獲definition UUID不等於binding UUID
    When 要求保存
    Then 不重映射、不觸FS寫入

  @M01-S2-B070 @M01-S2-T070
  Scenario: 移動root保留ID
    Given saved definition在另一原生選定root，無其他opened claim
    When 唯讀開啟
    Then 持久UUID與revision不變、legacy aliases不改

  @M01-S2-B071 @M01-S2-T071
  Scenario: 重複UUID不同root
    Given 可信opened claims含同UUID於另一root
    When 唯讀開啟或建立binding
    Then IdentityConflict，不以名稱猜測或自動copy

  @M01-S2-B072 @M01-S2-T072
  Scenario: 讀取失敗不是legacy
    Given definition read遇PermissionDenied或其他非NotFound錯誤
    When 唯讀開啟
    Then StorageFailure而非Legacy，不生成UUID

  @M01-S2-B073 @M01-S2-T073
  Scenario: 讀中來源變更
    Given definition兩次讀到的raw bytes不同
    When 唯讀開啟
    Then 拒絕混版snapshot/digest

  @M01-S2-B074 @M01-S2-T074
  Scenario: legacy唯讀
    Given root有ESS/manifest/prefs但無definition
    When 唯讀開啟
    Then Legacy migration_required，0寫入且不自動UUID

  @M01-S2-B075 @M01-S2-T075
  Scenario: adoptLegacy
    Given owner明確授權adopt且提供trustedUUID，definition仍不存在
    When 保存遷移定義
    Then 只新增definition/缺少metadata，ESS/manifest/prefs原樣

  @M01-S2-B076 @M01-S2-T076
  Scenario: adopt遇definition競爭
    Given 預覽後definition被他人建立
    When 明確adopt
    Then expectedNone衝突，來源不變、不覆寫

  @M01-S2-B077 @M01-S2-T077
  Scenario: metadata被檔案佔用
    Given legacy .sgenaxis是含資料檔案
    When 明確adopt
    Then 拒絕且原檔保留

  @M01-S2-B078 @M01-S2-T078
  Scenario: ordinary_fault_CreateRoot
    Given 合法新建，於CreateRoot注入可回復故障
    When 保存專案
    Then 結果依root取得/definition提交進度分類，exact ledger與protected hashes

  @M01-S2-B079 @M01-S2-T079
  Scenario: ordinary_fault_CreateMetadata
    Given 合法新建，於CreateMetadata注入可回復故障
    When 保存專案
    Then 結果依root取得/definition提交進度分類，exact ledger與protected hashes

  @M01-S2-B080 @M01-S2-T080
  Scenario: ordinary_fault_CommitDefinition
    Given 合法新建，於CommitDefinition注入可回復故障
    When 保存專案
    Then 結果依root取得/definition提交進度分類，exact ledger與protected hashes

  @M01-S2-B081 @M01-S2-T081
  Scenario: ordinary_fault_CommitPreferences
    Given 合法新建，於CommitPreferences注入可回復故障
    When 保存專案
    Then 結果依root取得/definition提交進度分類，exact ledger與protected hashes

  @M01-S2-B082 @M01-S2-T082
  Scenario: recovery_fault_CommitDefinition
    Given CommitDefinition回傳精確RecoveryRequired診斷
    When 保存專案
    Then 頂層RecoveryRequired與原路徑保留，不能降成Partial；prefs案含definition proof

  @M01-S2-B083 @M01-S2-T083
  Scenario: recovery_fault_CommitPreferences
    Given CommitPreferences回傳精確RecoveryRequired診斷
    When 保存專案
    Then 頂層RecoveryRequired與原路徑保留，不能降成Partial；prefs案含definition proof

  @M01-S2-B084 @M01-S2-T084
  Scenario: prefs外部collision
    Given definition已提交但prefs被外部建立
    When 結束新建保存
    Then Partial有definition proof且prefs外部bytes不變、不回滾definition

  @M01-S2-B085 @M01-S2-T085
  Scenario: leaseBusy
    Given existing definition被另一writer持有
    When 要求保存
    Then Busy且不重試/不刪鎖

  @M01-S2-B086 @M01-S2-T086
  Scenario: 捕獲證據不越權安裝
    Given 提交完後caller切換session或編輯更高revision
    When 讀取保存回傳
    Then 只證明舊捕獲revision；S2未改caller的active owner/baseline

  @M01-S2-B087 @M01-S2-T087
  Scenario: 新建重送
    Given 同root首次建立已成功但無S3 request cache
    When 再次以NewProject保存
    Then ExistingTarget；不隱式重做或開啟

  @M01-S2-B088 @M01-S2-T088
  Scenario: 端口隔離
    Given same-FS commit double、HOST FS spy拒絕write/mkdir/remove
    When 完成正常或故障保存
    Then HOST只讀FS、寫入全由commit Port，fault reached且沒有跨目標寫入

  @M01-S2-B089 @M01-S2-T089
  Scenario: 未知格式保存前拒絕
    Given 磁碟v1未知欄位或版本且被選為existing
    When 開啟後要求保存
    Then 不靜默刪未知欄位，不建立active binding

  @M01-S2-B090 @M01-S2-T090
  Scenario: 跨平台證據界線
    Given Windows10 native IO與尚未完成Windows11 gate
    When 評估S2交付
    Then 不把fake/Win10測試當Windows11驗收

  @M01-S2-B091 @M01-S2-T091
  Scenario: 舊入口_create_new_project_root_absent
    Given 合法舊新建請求，目標absent
    When 透過舊HOST新建入口
    Then WizardRequired且全部FS方法0次、原樹不變；不直接建專案

  @M01-S2-B092 @M01-S2-T092
  Scenario: 舊入口_create_new_project_root_existing_file
    Given 合法舊新建請求，目標existing_file
    When 透過舊HOST新建入口
    Then WizardRequired且全部FS方法0次、原樹不變；不直接建專案

  @M01-S2-B093 @M01-S2-T093
  Scenario: 舊入口_create_new_project_root_existing_directory
    Given 合法舊新建請求，目標existing_directory
    When 透過舊HOST新建入口
    Then WizardRequired且全部FS方法0次、原樹不變；不直接建專案

  @M01-S2-B094 @M01-S2-T094
  Scenario: 舊入口_create_new_project_under_absent
    Given 合法舊新建請求，目標absent
    When 透過舊HOST新建入口
    Then WizardRequired且全部FS方法0次、原樹不變；不直接建專案

  @M01-S2-B095 @M01-S2-T095
  Scenario: 舊入口_create_new_project_under_existing_file
    Given 合法舊新建請求，目標existing_file
    When 透過舊HOST新建入口
    Then WizardRequired且全部FS方法0次、原樹不變；不直接建專案

  @M01-S2-B096 @M01-S2-T096
  Scenario: 舊入口_create_new_project_under_existing_directory
    Given 合法舊新建請求，目標existing_directory
    When 透過舊HOST新建入口
    Then WizardRequired且全部FS方法0次、原樹不變；不直接建專案

  @M01-S2-B097 @M01-S2-T097
  Scenario: 舊入口_create_project_with_preferences_absent
    Given 合法舊新建請求，目標absent
    When 透過舊HOST新建入口
    Then WizardRequired且全部FS方法0次、原樹不變；不直接建專案

  @M01-S2-B098 @M01-S2-T098
  Scenario: 舊入口_create_project_with_preferences_existing_file
    Given 合法舊新建請求，目標existing_file
    When 透過舊HOST新建入口
    Then WizardRequired且全部FS方法0次、原樹不變；不直接建專案

  @M01-S2-B099 @M01-S2-T099
  Scenario: 舊入口_create_project_with_preferences_existing_directory
    Given 合法舊新建請求，目標existing_directory
    When 透過舊HOST新建入口
    Then WizardRequired且全部FS方法0次、原樹不變；不直接建專案

  @M01-S2-B100 @M01-S2-T100
  Scenario: 舊非法名稱仍拒絕
    Given path/name為非法值
    When 經root舊wrapper執行唯讀語法檢查
    Then 保留原驗證錯誤與zeroFS，不再觸發create

  @M01-S2-B101 @M01-S2-T101
  Scenario: 三路由靜態追溯
    Given 三個Tauri handler與既有Dispatch呼叫
    When 核對轉接計畫
    Then S2未修改Tauri/DTO；三條路最終S3都必須導向精靈

  @M01-S2-B102 @M01-S2-T102
  Scenario: 沒有binding授權脈絡
    Given empty selection/session/window context
    When 核對或執行宣告的S2操作
    Then NotBound，不變更其他owner與檔案

  @M01-S2-B103 @M01-S2-T103
  Scenario: native拒絕location
    Given existing acquire returns CommitError.InvalidPath
    When 核對或執行宣告的S2操作
    Then InvalidLocation(path,reason,retained=[])，不變更其他owner與檔案

  @M01-S2-B104 @M01-S2-T104
  Scenario: root取得後native拒絕
    Given new definition acquire returns CommitError.InvalidPath
    When 核對或執行宣告的S2操作
    Then PartialProjectCreated(cause=InvalidLocation,root_created=true)，不變更其他owner與檔案

  @M01-S2-B105 @M01-S2-T105
  Scenario: rollback後ordinarystage保留
    Given existing commit returns Storage VerifyPublished after verified rollback
    When 核對或執行宣告的S2操作
    Then StorageFailure(original stage=VerifyPublished)，不變更其他owner與檔案

  @M01-S2-B106 @M01-S2-T106
  Scenario: S3之外不聲稱caller授權
    Given static authorization ownership audit
    When 核對或執行宣告的S2操作
    Then S2 precondition recorded; UI UnauthorizedCaller deferred S3，不變更其他owner與檔案

  @M01-S2-B107 @M01-S2-T107
  Scenario: 提交證據不一致_CommitDefinition
    Given CommitDefinition回報的成功receipt與請求矛盾
    When 結束本次保存
    Then 明示無法確認提交證據，不切換專案或清理；偏好階段保留已確認定義

  @M01-S2-B108 @M01-S2-T108
  Scenario: 提交證據不一致_CommitPreferences
    Given CommitPreferences回報的成功receipt與請求矛盾
    When 結束本次保存
    Then 明示無法確認提交證據，不切換專案或清理；偏好階段保留已確認定義

