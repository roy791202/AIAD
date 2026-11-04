# 需求確認清單

狀態：REQUIREMENTS_CONFIRMATION_ONLY；不是實作工單。

已確認：先完成本機專案與文件操作。

[完整互動閱讀清單](index.html) · [結構化追溯](requirements.json)

## 優先確認

Q1 首階段的使用者、平台及交付形態？
建議：本機專案作者；Windows免安裝版先；其他平台需求保留。

Q2 首階段必需的文件種類與操作？
建議：先列清.ess場景、架構文件、.sgendesign UI的用途與新增／開啟／保存；不要先假設三者格式相同。

Q3 跨專案匯入是副本還是持續參照？重複匯入如何處理？
建議：預設副本且來源不變；有重複／衝突先讓人決定，不自動覆寫或重映射。

Q4 復原保證到哪個範圍與時間？
建議：目前文件一次複合Undo沿用既有方向；關閉後快照、保留期及跨檔還原另明定。

Q5 第一階段是否排除AI執行、Git寫入與Plugin安裝？
建議：先本機文件流程；後續需求完整保留，需求確認不等於執行授權。

## 30卡逐一對照

|需求確認ID|原卡|使用者目標|
|---|---|---|
|RC-01|PD-RUST-IMPROVE-20261025|維護者看懂目前可用與未完成的能力|
|RC-02|PD-RUST-SYSTEM-REGRESSION-01|使用者能知道一次任務是否真正完成|
|RC-03|PD-RUST-NATIVE-UI-VERIFY-01|使用者在真正桌面產品完成主要操作|
|RC-04|PD-ELU-COLLAB-20261026|有無Git都能交換並整合工作成果|
|RC-05|PD-ELU-RECOVERY-ARCH-01|使用者知道清空與復原會影響什麼|
|RC-06|PD-ELU-PROJECT-IMPL-01|使用者建立或開啟專案並安全切換|
|RC-07|PD-ELU-DOCUMENT-IMPL-01|使用者自然地開啟保存與獨立交換文件|
|RC-08|PD-ELU-IMPORT-IMPL-01|使用者將既有程式碼轉為可檢視的模型建議|
|RC-09|PD-ELU-BINDING-IMPL-01|使用者把畫面元素與正確資料或行為連結|
|RC-10|PD-ELU-INTEGRATION-IMPL-01|使用者理解外來修改並安全採用|
|RC-11|PD-ELU-RECOVERY-IMPL-01|誤操作後能找回選定內容|
|RC-12|PD-ELU-GIT-IMPL-01|需要Git的使用者明確控制版本操作|
|RC-13|PD-ELU-UX-IMPL-01|使用者從一致入口完成導入與綁定|
|RC-14|PD-ELU-FIXTURE-IMPL-01|驗證不會污染使用者專案|
|RC-15|PD-ELU-VERIFY-IMPL-01|使用者能分辨功能有無真正驗證|
|RC-16|PD-ELU-GIT-ARCH-01|提交的內容與使用者預覽相同|
|RC-17|PD-ELU-TASKFLOW-20261026|使用者追蹤需求到成果的工作狀態|
|RC-18|PD-ELU-TF-REF-IMPL-01|AI取得正確版本與最少必要內容|
|RC-19|PD-ELU-TF-EVID-IMPL-01|使用者看懂每項需求如何被證明|
|RC-20|PD-ELU-TF-RUN-IMPL-01|使用者控制一次工作開始與停止|
|RC-21|PD-ELU-TF-AUDIT-IMPL-01|使用者知道誰在何時對哪個版本做了什麼|
|RC-22|PD-ELU-TF-DELIV-IMPL-01|使用者確認成果後才將其視為已接受|
|RC-23|PD-ELU-TF-BATCH-IMPL-01|使用者在資源限制內選擇一批工作|
|RC-24|PD-ELU-TF-UX-IMPL-01|使用者清楚知道下一步與阻塞原因|
|RC-25|PD-ELU-PLUGIN-20261026|使用者選一個AI工具完成受控協作|
|RC-26|PD-ELU-PLG-BRIDGE-IMPL-01|外部工具只取得授權工作並明確回報|
|RC-27|PD-ELU-PLG-HOST-IMPL-01|使用者可安裝、停用並移除指定宿主整合|
|RC-28|PD-ELU-PLG-CAP-IMPL-01|使用者知道所選工具能做什麼|
|RC-29|PD-ELU-SET-RESOURCE-POLICY-01|使用者為各專案保存獨立偏好|
|RC-30|PD-ELU-SET-BATCH-INTEGRATION-01|修改設定不會悄悄改變已開始的工作|
