@SPEC-002 @planning
Feature: SPEC-002 規格修訂與核准鎖定
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 核准綁定內容雜湊；修訂不繼承先前核准

    @BDD-SPEC-002-01
    Scenario: BDD-SPEC-002-01
      Given 規格版本 v1 已核准
      When 使用者建立 v2 草稿
      Then v1 保持不可變且 v2 等待核准

    @BDD-SPEC-002-02
    Scenario: BDD-SPEC-002-02
      Given Agent 正在實作已鎖定 v1
      When Agent 嘗試修改公開 Contract
      Then 拒絕修改並回報 REPLAN_REQUIRED

    @BDD-SPEC-002-03
    Scenario: BDD-SPEC-002-03
      Given 核准人正在檢視 v1 而草稿已更新為 v2
      When 核准人送出 v1 的核准
      Then 僅核准 v1 且不得套用到 v2
