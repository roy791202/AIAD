# language: zh-TW
Feature: PD-RELEASE-REC-01 releases JSON 紀錄＋#release 可見
  BDD-PD-RELEASE-REC-01

  Background:
    Given 看板 #board-snapshot 存在且 HTML 殼含 DOCTYPE 與 #release

  Scenario: 可追加一筆 release（version／artifacts／reportPath）
    When Agent 以 tools/board/release_report.py 追加 version、artifacts、reportPath
    Then snapshot.releases 含該筆紀錄
    And HTML 殼仍含 DOCTYPE 與 #tab-release／#view-release

  Scenario: 空陣列仍有空態
    Given snapshot.releases 為 []
    Then 頁面仍保留「還沒有佈版紀錄」空態文案（供 #release 渲染）

  Scenario: #release 顯示最近佈版
    Given 已追加至少一筆 release
    Then list_releases 可依 releasedAt 取得最近一筆 version 與成品路徑
