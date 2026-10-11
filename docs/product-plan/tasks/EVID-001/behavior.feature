@EVID-001 @planning
Feature: EVID-001 測試 Runner 與有效 RED
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: RED 必須 test build 成功且因指定缺失行為失敗；空輸出不算 PASS

    @BDD-EVID-001-01
    Scenario: BDD-EVID-001-01
      Given 測試可建置且指定行為尚未實作
      When 系統執行 RED 驗證
      Then 登錄 behavioral RED 並連結 BDD

    @BDD-EVID-001-02
    Scenario: BDD-EVID-001-02
      Given 測試因編譯或 fixture 損壞失敗
      When 系統執行 RED 驗證
      Then 拒絕 RED 資格並分類失敗

    @BDD-EVID-001-03
    Scenario: BDD-EVID-001-03
      Given 命令 exit 0 但缺少必要測試結果
      When 系統解析結果
      Then 標記未測得而非 PASS
