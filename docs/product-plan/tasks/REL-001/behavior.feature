@REL-001 @planning
Feature: REL-001 部署設定與版本產物追溯
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 部署 profile 版本化；產物不可變且有 hash；secret 僅保存引用

    @BDD-REL-001-01
    Scenario: BDD-REL-001-01
      Given 具備環境、命令、檢查與復原策略的 profile
      When 使用者建立部署候選
      Then 候選綁定 commit、artifact hash 與 profile revision

    @BDD-REL-001-02
    Scenario: BDD-REL-001-02
      Given profile 缺少健康檢查或復原聲明
      When 使用者驗證候選
      Then 阻止部署並列出缺口

    @BDD-REL-001-03
    Scenario: BDD-REL-001-03
      Given 產物內容在核准後被替換
      When 使用者開始部署
      Then 雜湊不符而拒絕執行
