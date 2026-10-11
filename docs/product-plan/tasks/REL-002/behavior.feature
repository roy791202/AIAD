@REL-002 @planning
Feature: REL-002 Windows 打包與靜默安裝驗證
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 精確 OS/installer 版本需 D-03 核准；命令成功還須安裝檢查

    @BDD-REL-002-01
    Scenario: BDD-REL-002-01
      Given 乾淨 Windows VM 與核准安裝包
      When 系統執行靜默安裝
      Then exit、log、檔案、捷徑、啟動與版本均符合 profile

    @BDD-REL-002-02
    Scenario: BDD-REL-002-02
      Given 安裝中途故障或權限不足
      When 系統執行靜默安裝
      Then 標失敗並保存實際環境與可用復原步驟

    @BDD-REL-002-03
    Scenario: BDD-REL-002-03
      Given 同版本已安裝
      When 系統重複安裝後卸載
      Then 符合冪等策略且卸載保留宣告的使用者資料
