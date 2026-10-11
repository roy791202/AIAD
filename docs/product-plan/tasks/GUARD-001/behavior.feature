@GUARD-001 @planning
Feature: GUARD-001 封包資格與範圍檢查
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 路徑允許不覆蓋模組限制；未核准或無有效 RED 不得啟動產品實作

    @BDD-GUARD-001-01
    Scenario: BDD-GUARD-001-01
      Given 封包已核准且 RED 證據有效
      When 執行器請求開始實作
      Then 回傳允許與 envelope hash

    @BDD-GUARD-001-02
    Scenario: BDD-GUARD-001-02
      Given 封包缺少批准或 RED 為編譯失敗
      When 執行器請求開始實作
      Then 拒絕並指出未滿足閘門

    @BDD-GUARD-001-03
    Scenario: BDD-GUARD-001-03
      Given 允許檔案列表含有另一模組檔案但未宣告整合範圍
      When 執行器檢查變更
      Then 回報 MODULE_BOUNDARY_ESCAPE
