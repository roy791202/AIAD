# language: zh-TW
Feature: 由已核准封包生成統一模組 HTML（ModuleSpec 投影）
  Primary module: module-engineering-projection
  Card: PD-RUST-MODULE-HTML-01
  Authority: existing SPEC ModuleSpecDocument + approved-a-contract + product-documents audit
  Note: 不新增競爭 schema SSOT；投影為 derived 表面

  Background:
    Given 已核准模組契約及受控輸入（DOCUMENT-CONTRACT 與 XML-PACKET A 封包唯讀）
    And SPEC model.rs 定義 ModuleSpecDocument 欄位為既有 SSOT
    And 投影輸出目錄為 reports/rust-improvements/continuous/module-engineering-projection

  @PD-RUST-MODULE-HTML-01 @normal
  Scenario: 正常刷新產生含兩張圖與必要區塊的 HTML
    When 執行本卡的 generate_report.py
    Then module.html 含 diagram_a_hexagonal 與 diagram_b_ownership_stale
    And HTML 含 contracts、tests、scope、evidence、risk 區塊
    And 嵌入 module-spec JSON 含 draft ModuleSpecDocument
    And stale 檢查為 CURRENT
    And 不宣告 production 行為 GREEN 或 board 綠燈

  @PD-RUST-MODULE-HTML-01 @bdd-tdd-trace
  Scenario: BDD↔TDD/task/result/sourcehash 可追溯
    When 投影讀取 fixture-packet.json 與 product-documents/module.json
    Then 產出列綁定 task_id、module_id、bdd、tdd、result 與可用的 source/payload sha256
    And A 封包 readiness 保持 NOT_READY
    And hints 不升級為核准

  @PD-RUST-MODULE-HTML-01 @stale
  Scenario: 來源變更可偵測 stale
    Given 已寫入 bound_source_sha256
    When 任一 SOURCES 位元組變更且未重新生成
    Then live stale 檢查回報 PROJECTION_STALE
    And 不得將舊 HTML 視為目前權威

  @PD-RUST-MODULE-HTML-01 @boundary
  Scenario: 邊界 — 無 BDD/TDD 文字的節點不捏造列
    Given 選取節點缺少 bddSpecs/tddSpecs
    When 建立 trace 列
    Then 不為該節點發明 BDD 或 TDD 文字

  @PD-RUST-MODULE-HTML-01 @invalid
  Scenario: 無效 — 缺少必要核准來源
    Given SOURCES 清單中某必要路徑不存在
    When 執行生成
    Then 生成失敗且不寫入 READY 宣稱

  @PD-RUST-MODULE-HTML-01 @dependency_failure
  Scenario: 依賴失敗 — 核准封包不可讀
    Given fixture-packet 或 product-documents/module.json 無法讀取
    When 執行生成
    Then 失敗關閉；不捏造 format inventory 或 packet 內容

  @PD-RUST-MODULE-HTML-01 @partial_failure
  Scenario: 部分失敗不產出半套 CURRENT
    Given 寫入 module.json 後 HTML 寫入失敗
    When 檢查輸出
    Then 不得留下僅一半更新且標為 CURRENT 的狀態（保留先前完整對或失敗）

  @PD-RUST-MODULE-HTML-01 @state
  Scenario: 狀態 — draft 不自動核准
    When 投影嵌入 ModuleSpecDocument
    Then revision status 為 draft 且 content_hash 未冒充 Approved
    And GUARD/EVID 診斷維持 unresolved 參考

  @PD-RUST-MODULE-HTML-01 @transaction
  Scenario: 交易 — 生成失敗不破壞先前有效對
    Given 先前存在有效 module.json 與 module.html
    When 新生成中途失敗
    Then 先前完整輸出對保持可讀

  @PD-RUST-MODULE-HTML-01 @lifecycle
  Scenario: 生命週期 — 刷新後 hashes 更新為 CURRENT
    Given 來源已變更且曾為 STALE
    When 重新執行 generate_report.py
    Then bound_source_sha256 更新且 stale 檢查為 CURRENT

  @PD-RUST-MODULE-HTML-01 @regression
  Scenario: 回歸 — 不修改 production 與既有 SSOT
    When 本卡完成
    Then production schema/API/Ports 未改
    And sample_module_spec.json 與 approved-a-contract.md 未被寫入
    And board 未自改綠
