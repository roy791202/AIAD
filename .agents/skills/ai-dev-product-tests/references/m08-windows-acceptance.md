# M08 Windows驗收整合（跨模組驗收與 Build Result）：測試參考

> 規格根目錄縮寫：`SPEC/` = `docs/requirements-confirmation/phase1-spec/`；`TASKS/` = `SPEC/tasks/`；`M08P/` = `TASKS/M08/planning/`。
> 本模組不擁有任何業務狀態（`SPEC/index.html` 模組表 M08 列：「驗證紀錄；不持業務權威狀態」）。其他模組的單一規則一律以 `R-M0x-*` 引用，並附規格錨點（REQ/BDD）；`R-M0x-` 後的確切流水號以各模組參考檔為準，本檔不重新定義。

## 1. 範圍與來源
| 功能 ID | 規格連結 | 交付卡 | BDD 場景 |
|---|---|---|---|
| M08（整合驗收，無自有功能；`feature_refs: []`） | `SPEC/index.html`「整體驗收與證據要求」A01～A08 表；「模組工作切片」P5 列 | `TASKS/PD-P1-M08-VERIFY-01.json`（BLOCKED_PENDING_MODULE_DELIVERIES）；準備卡 `TASKS/PD-P1-M08-PREP-01.json`（`M08P/current-state.json`：PREPARATION_ACCEPTED_SCOPE_ONLY） | `SPEC/phase1.feature` @BDD-32；`SPEC/index.html` 補充組 X08；`M08P/module.feature`（BDD-32、BDD-M08-A，planning_only） |
| REQ-01（交付平台） | `SPEC/index.html` 需求基線 REQ-01；追溯表 REQ-01→M08/F12→BDD-32; X08→A07 | VERIFY-01；F12 為 `TASKS/PD-P1-F12-DELIVERY-01.json`（M07 擁有） | @BDD-32、X08 |
| REQ-23（第一階段範圍） | `SPEC/index.html` REQ-23；追溯表 REQ-23→M08/F03/F04/F08→A06/A08 | VERIFY-01；F03/F04/F08 交付卡 | X02/X03/X06/X08 + boundary review |
| F01～F12（作為驗收輸入，不由 M08 實作） | `TASKS/M08/verification/input-admission-correction-20261103/feature-input-matrix.json`（每個 F 的 trace/review 指標） | `TASKS/PD-P1-F01..F12-DELIVERY-01.json`（VERIFY-01 `dependencies`） | 各 F 自有 BDD；M08 只引用 |
| 原生案例 M08-N01～N16（規劃，未執行） | `M08P/native-evidence-plan/case-matrix.json`、`module-spec.json`；對照 `TASKS/M08/verification/input-admission-correction-20261103/native-case-crosswalk.json` | PREP-01（規劃產物）；VERIFY-01 執行 | `M08P/native-evidence-plan/module.feature` @M08-N01..N16（planning_only） |

## 2. 業務規則
### 已核准
| 規則 ID | 規則 | 規格出處 | 核准依據 |
|---|---|---|---|
| R-M08-01 | 必要驗收只認實體 Windows 11 x64；Windows 10（含目前開發機 10.0.19045）結果不得代替。 | `SPEC/index.html` REQ-01（「Windows 10 未承諾支援」）、X08（「實體Windows11 x64」）；VERIFY-01 `contract[0]` | 正式核准 |
| R-M08-02 | 交付形態為免安裝版；免安裝驗收不得冒稱 MSI／silent installer 驗證成功。 | VERIFY-01 `acceptance[2]`；`SPEC/index.html` P5 列與 A 表下註「免安裝版驗證不冒稱silent install成功」 | 正式核准 |
| R-M08-03 | 驗收必須用本次 build/package 出的鎖定 artifact，並記錄 artifact hash、依賴版本、Windows 版本（含 WebView2）；不得以既有／歷史 artifact 代替。 | `SPEC/index.html` A07；VERIFY-01 `tdd.command`、`steps[1]`；`M08P/consolidated-decisions.json` D7（方向 ADOPTED：「Windows11 x64/WebView2實測＋新artifact lock」「舊binary驗新需求不可採」） | 正式核准 |
| R-M08-04 | 只操作隔離測試專案與唯讀來源副本；來源與使用者資料隔離，不碰使用者專案與既有 release artifact。 | VERIFY-01 `contract[0]`、`protected_files`；`M08P/module.feature` 背景 | 正式核准 |
| R-M08-05 | 必須有免安裝「啟動」與「搬移後再啟動」的實際結果，並記錄執行檔實際路徑與使用者資料區位置（復原內容是否可見另見 R-M08-20）。 | `SPEC/index.html` A07（「免安裝啟動／搬移／使用者資料區結果」）；VERIFY-01 `steps[2]` | 正式核准 |
| R-M08-06 | X08 五類情境（移動 portable、唯讀專案、離線磁碟、多程序、程序強制終止）每類都要有一筆結果紀錄（已執行結果，或 BLOCKED／NOT RUN 加原因），不可省略。各情境預期結果見 R-M08-21。 | `SPEC/index.html` 補充組 X08；VERIFY-01 `steps[2]`、`tdd.scenarios` | 正式核准 |
| R-M08-07 | NOT RUN／PARTIAL／FAIL 不可改寫成 PASS；文件靜態 PASS 不能代替產品結果；不可虛構測試通過率。 | VERIFY-01 `acceptance[1]`；`SPEC/index.html` A08、A 表下註 | 正式核准 |
| R-M08-08 | Build Result 必須逐項列出 A01～A08，每項都有證據或明確狀態；並交付 build-result、compatibility-report、regression-results、milestone-review 四件。 | VERIFY-01 `acceptance[0]`、`deliverables`；`SPEC/index.html` A01～A08 表 | 正式核准 |
| R-M08-09 | REQ-01～23 每條都有「模組→BDD/TDD／補充案例→版本化結果」追溯；局部建議要另外批准，不能混入已確認需求的結果。 | `SPEC/index.html` A01；「完整需求追溯與驗證義務」表 | 正式核准 |
| R-M08-10 | 沒選 DCC 宿主時不虛構 DCC 驗證；DCC 相關實機驗證列 NOT RUN，或經確認列 N/A。 | VERIFY-01 `acceptance[3]`；`SPEC/index.html` P5 列 | 正式核准 |
| R-M08-11 | M08 沒有發布或 Git 寫入授權：不 release、不 commit/push、不自動綠燈；release 等獨立授權。 | VERIFY-01 `contract[1]`、`acceptance[4]`、`steps[4]`；`SPEC/index.html` P5 列 | 正式核准 |
| R-M08-12 | 整合卡不虛構 aggregate RED；RED 由各對應模組各自獨立證明。 | VERIFY-01 `tdd.valid_red` | 正式核准 |
| R-M08-13 | F01～F12 交付還沒被獨立接受前，不執行原生驗收；對應列為 BLOCKED，文件 trace PASS 不等於依賴已滿足。 | VERIFY-01 `dependencies`、`status`；`TASKS/M01/planning/dispatch-next-actions-20261103/next-m08-task.json` `dependency_semantics`；`.../input-admission-correction-20261103/missing-inputs.json` | 正式核准 |
| R-M08-14 | 第一階段驗收不把 AI 任務執行、Git 協作、Plugin 安裝列為第一階段功能 PASS；設計未完成或功能未驗證不得標成功。 | `SPEC/index.html` REQ-23；追溯表 REQ-23→A06/A08 | 正式核准 |
| R-M08-15 | 跨模組與系統回歸都要執行，每個失敗都要分類（模組、原因、是否阻擋）；獨立審查／Acceptance 才算完成。 | VERIFY-01 `steps[3]`；`SPEC/index.html` A08、測試層級 L4/L5 | 正式核准 |
| R-M08-26（原列待決策） | 每筆結果只能用五值之一：PASS／FAIL／BLOCKED／NOT RUN／PARTIAL。判 PASS 必須在輸出中確認測試真的執行（不是 skip 或 NOT RUN），不能只看 exit code。BLOCKED 與 FAIL 的精確界線（HR04）、紀錄格式 `m08.native-evidence.v1`、證據層 E0～E4、HR01～HR12 仍屬 M08-PD2，不在本條 | `.agents/skills/ai-dev-pipeline/references/project.md`「建置結果用 PASS／FAIL／BLOCKED／NOT RUN／PARTIAL」；L3 決策 3 | 正式核准（`.agents/skills/ai-dev-pipeline/references/project.md`） |

### 待決策
| 規則 ID | 卡在 | 目前選項 | 開發期處理 |
|---|---|---|---|
| R-M08-20 | G03（快照）＋G01（穩定 Project ID） | BDD-32「搬移後使用者資料區快照仍可找到並復原」；方向 D1/D4/D6 已採納，精確設計待審。結果判定引用 R-M07-*（REQ-17/REQ-22） | 只寫 BLOCKED 紀錄（缺 G03／M07 runtime），不寫斷言 |
| R-M08-21 | G03＋G01 | X08／N02～N06：唯讀與離線可另存、雙 session 不互蓋、強制終止後提供最後成功快照、寫入中斷不啟用半成品（引用 R-M07-*：REQ-17～20） | 每案例只保留 BLOCKED 列與前置清單（`case-matrix.json` prerequisite） |
| R-M08-22 | G02＋G03 | N13：合併／Undo 進行中觸發檢查，只擷取完成或完整回復狀態、一次 Undo、共用素材保留（引用 R-M04-*、R-M05-*、R-M06-*、R-M07-*） | BLOCKED，不寫斷言 |
| R-M08-23 | G01（＋M06 交付） | N14：明確接受的不完整匯入可檢視／保存，依賴它的執行與生成要阻擋（引用 R-M06-*：REQ-13） | BLOCKED |
| R-M08-24 | G03 | N15：移除歷史項目後文件／快照／素材位元組不變（引用 R-M07-*：REQ-22） | BLOCKED |
| R-M08-25 | G04 | 雙骨架生成與 UI 預覽的原生驗收、相容報告的模板／媒體列（方向 D3 已採納，矩陣未定；引用 R-M02-*、R-M03-*） | 相容報告該列標 NOT RUN（G04 未定） |
| R-M08-26（剩餘部分；五值已移到已核准） | M08-PD2（未核准；`M08P/precision-correction/decisions.json`） | BLOCKED 和 FAIL 的界線（HR04：前置未滿足判 BLOCKED，前置滿足後失敗判 FAIL）、紀錄格式 `m08.native-evidence.v1`、證據層 E0～E4、HR01～HR12（`M08P/harness-contract/record-fields.json`、`record-invariants.json`，皆 PROPOSED） | 只斷言五值本身與「確認真的執行」；界線、schema、證據層檢查不寫成斷言 |
| R-M08-27 | M08-PD1（未核准） | UI 不阻塞的量化門檻：30 輸入／30 秒、p95 ≤ 250ms、max ≤ 1000ms 等（`responsiveness-oracles.json`）；質性規則屬 R-M07-*（REQ-20） | 不寫量測斷言；N08 列 BLOCKED |
| R-M08-28 | M08-PD3（未核准） | 核准後只先建立 `tests/test_p1_portable_acceptance.py` Skeleton 與純 checker RED；N01～N16 另外阻擋 | 檔案還不存在（`validator-contract.json` `current_file_exists: false`）；不得先建 |
| R-M08-29 | D7 精確設計（EXACT_DESIGN_REVIEW_PENDING） | N10：WebView2 缺失時要明確顯示前置條件結果，不得假造啟動成功；「approved dependency handling」未定 | 只記錄 WebView2 版本或 ABSENT（R-M08-03）；行為不寫斷言 |
| R-M08-30 | M08-PD2 | 復原情境要用獨立測試帳號／profile，不改真實 `%LOCALAPPDATA%`，也不假設有 test-data-dir override（HR07） | 沒有隔離帳號前，復原相關原生案例一律 BLOCKED |

## 3. 已有測試對照
> 結論：**目前沒有任何測試涵蓋第一階段 M08 規則**。下表列的都是第一階段之前（M2／PD-REL）的測試，只能當模式參考，不算覆蓋。

| 規則 ID | 測試檔::函式 | 已涵蓋類別 | 缺口 |
|---|---|---|---|
| R-M08-07 | `tests/test_pd_rel_03_verify_install.py::test_verify_install_ps1_marks_elevated_not_run_without_elevation`、`::test_verify_install_does_not_run_elevated_when_flag_absent_even_if_admin` | 模式參考：非提權時 overall 只能是 PARTIAL／NOT RUN | 對象是 MSI（PD-REL-03），不是第一階段 portable Build Result；正常、邊界、無效、失敗四類都沒有 |
| R-M08-07 | `tests/test_pd_rel_artifacts_01.py::test_artifacts_inventory_marks_missing_and_not_run`、`::test_artifacts_inventory_anti_unsigned_pass_forge`、`::test_sign_stub_status_is_not_run` | 模式參考：簽章維持 NOT RUN | 對象是舊 release inventory，不是 phase1 |
| R-M08-07（反例） | `apps/sgenaxis-desktop/crates/sgenaxis-host/tests/m2_e2e_loop.rs::m2_e2e_std_git_summarize_or_not_run`、`::m2_e2e_std_board_load_or_not_run`；`crates/sgenaxis-exec/tests/live_cli_smoke.rs::live_cli_smoke_start_chunk_exit_or_skip`（feature `real-spawn`）；`live_mcp_smoke.rs::live_mcp_smoke_connect_tool_or_skip`（feature `real-mcp`） | 無（屬 M2 AI 執行／Git，依 R-M08-14 不在第一階段） | **風險**：NOT RUN 只印在 stderr，cargo 仍回報 `ok`／exit 0。Build Result 不能只看 exit code，否則 NOT RUN 會被當成 PASS |
| R-M08-02 | `tests/test_pd_harness_portable_01.py`（4 個函式） | 無 | 測的是瀏覽器 mock harness（`tools/harness/portable`），不是 Windows portable artifact |
| R-M08-03 | （無測試）`packaging/windows/portable/README.md` 只有 2026-10-25 的歷史 hash | 無 | 依 R-M08-03，歷史 hash 只能用來辨識檔案，不能證明 artifact 合格 |
| R-M08-01、04、05、06、08～13、15 | 無 | 無 | 全缺；`tests/test_p1_portable_acceptance.py` 尚未建立（R-M08-28） |
| R-M08-14 | 無 | 無 | 缺「第一階段 Build Result 不含 AI／Git／Plugin PASS 列」檢查 |
| R-M08-26 | 無（`m2_e2e_loop.rs`、`live_cli_smoke.rs`、`live_mcp_smoke.rs` 是反例模式：stderr 印 NOT RUN／skip 後 `return`，cargo 仍回 `ok`） | 無 | 全缺：沒有「判定值必須是五值之一」與「exit 0 但輸出顯示 skip／NOT RUN 時不得判 PASS」的檢查 |

## 4. 測試矩陣
> 層：spec＝Build Result／紀錄／追溯文件的靜態檢查；command＝實際 build/package/回歸命令；ui＝實體 Win11 原生操作。

| 規則 ID | 類別 | 輸入 | 預期 | 層 |
|---|---|---|---|---|
| R-M08-01 | 正常 | 紀錄 OS_build 為 Win11、arch x64、實機 | 可作為必要驗收證據 | spec |
| R-M08-01 | 邊界 | Win11 但 arch=arm64，或在 VM／未確認實機 | 不算必要驗收；標 BLOCKED 並寫原因 | spec |
| R-M08-01 | 無效輸入 | OS_build=10.0.19045（Win10）卻宣稱 Win11 PASS | 拒絕這個宣稱 | spec |
| R-M08-01 | 失敗 | 無法取得 OS 版本 | 結果不得是 PASS；列缺前置 | spec |
| R-M08-02 | 正常 | portable 驗收紀錄，沒有安裝器欄位 | 報告寫「免安裝」，silent install 列 NOT RUN 或 N/A | spec |
| R-M08-02 | 邊界 | 同版本也有 MSI artifact | portable 結果不能沿用到 MSI 列 | spec |
| R-M08-02 | 無效輸入 | 報告用 portable 結果宣稱「silent install PASS」 | 拒絕 | spec |
| R-M08-02 | 失敗 | 解壓或啟動失敗 | portable 列 FAIL（前置已滿足時），不改去引用安裝器結果 | ui |
| R-M08-03 | 正常 | 本次 build 的 artifact，紀錄的 hash 和實際執行檔 hash 相同，並有依賴與 WebView2 版本 | 可引用 | command |
| R-M08-03 | 邊界 | hash 和 README 的歷史 hash 相同，但沒有本次 build 紀錄 | 只算辨識，不算合格 | spec |
| R-M08-03 | 無效輸入 | 缺 artifact hash 或依賴版本欄位 | 拒絕 | spec |
| R-M08-03 | 失敗 | 啟動前後 hash 不一致（中途被換掉） | 該次結果作廢，重新鎖定 artifact | command |
| R-M08-04 | 正常 | 只用拋棄式目錄與唯讀來源副本 | 跑完後來源 hash 前後相同 | ui |
| R-M08-04 | 邊界 | 測試根目錄路徑前綴和沙箱相同，但其實不在沙箱內 | 不可只看前綴；不能證明擁有權就 BLOCKED | spec |
| R-M08-04 | 無效輸入 | 測試根目錄指向使用者真實專案 | 拒絕執行 | spec |
| R-M08-04 | 失敗 | 執行後來源 hash 改變 | FAIL 並保留證據；不自動清理 | ui |
| R-M08-05 | 正常 | 把 portable 從 A 搬到 B 再啟動 | 有實際結果：執行檔路徑是 B，使用者資料區位置有記錄 | ui |
| R-M08-05 | 邊界 | 路徑含空白與非 ASCII 字元（N16 位置） | 啟動結果有記錄；不依賴開發者 checkout | ui |
| R-M08-05 | 無效輸入 | 只有啟動結果，沒有搬移結果 | A07 不得標 PASS（最多 PARTIAL） | spec |
| R-M08-05 | 失敗 | 搬移後啟動失敗 | FAIL（前置已滿足）並保留 log | ui |
| R-M08-06 | 正常 | 五類情境各有一列 | 完整 | spec |
| R-M08-06 | 邊界 | 五列都是 BLOCKED 且都有原因 | 合格紀錄，但 X08 整體不是 PASS | spec |
| R-M08-06 | 無效輸入 | 少了「強制終止」這一列 | 拒絕 | spec |
| R-M08-06 | 失敗 | 某列狀態是 BLOCKED 但原因空白 | 拒絕 | spec |
| R-M08-07 | 正常 | 所有項目都已執行且通過 | 整體可寫 PASS | spec |
| R-M08-07 | 邊界 | 全部 PASS，只有一項 NOT RUN | 整體不得是 PASS（最多 PARTIAL） | spec |
| R-M08-07 | 無效輸入 | 某項把 NOT RUN 改寫成 PASS；或只靠 cargo exit 0 就判 PASS，而 stderr 有 NOT RUN | 拒絕 | spec |
| R-M08-07 | 失敗 | 只有文件靜態 PASS，沒有產品結果 | 不能代替產品結果；產品列維持 NOT RUN | spec |
| R-M08-08 | 正常 | A01～A08 八列都有證據，四件交付物齊全 | 完整 | spec |
| R-M08-08 | 邊界 | 八列都在，其中 A06 標 NOT RUN 並附原因 | 合格，但整體不是 PASS | spec |
| R-M08-08 | 無效輸入 | 缺 A05 列，或缺 compatibility-report | 拒絕 | spec |
| R-M08-08 | 失敗 | 某列有引用但證據檔不存在 | 該列判無證據；不得 PASS | spec |
| R-M08-09 | 正常 | REQ-01～23 二十三列都有追溯 | 完整 | spec |
| R-M08-09 | 邊界 | REQ-23 只對應 boundary review（沒有 BDD） | 接受，依規格追溯表 | spec |
| R-M08-09 | 無效輸入 | 把建議項（例如 D01 保留政策）當已確認需求列 PASS | 拒絕 | spec |
| R-M08-09 | 失敗 | 某 REQ 沒有版本化結果 | 該 REQ 標 NOT RUN；A01 不得 PASS | spec |
| R-M08-10 | 正常 | 沒選 DCC 宿主，DCC 列 NOT RUN | 接受 | spec |
| R-M08-10 | 邊界 | DCC 列 N/A 並有確認紀錄 | 接受 | spec |
| R-M08-10 | 無效輸入 | 沒選宿主，DCC 列卻是 PASS | 拒絕 | spec |
| R-M08-10 | 失敗 | DCC 列 N/A 但沒有確認紀錄 | 改回 NOT RUN | spec |
| R-M08-11 | 正常 | 驗收跑完，git 狀態與 release 目錄都沒變 | 合格 | command |
| R-M08-11 | 邊界 | 全部 PASS | 只寫 release 建議，不發布 | spec |
| R-M08-11 | 無效輸入 | 流程含 `git commit`／`git push`／發布步驟 | 拒絕 | spec |
| R-M08-11 | 失敗 | 驗收後發現 HEAD 或看板燈號被改 | TDD_FAIL；回報 | command |
| R-M08-12 | 正常 | 每個模組的 RED 都引用該模組自己的證據 | 接受 | spec |
| R-M08-12 | 邊界 | 某模組不需要 RED（N/A）且有理由 | 接受 | spec |
| R-M08-12 | 無效輸入 | 整合卡自己寫一個 aggregate RED | 拒絕 | spec |
| R-M08-12 | 失敗 | 用缺原生環境當作 RED | 拒絕（環境缺失不是有效 RED） | spec |
| R-M08-13 | 正常 | F01～F12 都已被獨立接受 | 可開始原生驗收 | spec |
| R-M08-13 | 邊界 | 11 個已接受，1 個未接受 | 和未接受功能有關的案例 BLOCKED；不推論整體 | spec |
| R-M08-13 | 無效輸入 | 用文件 trace PASS 當產品已接受 | 拒絕 | spec |
| R-M08-13 | 失敗 | 依賴未滿足卻仍啟動原生驗收 | 結果作廢 | spec |
| R-M08-14 | 正常 | 第一階段 Build Result 沒有 AI／Git／Plugin 功能 PASS 列 | 接受 | spec |
| R-M08-14 | 邊界 | M2 測試（如 m2_e2e_loop）在回歸中通過 | 只放在回歸附錄，不算第一階段功能 | spec |
| R-M08-14 | 無效輸入 | 用 live_cli_smoke 結果當第一階段功能驗收 | 拒絕 | spec |
| R-M08-14 | 失敗 | 未驗證功能標成功 | 拒絕 | spec |
| R-M08-15 | 正常 | `cargo test --workspace` 與 UI node 測試全部執行並記錄 | regression-results 完整 | command |
| R-M08-15 | 邊界 | 有 feature-gated 測試（real-spawn／real-mcp）沒跑 | 列 NOT RUN 並寫 feature 名稱 | command |
| R-M08-15 | 無效輸入 | 失敗項目沒有分類 | 拒絕 | spec |
| R-M08-15 | 失敗 | 回歸有失敗 | 分類到模組；整體不得 PASS | command |
| R-M08-26 | 正常 | 每筆紀錄的判定是 PASS／FAIL／BLOCKED／NOT RUN／PARTIAL 之一，PASS 列的輸出末段有實際執行的測試數 | 接受 | spec |
| R-M08-26 | 邊界 | `cargo test -p sgenaxis-host --test m2_e2e_loop` exit 0，但 stderr 有 `NOT RUN` | 判 NOT RUN，不是 PASS | command |
| R-M08-26 | 無效輸入 | 判定寫成 `SKIP`、`OK`、`GREEN` 或空白 | 拒絕 | spec |
| R-M08-26 | 失敗 | 輸出是 `test result: ok. 0 passed`（全部被 filter 或 skip）卻判 PASS | 拒絕，改判 NOT RUN | spec |

## 5. 開發段（RED）
- **目前狀態**：M08 不能開始 RED。原因是 M08-PD1～PD3 還沒核准（`M08P/current-state.json` `next`），而且 F01～F12 都沒交付（R-M08-13）。
- **放置位置（核准後）**：只有 `tests/test_p1_portable_acceptance.py`（`M08P/precision-correction/validator-contract.json` `proposed_file`；目前不存在）。範圍只限純 checker（Build Result／紀錄靜態檢查，對應第 4 段 spec 層的列）。原生 N01～N16 不寫成可執行斷言。
- **先跑紅的指令**：`python -m pytest tests/test_p1_portable_acceptance.py -q`（repo 根目錄；來源：`M08P/native-evidence-plan/module-spec.json` `planned_automation.future_command`）。M08 的 harness 規劃用 Python，所以不是 `cargo test`／`node --test`。
- **預期失敗關鍵字**：`AssertionError` 或 `NotImplementedError`，表示 checker 行為還沒實作。以下都**不算**有效 RED：`ModuleNotFoundError`、`collected 0 items`、fixture 缺失、缺 Win11／WebView2 環境（`M08P/harness-contract/validator-test-plan.json` `valid_RED`）。
- **禁止事項**：
  - 不改規格、交付卡、case-matrix 的原本語意。
  - R-M08-20～25、27～30 與 R-M08-26 的剩餘部分不寫成斷言；只能寫 BLOCKED 紀錄或 `pytest.skip("BLOCKED: <卡在>")`，並附原因。
  - 不弱化斷言，例如把「整體不得 PASS」放寬成「允許 PASS」。
  - 不建 aggregate RED（R-M08-12）。
  - 不改任何產品原始碼或其他模組測試。
  - 不 build、不 package、不啟動歷史 binary。
  - 不 commit／push。

## 6. 驗證段
> 執行者不可以是寫這段程式的代理。

- **重跑指令**：
  - M08 checker：`python -m pytest tests/test_p1_portable_acceptance.py -q`（核准建立後才有）。
  - 跨模組回歸（R-M08-15）：在 `apps/sgenaxis-desktop/` 執行 `cargo test --workspace`。逐檔加跑本卡相關目標，例如 `cargo test -p sgenaxis-host --test m2_e2e_loop`。另外跑 `node --test ui/project-document-ui.test.cjs`、`node --test ui/project-preferences-ui.test.cjs`、`node --test ui/git-index-commit-ui.test.cjs`。
  - feature-gated 測試要逐一標記：`cargo test -p sgenaxis-exec --features real-spawn --test live_cli_smoke`、`--features real-mcp --test live_mcp_smoke`。沒跑就列 NOT RUN。
  - **確認真的執行，不只看 exit code**（R-M08-26）：判 PASS 前，輸出末段要有實際執行的測試數（`test result: ok. N passed`，N>0），且 stdout／stderr 沒有 `NOT RUN`、`skip` 字樣。`m2_e2e_loop`（`m2_e2e_std_git_summarize_or_not_run`、`m2_e2e_std_board_load_or_not_run`）、`live_cli_smoke_start_chunk_exit_or_skip`、`live_mcp_smoke_connect_tool_or_skip` 缺前置時會印 NOT RUN 後 `return`，cargo 仍回 exit 0；出現這種 skip 語意就直接判 NOT RUN。
  - 各模組 focused 命令依該模組參考檔第 6 段。
- **介面實測步驟**（只在 R-M08-13 依賴都滿足，且在實體 Win11 x64 上）：
  1. 記錄 OS build、arch、WebView2 版本。
  2. 用核准的 build 命令產生 artifact，記錄 hash 與依賴（R-M08-03）。
  3. 建立拋棄式沙箱與測試帳號，記錄來源副本 hash（R-M08-04；帳號規則待 R-M08-30）。
  4. 從資料夾 A 啟動，記錄執行檔路徑與資料區位置。
  5. 複製到含空白與非 ASCII 字元的資料夾 B 再啟動（R-M08-05）。
  6. 依 X08 五類情境逐一操作或標 BLOCKED（R-M08-06、R-M08-21）。
  7. 比對來源 hash 前後；只清理自己擁有的沙箱。
  8. 截圖或錄影要和同一 run_id／PID／執行檔 hash 綁在一起。
- **證據**（L3 決策 2）：
  - 截圖、錄影與原始 log 放 `reports/dispatch-pd/PD-P1-M08-VERIFY-01-evidence/`（`reports/` 不進 git，依 `.agents/skills/ai-dev-pipeline/references/project.md`）。
  - 驗收結論寫在 `TASKS/M08/verification/`（VERIFY-01 的 `allowed_files` 範圍），結論裡引用上面證據的檔名與 hash。
  - 每條規則一筆，欄位如下：

  | 規則 | 指令 | Exit code | 輸出末段 | 介面證據 | 判定 |
  |---|---|---|---|---|---|
  | R-M08-xx | 實際指令或手動步驟 | 數字 | 最後 20 行（含 stderr NOT RUN） | 截圖／錄影路徑＋run_id／PID／hash，或「無介面」 | PASS／FAIL／BLOCKED／NOT RUN／PARTIAL（R-M08-26）；BLOCKED／NOT RUN 要附原因（R-M08-06）；BLOCKED 與 FAIL 的精確界線（HR04）仍待 M08-PD2 |

- **直接判 TDD_FAIL 的情況**：
  - 任何 NOT RUN／PARTIAL／FAIL 或文件靜態 PASS 被寫成 PASS（R-M08-07）。
  - Win10 或其他非 Win11 x64 結果被當作必要驗收（R-M08-01）。
  - 用歷史或其他 artifact 代替本次版本，或 hash 對不上（R-M08-03）。
  - 用 portable 宣稱 silent install 成功（R-M08-02）。
  - 來源或使用者資料被改動（R-M08-04）。
  - DCC 沒選宿主卻標 PASS（R-M08-10）。
  - 出現 commit／push／release 或看板自動綠燈（R-M08-11）。
  - 出現 aggregate RED（R-M08-12）。
  - 依賴未接受就執行原生驗收（R-M08-13）。
  - 判定不是五值之一，或只憑 exit code 判 PASS、輸出其實是 skip／NOT RUN／0 passed（R-M08-26）。
  - `m2_e2e_loop`、`live_cli_smoke`、`live_mcp_smoke` 印出 NOT RUN／skip 卻記成 PASS（這類結果一律直接判 NOT RUN）。
  - 待決策規則 R-M08-20～25、27～30 或 R-M08-26 的剩餘部分被寫成斷言。
  - 驗證者和開發者是同一個代理。

## 7. 已知衝突

| 衝突 | 規格出處 | 實作出處 | 影響規則 ID | 處理 |
|---|---|---|---|---|
| 目前無（UI token 與最小視窗的衝突見 `ui-parameters.md` §7；M08 原生驗收引用時同樣暫不斷言） | — | — | — | — |
