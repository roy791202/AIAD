"""Render requirements intake only; never writes board or production files."""
import json, hashlib, html, re
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT=Path('D:/AIAD')
OUT=Path(__file__).parent
ARCHIVE=Path('C:/AIAD-Recovery/requirements-reset-20261031T135405Z/board-snapshot.json')
archived=json.loads(ARCHIVE.read_text(encoding='utf8'))
cards=[t for t in archived['tasks'] if t.get('zone')!='green']
assert len(cards)==30
# Old IDs are provenance, not recreated execution tasks.
rows=[
('PD-RUST-IMPROVE-20261025','品質與驗收','維護者看懂目前可用與未完成的能力','查看功能清單 → 查看對應版本與證據 → 確認缺口','整理使用者能力及原始案例的追溯，不重做已完成模組','把規劃或測試數量當功能完成','交付摘要是否應以可操作流程，而非Rust檔案或技術切片為主？','以使用者流程呈現能力與證據；技術切片只作追溯。'),
('PD-RUST-SYSTEM-REGRESSION-01','AI執行閉環','使用者能知道一次任務是否真正完成','確認需求 → 建立工作包 → 明確授權 → 執行 → 回報 → 獨立驗證 → 接受','先確認手動閉環的成功、失敗、取消與重開結果','本輪啟動capture／Agent／S4或將封包Ready視為驗收','本機文件流程穩定後，第一版是否先採一次一項、人工接受的閉環？','先人工啟動與接受；自動化另確認，不執行。'),
('PD-RUST-NATIVE-UI-VERIFY-01','品質與驗收','使用者在真正桌面產品完成主要操作','開啟桌面產品 → 操作專案／文件 → 保存 → 關閉重開 → 核對','本機主流程的原生驗收需求與錯誤可見性','用瀏覽器或元件測試冒充原生通過','第一階段驗收是否以Windows免安裝版為必要目標，其餘平台待定？','先確認Windows免安裝版；跨平台需求保留待確認，不宣稱已支援。'),
('PD-ELU-COLLAB-20261026','協作整體','有無Git都能交換並整合工作成果','開啟專案 → 導入資料 → 預覽差異 → 選擇整合 → 保存','保留原44案例來源；需求依使用者情境確認','一次把44案例改成單一大工單或強迫Git','無Git是否為第一階段完整日常流程，Git協作列下一階段？','先本機無Git流程，保留Git相同行為需求與差異。'),
('PD-ELU-RECOVERY-ARCH-01','復原','使用者知道清空與復原會影響什麼','選定文件 → 查看清空範圍 → 確認 → Undo；另選快照還原','界定單次Undo與關閉後可恢復的差別','把session快照當耐久備份或改已有複合Undo方向','第一階段要保證關閉程式後還能還原嗎？保留幾份、多久？','保留既有單文件複合Undo；耐久快照列明確待決需求，不默認已完成。'),
('PD-ELU-PROJECT-IMPL-01','本機專案','使用者建立或開啟專案並安全切換','新增／開啟目錄 → 選擇偏好或略過 → 顯示目前專案 → 編輯 → 切換／關閉','專案位置、偏好選擇、dirty提示、失敗保全、A/B隔離','搬移主線、重做已交付偏好核心或自動覆寫原專案','建立專案最少必填哪些？目錄已有內容時應開啟、拒絕還是另選目錄？','預設最少步驟；既有內容先辨識，不覆寫；偏好可明確略過。'),
('PD-ELU-DOCUMENT-IMPL-01','文件','使用者自然地開啟保存與獨立交換文件','選文件 → 開啟／編輯 → 保存；匯出 → 在另一專案匯入 → 檢查結果','區分場景、架構、UI文件；缺依賴待綁定；非法內容拒絕；來源保全','把手動登記身分當日常必要步驟、metadata登記當完整匯入或自動改ID','一般使用者是否只操作新增／開啟／保存／匯入／匯出，身分處理隱藏在系統內？匯入預設建立副本還是參照來源？','建議日常流程隱藏身分技術步驟；跨專案匯入優先副本、來源不變。這是需求候選，不授權自動寫manifest。'),
('PD-ELU-IMPORT-IMPL-01','程式碼導入','使用者將既有程式碼轉為可檢視的模型建議','選資料夾／檔案 → 選包含／排除 → 分析 → 查看事實與推論 → 接受建議','唯讀來源、增量更新與來源對照','自動改來源、把推論當解析事實或任意掃整台機器','第一版必須支援哪些語言與檔案？分析只需檔案／符號結構還是語意依賴？','先明確選定範圍與少數必要語言；顯示不確定，不自動套用。'),
('PD-ELU-BINDING-IMPL-01','綁定','使用者把畫面元素與正確資料或行為連結','選UI元素 → 選目標 → 檢查綁定 → 保存；目標變動 → 顯示失效 → 修復','可見待綁定／失效狀態，保留UI與歷史證據','依顯示名稱猜測重綁或悄悄刪失效元素','目標不存在時是否允許繼續編輯保存，但只阻擋依賴該綁定的執行？','允許保存待修文件；具體指出受影響操作，執行範圍後續確認。'),
('PD-ELU-INTEGRATION-IMPL-01','內容整合','使用者理解外來修改並安全採用','選外來文件 → 比較本地／外來／可用基準 → 選新增更新或略過 → 確認','衝突可見、取消不變、過期結果不可覆寫、同版匯入不重複','無基準自動三方合併、隱藏ID重映射或整包覆寫','第一階段是否採人工逐項選擇；取代是否限明確選定文件，不取代整專案？','先人工逐項選擇與明確文件範圍，無可靠基準時不自動合併。'),
('PD-ELU-RECOVERY-IMPL-01','復原','誤操作後能找回選定內容','清空前確認 → 一次Undo；需要時選快照 → 預覽 → 還原','以既有複合Undo成果為基礎，確認未保存與已保存內容的保護','刪來源檔、Git reset、全專案清空或未確認的跨檔回滾','清空按鈕作用於目前文件、選取物件還是整個專案？快照還原前是否保留目前版本？','日常清空限目前文件／明選範圍；還原前保留現況的需求另明定。'),
('PD-ELU-GIT-IMPL-01','Git協作','需要Git的使用者明確控制版本操作','查看狀態／差異 → 暫存選定內容 → 預覽提交 → 本人確認 → 查看結果','區分既有add-A與Index-only路徑、錯誤後顯示真實狀態','本輪真實commit/push/reset、預設上傳非程式主線與佈版資料','第二階段需要哪些Git日常操作？是否將Index-only作新流程的明確預設而保留舊行為？','先狀態／差異及明確Index-only確認；圖形歷史、hunk、衝突另確認。'),
('PD-ELU-UX-IMPL-01','本機操作介面','使用者從一致入口完成導入與綁定','專案／文件入口 → 選擇 → 預覽 → 確認或取消 → 查看結果','主要流程入口、空狀態、忙碌、錯誤、成功及可取消狀態','只為技術切片新增孤立入口或暴露未實作控制項','哪些操作放檔案選單、文件工具列與Inspector？哪些屬進階診斷？','依日常任務設入口；文件身分獨立入口是否保留進階模式待確認。'),
('PD-ELU-FIXTURE-IMPL-01','品質與驗收','驗證不會污染使用者專案','選測試範本 → 建隔離副本 → 操作 → 只重設該副本','測試專案與真實資料區隔，來源唯讀','把測試工具當一般使用者功能或重設真實看板','這是工程驗收工具，是否不列為第一版對外功能？','列工程驗收支援需求；維持隔離，不增加日常UI。'),
('PD-ELU-VERIFY-IMPL-01','品質與驗收','使用者能分辨功能有無真正驗證','選流程 → 看受測版本／模式 → 看結果與限制','原44案例保留追溯，mock/real及NOT RUN分開','把歷史PASS視為現行PASS或只驗一種模式宣稱兩種完成','無Git流程先驗完整，Git模式後續獨立驗收，是否符合優先順序？','兩模式需求保留；按階段驗收，不能互相代替。'),
('PD-ELU-GIT-ARCH-01','Git協作','提交的內容與使用者預覽相同','選Index內容 → 預覽 → 確認 → 查看提交與未暫存檔','保留A1成果，需求先確認提交範圍、過期與錯誤結果','為新需求改掉既有Git契約、force或真實Git操作','graph、hunk staging與衝突介面哪些為下一階段必需？','不重做A1；先確認需要的操作，再定各自契約。'),
('PD-ELU-TASKFLOW-20261026','任務工作流','使用者追蹤需求到成果的工作狀態','建立需求 → 確認規格 → 指派 → 看進度 → 驗證 → 接受 → 交付','區分需求、工作執行、驗證與接受；保留原61案例追溯','將原30卡重新派工或恢復輪詢','任務的最小日常狀態與哪些轉換須本人確認？','先人工操作一條清楚流程；狀態語意先於自動化。'),
('PD-ELU-TF-REF-IMPL-01','任務參照','AI取得正確版本與最少必要內容','選相關文件／元素 → 預覽工作包 → 鎖定版本 → 送出','可追溯版本、唯讀參照與可寫範圍區分','引用即授權或把整個專案內容全送出','使用者如何選參照與可寫範圍？送出前是否能預覽內容？','預覽明列來源／版本／寫入範圍，未授權內容不加入。'),
('PD-ELU-TF-EVID-IMPL-01','驗證證據','使用者看懂每項需求如何被證明','查看需求 → 看BDD情境 → 看對應測試／執行版本 → 看證據','證據與被驗內容版本綁定，過期明示','測試通過自動代表使用者接受','一般使用者需要摘要到哪個層級？測試細節是否可展開查看？','先人可讀摘要，細節可追溯；接受是獨立動作。'),
('PD-ELU-TF-RUN-IMPL-01','AI執行閉環','使用者控制一次工作開始與停止','明確開始 → 查看執行 → 取消／完成 → 重開後看結果','先確認執行中、取消、斷線、失敗、重啟時可見結果','任何本輪Runner／S4實作、背景自動啟動或假成功','失聯工作重開後應顯示待確認、可重試還是自動續跑？','失聯先標待確認，不自動重跑；原生Yes始終本人按。'),
('PD-ELU-TF-AUDIT-IMPL-01','工作紀錄','使用者知道誰在何時對哪個版本做了什麼','查看時間線 → 篩選工作／人／版本 → 展開結果與原因','重要授權、操作、取消、驗證與接受的追溯','把所有底層log直接塞到日常畫面','紀錄保存多久？哪些內容不得記錄？需要匯出供審查嗎？','保留必要事件與版本，隱去憑證與敏感內容；保留期待確認。'),
('PD-ELU-TF-DELIV-IMPL-01','接受與交付','使用者確認成果後才將其視為已接受','查看產出 → 看獨立驗證 → 接受或退回 → 明確交付','驗證與接受分離、退回原因、失敗時可恢復','自動commit/push/release或把綠燈當部署授權','接受後「交付」具體指本機保存、匯出包還是Git提交？','第一版先本機可取得的成果與本人接受；對外發布另授權。'),
('PD-ELU-TF-BATCH-IMPL-01','批次與資源','使用者在資源限制內選擇一批工作','選工項 → 查看批次與預算 → 調整 → 確認 → 查看分項結果','需求只確認合批規則、預算上限與部分失敗處理','本輪啟動批次、成本預留或更改Run契約','合批的首要目的是減少上下文成本、提高速度還是限制資源？超額是否一律停止？','第一階段可延後；啟用前必須可見上限與逐項結果。'),
('PD-ELU-TF-UX-IMPL-01','任務操作介面','使用者清楚知道下一步與阻塞原因','選任務 → 看需求／範圍／狀態 → 操作允許動作 → 看結果','狀態命名、必要確認、停用原因與重試入口','顏色代替狀態語意、空按鈕或反覆叫使用者重按','Tasks首頁主要讓使用者看進度、確認需求還是接受成果？','依主要工作給下一步；停用一定顯示原因。'),
('PD-ELU-PLUGIN-20261026','外部AI接入','使用者選一個AI工具完成受控協作','選宿主 → 連接 → 人工取一項工作 → 回報 → 驗證 → 接受','先一個宿主的最小手動閉環，再考慮第二個','本輪安裝Plugin、探測未知端點或宣稱雙宿主支援','第一個必需宿主是Codex還是Claude？是否晚於本機流程完成？','本機流程先；首宿主由Owner選，逐版本驗證。'),
('PD-ELU-PLG-BRIDGE-IMPL-01','外部AI接入','外部工具只取得授權工作並明確回報','連接 → 檢查身分與權限 → 查詢／領取 → 回報狀態','能力、錯誤、取消、重送與可寫範圍的使用者期待','先選transport/auth實作或在需求階段定新Port','本機手動連接是否足夠？需要跨機器或多人共用嗎？','先本機明確連接與窄權限；遠端多人列後續需求。'),
('PD-ELU-PLG-HOST-IMPL-01','外部AI接入','使用者可安裝、停用並移除指定宿主整合','選版本 → 安裝／啟用 → 測試連接 → 停用／移除','安裝位置、原設定保全、升級與回復需求','實際安裝、默改既有宿主設定或假設套件通用','可接受免安裝接入還是必需宿主Plugin？支援的OS／版本為何？','先選一種明確接入方式與版本；安裝另案確認。'),
('PD-ELU-PLG-CAP-IMPL-01','外部AI能力','使用者知道所選工具能做什麼','選宿主 → 看已測／未測能力 → 選允許模式 → 不支援時得知原因','版本化能力與未知狀態，安全降級的使用者預期','Runner降級實作、未知能力當支援或自動切換供應者','功能不足時應停止、改手動還是詢問切換工具？','未知即明示未測；先提供人工選擇，不自動切換。'),
('PD-ELU-SET-RESOURCE-POLICY-01','專案偏好','使用者為各專案保存獨立偏好','開專案 → Settings → 選方案／調整 → 保存 → 重開確認；新建時可略過','保留已交付schema／保存／UI；確認日常必要欄位與A/B隔離','重做已交付保存、還原成本紀錄或混入使用者憑證','第一階段Settings哪些欄位有用？無AI執行時是否先隱藏模型／預算進階區？','保留專案獨立偏好與可略過選項；進階項依實際需求呈現。'),
('PD-ELU-SET-BATCH-INTEGRATION-01','批次與資源','修改設定不會悄悄改變已開始的工作','保存新政策 → 新批次採新版本；執行中工作保留舊版本 → 看預算結果','政策版本、重送／過期／重啟對帳與專案隔離的需求','本輪修改BATCH／RUN／S4或把偏好保存當完整閉環','資源上限與成本顯示必須在第一版上線，還是等批次執行一起確認？','與批次共同確認；不將此需求塞入本機文件主流程。'),
]
assert set(r[0] for r in rows)==set(t['id'] for t in cards)
byid={t['id']:t for t in cards}
items=[]
for n,r in enumerate(rows,1):
 old,group,goal,flow,scope,excluded,question,reco=r;t=byid[old]
 items.append(dict(id=f'RC-{n:02}',source_card=old,source_title=t['title'],group=group,user_goal=goal,user_flow=flow,in_scope_candidate=scope,out_of_scope=excluded,question=question,recommendation=reco,status='NEEDS_CONFIRMATION',source_version=t.get('version'),prior_zone=t['zone'],historical_bdd=t.get('bdd'),historical_tdd=t.get('tdd'),historical_note=t.get('note'),historical_owner_actions=t.get('ownerActions',[])))
skills=[]
for f in sorted((ROOT/'AI_INSTRUCTIONS').rglob('SKILL.md')):
 skills.append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
spec={'stage':'REQUIREMENTS_CONFIRMATION_ONLY','generated_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'source_archive':str(ARCHIVE),'archive_sha256':hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),'instruction_sources':skills,
 'confirmed':['Owner選定：先完成本機專案與文件操作','298張綠燈成果保留；30張非綠燈封存不復建','主線D:/AIAD；保留C修改與原免安裝版','輪詢維持PAUSED；看板--no-dispatch；S4不動','本輪不實作、不建立新執行卡、不執行產品測試或RED'],
 'assumptions_pending':['主要使用者暫以本機專案作者／設計者為候選；是否另有非技術使用者待確認','Windows免安裝版為首階段候選；其他OS／版本尚待確認','本機文件主流程不強迫Git；尚待Owner確認','日常文件流程隱藏技術身分管理是建議，不是自動採納／寫manifest的批准'],
 'lessons':{'lookup':'以rg --files搜尋docs及主線命名LESSON/lesson的文件，未找到既有失敗經驗專檔；不宣稱已讀不存在文件。','derived_from':'本次對話及封存卡的明確紀錄；本檔內列入，不改寫歷史證據。','items':['先釐清使用者工作，再拆技術切片；不要為切片增加孤立操作入口。','停止只重複巡檢及重製報告；需要可觀察的流程結果。','提示停用原因；反覆點擊不是除錯方法。','元件／VM／建置PASS不能代表原生UI、保存重開及隔離PASS。','既有成果與批准保留但不等於新範圍授權；不重做綠燈成果。','清空工項時必須區分已完成與未完成；本輪綠燈逐筆核對。','需求階段不先承諾原子跨檔交易、自動合併、自動改ID或宿主能力。']},
 'priority_flow':['新增／開啟專案','選擇偏好或略過','開啟／編輯／保存文件','關閉重開及專案切換','獨立匯出／匯入','衝突處理與復原'],
 'first_decisions':[
 {'id':'Q1','question':'首階段的使用者、平台及交付形態？','recommendation':'本機專案作者；Windows免安裝版先；其他平台需求保留。','affected':['RC-03','RC-06','RC-13']},
 {'id':'Q2','question':'首階段必需的文件種類與操作？','recommendation':'先列清.ess場景、架構文件、.sgendesign UI的用途與新增／開啟／保存；不要先假設三者格式相同。','affected':['RC-07','RC-13']},
 {'id':'Q3','question':'跨專案匯入是副本還是持續參照？重複匯入如何處理？','recommendation':'預設副本且來源不變；有重複／衝突先讓人決定，不自動覆寫或重映射。','affected':['RC-07','RC-09','RC-10']},
 {'id':'Q4','question':'復原保證到哪個範圍與時間？','recommendation':'目前文件一次複合Undo沿用既有方向；關閉後快照、保留期及跨檔還原另明定。','affected':['RC-05','RC-11']},
 {'id':'Q5','question':'第一階段是否排除AI執行、Git寫入與Plugin安裝？','recommendation':'先本機文件流程；後續需求完整保留，需求確認不等於執行授權。','affected':['RC-02','RC-12','RC-17','RC-25','RC-30']}],
 'nonfunctional_intake':{'data_safety':'保存失敗、取消及非法匯入時原專案／來源不變；精確保證待規格階段定義。','concurrency':'多視窗與切換專案需避免過期覆寫；不在此階段指定鎖實作。','security':'不靜默讀取外部目錄，不帶入憑證；路徑越界與敏感資料需後續案例。','resources':'大檔大小、節點數、匯入耗時及取消時限待量化，不編造數值。','observability':'使用者能看到處理中、錯誤、未保存與未驗證狀態；診斷細節與友善提示分開。','accessibility':'鍵盤操作、焦點返回、停用原因列UI階段確認。'},
 'next_gate':'先逐項確認需求；再做有2–3個成熟產品參考依據的UI/UX、架構與契約、BDD/TDD、Implementation Envelope。不得從本清單直接進入實作。',
 'deferred':['UI原型與成熟產品比較尚未開始；本輪只列流程與範圍，不假稱完成UI Schema','架構／契約／交易選型尚未重核','BDD feature、step stubs、fixtures及TDD/RED須需求與架構確認後產出；舊BDD僅歷史追溯','測試者、審查者須與開發者為獨立新工作階段；本輪無開發驗收','PR／Git寫入／安裝／發布不在本輪範圍'],
 'items':items}
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'requirements.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf8')
esc=lambda s:html.escape(str(s))
parts=['<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EluSlot 需求確認清單</title><style>body{font:16px system-ui;max-width:1150px;margin:32px auto;padding:0 20px;line-height:1.7;color:#202833}h1,h2,h3{line-height:1.35}section,article{border:1px solid #ccd4df;border-radius:10px;padding:20px;margin:20px 0}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd4df;padding:9px;text-align:left;vertical-align:top}small{color:#526174}a{color:#245cb4}li{margin:7px 0}pre{white-space:pre-wrap}.badge{background:#fff1ca;padding:4px 10px}nav a{display:inline-block;margin:5px}</style><h1>EluSlot：先確認需求，再重新規劃</h1><p><span class="badge">需求草案，未批准實作</span>　30張封存卡逐一追溯；298張綠燈不變。</p><p>已確認優先：<strong>本機專案與文件操作</strong>。本頁不是恢復的工作看板，也不是新執行工單。</p>']
for heading,key in [('已確認的邊界','confirmed'),('仍待確認的假設','assumptions_pending'),('第一條主流程','priority_flow')]:
 parts.append('<section><h2>'+heading+'</h2><ol>'+''.join('<li>'+esc(v)+'</li>' for v in spec[key])+'</ol></section>')
parts.append('<section><h2>先確認的五個問題</h2><table><tr><th>問題</th><th>唯一推薦（尚待確認）</th><th>追溯</th></tr>'+''.join('<tr><td>'+esc(q['id']+' '+q['question'])+'</td><td>'+esc(q['recommendation'])+'</td><td>'+esc(', '.join(q['affected']))+'</td></tr>' for q in spec['first_decisions'])+'</table></section>')
parts.append('<h2>30項需求確認清單</h2><p>RC編號僅供討論追溯；不是新的實作卡。相同流程的規劃卡、功能卡與驗收卡可合併確認，但不刪除原始案例。</p><nav>'+''.join('<a href="#'+i['id']+'">'+i['id']+'</a>' for i in items)+'</nav>')
for i in items:
 parts.append('<article id="'+i['id']+'"><h3>'+esc(i['id']+' · '+i['user_goal'])+'</h3><small>'+esc(i['group']+'｜來源 '+i['source_card']+' v'+str(i['source_version']))+'</small><p><strong>使用者流程：</strong>'+esc(i['user_flow'])+'</p><p><strong>候選範圍：</strong>'+esc(i['in_scope_candidate'])+'</p><p><strong>不納入本輪：</strong>'+esc(i['out_of_scope'])+'</p><p><strong>待確認：</strong>'+esc(i['question'])+'</p><p><strong>建議：</strong>'+esc(i['recommendation'])+'</p><details><summary>原卡規格、已完成範圍與歷史批准（不代表新授權）</summary><pre>'+esc(json.dumps({k:i[k] for k in ['source_title','prior_zone','historical_bdd','historical_tdd','historical_owner_actions','historical_note']},ensure_ascii=False,indent=2))+'</pre></details></article>')
for heading,value in [('非功能需求待確認',spec['nonfunctional_intake']),('失敗經驗與防重複措施',spec['lessons']),('準則來源',skills),('後續關卡與尚未執行',{'next_gate':spec['next_gate'],'deferred':spec['deferred']})]:
 parts.append('<section><h2>'+heading+'</h2><pre>'+esc(json.dumps(value,ensure_ascii=False,indent=2))+'</pre></section>')
parts.append('<script type="application/json" id="requirements-spec">'+json.dumps(spec,ensure_ascii=False).replace('</','<\\/')+'</script></html>')
(OUT/'index.html').write_text(''.join(parts),encoding='utf8')
lines=['# 需求確認清單','', '狀態：REQUIREMENTS_CONFIRMATION_ONLY；不是實作工單。','', '已確認：先完成本機專案與文件操作。','', '[完整互動閱讀清單](index.html) · [結構化追溯](requirements.json)','', '## 優先確認']
for q in spec['first_decisions']:lines+=['',q['id']+' '+q['question'],'建議：'+q['recommendation']]
lines+=['','## 30卡逐一對照','','|需求確認ID|原卡|使用者目標|','|---|---|---|']
for i in items:lines+=['|'+i['id']+'|'+i['source_card']+'|'+i['user_goal']+'|']
(OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
print(json.dumps({'items':len(items),'skills_read':len(skills),'path':str(OUT/'index.html'),'stage':spec['stage']}))
