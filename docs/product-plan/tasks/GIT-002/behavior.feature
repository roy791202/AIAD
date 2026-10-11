@GIT-002 @planning
Feature: GIT-002 Fetch、安全 Pull 與分支切換
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 默认 FF-only；分歧拒絕自動 merge/rebase；活動租約禁止切換

    @BDD-GIT-002-01
    Scenario: BDD-GIT-002-01
      Given 工作目錄乾淨且遠端可快轉
      When 使用者 pull
      Then 更新到遠端提交並顯示新版本

    @BDD-GIT-002-02
    Scenario: BDD-GIT-002-02
      Given 分支分歧或更新會覆蓋本機變更
      When 使用者 pull
      Then 停止並保留本機內容與提交

    @BDD-GIT-002-03
    Scenario: BDD-GIT-002-03
      Given 目前工作區有活動 Run
      When 使用者切換分支
      Then 拒絕並指出佔用 Run
