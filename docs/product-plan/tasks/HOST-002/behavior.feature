@HOST-002 @planning
Feature: HOST-002 Electron 宿主、受限 IPC 與組裝入口
  Background:
    Given 使用者已選定正確專案與規格版本

  Rule: renderer 無任意檔案或 shell 權限；只允許經驗證命令；composition root 組裝 adapters

    @BDD-HOST-002-01
    Scenario: BDD-HOST-002-01
      Given 已核准的視窗與服務組裝設定
      When 使用者啟動應用程式
      Then 顯示初始視窗且服務透過型別化橋接提供

    @BDD-HOST-002-02
    Scenario: BDD-HOST-002-02
      Given 呼叫來源或 IPC 輸入不符合契約
      When 介面送出請求
      Then 拒絕操作且不執行檔案或 shell 副作用

    @BDD-HOST-002-03
    Scenario: BDD-HOST-002-03
      Given 服務在啟動中途失敗
      When 使用者啟動應用程式
      Then 顯示診斷並釋放已建立資源
