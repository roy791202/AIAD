@EXEC-001 @planning
Feature: EXEC-001 Agent Provider 邊界與模擬執行
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: Run 綁定 project/root/spec/commit；程序輸出不是完成權威

    @BDD-EXEC-001-01
    Scenario: BDD-EXEC-001-01
      Given 合格封包與模擬 Provider 已就緒
      When 使用者啟動 Run
      Then 事件按序回填且每筆綁定相同 Run ID

    @BDD-EXEC-001-02
    Scenario: BDD-EXEC-001-02
      Given Provider 不可用
      When 使用者啟動 Run
      Then 回報失敗且不宣告工項完成

    @BDD-EXEC-001-03
    Scenario: BDD-EXEC-001-03
      Given Provider 輸出完成但尚無測試證據
      When 系統處理輸出
      Then 只保存候選結果而不將 Task 標綠
