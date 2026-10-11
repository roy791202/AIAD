@FLOW-001 @planning
Feature: FLOW-001 執行狀態機與核准閘門
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 狀態只能透過合法事件轉移；審查前不得 COMPLETE

    @BDD-FLOW-001-01
    Scenario: BDD-FLOW-001-01
      Given Task 在 TDD_RED 且有效 RED 已登錄
      When 系統提交開始實作事件
      Then Task 進入 IMPLEMENTATION

    @BDD-FLOW-001-02
    Scenario: BDD-FLOW-001-02
      Given Task 尚未完成驗收
      When 系統收到完成請求
      Then 拒絕 COMPLETE 並保留目前狀態

    @BDD-FLOW-001-03
    Scenario: BDD-FLOW-001-03
      Given 同一合法事件被重複送達
      When 系統處理事件
      Then 只發生一次狀態轉移
