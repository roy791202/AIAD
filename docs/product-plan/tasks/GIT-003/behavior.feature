@GIT-003 @planning
Feature: GIT-003 審核式 Commit 與 Push
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: commit 需驗收；只納入選定範圍；push 需授權；禁自動 force

    @BDD-GIT-003-01
    Scenario: BDD-GIT-003-01
      Given 工項驗收通過且已選取範圍內變更
      When 使用者提交並授權 push
      Then 建立可追溯 commit 並回報遠端結果

    @BDD-GIT-003-02
    Scenario: BDD-GIT-003-02
      Given 工作區含其他未選取 WIP
      When 使用者提交此工項
      Then 提交只包含選定工項且保留 WIP

    @BDD-GIT-003-03
    Scenario: BDD-GIT-003-03
      Given 遠端已前進而拒絕 push
      When 使用者 push
      Then 保留本機 commit 並顯示拒絕原因
