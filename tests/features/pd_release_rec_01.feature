# language: zh-TW
Feature: PD-RELEASE-REC-01 發布紀錄 JSON（不寫看板）
  BDD-PD-RELEASE-REC-01（PD-BOARD-GAPS-RELEASE-01 改版）
  看板唯一來源是 docs/board.json；發布工具不再寫任何看板檔，
  改輸出一筆發布紀錄 JSON，供人或其他工具取用。

  Background:
    Given 範例 MSI 與發布報告存在

  Scenario: build 子指令把發布紀錄 JSON 印到 stdout
    When Agent 執行 release_report.py build，帶 version、artifact、reportPath
    Then stdout 是一筆發布紀錄 JSON
    And 欄位與 build_release 產生的紀錄一致

  Scenario: build 子指令以 --out 寫出發布紀錄檔
    When Agent 執行 release_report.py build 並帶 --out <path>
    Then <path> 寫出同一筆發布紀錄 JSON

  Scenario: 發布工具不碰任何看板檔
    Given 工作目錄有一份看板檔
    When Agent 執行 release_report.py build
    Then 看板檔內容不變
    And release_report 沒有 --board 選項，也不提供 append_release／list_releases

  Scenario: 呼叫端寫出 <report>.release.json
    When build_result、rel_hang_final、rel_hang_post 掛發布紀錄
    Then 報告旁產生 <report>.release.json，內容等於回傳的發布紀錄
