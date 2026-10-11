@GIT-001 @planning
Feature: GIT-001 Clone、Init 與程式庫摘要
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: clone 失敗不登錄為完整專案；憑證不得出現在輸出

    @BDD-GIT-001-01
    Scenario: BDD-GIT-001-01
      Given 可用的本機 bare 遠端與空目標資料夾
      When 使用者 clone
      Then 成功後登錄專案並顯示 branch 與 remote

    @BDD-GIT-001-02
    Scenario: BDD-GIT-001-02
      Given 遠端不可達或認證被拒
      When 使用者 clone
      Then 顯示脫敏錯誤且不宣告 clone 成功

    @BDD-GIT-001-03
    Scenario: BDD-GIT-001-03
      Given 目標資料夾非空
      When 使用者 clone
      Then 拒絕覆寫並保留既有資料
