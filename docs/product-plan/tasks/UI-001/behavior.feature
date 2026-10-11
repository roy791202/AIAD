@UI-001 @planning
Feature: UI-001 專案切換與狀態看板
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: stage 與 health 分離；顏色配文字圖示；UI 不改權威狀態

    @BDD-UI-001-01
    Scenario: BDD-UI-001-01
      Given 有待執行、執行中及待核准 Tasks
      When 使用者開啟看板
      Then 顯示灰藍黃狀態及原因和下一步

    @BDD-UI-001-02
    Scenario: BDD-UI-001-02
      Given 載入專案失敗
      When 使用者開啟看板
      Then 顯示錯誤且不殘留另一專案內容

    @BDD-UI-001-03
    Scenario: BDD-UI-001-03
      Given 搜尋沒有符合項目
      When 使用者篩選 Tasks
      Then 顯示空狀態與清除篩選入口
