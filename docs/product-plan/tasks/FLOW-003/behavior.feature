@FLOW-003 @planning
Feature: FLOW-003 重新規劃與人工決策
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 架構、Contract 或 BDD 變更需重新核准，不得自我批准

    @BDD-FLOW-003-01
    Scenario: BDD-FLOW-003-01
      Given Agent 發現必要交易邊界不足
      When Agent 回報結構變更需求
      Then Task 進入 REPLAN_REQUIRED 並停止後續產品修改

    @BDD-FLOW-003-02
    Scenario: BDD-FLOW-003-02
      Given 新規格未核准
      When 使用者請求繼續實作
      Then 拒絕續跑並顯示待核准內容

    @BDD-FLOW-003-03
    Scenario: BDD-FLOW-003-03
      Given 只有保持 Contract 的私有函式整理
      When 系統審查變更分類
      Then 允許在原 envelope 內繼續
