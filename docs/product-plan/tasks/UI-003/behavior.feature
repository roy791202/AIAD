@UI-003 @planning
Feature: UI-003 BDD/TDD 工程封包與執行詳情
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 顯示的封包 hash 必須等於啟動使用的 hash

    @BDD-UI-003-01
    Scenario: BDD-UI-003-01
      Given 完整 Task 已選取
      When 使用者展開詳情
      Then 呈現 BDD、TDD、範圍、命令、證據及核准狀態

    @BDD-UI-003-02
    Scenario: BDD-UI-003-02
      Given 封包缺少必要資料
      When 使用者查看 Task
      Then 啟動停用並列出缺漏

    @BDD-UI-003-03
    Scenario: BDD-UI-003-03
      Given 畫面載入後封包已改版
      When 使用者啟動 Task
      Then 要求重新檢視而不使用舊核准
