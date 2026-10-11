@REL-003 @planning
Feature: REL-003 發布核准、健康檢查與回滾
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 部署成功和回滾成功是不同結果；不可逆變更需明確處置

    @BDD-REL-003-01
    Scenario: BDD-REL-003-01
      Given 測試環境驗證完成且正式發布已核准
      When 系統部署到正式環境
      Then 使用同一產物並在健康檢查通過後標記成功

    @BDD-REL-003-02
    Scenario: BDD-REL-003-02
      Given 部署命令成功但健康檢查失敗
      When 系統驗證部署
      Then 部署標 FAIL 並依已核准策略復原

    @BDD-REL-003-03
    Scenario: BDD-REL-003-03
      Given 回滾過程也失敗
      When 系統處理復原結果
      Then 回滾標 FAIL 並提供人工處置且保留環境狀態
