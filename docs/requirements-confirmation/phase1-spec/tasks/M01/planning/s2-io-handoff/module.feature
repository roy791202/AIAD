Feature: Existing M01-S2 project-definition handoff
  Background:
    Given the user has explicitly selected a project operation and authorized its location

  @TDD-M01-EX-06
  Scenario: 持久ID不依路徑
    Given 同一projectUuid的定義被搬到新root
    When 開啟已保存definition
    Then UUID不變；legacy key只作alias

  @TDD-M01-EX-07
  Scenario: 拒既有檔案
    Given 目標路徑已有含資料一般檔案
    When 從所有新建入口建立
    Then 拒絕且原始bytes不變，不remove_file

  @TDD-M01-EX-08
  Scenario: 拒既有目錄
    Given 目標已存在空或非空目錄
    When 建立新專案
    Then 拒絕並保留目錄；resume需獨立流程

  @TDD-M01-EX-09
  Scenario: 首次存草稿
    Given 目標不存在且有效draft
    When 明確保存draft
    Then exclusive建立並寫definition；UI事前揭露建立位置

  @TDD-M01-EX-10
  Scenario: 部分建立失敗
    Given 新目錄已建立但寫definition或選定偏好失敗
    When 結束本輪保存
    Then PartialProjectCreated列本次產物且不綁成功、不刪來源

  @TDD-M01-EX-11
  Scenario: 遷移不碰來源
    Given legacy專案含ESS與manifest/preferences
    When 明確採用持久定義
    Then 只新增definition，其他bytes原樣

  @TDD-M01-EX-12
  Scenario: 同UUID兩root
    Given 已開專案UUID出現另一root
    When 要求開啟
    Then 標示move/copy衝突，不自動重映射

  @TDD-M01-EX-13
  Scenario: schema往返
    Given 含extensions及六步保存位置
    When encode再decode
    Then 定義語義一致且未知schema先拒絕

