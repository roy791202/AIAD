@WORK-002 @planning
Feature: WORK-002 切換、租約與重新定位
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: UI selection 與 Run binding 分離；活動租約保護 root

    @BDD-WORK-002-01
    Scenario: BDD-WORK-002-01
      Given A 有活動 Run 且 B 已登錄
      When 使用者切換到 B
      Then 畫面顯示 B 且 A 的 Run 維持原 root

    @BDD-WORK-002-02
    Scenario: BDD-WORK-002-02
      Given A 有活動執行租約
      When 使用者重新定位 A
      Then 拒絕重新綁定並指出活動 Run

    @BDD-WORK-002-03
    Scenario: BDD-WORK-002-03
      Given A 已停止且搬移到新目錄
      When 使用者驗證後重新定位
      Then 保持 Project ID 並將舊證據標記待核對
