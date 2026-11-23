# M03 架構與UI設計：測試參考

> 範圍：F04 互動預覽的業務邏輯（自動開窗、預覽／成功狀態分離、往返一致性、預覽版本隔離）。
> `.sgendesign` 元件屬性與架構圖 Inspector 參數的 UI/UX 調整驗證不在本檔，由 `ui-parameters.md` 負責。
> 規格根目錄簡寫：`SPEC = docs/requirements-confirmation/phase1-spec/`；產品根目錄簡寫：`APP = apps/sgenaxis-desktop/`。
> 讀取基準：分支 `claude/skills-index-structure-f8398d`，HEAD `ef4896fa`。本檔撰寫時沒有執行任何產品測試。

## 1. 範圍與來源

| 功能 ID | 規格連結 | 交付卡 | BDD 場景 |
|---|---|---|---|
| F04 架構與UI設計互動預覽（整體狀態「建議採用」；只有標「確認」的子句已核准） | `SPEC/index.html` → 「F04 架構與UI設計互動預覽」段、「已確認需求基線」REQ-05／REQ-18／REQ-23、UX21～30 追溯列 | `SPEC/tasks/PD-P1-F04-DELIVERY-01.json`（BLOCKED_PENDING_APPROVED_ENVELOPE_AND_VALID_RED）；前置卡 `SPEC/tasks/PD-P1-M03-PREP-01.json` | `SPEC/phase1.feature` @BDD-05、@BDD-06（已確認）；`SPEC/tasks/M03/planning/module.feature` @BDD-M03-A、@BDD-M03-B（planning_only，屬提案） |
| F04 追溯（7 條 TDD 配方） | `SPEC/tasks/F04/feature-trace-preparation/feature-trace.json`（F04-TDD-AC04-01～07） | 同上 | AC04-01→BDD-05，AC04-02→BDD-06，AC04-03～07→X03（提案） |
| M03 規劃資料 | `SPEC/tasks/M03/planning/`：`module-spec.json`、`test-plan.json`、`envelope.json`、`decision-request.json`（D2/D3/D4）、`current-state.json`（CX_REVISION_PENDING_OWNER）、`roundtrip-evidence/`、`h2-exact-design/`、`media-fixture-bytes-20261115/` | — | X03（`SPEC/index.html` 補充案例表） |

## 2. 業務規則

### 已核准

| 規則 ID | 規則 | 規格出處 | 核准依據 |
|---|---|---|---|
| R-M03-01 | 有 UI 的專案成功生成雙骨架後，顯示建立結果時自動開啟內建 UI 設計視窗，並載入主要畫面。 | `SPEC/index.html` REQ-05（已確認）；F04「操作流程」的「確認：」子句；F04「邊界」的「自動開窗已確認」；`SPEC/phase1.feature` @BDD-05 | 正式核准 |
| R-M03-02 | 無 UI 的專案成功生成骨架後，不開啟多餘的 UI 設計視窗。 | `SPEC/index.html` REQ-05（已確認）；UX16～20 列「無UI不開窗已確認」；`SPEC/phase1.feature` @BDD-06 | 正式核准 |
| R-M03-03 | 設計未完成、功能未驗證時不得標為成功：設計檔、預覽建置結果與預覽畫面都不能表示產品或正式功能 PASS。 | `SPEC/index.html` REQ-23（已確認，追溯表對應 F03/F04/F08）；F04 驗收條件 AC04「假資料不顯示正式成功」只作為 F04 範圍的說明 | 正式核准 |

### 待決策

| 規則 ID | 卡在 | 目前選項 | 開發期處理 |
|---|---|---|---|
| R-M03-04 設計欄位往返：保存後重開，語義內容要完整，或明確拒絕未知版本，不能靜默丟欄位 | C1 保存契約等 Owner 一次確認（`M03/planning/c1-owner-packet/`、`cx-c1-revision-v3/`；`current-state.json` pending M03-CP1～CP4）；G01 設計 schema／版本 | 現況證據：`roundtrip-evidence/semantic-diff.json` 重現 4 個接受後遺失的案例：`/meta/guides`、根層未知欄位、節點未知欄位，以及 UI 自有欄位 gridSize/formSize/scope/uiExclusive。選項一是 C1 保留並帶 pointer 拒絕（CodecRejected），選項二是拒絕未知版本 | 不寫成斷言；probe 只當現況特徵化證據；等 C1 採納後才能把 BDD-M03-A 落成測試。HOST 存檔丟欄位屬已知衝突，暫不斷言（見 §7） |
| R-M03-05 預覽版本可辨：Viewer 顯示所依據的 revision；Editor 改到 R+1 後，舊 Viewer 要標成舊版，不能冒充最新 | AC04 提案（F04-TDD-AC04-04）；D07；G04；H2-D5／D6（`h2-exact-design/decisions.json`） | H2 提案：PreviewSession 綁定 immutable revision，revision 以十進位 u64 字串表示，active/stale 狀態 | 不寫成斷言；fixture 只能準備 R／R+1 兩版 |
| R-M03-06 Build 失敗時指出畫面／元件原因；若保留舊預覽，要明標舊版，且不寫正式資料 | F04「失敗處理」（建議）；D07；G04 支援矩陣；F04-TDD-AC04-07 | 現況：`APP/ui/app.js` 的 cmdUidesignBuild 只顯示泛用 `String(err)`。選項：結構化錯誤帶元件 ID（H2-D4 dto-errors） | 不寫成斷言 |
| R-M03-07 Viewer 用假資料，沒有副作用：不寫正式資料、不呼叫副作用服務，Viewer 也沒有寫入權 | F04「邊界」子句未標「確認」（整段狀態為建議採用）；D07；INV08（位於架構提案段）；H2-D5／D6 | H2 提案：六種節點的 mock 動作寫入 detached map，不做 dispatch/IO。現況：legacy `build_preview_file` 會寫出 `design/build/*.html` | 不寫成斷言；正式副作用 spy 只放在規劃 fixture |
| R-M03-08 選取一致：架構↔Editor 用穩定 ID 互相定位；引用失效時可以定位，但不能依同名猜測 | F04「資料影響／失敗處理」（建議）；G01 身分契約；H2-D1；F04-TDD-AC04-03 | 穩定 ID 雙向定位；遇到同名控制項時必須用 ID 判斷 | 不寫成斷言 |
| R-M03-09 不支援的節點或缺 Form 時唯讀並停用編輯、mock 與保存，不做靜默轉換 | H2-D3；G04 支援矩陣 | inert read-only placeholder | 不寫成斷言 |
| R-M03-10 文件權威與多視窗：同一份文件只有一個寫入者，其他視窗只投影 | D2（G01/G03）；H2-D1／D6；INV02（提案） | 方案一是 WORK/DispatchHost 持有 S1 DocumentSession；方案二是維持 UI 為唯一權威，但這需要修改架構規則 | 不寫成斷言；`commands.rs` 的 capability 測試只當回歸 |
| R-M03-11 Editor 事件隔離：Editor 不觸發 Viewer 事件；遇到未知動作顯示「未實作」 | D07；X03（補充義務，細則未定） | — | 不寫成斷言 |
| R-M03-12 缺綁定時停用相關互動並說明原因（MissingBinding，不新建 UUID、不做 IO） | F04「UI schema摘要」（建議）；H2-B001；G01 | — | 不寫成斷言 |
| R-M03-13 狀態分開呈現：已定義／已生成／預覽已建置／預覽過期／未實作／功能驗證 NOT RUN | F04「狀態」欄（整段為建議採用）；A05 | 上位原則已由 R-M03-03 核准；六態名稱與轉移規則尚未定 | 只有「不得標成功」這部分走 R-M03-03，六態本身不寫成斷言 |
| R-M03-14 快照包含 UI 設計與互動設定 | REQ-18 已確認，但屬 M07 主責，且依賴 G03 | — | M03 不寫斷言；交給 M07 |
| R-M03-15 媒體預覽格式矩陣 MM01～MM08（PNG/JPEG/受限 SVG 優先） | G04；D08 | `media-fixture-bytes-20261115/` 有 29 個合成檔，TDD_PASS 只證明文件身分；format/sdk/thresholds 都是 null | fixture 可以引用，但不能宣稱已支援解碼 |
| R-M03-16 Undo／capture fingerprint 排除 selection、viewport、playback | D4（G02/G03） | — | 不寫成斷言 |
| R-M03-17 「主要畫面」的身分判定方式（R-M03-01 的 oracle 細節） | G01 設計 schema；G04 模板；M02 生成結果身分 | F04 trace 提案：fixture 帶 immutable main screen ID | R-M03-01 只斷言「生成結果所指定的主要畫面」；不自訂判定規則 |

## 3. 已有測試對照

| 規則 ID | 測試檔::函式 | 已涵蓋類別 | 缺口 |
|---|---|---|---|
| R-M03-01 | （無） | 無 | 生成結果→原生視窗的交接點與主要畫面 oracle 都沒有測試。`uidesign_build_preview` 的 `open_after` 是另一個觸發點（Build 後用 OS 開 HTML），不算 |
| R-M03-02 | （無） | 無 | 沒有視窗清單差集的測試 |
| R-M03-03 | `APP/crates/sgenaxis-host/src/uidesign_doc.rs::tests::rejects_product_pass_true` | 無效輸入 | 只測 serialize；parse 端的拒絕只見於 roundtrip probe |
| R-M03-03 | `uidesign_doc.rs::tests::preview_contains_banner_and_node`、`build_preview_file_writes`、`roundtrip_sgendesign`（斷言 `!product_pass`）、`ask_draft_mentions_not_pass` | 正常 | 沒有邊界案例（例如空白標題、只含 root）；沒有測 command DTO `UiDesignBuildDto.product_pass=false`；沒有 UI 測試證明 Build 失敗或成功後的狀態不會顯示 PASS |
| R-M03-03 | （無） | 失敗 | Build validate 失敗後不產生檔案、不顯示成功：沒有測試 |
| R-M03-10（待決策，只當回歸） | `APP/src-tauri/src/commands.rs::tests::guard_owner_invoke_permission_isolated_to_main_capability` | — | 只證明 ui-editor/ui-viewer capability 不含 guard-owner 權限；不證明 Viewer 沒有寫入權 |
| G01 相鄰回歸（不計 M03 覆蓋） | `APP/crates/sgenaxis-host/tests/identity_preview.rs`（9 個測試）、`APP/crates/sgenaxis-spec/tests/identity_preview.rs`（6 個測試） | — | **不屬於 M03，標為 G01 相鄰回歸，不計入任何 M03 規則的覆蓋。** 它們測的是 `.sgendesign`/`.ess` 的唯讀「文件身分」檢查（IdentityState / StaleSource / DuplicateElementId），屬於 G01 檔案與身分契約範圍。名字裡的 preview 指身分預覽，不是 UI 設計預覽。F04 trace `commands.existing_identity_regression` 也註明「not trusted Viewer capability tests」。只能當相鄰回歸 |
| 非本模組 | 根目錄 `tests/test_pd_uidesign_spec_01.py`、`tests/test_pd_uidesigner_edit_p2.py` 等 | — | 只是靜態文字或控制項存在檢查，屬 UI/UX 範圍（`ui-parameters.md`）。`test-plan.json` 也註明「not behavior proof」 |

## 4. 測試矩陣

| 規則 ID | 類別 | 輸入 | 預期 | 層 |
|---|---|---|---|---|
| R-M03-01 | 正常 | 隔離 TEMP_ROOT 專案，M02 成功生成結果 `has_ui=true`，結果指定主要畫面 | 顯示建立結果時，UI 設計視窗開啟並載入該主要畫面（看得到主要畫面內容，並有原生視窗截圖） | ui（native 由 M08 驗證） |
| R-M03-01 | 邊界 | 有 UI，但主要畫面只有最小內容（只有 root Form） | 仍會開窗並載入該畫面，不因內容少而跳過 | ui |
| R-M03-01 | 無效輸入 | 交付目標的 `hasUi` 未決（`None`） | M02 生成門檻回報缺 `deliveryTargets[0].hasUi`，沒有「成功生成」，也不開 UI 設計視窗（依 REQ-05 前提「成功生成」推論；門檻本身由 M02 測試） | work + ui |
| R-M03-01 | 失敗 | `has_ui=true`，但生成失敗或未完成 | 不觸發自動開窗；建立結果不顯示成功、也不顯示已載入主要畫面（REQ-05 前提＋REQ-23） | ui |
| R-M03-02 | 正常 | M02 成功生成結果 `has_ui=false`，先記錄開窗前的視窗清單 | 顯示建立結果後，視窗清單差集為空 | ui（native 由 M08 驗證） |
| R-M03-02 | 邊界 | `has_ui=false`，而且 UI 設計視窗原本已由使用者開著 | 不新增任何 UI 設計視窗，差集仍為空 | ui |
| R-M03-02 | 無效輸入 | 建立結果缺 UI 旗標或旗標無法辨識 | 不把缺值當成「有 UI」來開窗（不開多餘視窗） | ui |
| R-M03-02 | 失敗 | `has_ui=false`，且生成失敗 | 不開 UI 設計視窗；顯示失敗原因，不顯示成功 | ui |
| R-M03-03 | 正常 | `DesignDoc::new_blank()` 序列化，並建置預覽 | `product_pass=false`；預覽 HTML 含 `PREVIEW_BANNER` 與 `product_pass=false` | host |
| R-M03-03 | 邊界 | 標題空白、只含 root 節點的設計 | 預覽仍含 banner 與 `product_pass=false`（標題用預設值），不因內容最小而省略非 PASS 標示 | host |
| R-M03-03 | 無效輸入 | 設計 JSON 或 `DesignDoc` 帶 `product_pass=true` | serialize 與 parse 都拒絕，錯誤訊息含 `product_pass`；不產生輸出檔 | host |
| R-M03-03 | 失敗 | Build 時 validate 失敗（例如格式錯或重複 ID） | `uidesign_build_preview` 回錯誤，不寫預覽檔；成功路徑的 DTO 一律 `product_pass=false`；UI 狀態列不顯示成功或 PASS | command + ui |

## 5. 開發段（RED）

- **放置位置**
  - R-M03-03：放在既有的 `APP/crates/sgenaxis-host/src/uidesign_doc.rs` `mod tests`（host），以及 `APP/src-tauri/src/commands.rs` 的 tests（command）。只能補邊界與失敗案例，不改既有斷言。
  - R-M03-01／02：新測試目標**尚未綁定**（F04 trace `new_feature_runner: UNBOUND_PENDING_OWNER_ENVELOPE_SKELETON`）。`envelope.json` 提議的 `APP/ui/design-preview-runtime.test.cjs`、`APP/crates/sgenaxis-host/tests/phase1_design_roundtrip.rs` 都還是 PROPOSED_NOT_APPROVED。要等 Owner 批准 envelope 與 Skeleton 後，才能在批准的路徑建檔。
- **先跑紅的指令**（cwd `APP`）
  - `cargo test -p sgenaxis-host --lib uidesign_doc::tests --locked`
  - 批准後的 UI 目標：`node --test ui/<批准檔名>.test.cjs`
- **有效 RED 的判定**：失敗輸出要是斷言失敗，例如 Rust 的 `assertion` / `left:` `right:`，或 node 的 `AssertionError`。下列都不算有效 RED：`error[E`（編譯失敗）、`Cannot find module`、fixture 自檢失敗、權限或環境錯誤、逾時。已經能通過的行為算回歸，不能偽造成 RED。
- **禁止事項**
  - 不改規格或規劃檔。
  - 不把 R-M03-04～17 寫成可驗收斷言（只可放 fixture 或特徵化紀錄）。
  - 不弱化既有斷言，例如不刪 `rejects_product_pass_true`、不放寬 banner 檢查。
  - 不把 `identity_preview` 測試當成 M03 覆蓋。
  - 不用 `open_after` 的 Build 開檔路徑代替 R-M03-01。
  - 不操作使用者真實專案（`fixtures.json` 的 safety 欄位）。

## 6. 驗證段

> 執行者不可以是寫這段程式的代理。

- **重跑指令**（cwd `APP`）
  - `cargo test -p sgenaxis-host --lib uidesign_doc::tests --locked`（R-M03-03 host）
  - `cargo test -p sgenaxis-desktop --lib commands::tests --locked`（R-M03-03 command；package 名 `sgenaxis-desktop`，取自 `src-tauri/Cargo.toml`）
  - 相鄰回歸：`cargo test -p sgenaxis-host --test identity_preview --locked`、`cargo test -p sgenaxis-spec --test identity_preview --locked`（兩者是 G01 相鄰回歸，不計 M03 覆蓋）、`cargo test -p sgenaxis-work --test phase1_generation_plan --locked`
  - R-M03-01／02：`node --test ui/<批准檔名>.test.cjs`（envelope 批准後才有）
- **介面實測步驟**
  1. 用隔離的 TEMP_ROOT 建兩個專案：A 是有 UI，B 是無 UI。
  2. 每次建立前記錄原生視窗清單。
  3. 完成建立，並顯示建立結果。
  4. A：截圖證明 UI 設計視窗已開，且顯示主要畫面內容。
  5. B：截圖並記錄視窗清單差集為空。
  6. 執行 Build 成功與 Build 失敗各一次，截圖狀態列與預覽，證明都看不到產品 PASS 或成功字樣。
- **證據**：放在 `reports/dispatch-pd/PD-P1-F04-DELIVERY-01-evidence/`。每條規則一筆，欄位為：規則／指令／Exit code／輸出末段／介面證據（截圖或錄影路徑、視窗清單 before/after）／判定。
- **直接判 TDD_FAIL 的情況**
  - 任一已核准規則缺少四類中的任何一類，或沒有實際執行紀錄。
  - RED 屬於編譯、fixture 或環境失敗。
  - 為了通過而改弱既有斷言。
  - 待決策規則被寫成通過或失敗的斷言。
  - 用 `identity_preview` 或靜態 Python 測試冒充 M03 覆蓋。
  - 用元件測試冒充原生 UI 結果。
  - 任何畫面或 DTO 出現 `product_pass=true` 或成功字樣。
  - 驗證者與實作者是同一個代理。

## 7. 已知衝突

| 衝突 | 規格出處 | 實作出處 | 影響規則 ID | 處理 |
|---|---|---|---|---|
| Designer 經 HOST 存檔（`design/main.sgendesign`）會丟掉 `meta.gridSize`、`meta.formSize`、`meta.guides` 與節點 `properties`；規劃要求保存後重開不得靜默丟欄位 | `SPEC/tasks/M03/planning/c1-owner-packet/`（C1 保存契約，待 Owner）；現況重現 `SPEC/tasks/M03/planning/roundtrip-evidence/semantic-diff.json` | `APP/crates/sgenaxis-host/src/uidesign_doc.rs:16-23`（`DesignMeta` 只有 title／updatedAt／targetStack）、`:30-44`（`DesignNode` 沒有 properties）；`APP/src-tauri/src/commands.rs:4471`（`uidesign_save_design`）；JS 寫入端 `APP/ui/app.js:13346`、`:13366`、`:13457` | R-M03-04（待決策，§4 無列） | 暫不斷言，待看板決策卡 |
