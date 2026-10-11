@EXEC-002 @planning
Feature: EXEC-002 首個真實 Agent CLI Adapter
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 僅使用已驗證 CLI 非互動協定；未知認證/版本不得猜測

    @BDD-EXEC-002-01
    Scenario: BDD-EXEC-002-01
      Given 已選定 Provider 的版本、認證與事件格式通過 spike
      When 使用者執行示範 Task
      Then Agent 在指定 root 產生範圍內變更與可解析事件

    @BDD-EXEC-002-02
    Scenario: BDD-EXEC-002-02
      Given 登入失效或 CLI 版本不相容
      When 使用者啟動 Agent
      Then 停止並回報 IMPLEMENTATION_BLOCKED 且不輸出憑證

    @BDD-EXEC-002-03
    Scenario: BDD-EXEC-002-03
      Given CLI 輸出截斷或非協定文字
      When 系統接收輸出
      Then 保存診斷並拒絕偽造成功
