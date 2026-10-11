@EVID-002 @planning
Feature: EVID-002 證據失效與模組覆蓋
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 結果綁定 spec hash 與工作樹指紋；passed count 不代表 BDD 完整

    @BDD-EVID-002-01
    Scenario: BDD-EVID-002-01
      Given 所有必要 BDD 有對應有效證據
      When 系統計算模組覆蓋
      Then 呈現已驗證數與缺口為零

    @BDD-EVID-002-02
    Scenario: BDD-EVID-002-02
      Given 程式或規格在測試後改變
      When 系統重新計算狀態
      Then 舊結果保留但不再支持當前綠燈

    @BDD-EVID-002-03
    Scenario: BDD-EVID-002-03
      Given 部分必要測試被 skip
      When 系統計算完成資格
      Then 列出未驗證行為並拒絕完成
