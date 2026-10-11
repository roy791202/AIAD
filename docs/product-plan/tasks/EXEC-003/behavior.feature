@EXEC-003 @planning
Feature: EXEC-003 取消、逾時與重啟對帳
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 取消涵蓋子程序樹；不確定外部效果不得盲目重跑

    @BDD-EXEC-003-01
    Scenario: BDD-EXEC-003-01
      Given Run 與其子程序正在執行
      When 使用者取消 Run
      Then 在設定的取消期限內終止程序樹並標記取消

    @BDD-EXEC-003-02
    Scenario: BDD-EXEC-003-02
      Given 程序拒絕正常結束
      When Run 到達逾時
      Then 執行升級終止並記錄結果而非成功

    @BDD-EXEC-003-03
    Scenario: BDD-EXEC-003-03
      Given 應用程式在外部命令完成與保存結果之間崩潰
      When 使用者重新啟動
      Then Run 標為待對帳且不自動重送命令
