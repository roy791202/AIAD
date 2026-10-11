@FLOW-002 @planning
Feature: FLOW-002 依賴排程與失敗停止
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: Task DAG 與架構 DAG 獨立；依賴失敗不自動執行後續

    @BDD-FLOW-002-01
    Scenario: BDD-FLOW-002-01
      Given A 已完成且 B 依賴 A
      When 排程器選擇下一個工項
      Then B 可排程並保存決策原因

    @BDD-FLOW-002-02
    Scenario: BDD-FLOW-002-02
      Given A 未完成而 B 依賴 A
      When 排程器選擇下一個工項
      Then B 保持等待且不啟動 Agent

    @BDD-FLOW-002-03
    Scenario: BDD-FLOW-002-03
      Given 工項依賴形成 A 到 B 到 A
      When 使用者驗證排程
      Then 顯示循環路徑並拒絕啟動
