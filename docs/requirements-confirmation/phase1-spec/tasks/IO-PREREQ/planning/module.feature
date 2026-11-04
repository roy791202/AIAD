# language: zh-TW
@planning_only @IO_PREREQ
功能: 單文件提交與失敗保全
  背景:
    假如 測試使用隔離目錄與完整舊版本文件

  @IO-BDD-01
  規則: 獨佔建立
    場景: 獨佔建立
      假如 存在父目錄與不存在的新名稱
      當 建立目錄
      那麼 只建立該新目錄並返回位置

  @IO-BDD-02
  規則: 已有目標不變
    場景: 已有目標不變
      假如 目標為檔案、空目錄或非空目錄
      當 要求建立
      那麼 AlreadyExists；既有bytes及內容不變

  @IO-BDD-03
  規則: 非法名稱
    場景: 非法名稱
      假如 名稱空白、保留名、含separator或穿越
      當 建立目錄
      那麼 InvalidPath且不建立任何子目錄

  @IO-BDD-04
  規則: 同程序競爭
    場景: 同程序競爭
      假如 已有一個同目標lease
      當 另一adapter instance要求lease
      那麼 Busy且不能讀寫提交

  @IO-BDD-05
  規則: 跨程序競爭
    場景: 跨程序競爭
      假如 子程序持有同目標sidecar handle
      當 父程序要求lease
      那麼 Busy；不是只靠同程序Mutex

  @IO-BDD-06
  規則: 程序死亡釋放
    場景: 程序死亡釋放
      假如 子程序持有lease且無未完成journal
      當 終止子程序後再取lease
      那麼 OS handle釋放，sidecar仍可再次打開；不按檔案年齡刪鎖

  @IO-BDD-07
  規則: 新檔提交
    場景: 新檔提交
      假如 期望不存在且無目標
      當 replace_checked(None,new)
      那麼 完整新bytes與receipt相符

  @IO-BDD-08
  規則: 既有檔提交
    場景: 既有檔提交
      假如 期望digest等於現行bytes
      當 replace_checked(Some(old),new)
      那麼 寫入完整new，保留old版本直到交易確認

  @IO-BDD-09
  規則: 過期拒絕
    場景: 過期拒絕
      假如 期望digest不等於目前檔案
      當 要求替換
      那麼 Conflict，不更動正式目標

  @IO-BDD-10
  規則: 存在性衝突
    場景: 存在性衝突
      假如 期望不存在但檔案已存在，或反之
      當 要求替換
      那麼 Conflict，不能自動覆寫

  @IO-BDD-11
  規則: 替換前故障
    場景: 替換前故障
      假如 prepare/backup/temp write/sync任一步失敗
      當 結束本次提交
      那麼 原有效正式bytes不變，清理僅本次owned scratch

  @IO-BDD-12
  規則: 替換後可回復故障
    場景: 替換後可回復故障
      假如 正式replace後verify/提交紀錄階段失敗且restore可用
      當 處理錯誤
      那麼 舊bytes恢復後才可回普通Storage錯誤

  @IO-BDD-13
  規則: 回復本身失敗
    場景: 回復本身失敗
      假如 restore/restore verify失敗
      當 回傳結果
      那麼 RecoveryRequired，保留old/new/journal，後續破壞性提交拒絕

  @IO-BDD-14
  規則: 重啟遇未完成紀錄
    場景: 重啟遇未完成紀錄
      假如 上次journal未到COMMITTED/ROLLED_BACK
      當 新程序acquire
      那麼 拒絕並回RecoveryRequired，不猜測哪版應生效

  @IO-BDD-15
  規則: 未知或損毀journal
    場景: 未知或損毀journal
      假如 journal版本未知、校驗不符或含越界路徑
      當 acquire
      那麼 RecoveryRequired，保留所有原資料，不解析成可執行動作

  @IO-BDD-16
  規則: lease關閉
    場景: lease關閉
      假如 已完成lease的handle正常drop
      當 另一程序取lease
      那麼 成功；不需等待stale timeout

  @IO-BDD-17
  規則: 目標被外部改動
    場景: 目標被外部改動
      假如 prepare後偵測目標digest變更
      當 commit前重查
      那麼 Conflict且不覆寫；不聲稱防止任意非合作writer最後瞬間競爭

  @IO-BDD-18
  規則: 失敗不刪他人檔案
    場景: 失敗不刪他人檔案
      假如 owned temp名碰撞或cleanup失敗
      當 保存或中止
      那麼 不刪非本次create_new成功取得的檔；保留可診斷結果
