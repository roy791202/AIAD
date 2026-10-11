@UI-002 @planning
Feature: UI-002 互動式模組架構 DAG
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: A→B 代表 A 依賴 B；繪圖不修改核准架構；Task DAG 分開

    @BDD-UI-002-01
    Scenario: BDD-UI-002-01
      Given 合法模組 DAG 與模組 Tasks 已載入
      When 使用者選取模組
      Then 顯示其責任、Ports、依賴與所屬 Tasks

    @BDD-UI-002-02
    Scenario: BDD-UI-002-02
      Given 架構含循環 A 到 B 到 A
      When 使用者驗證架構
      Then 顯示循環路徑並禁止核准

    @BDD-UI-002-03
    Scenario: BDD-UI-002-03
      Given 模組沒有工項或證據
      When 使用者查看節點
      Then 顯示未評估而非完成綠燈
