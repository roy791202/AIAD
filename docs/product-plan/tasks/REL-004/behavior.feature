@REL-004 @planning
Feature: REL-004 SSH、容器與 DCC 部署擴充規劃
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: 此 Task 僅產出設計；不可宣告 Adapter 已支援

    @BDD-REL-004-01
    Scenario: BDD-REL-004-01
      Given 首個擴充目標及版本由使用者指定
      When 規劃 Agent 產生擴充封包
      Then 每種方式各有 port mapping、BDD/TDD、回滾限制與新工項

    @BDD-REL-004-02
    Scenario: BDD-REL-004-02
      Given 尚未指定 OS 或 DCC 版本
      When 規劃 Agent 檢查就緒度
      Then 標待決策且不進入產品實作

    @BDD-REL-004-03
    Scenario: BDD-REL-004-03
      Given DCC 版本使用不同 Python/Qt 執行環境
      When 規劃 Agent 定義相容性矩陣
      Then 分列 load/unload、環境隔離及 batch 驗證
