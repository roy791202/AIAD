@GUARD-002 @planning
Feature: GUARD-002 變更保護與執行權限
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: worktree 不是安全沙箱；無法強制執行的限制不得聲稱已保護

    @BDD-GUARD-002-01
    Scenario: BDD-GUARD-002-01
      Given 已套用且驗證 OS 或 Provider 寫入限制
      When Agent 嘗試寫入受保護檔案
      Then 寫入遭拒且留下審計紀錄

    @BDD-GUARD-002-02
    Scenario: BDD-GUARD-002-02
      Given 執行環境無法提供所需強制限制
      When 使用者啟動要求該限制的 Task
      Then 拒絕自動實作並列出缺失能力

    @BDD-GUARD-002-03
    Scenario: BDD-GUARD-002-03
      Given Agent 修改測試期待以讓測試通過
      When 系統審查變更
      Then 攔截驗收並要求規格審查
