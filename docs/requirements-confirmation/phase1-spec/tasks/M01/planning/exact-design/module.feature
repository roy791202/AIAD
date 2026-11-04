# language: zh-TW
@design_only @M01
功能: M01 精確架構與行為契約
  背景:
    假如 測試使用隔離專案且來源唯讀

  @BDD-M01-EX-01
  規則: 空白名稱拒絕
    場景: 空白名稱拒絕
      假如 草稿名稱只有空白
      當 要求保存
      那麼 欄位錯誤且無任何FS寫入

  @BDD-M01-EX-02
  規則: 草稿允許未決
    場景: 草稿允許未決
      假如 目標/框架尚未選定
      當 保存draft
      那麼 保留未決資訊且不生成骨架

  @BDD-M01-EX-03
  規則: 版本前進
    場景: 版本前進
      假如 期望revision等於目前
      當 更新definition
      那麼 只更新允許欄位且revision checked加一

  @BDD-M01-EX-04
  規則: 過期revision拒絕
    場景: 過期revision拒絕
      假如 草稿已被較新版本更新
      當 用舊revision保存
      那麼 RevisionConflict且原定義不變

  @BDD-M01-EX-05
  規則: 未確認不能生成
    場景: 未確認不能生成
      假如 有tentative或unresolved必要欄位
      當 finalize
      那麼 列缺決策；可存draft，不能宣稱已生成

  @BDD-M01-EX-06
  規則: 持久ID不依路徑
    場景: 持久ID不依路徑
      假如 同一projectUuid的定義被搬到新root
      當 開啟已保存definition
      那麼 UUID不變；legacy key只作alias

  @BDD-M01-EX-07
  規則: 拒既有檔案
    場景: 拒既有檔案
      假如 目標路徑已有含資料一般檔案
      當 從所有新建入口建立
      那麼 拒絕且原始bytes不變，不remove_file

  @BDD-M01-EX-08
  規則: 拒既有目錄
    場景: 拒既有目錄
      假如 目標已存在空或非空目錄
      當 建立新專案
      那麼 拒絕並保留目錄；resume需獨立流程

  @BDD-M01-EX-09
  規則: 首次存草稿
    場景: 首次存草稿
      假如 目標不存在且有效draft
      當 明確保存draft
      那麼 exclusive建立並寫definition；UI事前揭露建立位置

  @BDD-M01-EX-10
  規則: 部分建立失敗
    場景: 部分建立失敗
      假如 新目錄已建立但寫definition或選定偏好失敗
      當 結束本輪保存
      那麼 PartialProjectCreated列本次產物且不綁成功、不刪來源

  @BDD-M01-EX-11
  規則: 遷移不碰來源
    場景: 遷移不碰來源
      假如 legacy專案含ESS與manifest/preferences
      當 明確採用持久定義
      那麼 只新增definition，其他bytes原樣

  @BDD-M01-EX-12
  規則: 同UUID兩root
    場景: 同UUID兩root
      假如 已開專案UUID出現另一root
      當 要求開啟
      那麼 標示move/copy衝突，不自動重映射

  @BDD-M01-EX-13
  規則: schema往返
    場景: schema往返
      假如 含extensions及六步保存位置
      當 encode再decode
      那麼 定義語義一致且未知schema先拒絕

  @BDD-M01-EX-14
  規則: 偽造身分拒絕
    場景: 偽造身分拒絕
      假如 非owner視窗或caller送projectUuid/root/approvalRefs
      當 提交draft
      那麼 caller/DTO驗證先拒絕且不寫檔

  @BDD-M01-EX-15
  規則: 重複request冪等
    場景: 重複request冪等
      假如 相同session及request_id同payload
      當 重送建立或保存
      那麼 不第二次建立/增加revision；同id異payload拒絕

  @BDD-M01-EX-16
  規則: 六步續作與late回應
    場景: 六步續作與late回應
      假如 草稿保存於第3步後切換專案
      當 重開及接收舊回應
      那麼 恢復已保存步驟；舊回應不能改新專案
