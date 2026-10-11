@REPORT-001 @planning
Feature: REPORT-001 統一模組 HTML 與系統總覽
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 報告為投影；嵌入結構資料；不得偽造核准或測試結果

    @BDD-REPORT-001-01
    Scenario: BDD-REPORT-001-01
      Given 規格與證據均可讀
      When 使用者產生報告
      Then 產生可離線開啟且含來源指紋的 HTML

    @BDD-REPORT-001-02
    Scenario: BDD-REPORT-001-02
      Given 測試結果尚未存在
      When 使用者產生報告
      Then 清楚呈現 NOT RUN

    @BDD-REPORT-001-03
    Scenario: BDD-REPORT-001-03
      Given 規格含 HTML 特殊字元與 script 標記
      When 使用者開啟報告
      Then 內容作為文字呈現而不執行注入
