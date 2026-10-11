@HOST-001 @planning
Feature: HOST-001 可重現工具鏈與測試骨架
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 版本固定且命令可重現；測試未發現不能回報通過；僅建立已核准模組骨架

    @BDD-HOST-001-01
    Scenario: BDD-HOST-001-01
      Given 乾淨 checkout 與核准工具版本已就緒
      When 開發者安裝鎖定依賴並執行測試入口
      Then 相依版本符合 lockfile 並產生含案例 ID 的機器結果

    @BDD-HOST-001-02
    Scenario: BDD-HOST-001-02
      Given 指定工項沒有可執行測試
      When 開發者執行該工項測試
      Then 回報無案例且不得偽造 GREEN

    @BDD-HOST-001-03
    Scenario: BDD-HOST-001-03
      Given 同一 fixture 測試在第二個乾淨工作目錄執行
      When 開發者重複測試
      Then 案例數與結果一致且不依賴第一個目錄
