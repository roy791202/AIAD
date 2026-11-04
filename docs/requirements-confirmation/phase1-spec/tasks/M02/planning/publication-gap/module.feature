# language: zh-TW
@proposal_only @M02_PUBLICATION_GAP
功能: 完整雙骨架生成與安全啟用
  背景:
    假如 使用者具有本機專案的編輯權

  @M02-PUB-T01
  規則: M02-PUB-I1 保護正式內容
    場景: M02-PUB-T01
      假如 未確認架構/契約條件
      當 準備生成
      那麼 只保存定義並列出missing，不寫任何產物

  @M02-PUB-T02
  規則: M02-PUB-I2 保護正式內容
    場景: M02-PUB-T02
      假如 完整定義、已驗證approval、相容模板
      當 準備生成
      那麼 預設同一binding包含程式及UI UX兩個artifact意圖

  @M02-PUB-T03
  規則: M02-PUB-I1 保護正式內容
    場景: M02-PUB-T03
      假如 任一定義revision/template digest/approval/base描述檔變動
      當 確認舊預覽
      那麼 stale/conflict，舊版本不變

  @M02-PUB-T04
  規則: M02-PUB-I1 保護正式內容
    場景: M02-PUB-T04
      假如 新版本第一或第二骨架渲染/驗證失敗
      當 處理生成錯誤
      那麼 不切換描述檔，不暴露不完整新版

  @M02-PUB-T05
  規則: M02-PUB-I3 保護正式內容
    場景: M02-PUB-T05
      假如 產物完整但啟用描述檔提交失敗
      當 確認生成
      那麼 沿已核准FileCommit錯誤/RecoveryRequired語意保留前後資料，不聲稱成功

  @M02-PUB-T06
  規則: M02-PUB-I4 保護正式內容
    場景: M02-PUB-T06
      假如 來源/版本區含未知檔或使用者改動
      當 再生成
      那麼 只產生新受管版本，衝突需明確處理，不刪未知資料

  @M02-PUB-T07
  規則: M02-PUB-I3 保護正式內容
    場景: M02-PUB-T07
      假如 啟用前或後程序中斷
      當 新程序讀取生成物
      那麼 只讀明確已啟用且完整版本；未知狀態fail closed，不假稱硬體斷電保證

  @M02-PUB-T08
  規則: M02-PUB-I4 保護正式內容
    場景: M02-PUB-T08
      假如 模板中含命令或跨根路徑
      當 驗證/預覽
      那麼 不執行模板；拒越界artifact意圖，原資料不變

