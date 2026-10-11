"""SGenAxis UI design deliverable generator, not application implementation."""
from pathlib import Path
import json, html, re
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'ui-design'
(OUT/'screens').mkdir(parents=True,exist_ok=True)
plan=json.loads((ROOT/'product-plan/plan.snapshot.json').read_text(encoding='utf-8'))
taskmap={t['id']:t for t in plan['tasks']}
pages=[]
def page(id,title,route,owners,tasks,goal,layout,fields,primary,states,nexts):
    pages.append(dict(id=id,title=title,route=route,owners=owners.split(),task_refs=tasks.split(),goal=goal,layout=layout,fields=[dict(zip(['name','default','validation'],x)) for x in fields],primary_action=primary,states=dict(zip(['empty','loading','error','disabled','stale'],states)),next=nexts.split(),image='screens/'+id+'.png',status='DESIGNED / PROPOSED',implementation='NOT IMPLEMENTED',verification='NOT RUN'))

page('UI-01','專案管理','/projects','WORK GIT','WORK-001 WORK-002 GIT-001','選擇或匯入正確資料夾並進入專案。',
 '左側最近專案與新增入口；中央以表格呈現專案名稱、完整路徑、Git 分支、活動執行數與存取狀態；右側 Inspector 顯示選中專案的身分、root 與重新定位。',
 [('專案名稱','SGenAxis','顯示名稱不可空白；Project ID 才是身分'),('工作目錄','D:\\AutoCode','驗證存在、權限及實體路徑去重'),('匯入方式','本機資料夾','本機開啟／Git Clone／空目錄初始化'),('重新定位','停用於活動租約','驗證新目錄身分；保留歷史 root')],
 '開啟專案 → UI-02；沒有專案時改為「加入專案」。',
 ['尚無專案，顯示選擇資料夾與 Clone 入口','只鎖定正在探測的列，不清掉其他專案','路徑不存在／拒絕存取，顯示重新定位；不登錄半成品','有活動 Run 時停用重新定位並連結該 Run','路徑搬移後舊證據顯示待核對'], 'UI-02 UI-08')
page('UI-02','專案總覽','/projects/:projectId/overview','UI FLOW','UI-001 FLOW-001','快速辨識下一個需要處理的工項及核准項目。',
 '緊湊專案摘要列，中央待處理工項清單及里程碑進度；下方最近執行；右 Inspector 顯示目前工作區、分支與所選工項下一步。避免裝飾性統計卡。',
 [('範圍','目前專案','摘要只計入目前 project ID'),('里程碑','全部','M0–M4；只讀目前規畫'),('健康摘要','未评估／待核准','缺測試與零工項不可顯示綠燈')],
 '檢視待核准項目 → UI-13。',
 ['新專案未建立規格，導向 UI-14','保留頁面骨架並標記載入來源','載入失敗清除舊專案內容並提供重試','沒有合格 Task 時停用啟動 Agent','過期證據計入待處理，不沿用完成數'], 'UI-03 UI-07 UI-13 UI-14')
page('UI-03','工項工作台','/projects/:projectId/tasks','UI FLOW','UI-001 UI-003 FLOW-001','搜尋、篩選並選取要審閱或執行的 Task。',
 '中央表格：ID、標題、模組、階段、健康、BDD、TDD；選中列藍色；右側工項 Inspector；底部封包摘要與執行入口。',
 [('搜尋','空字串','ID／標題／模組文字，不觸發狀態變更'),('模組／階段／健康','全部','可清除篩選；健康與階段分開'),('排序','工項 ID','穩定排序；排序不影響排程'),('選中工項','無','只啟動單項；第一版並行上限 1')],
 '開啟工程封包 → UI-05；啟動資格不足則只顯示缺口。',
 ['無符合工項，提供清除篩選','表格 skeleton；保留搜尋條件','載入失敗顯示目前 project ID 與重試','封包不完整／未核准／無有效 RED 時禁止產品實作','封包改版後重新載入，舊選取不沿用批准'], 'UI-05 UI-06 UI-07')
page('UI-04','模組架構 DAG','/projects/:projectId/architecture','UI SPEC','UI-002 SPEC-002','理解模組責任、依賴方向與受影響模組。',
 '點陣畫布為主；左模組樹；節點顯示責任與健康；右側 Ports、Contracts、所屬 Tasks；畫布下方縮放、適應與表格替代入口。',
 [('架構版本','DRAFT-0.1','已核准版本唯讀；變更建立新草稿'),('選取／平移／縮放','選取／100%','視圖座標不改工程依賴'),('依賴方向','A → B = A 依賴 B','不可與 Task 前置執行箭頭混用'),('節點連線','唯讀','只有草稿編輯可提議連線；循環禁止核准')],
 '開啟所選模組規格 → UI-14。',
 ['尚無模組，導向建立規格','畫布載入時不暫時顯示錯誤架構','循環顯示完整路徑及紅色問題邊，停止核准','唯讀版本停用新增／刪除依賴','來源版本更新時顯示重新載入提示'], 'UI-05 UI-06 UI-14')
page('UI-05','工項工程封包','/projects/:projectId/tasks/:taskId','UI SPEC EVID','UI-003 SPEC-002 GUARD-001','完整查看 Agent 可執行的 BDD、TDD、範圍與驗收。',
 '左模組／Task 樹；中央文件分頁：概覽、Contract、BDD、TDD、範圍、驗收；右 Inspector 顯示規格 hash、核准、前置與啟動資格；底部執行控制。',
 [('工項','FLOW-001','primary module 唯一；ID 不可就地變更'),('BDD 分頁','Given / When / Then','顯示 scenario ID、Invariant、TDD 映射'),('TDD 分頁','NOT RUN','前置、fixture、操作、斷言、RED 判準與命令全部可讀'),('允許範圍','packages/workflow/**','保護範圍明列；不得只靠檔案白名單跨模組'),('啟動模式','依狀態決定','測試準備與產品實作資格分開；不能無 RED 實作')],
 '檢視待核准項目 → UI-13；合格封包可開啟啟動確認。',
 ['封包缺欄位，逐項列缺口而非空白','只載入指定 task/spec hash','追溯斷鏈顯示缺失 ID 與修訂入口','未批准／版本過期時停用啟動','使用者讀取後規格改版，啟動拒絕並要求重閱'], 'UI-07 UI-13 UI-14')
page('UI-06','工項依賴排程','/projects/:projectId/schedule','FLOW UI','FLOW-002','看清哪些 Task 可以排程，哪些被前置工項阻塞。',
 '中央工項 DAG／佇列雙視圖，箭頭前置→後續；右側依賴原因、全域閘門與下一個候選；底部一個 Agent slot。',
 [('視圖','工項依賴','清楚區別架構依賴頁'),('執行上限','1','首版唯讀；不暗示多 Agent 功能已支援'),('候選','由前置與閘門計算','Task DAG 完成不足以略過里程碑'),('暫停派工','關閉','只停止派出新工項，不取消活動 Run')],
 '檢查下一個工項 → UI-05。',
 ['沒有可排程工項，列出阻塞原因','載入依賴圖時停止新的派工','循環完整路徑可讀並禁止派工','slot 被佔用或必要閘門未完成時不派工','前置版本變更，重新計算而不沿用資格'], 'UI-05 UI-07 UI-13')
page('UI-07','Agent 執行與證據','/projects/:projectId/runs/:runId','EXEC EVID','EXEC-001 EXEC-002 EXEC-003 EVID-001','監看特定 Run，查閱測試證據並安全取消或對帳。',
 '左 Run 歷史；中央事件時間軸與 log 分頁，底部測試結果；右綁定 project/root/spec/commit、provider、階段及逾時；取消是唯一執行期主要動作。',
 [('Run 綁定','建立時固定','UI 切專案不改 Run root'),('輸出分頁','事件','事件／測試／stdout／stderr；敏感資料脫敏'),('跟隨最新','開啟','使用者捲動閱讀時暫停；不搶焦點'),('取消','僅活動 Run 可用','要求終止程序樹；取消中不先宣告已停止'),('重啟對帳','未知效果時顯示','禁止盲目重送具副作用命令')],
 '活動 Run：「取消執行」；中斷 Run：「檢視對帳項目」。',
 ['尚無執行紀錄，導向工項封包','訂閱時顯示連線中，不重複啟動 Run','provider/認證/格式錯誤分類，顯示脫敏診斷','非活動 Run 停用取消；未知效果停用重跑','證據與目前 spec/tree 不符時標過期'], 'UI-05 UI-11 UI-13')
page('UI-08','Git 版本控管','/projects/:projectId/git','GIT WORK','GIT-001 GIT-002 GIT-003','檢視差異，保護既有工作並提交已驗收的工項。',
 '左分支／remote／提交歷史；中央可勾選檔案列表與 split diff；右 commit message、Task/驗收、選取摘要；頂部 Fetch/Pull/Push；底部結果。',
 [('remote／branch','目前程式庫','repo 變更先確認 lease'),('檔案選取','全部不選','只提交選定且核准 scope；保留其他 WIP'),('Commit message','空','不可空白；需要 Task 與驗收'),('Pull 策略','FF-only','dirty/untracked/diverged 必須檢查'),('Push','手動','只上傳 commit；無自動 force')],
 '檢視提交內容 → commit 確認；Push 是獨立後續操作。',
 ['非 Git 專案提供初始化；乾淨目錄顯示無變更','Fetch 不封鎖只讀 diff；變更操作序列化','分歧／衝突／認證被拒明示且保留本機內容','活動 Run 禁切分支/Pull；無驗收禁 Commit','HEAD/tree 改變後刷新 diff 並清除過期提交確認'], 'UI-01 UI-05 UI-13')
page('UI-09','部署設定與產物','/projects/:projectId/deployments','REL','REL-001 REL-002','選定部署方式、環境、版本與同一份已驗證產物。',
 '左 Profiles 測試／正式；中央表單與不可變 artifact 列表；右版本與 gate 檢查；底部準備測試部署。未支援 Adapter 呈現停用。',
 [('Profile','測試環境','名稱、revision、target 明確'),('部署方式','Windows Installer','SSH/Container/DCC 標後續規畫並停用'),('Artifact','未選取','commit、hash、build result 完整；禁止直接輸入假產物'),('健康／復原策略','必填','缺任一則不允許候選'),('Secret','引用名稱','不顯示實際 token；不存入 profile 明文')],
 '驗證部署候選；合格後「準備測試部署」。',
 ['無產物時提供查看 Build Result 入口，不偽造候選','hash 驗證中禁止啟動','hash/profile 無效逐欄顯示；不更動目標環境','缺平台版本、健康檢查或復原聲明則停用部署','profile 或產物改版使原批准失效'], 'UI-10 UI-11 UI-13')
page('UI-10','部署執行與復原','/projects/:projectId/deployments/:deploymentId','REL','REL-002 REL-003','查看部署步驟、健康結果及回滾的實際狀態。',
 '左部署歷史；中央步驟時間軸：驗證→安裝→環境→健康→回歸；下方 log；右目標、artifact hash、profile revision、核准與復原結果。',
 [('部署綁定','唯讀','環境、commit、hash、profile 固定'),('結果','NOT RUN／RUNNING／PASS／FAIL','exit 0 不覆蓋 health fail'),('回滾','依 profile','可逆與不可逆步驟分別列出'),('人工復原','必要時展開','保留實際環境狀態及處置記錄')],
 '失敗時「檢視復原方案」；未核准正式發布時導向 UI-13。',
 ['無部署紀錄，回 UI-09 建立候選','步驟事件即時追加；未知步驟不先標成功','部署 FAIL 與回滾 FAIL 分開顯示','無適用策略時回滾停用，顯示人工復原','版本不符禁止重用舊核准與產物'], 'UI-09 UI-11 UI-13')
page('UI-11','模組報告與里程碑','/projects/:projectId/reports','REPORT EVID','REPORT-001 EVID-002','閱讀模組責任、BDD/TDD 證據、回歸與發布缺口。',
 '左模組／里程碑目錄；中央可讀報告與追溯表；右來源版本、生成時間、過期狀態與匯出；用結果表取代不明百分比。',
 [('報告範圍','目前專案／模組','system 與 module 可切換'),('證據版本','最新符合版本','NOT RUN/skip/unknown 不計已驗證'),('匯出','HTML','含結構 JSON 與來源指紋；離線可讀'),('發布資格','DO NOT RELEASE','不能由單一測試數量推導')],
 '產生／匯出 HTML 報告。',
 ['尚無測試，完整顯示 NOT RUN','生成中保留上一份報告並標為舊版','來源缺失報錯，不覆寫上一份有效文件','來源不完整時不能生成宣稱完整報告','版本改變顯示過期並要求重生成'], 'UI-04 UI-05 UI-07 UI-10')
page('UI-12','環境與 Agent 設定','/settings','HOST EXEC WORK','HOST-002 EXEC-002 EXEC-003','檢查工具可用性並管理本機執行設定。',
 '左設定分類：一般、工作區、Agent、Git、部署、外觀；中央表單；右環境診斷；底部測試連線、儲存與取消。',
 [('Provider','未設定','只有能力 spike 驗證的 Adapter 可啟用'),('CLI 路徑','自動偵測候選','驗證存在與版本，未確認不自動執行'),('認證','外部憑證引用','登入交由官方流程；畫面不展示 token'),('逾時','600 秒','正整數且依已核准政策限制'),('並行數','1','首版唯讀'),('外觀','深色／100%','高對比與字級縮放不改領域狀態')],
 '檢查環境；通過後儲存設定（套用新 Run）。',
 ['未配置 Provider，提供設定步驟','檢測中顯示逐項狀態','版本不相容／認證失效具體標示','檢測失敗不啟用 Adapter；活動 Run 不熱換綁定','設定改變後驗證紀錄失效；下次 Run 重新檢查'], 'UI-01 UI-07 UI-09')
page('UI-13','核准與重新規劃','/projects/:projectId/reviews/:reviewId','FLOW SPEC REL','FLOW-003 SPEC-002 REL-003','讓人明確核准架構、規格、驗收或發布；處理越界。',
 '左核准佇列按類型分组；中央目前／提案差異及必要證據；右決策人、版本、scope 和未完成項；底部核准／退回。REPLAN_REQUIRED 可見。',
 [('核准類型','選取後固定','架構／封包／验收／發布不可互相替代'),('版本／hash','唯讀','核准只綁定所見版本'),('決策說明','空','退回必填；不透過 checkbox 略過 evidence'),('影響範圍','必顯示','架構/業務/Contract/BDD/Skeleton'),('發布目標','僅發布核准顯示','精確環境、產物、hash、復原策略')],
 '核准目前版本／退回修訂；不足資格則只允許退回與查看缺口。',
 ['沒有待核准項目，顯示已處理歷史','載入比對與證據時禁止決策','SPEC_CONFLICT 顯示衝突來源與阻塞行為','必要證據缺失不可核准；Agent 不可代替人決策','審閱期間改版則拒絕提交旧核准'], 'UI-05 UI-09 UI-10 UI-14')
page('UI-14','模組規格與修訂','/projects/:projectId/specs/:moduleId','SPEC UI','SPEC-001 SPEC-002','編寫模組架構、Contract、BDD/TDD 與工項，提交版本審查。',
 '左模組目錄；中央結構化文件編輯器分頁：架構、Ports、Contracts、BDD、TDD、Tasks；右 revision、未儲存與驗證缺口；底部儲存草稿、驗證、提交審查。',
 [('Revision','新草稿','核准版唯讀；另建新版本'),('架構／Ports','結構化欄位','A1–A14 與 ownership/transaction 明列'),('BDD','Given/When/Then','每情境唯一 ID，必須映射 invariant 與 TDD'),('Task','primary module 必填','禁止跨模組隱含 scope'),('TDD','fixture/action/assertions','未實作測試不得標為完成'),('儲存','手動＋未儲存提醒','原子替換；失敗保留原版本與編輯內容')],
 '驗證草稿；完整後提交審查 → UI-13。',
 ['空模組提供規格模板並標草稿','讀取中唯讀；不覆蓋使用者輸入','重複 ID／斷鏈／缺欄位定位到錯誤欄位','批准版不允許就地改寫；缺資料不可提交','發現更新版本時保留本地草稿並要求比對'], 'UI-04 UI-05 UI-13')

dialogs=[
 dict(id='DLG-01',name='加入專案／Clone',pages=['UI-01'],fields=['來源：本機／Git','完整 root','remote URL','專案顯示名'],confirm='驗證後加入',cancel='取消不修改磁碟',rules='非空 clone 目標拒絕覆寫；認證由外部工具處理；失敗不得登錄半成品',tests=['BDD-WORK-001-02','BDD-GIT-001-03']),
 dict(id='DLG-02',name='重新定位專案',pages=['UI-01'],fields=['Project ID','原路徑','新路徑','活動租約'],confirm='驗證並重新綁定',cancel='保留原綁定',rules='有活動 Run 停用；核對身分後才切換；歷史證據待核對',tests=['BDD-WORK-002-02','BDD-WORK-002-03']),
 dict(id='DLG-03',name='啟動 Agent',pages=['UI-05','UI-06'],fields=['Project/root','Task/spec hash','branch/tree','模式','允許/保護範圍','timeout'],confirm='啟動此封包',cancel='不建立 Run',rules='資格與畫面版本二次核對；實作模式須有效 RED；已滿 slot 不啟動',tests=['BDD-UI-003-02','BDD-UI-003-03']),
 dict(id='DLG-04',name='取消執行',pages=['UI-07'],fields=['Run ID','root','執行階段','已知副作用'],confirm='取消此 Run',cancel='繼續執行',rules='確認後顯示取消中，待程序樹結束才顯示已取消；不回滾未知檔案',tests=['BDD-EXEC-003-01']),
 dict(id='DLG-05',name='提交與 Push',pages=['UI-08'],fields=['選中檔案','diff','Task 驗收','commit message','remote/branch'],confirm='Commit；Push 另行操作',cancel='保留工作區與 staging 選取',rules='未選 WIP 不納入；push 被拒不得 force；確認後 tree 改變需重閱',tests=['BDD-GIT-003-02','BDD-GIT-003-03']),
 dict(id='DLG-06',name='發布核准',pages=['UI-09','UI-13'],fields=['目標環境','artifact hash','profile revision','測試證據','復原策略'],confirm='核准此版本到此環境',cancel='保持待核准',rules='不得核准模糊 latest；核准與真正部署分開；雜湊改變失效',tests=['BDD-REL-001-03','BDD-REL-003-01']),
 dict(id='DLG-07',name='回滾／人工復原',pages=['UI-10'],fields=['目前部署','復原目標','可逆/不可逆步驟','資料影響'],confirm='執行已核准復原方案',cancel='保留失敗狀態',rules='無可用方案不顯示假回滾；回滾失敗獨立標 FAIL',tests=['BDD-REL-003-02','BDD-REL-003-03']),
 dict(id='DLG-08',name='未儲存草稿',pages=['UI-14'],fields=['目前模組','revision','未儲存修改'],confirm='儲存草稿並離開',cancel='繼續編輯；另提供明確捨棄草稿',rules='寫入失敗保留輸入；不就地修改核准版本',tests=['BDD-SPEC-002-01']),
]

tokens={'background':'#101112','panel':'#1b1d1f','panelRaised':'#23262a','border':'#34383e','text':'#eef0f3','muted':'#aeb5bf','blue':'#246bff','gray':'#a4adba','running':'#56a8ff','attention':'#f2b544','failed':'#f07979','complete':'#5bc98b','font':'Segoe UI / Microsoft JhengHei','mono':'Cascadia Code / Consolas','body_px':14,'secondary_px':12,'heading_px':18,'control_height_px':32,'radius_px':4,'spacing_px':[4,8,12,16,24],'reference_canvas':[1536,1024],'min_window':[1024,720]}
for p in pages:
    p['bdd_refs']=[b['id'] for task in p['task_refs'] for b in taskmap[task]['bdd']]
    p['tdd_refs']=[b['test'] for task in p['task_refs'] for b in taskmap[task]['bdd']]
    p['page_acceptance']=['可由固定導覽抵達並看清目前 project/root','主要動作在資格不足時停用且有文字原因','empty/loading/error/disabled/stale 均有明確處置','鍵盤可操作；狀態不只靠顏色；長路徑可查看完整內容']
    p['ui_tests']=[{'id':f'UIT-{p["id"]}-{n:02}','status':'PLANNED / NOT RUN','assertion':text} for n,text in enumerate(p['page_acceptance'],1)]

meta={'product':'SGenAxis','version':'UI Design 0.1','created':datetime.now(timezone.utc).isoformat(),'status':'DESIGN PROPOSAL','reference':'D:/VGenAxIs/UI/Prompt Assembly Component.png','product_implementation':'NOT IMPLEMENTED','product_test_results':'NOT RUN','image_note':'所有視覺稿為模擬示例，不是產品執行證據；以文字 schema、BDD 與既有 Contract 為準。','scope':'14 個頁面、8 個共用對話框規格、5 種頁面狀態。未新增業務模組。','new_behavior_note':'新補的外觀、表單草稿、鍵盤與導覽行為為 UI 提案，UIT案例須另核准後才能實作。'}
design={'metadata':meta,'tokens':tokens,'pages':pages,'dialogs':dialogs}
(OUT/'ui-spec.json').write_text(json.dumps(design,ensure_ascii=False,indent=2),encoding='utf-8')

base='''Create ONE production-quality desktop application UI design screenshot, 1536 x 1024 pixels. Product name exactly "SGenAxis" (not AutoCode, not SGenAxis Studio). Use attached VGenAxIs screenshot ONLY as visual style reference; do not copy its artwork, entities, character assets or prompt generation features. Match near-black #101112 workspace, charcoal #1b1d1f dock panels, thin gray #34383e borders, modest 4px corners, cobalt blue #246bff selection and primary button, narrow monochrome line icons, compact professional DCC workstation density. Crisp readable Traditional Chinese typography, 14px body and 12px secondary, technical IDs in monospace. No marketing dashboard, hero, gradients, glow, huge headings, decorative KPI cards, image thumbnails or white panels. Full app viewport, no device/browser frame. Date anchor 2026-10-06. Top menu fixed: "SGenAxis  檔案 編輯 專案 模組 工項 視窗 說明". Top-right quiet label "設計預覽 · 示範資料". Second 48px toolbar contains project selector SGenAxis, path D:\\AutoCode, branch main and current page breadcrumb. 220px left navigation with compact icons and labels exactly: 專案管理 / 總覽 / 工項 / 模組架構 / 依賴排程 / 執行紀錄 / Git / 部署 / 報告 / 核准 / 設定. Central content about 980px, right 310px Inspector tab with blue underline and collapsible sections. Bottom about 100px contextual activity tray plus 28px status strip. Consistent fixed anatomy on every page. Colors represent labeled statuses gray 未開始, blue 執行中, amber 待核准, red 失敗, green 已驗證 only when mock evidence exists. All business activity is design sample data. Screen must show one clear primary action. Avoid unnecessary tools such as brush/text/image generation icons; each toolbar command must suit this page. Do not turn everything into cards; use row separators and grouped panels. Make screen polished, un-clipped and readable. Use accurate compact text, can omit secondary prose to protect legibility. Keep SGenAxis naming exact throughout. Specific page design follows:\n'''
prompts={
'UI-01':'專案管理. Selected nav 專案管理. Main table 3 local projects SGenAxis at D:\\AutoCode branch main status 可存取, Sample Project at D:\\Projects\\Sample branch dev 未開啟, Legacy Demo at D:\\Archive\\Demo 路徑不存在 amber. Top actions 加入專案 cobalt, Clone 程式庫 secondary. Inspector selected SGenAxis: Project ID prj-sgenaxis, root, branch, Git remote 未設定, active runs 0, 重新定位 secondary. Bottom no activity. Opening a project does not start an Agent. All example projects demo only.',
'UI-02':'專案總覽. Selected nav 總覽. Central compact project title SGenAxis with 11 模組 · 27 工項 · 架構待核准. Main grouped next-action list three rows HOST-001 工具鏈 待核准, SPEC-001 工程封包 待核准, WORK-001 專案登錄 未開始. Then milestone table M0 架構核准 待處理, M1 可測試骨架 未開始, M2 開發閉環 未開始, M3 部署閉環 未開始. Small recent runs area empty 尚無執行紀錄. Inspector 下一步 shows architecture DRAFT-0.1, reviews 6 待決策, NOT RUN evidence and cobalt 檢視待核准項目. No fake completed percentage.',
'UI-03':'工項工作台. Selected nav 工項. Main table columns 工項, 模組, 階段, 狀態, BDD, TDD. 7 rows HOST-001 工具鏈 HOST 規格 待核准 草稿 NOT RUN; SPEC-001 工程封包 SPEC 規格 待核准 草稿 NOT RUN blue-selected; WORK-001 專案登錄 WORK 規格 未開始 草稿 NOT RUN; FLOW-001 執行狀態機 FLOW 規格 待核准; EXEC-002 Agent CLI EXEC 規格 未開始; UI-002 模組 DAG UI 規格 未開始; REL-002 靜默安裝 REL 規格 未開始. Filters search, module 全部, health 全部. Below table compact selected BDD preview. Inspector SPEC-001 scope packages/spec/**, approval 待完成, TDD NOT RUN. Primary 開啟工程封包, disabled 啟動 Agent. Do not confuse missing tests with RED.',
'UI-04':'模組架構 DAG. Selected nav 模組架構. Main dotted canvas with seven nodes UI 工程控制台 left, FLOW 流程與核准 center upper selected blue, REL 部署與發布 center lower, SPEC 工程規格 upper right, EXEC Agent 執行 middle right, EVID 驗證證據 lower right, WORK 專案工作區 far right. Directed edges only UI→FLOW UI→REL FLOW→SPEC FLOW→EXEC FLOW→EVID EXEC→WORK REL→EVID, no cycles. Each node gray 未開始 or amber 待核准. Clearly visible legend A → B 表示 A 依賴 B. Right Inspector FLOW, responsibility, IWorkflowCommands, related tasks FLOW-001 FLOW-002 FLOW-003, architecture DRAFT-0.1. Primary 開啟模組規格. Compact pan/zoom/fit controls, bottom no agent running.',
'UI-05':'工項工程封包. Selected nav 工項. Main header FLOW-001 執行狀態機, amber 規格待核准. Tabs 概覽 Contract BDD TDD 範圍 驗收, BDD active. Three readable grouped scenarios: 合法狀態轉移 Given 有效 RED 已驗證 / When 請求開始實作 / Then 進入 IMPLEMENTATION; 未驗收不得完成 Given 驗收尚未完成 / When 請求完成工項 / Then 拒絕並保留狀態; 重複事件 Given 事件已處理 / When 再次收到事件 / Then 不重複轉移. Each has TDD ID and NOT RUN actual status. Inspector task module FLOW, version DRAFT-0.1, scope packages/workflow/**, architecture 待核准, test evidence NOT RUN. Bottom primary 檢視待核准項目, disabled 啟動 Agent and reason 缺少核准與有效 RED.',
'UI-06':'工項依賴排程. Selected nav 依賴排程. Dotted canvas TASK DAG, unlike module DAG arrows mean 前置工項 → 後續工項. Six task nodes HOST-001 → SPEC-001 → SPEC-002; HOST-001 → WORK-001 → WORK-002; SPEC-002 → GUARD-001. All gray 未開始/amber 待核准. Bottom dispatch queue empty 沒有可執行工項, 執行槽 0 / 1. Inspector selected GUARD-001: 前置 SPEC-002 未完成; 架構 待核准; RED NOT RUN; primary 檢視阻塞原因. Compact 暫停派工 switch off with text 不會取消活動 Run. No fake active progress.',
'UI-07':'Agent 執行紀錄, DEMO ACTIVE RUN. Selected nav 執行紀錄. Left secondary run list Run-018 selected 執行中, Run-017 已取消, Run-016 待對帳. Main Run-018 / EVID-001 title blue 執行中 · 測試準備. Events at 13:40:02 已綁定工作區, 13:40:03 檢查工程封包, 13:40:05 開始測試, 13:40:07 等待測試結果. Tabs 事件 測試 stdout stderr with concise monospace logs. Evidence summary RED 待判定, GREEN NOT RUN, 驗收 未開始. Inspector Run ID, project SGenAxis, root D:\\AutoCode, spec rev demo-r3, provider 示範 Provider, timeout 600 s. Primary outlined red 取消執行; no deploy or automatic success. Status bar Agent 執行中 (示範). No secrets.',
'UI-08':'Git 版本控管. Selected nav Git. Toolbar Fetch, Pull (FF-only), Push. Main two columns change list with checkboxes and code diff. 3 files: checked packages/evidence/result-parser.ts, checked tests/evidence/result-parser.test.ts, unchecked notes/local-wip.md. Diff readable + result.status = evidence.valid ? passed : unknown; code is illustrative. Top branch feature/evidence, 本機變更 3. Right inspector commit field fix: validate test evidence; Task EVID-001, 驗收 待完成; selected files 2; unrelated WIP 保留. Primary 檢視提交內容; Commit disabled with reason 工項尚未驗收; Push disabled 無待推送提交. Bottom historical sample commit rows. No force push button and no upload claim.',
'UI-09':'部署設定與產物. Selected nav 部署. Secondary profile tabs 測試環境 active / 正式環境. Main form sections 部署設定: Profile windows-test, 方式 Windows Installer, target 測試 VM · 待設定, OS 版本 待確認. Artifact list empty 尚無已驗證產物 with 查看 Build Result link. Required fields 健康檢查 未設定, 復原策略 未設定, 憑證 僅引用. Disabled future method choices SSH 後續, Container 後續, DCC 後續. Inspector 候選檢查 產物 未選取, 雜湊 待驗證, 相容性 NOT RUN, 核准 待完成. Primary 檢查部署設定, disabled 開始部署. Bottom no deployment history.',
'UI-10':'部署執行與復原, DEMO FAILURE STATE. Selected nav 部署. Main title Deploy-007 / 測試環境 · 示例, red 部署失敗. Vertical or horizontal step timeline 驗證產物 PASS, 安裝 PASS, 環境檢查 PASS, 健康檢查 FAIL, 後續回歸 NOT RUN. Main diagnosis clearly says 安裝 exit 0，健康檢查失敗. Log shows health check timeout example. Separate recovery panel 回滾：未執行, target 前一版本, backup 可用（示範）. Right inspector project, env 測試 VM, artifact demo-0.1.0, hash example only, profile windows-test r2, 正式發布 未核准. Primary 檢視復原方案, secondary 匯出紀錄. Do not mark rollback succeeded or auto-release.',
'UI-11':'模組報告與里程碑. Selected nav 報告. Left secondary module list 系統總覽, SPEC, FLOW selected, EXEC, EVID, REL. Main readable report FLOW 流程與核准, architecture 草稿, implementation 未開始. BDD-to-TDD traceability table three rows BDD-FLOW-001-01 to TDD-FLOW-001-01 NOT RUN; -02 NOT RUN; -03 NOT RUN. Regression table L0 L1 L2 L3 L4 L5 all NOT RUN. Below known gaps 架構未核准; 測試尚未自動化. Inspector source DRAFT-0.1, generated 2026-10-06, validity 草稿, release DO NOT RELEASE. Primary 匯出 HTML. No misleading green metrics. Compact report document surface and clear typography.',
'UI-12':'環境與 Agent 設定. Selected nav 設定. Secondary category list 一般 工作區 Agent selected Git 部署 外觀. Main form Provider 未設定, CLI 路徑 選擇執行檔, 版本 尚未偵測, 認證 使用外部憑證, 執行逾時 600 秒, 並行上限 1 readonly. Under form test diagnostics Node 待檢查, Git 待檢查, Agent CLI 未設定. Right Inspector 能力檢查: 非互動執行 未驗證, 取消程序 未驗證, 事件格式 未驗證, 工作區限制 未驗證. Primary 檢查環境, disabled 儲存並啟用, secondary 取消. Note 設定只套用新 Run. No raw keys, no automatic grants, no shell terminal.',
'UI-13':'核准與重新規劃. Selected nav 核准. Left queue three items 架構 D-01 待核准, FLOW-003 重新規劃 selected amber, 發布候選 尚未就緒. Main title REPLAN_REQUIRED and transaction boundary change proposal. Side-by-side document columns 目前核准版 / 待審提案; concise contract text and list 影響: Architecture, Contract, BDD, Skeleton. Visible message 產品實作已停止，等待重新規劃. Review checklist shows 架構 待確認, BDD 待确认, 新測試 NOT RUN. Right Inspector review kind 結構變更, source r1, proposal r2, operator 本機使用者, decision note textarea. Primary 退回修訂; 核准此版本 disabled due incomplete evidence; 請求補充 secondary. No Agent self approval.',
'UI-14':'模組規格與修訂. Selected nav 模組架構; breadcrumb SPEC > 規格草稿. Left secondary module tree SPEC selected with r1 已核准（示範歷史） and r2 草稿 active. Central structured document editor tabs 架構 Ports Contracts BDD selected TDD Tasks. Scenario editor fields ID BDD-SPEC-001-01, title 封包缺少 BDD, Given 封包缺少必要情境, When 請求啟動實作, Then 拒絕執行並列出缺漏. Linked invariant INV-SPEC-001-01; TDD mapping 尚未選取 amber validation below. Right Inspector Revision r2 草稿, unsaved 未儲存, validity 1 個缺口, protected r1 唯讀; diagnostic 缺少 TDD 對應. Primary 儲存草稿; 驗證 secondary; 提交審查 disabled. Bottom autosave not claimed; exact text 儲存失敗時保留編輯內容.'
}
(OUT/'image-prompts.json').write_text(json.dumps({p['id']:base+prompts[p['id']] for p in pages},ensure_ascii=False,indent=2),encoding='utf-8')

E=html.escape
def table(head,rows):return '<div class="table-scroll"><table><thead><tr>'+''.join('<th>'+E(str(x))+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
css='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#101112;color:#eef0f3;font:14px/1.7 "Segoe UI","Microsoft JhengHei",sans-serif}a{color:#8bb8ff}button,input{font:inherit}header{position:sticky;top:0;z-index:10;background:#141618;border-bottom:1px solid #34383e;padding:13px 24px;display:flex;align-items:center;gap:20px}header strong{font-size:20px}header span{color:#aeb5bf}aside{position:fixed;top:63px;left:0;bottom:0;width:236px;padding:18px 12px;overflow:auto;background:#1b1d1f;border-right:1px solid #34383e}aside a{display:block;padding:8px 10px;color:#c1c8d2;text-decoration:none;border-radius:4px}aside a:hover,aside a.active{background:#223550;color:#8bb8ff}main{margin-left:236px;padding:28px;max-width:1780px}h1{font-size:30px;margin:0 0 8px}h2{font-size:22px}h3{font-size:16px}section{scroll-margin-top:80px;margin-bottom:38px}.muted{color:#aeb5bf}.pill{font-size:12px;padding:3px 9px;border:1px solid #5b4b29;color:#f2b544;border-radius:4px}.intro{max-width:950px}.screen{display:block;width:100%;height:auto;border:1px solid #34383e;border-radius:4px;background:#1b1d1f}.screen-link{display:block;margin:18px 0}.table-scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;vertical-align:top;padding:10px 12px;border-bottom:1px solid #34383e}th{color:#aeb5bf;background:#1b1d1f}code{font:12px Consolas,monospace;color:#afccff;overflow-wrap:anywhere}details{border:1px solid #34383e;border-radius:4px;margin:12px 0;padding:12px 16px}summary{cursor:pointer;color:#dce6f3}button{background:#246bff;color:#fff;border:0;padding:8px 12px;border-radius:4px;cursor:pointer}.outline{background:#23262a;border:1px solid #34383e}input{background:#101112;border:1px solid #34383e;color:#eef0f3;padding:9px;width:100%;border-radius:4px;margin-bottom:15px}.note{border-left:3px solid #f2b544;background:#252117;padding:14px 18px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.tile{padding:18px;background:#1b1d1f;border:1px solid #34383e;border-radius:4px}.tile img{width:100%;height:auto}.page-num{font:12px Consolas,monospace;color:#7da8e8;letter-spacing:1px}.actions{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}.anchor-list{display:flex;gap:8px;flex-wrap:wrap}.anchor-list a{padding:4px 8px;background:#23262a;text-decoration:none}.swatch{display:inline-block;width:16px;height:16px;border:1px solid #666;vertical-align:middle;margin-right:8px}.missing{padding:50px;border:1px dashed #5b4b29;color:#f2b544}.hidden{display:none}:focus-visible{outline:2px solid #8bb8ff;outline-offset:3px}@media(max-width:1000px){aside{position:static;width:auto;display:flex;flex-wrap:wrap;gap:4px}aside input{width:100%}main{margin:0;padding:16px}header{position:static}.grid{grid-template-columns:1fr}}@media print{header,aside,.actions{display:none}main{margin:0;padding:0}body{background:white;color:black}.muted,summary,a{color:#333}section{break-before:page}.screen{max-height:70vh;object-fit:contain}details{break-inside:avoid}.hidden{display:block}}'''
nav=''.join(f'<a href="#{p["id"]}" data-search="{p["id"]} {p["title"]}">{p["id"]}　{p["title"]}</a>' for p in pages)
body='<section id="overview"><div class="page-num">DESIGN SYSTEM / 0.1</div><h1>SGenAxis 全頁面 UI 設計</h1><p class="muted">14 個頁面 · 8 個共用對話框 · 70 種頁面狀態定義 · 56 項 UI 驗收案例</p><p class="intro">延續已選定的深色工作站視覺：固定選單與專案列、左侧資源／功能導覽、中央工作區、右側 Inspector、底部執行列。產品框架仍為 Electron + React + TypeScript；本交付是設計文件，不是產品程式。</p><p class="note">所有視覺稿都是示範狀態，不代表真實執行、核准或測試結果。圖中文字或連線若與 schema 有差異，以 schema 與原產品 Contract 為準。新增 UI 行為仍待設計審查，未自動批准架構。</p><div class="actions"><a href="../product-plan/index.html">產品規畫</a><a href="ui-spec.json">完整 UI Schema</a><a href="verification.json">文件檢查</a><button id="expand">展開全部規格</button><button class="outline" id="collapse">收合全部規格</button></div><div class="grid">'
for p in pages:
    image=OUT/p['image'];body+=f'<a class="tile" href="#{p["id"]}"><span class="page-num">{p["id"]}</span><h3>{E(p["title"])}</h3>'+(f'<img loading="lazy" src="{p["image"]}" alt="{E(p["title"])}視覺稿">' if image.exists() else '<p class="muted">視覺稿生成中</p>')+'</a>'
body+='</div></section>'
body+='<section id="system"><h2>共用設計系統</h2>'+table(['Token','值'],[[E(k),('<span class="swatch" style="background:'+v+'"></span>' if isinstance(v,str) and v.startswith('#') else '')+E(str(v))] for k,v in tokens.items()])+'<h3>狀態語意</h3><p>灰：未開始；藍：執行中；黃：待核准／待對帳／證據過期；紅：非預期失敗／阻塞；綠：必要驗證與驗收完成。TDD RED 是開發階段，不能把「缺測試」或「未核准」寫成 RED。產品發布資格獨立判定。</p><h3>尺寸與可及性</h3><p>1536×1024 為視覺基準；1280×800 收窄 Inspector 並允許頁內捲動；1024×720 將 Inspector 改為可開關側抽屜，不縮小文字硬塞。低於此尺寸提示擴大桌面視窗；本期不設計手機操作產品。所有按鈕有語意標籤與鍵盤焦點；Tab 切換、Escape 關閉非破壞性對話框並歸還焦點；狀態用文字與圖示雙重表達。色彩對比須在實作時實測 WCAG AA，圖片不構成可及性通過證據。</p><h3>導覽及資料綁定</h3><p>route 為邏輯導覽識別，不是已存在的 URL API。Project ID、Task ID、spec revision 保留於頁面上下文；專案切換清除視圖快取並重新載入，執行中的 Run 維持原绑定。使用者在 dirty 草稿離頁時顯示 DLG-08。</p></section>'
for p in pages:
    body+=f'<section id="{p["id"]}" class="design-page"><div class="page-num">{p["id"]} / {E(p["route"])}</div><h2>{E(p["title"])} <span class="pill">設計提案</span></h2><p>{E(p["goal"])}</p>'
    body+=(f'<a class="screen-link" href="{p["image"]}" target="_blank"><img class="screen" loading="lazy" src="{p["image"]}" alt="SGenAxis {E(p["title"])}設計示意；模擬資料"></a>' if (OUT/p['image']).exists() else '<div class="missing">視覺稿待生成</div>')
    body+='<details><summary>UI Schema、欄位與操作</summary><p>'+E(p['layout'])+'</p>'+table(['控制項','預設','驗證與互動'],[[E(f[k]) for k in ['name','default','validation']] for f in p['fields']])+'<p><strong>主要動作：</strong>'+E(p['primary_action'])+'</p><p>Owner：'+E(', '.join(p['owners']))+'</p><p>下一頁：</p><div class="anchor-list">'+''.join(f'<a href="#{n}">{n}</a>' for n in p['next'])+'</div></details>'
    body+='<details><summary>空白、載入、錯誤、停用與過期狀態</summary>'+table(['狀態','可見內容與處置'],[[E(k),E(v)] for k,v in p['states'].items()])+'</details>'
    body+='<details><summary>BDD／TDD 追溯與 UI 驗收</summary>'+table(['產品工項','既有規格'],[[t,f'<a href="../product-plan/index.html#task-{t}">{E(taskmap[t]["title"])}</a>'] for t in p['task_refs']])+table(['BDD','TDD','目前結果'],[[b,t,'NOT RUN'] for b,t in zip(p['bdd_refs'],p['tdd_refs'])])+table(['UI case','可量測斷言','狀態'],[[c['id'],E(c['assertion']),c['status']] for c in p['ui_tests']])+'<p>UI cases 是補充設計提案；其餘引用原封包，不改變既有測試期待。</p></details></section>'
body+='<section id="dialogs"><h2>共用對話框與操作狀態</h2><p>對話框沿用相同暗色 panel，寬 560–720px；背景保留所在專案 context。主要動作明列操作对象；送出中禁止重複送出；錯誤保留輸入；關閉後焦點返回觸發控制項。此處為結構／互動規格，尚無逐框高擬真稿。</p>'
for d in dialogs:body+='<details><summary>'+d['id']+' · '+E(d['name'])+'</summary>'+table(['項目','規格'],[['出現頁面',E(', '.join(d['pages']))],['欄位',E(' / '.join(d['fields']))],['確認',E(d['confirm'])],['取消',E(d['cancel'])],['規則',E(d['rules'])],['BDD',E(', '.join(d['tests']))]])+'</details>'
body+='</section><section id="handoff"><h2>交付與實作邊界</h2><p>本交付完成頁面設計與工程追溯；尚未連接 Agent、Git、檔案系統或部署服務。圖中 click target 是視覺示意，不是可執行產品。畫廊僅提供頁面導覽、檢視圖片與展開規格。</p><p>實作順序：核准共用 shell／UI schema → HOST-002 與 UI-001 → UI-002/003 → 其他模組 driving adapters。新增 UI 行為須回到對應模組規格審查，不以畫稿默認批准新的業務契約。</p><p>已知限制：ImageGen 可能簡化小字、欄位或連線；精確品牌拼字、節點邊、狀態、scope 与測試 ID 以 ui-spec.json / 產品 ModuleSpec 為準。未進行產品 UI、鍵盤、對比或響應式實測。</p></section>'
js='''const q=document.querySelector('#search');q.addEventListener('input',()=>{document.querySelectorAll('aside a[data-search]').forEach(a=>a.classList.toggle('hidden',!a.dataset.search.toLowerCase().includes(q.value.toLowerCase())));});document.querySelector('#expand').onclick=()=>document.querySelectorAll('details').forEach(d=>d.open=true);document.querySelector('#collapse').onclick=()=>document.querySelectorAll('details').forEach(d=>d.open=false);document.querySelectorAll('aside a').forEach(a=>a.addEventListener('click',()=>{document.querySelectorAll('aside a').forEach(x=>x.classList.toggle('active',x===a));}));window.addEventListener('beforeprint',()=>document.querySelectorAll('details').forEach(d=>d.open=true));'''
doc='<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SGenAxis UI Design</title><style>'+css+'</style></head><body><header><strong>SGenAxis</strong><span>UI 設計規格 / 0.1</span><span class="pill">設計稿 · 非產品</span></header><aside><input id="search" type="search" aria-label="搜尋頁面" placeholder="搜尋頁面…"><a href="#overview">全部頁面</a><a href="#system">設計系統</a>'+nav+'<a href="#dialogs">共用對話框</a><a href="#handoff">交付邊界</a></aside><main>'+body+'</main><script type="application/json" id="ui-spec">'+json.dumps(design,ensure_ascii=False).replace('<','\\u003c')+'</script><script>'+js+'</script></body></html>'
(OUT/'index.html').write_text(doc,encoding='utf-8')
(OUT/'README.md').write_text('''# SGenAxis UI design

Open index.html locally. All main screenshots live under screens/.
ui-spec.json defines 14 pages, states, controls, dialogs and BDD/TDD mappings.
Image mockups illustrate the selected visual style; schema controls precise behavior.
Product code, real Agent execution, Git mutation, deployment and test results are NOT implemented.

Regenerate document: python docs/build_ui_design.py
Validate document: python docs/verify_ui_design.py

Do not treat mock PASS states in screenshots as product verification evidence.
This design does not approve architecture, new domain rules or release.
''',encoding='utf-8')
print(json.dumps({'pages':len(pages),'dialogs':len(dialogs),'screens_present':sum((OUT/p['image']).exists() for p in pages),'output':str(OUT/'index.html')},ensure_ascii=False))
