@SPEC-001 @planning
Feature: SPEC-001 ModuleSpec 與追溯模型
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 每個 Task 恰有一個主要模組；BDD 必須追溯到 invariant 與 TDD；核准資料版本不可變

    @BDD-SPEC-001-01
    Scenario: BDD-SPEC-001-01
      Given 一份包含架構、Contract、BDD、TDD 與範圍的完整封包
      When 使用者驗證封包
      Then 列出有效追溯鏈且不自動核准架構

    @BDD-SPEC-001-02
    Scenario: BDD-SPEC-001-02
      Given 封包缺少 BDD 或參照不存在的 TDD
      When 使用者驗證封包
      Then 拒絕實作資格並列出缺少欄位與斷鏈 ID

    @BDD-SPEC-001-03
    Scenario: BDD-SPEC-001-03
      Given 兩個 Task 使用相同 ID
      When 使用者匯入封包
      Then 拒絕重複 ID 且保留原規格
