@WORK-001 @planning
Feature: WORK-001 專案登錄與資料夾驗證
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: Project ID 穩定；實體 root 不得重複；失敗不部分登錄

    @BDD-WORK-001-01
    Scenario: BDD-WORK-001-01
      Given 存在可讀寫且名稱含中文空白的資料夾
      When 使用者登錄專案
      Then 產生 Project ID 並保存正確完整路徑

    @BDD-WORK-001-02
    Scenario: BDD-WORK-001-02
      Given 目標不存在或不可存取
      When 使用者登錄專案
      Then 顯示原因且未新增專案

    @BDD-WORK-001-03
    Scenario: BDD-WORK-001-03
      Given 同一路徑透過大小寫或 junction 別名已登錄
      When 使用者再次登錄
      Then 導向既有專案且不產生重複
