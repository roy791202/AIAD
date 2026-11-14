# language: zh-TW
@design_only @M04
功能: M04 精確架構與行為契約
  背景:
    假如 測試使用隔離專案且來源唯讀

  @BDD-M04-EX-01
  規則: 清空一次Undo
    場景: 清空一次Undo
      假如 ESS含work/arch/design及關係引用
      當 確認清空後Undo一次
      那麼 還原整份文件語義及引用限制，單筆history

  @BDD-M04-EX-02
  規則: 取消無歷史
    場景: 取消無歷史
      假如 已有prepare plan但尚未apply
      當 取消
      那麼 內容、refs、兩基準與history不變

  @BDD-M04-EX-03
  規則: 過期plan拒絕
    場景: 過期plan拒絕
      假如 prepare後content revision改變
      當 確認舊plan
      那麼 拒絕且不加history不改內容

  @BDD-M04-EX-04
  規則: 單文件範圍
    場景: 單文件範圍
      假如 plan需要改另一實體文件
      當 prepare或commit
      那麼 拒絕並指出跨文件前置條件

  @BDD-M04-EX-05
  規則: 不包含暫態
    場景: 不包含暫態
      假如 只有selection/focus/playback改變
      當 計算語義變更
      那麼 semantic digest及快照需求不變

  @BDD-M04-EX-06
  規則: Undo單調revision
    場景: Undo單調revision
      假如 內容經apply再Undo回formal內容
      當 檢查狀態
      那麼 revision仍增加；dirty依內容可回false；snapshot基準不被formal重設

  @BDD-M04-EX-07
  規則: 穩定capture
    場景: 穩定capture
      假如 clear/merge/rollback進行中
      當 要求capture
      那麼 Busy不交付中間狀態；完成後給immutable版本

  @BDD-M04-EX-08
  規則: 兩個基準獨立
    場景: 兩個基準獨立
      假如 formal=R0、snapshot=R1、current=R2
      當 正式保存R2成功
      那麼 只更新formal；snapshot仍R1

  @BDD-M04-EX-09
  規則: 保存中再編輯
    場景: 保存中再編輯
      假如 R1在IO中且current已R2
      當 回報R1保存成功
      那麼 formal基準只R1，R2仍dirty，不吞新內容

  @BDD-M04-EX-10
  規則: 普通IO故障保全
    場景: 普通IO故障保全
      假如 有原有效文件與新內容
      當 stage/sync/replace任一可回復失敗
      那麼 原檔bytes完整，current dirty與history保留

  @BDD-M04-EX-11
  規則: rollback本身失敗
    場景: rollback本身失敗
      假如 replace或驗證失敗且restore又失敗
      當 處理結果
      那麼 RecoveryRequired保留原版本/journal並阻擋破壞性後續；不聲稱未改或成功

  @BDD-M04-EX-12
  規則: 外部版本衝突
    場景: 外部版本衝突
      假如 正式raw bytes已被其他writer修改
      當 保存舊版本
      那麼 lease重查digest後拒絕，不覆寫

  @BDD-M04-EX-13
  規則: 格式與擴充欄位
    場景: 格式與擴充欄位
      假如 ESS/設計有批准的擴充欄位與素材引用
      當 HOST codec保存重開
      那麼 保留語義；未知unsupported schema拒絕不丟欄位

  @BDD-M04-EX-14
  規則: 離開三選擇
    場景: 離開三選擇
      假如 有dirty且close/switch/exit待執行
      當 分別選保存/不保存/取消
      那麼 只有保存成功或明確discard才離開；取消或失敗留原處

  @BDD-M04-EX-15
  規則: 第二視窗不能寫
    場景: 第二視窗不能寫
      假如 同文件有owner editor與viewer
      當 viewer提交或使用舊session token
      那麼 拒絕且不得更新權威內容

  @BDD-M04-EX-16
  規則: 共享素材不刪
    場景: 共享素材不刪
      假如 Undo後活文件不引用但保留快照仍pin該asset
      當 評估釋放本次素材
      那麼 只移除live引用；bytes保留且other docs不變

  @BDD-M04-EX-17
  規則: 待綁定完整回復
    場景: 待綁定完整回復
      假如 成功merge包含pending binding與blocked capability
      當 Undo一次
      那麼 兩種狀態回before且來源BIN不變

  @BDD-M04-EX-18
  規則: 重新開啟不延續Undo
    場景: 重新開啟不延續Undo
      假如 文件保存關閉再開
      當 查詢Undo
      那麼 空history；復原開啟仍dirty但不帶舊session Undo
