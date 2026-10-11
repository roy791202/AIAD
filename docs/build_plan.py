"""Generate offline planning artifacts; this is not the SGenAxis product."""
from pathlib import Path
import json, html, hashlib
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'product-plan'
OUT.mkdir(parents=True, exist_ok=True)
E = html.escape

modules = [
 ('HOST','桌面宿主與建置','擁有應用程式生命週期、composition root、IPC 與工具配置','Driving / Infrastructure Adapter','Desktop Bootstrap','IApplicationFactory, ISettingsStore','ElectronMain, PreloadBridge','啟動失敗須關閉已建立資源；IPC 不提供任意 shell；不擁有業務狀態'),
 ('SPEC','工程規格','擁有 ModuleSpec、架構版本、Contracts、BDD/TDD 與工項定義','Domain / Application','IModuleSpecCommands','ISpecRepository','SpecFileAdapter','核准後規格不可原地變更；修訂產生新版本並使相關證據待重驗'),
 ('FLOW','流程與核准','擁有 Task 執行階段、核准紀錄與前置條件','Domain / Application','IWorkflowCommands','IWorkflowStore, IExecutionPort','SQLiteWorkflowStore, ExecutionAdapter','狀態與事件同一交易提交；外部操作用 operation ID 對帳，不承諾 exactly-once'),
 ('WORK','專案工作區','擁有 Project ID、root 綁定與工作區租約','Application','IWorkspaceCommands','IPathProbe, IWorkspaceStore','LocalPathAdapter, SQLiteWorkspaceStore','驗證新路徑後原子切換綁定；有執行租約時拒絕重新定位'),
 ('GIT','版本控管','管理程式庫操作與工作區變更；Git 是版本歷史權威','Application / Adapter','IVersionControl','IGitProcess, IWorkspaceLease','GitCliAdapter','遠端寫入失敗保留本機 commit；衝突不得自動丟棄資料'),
 ('EXEC','Agent 執行','擁有 Run、程序生命週期、取消與環境綁定','Application','IAgentExecution','IAgentProvider, IProcessHost, IRunStore','ProviderCliAdapter, WindowsProcessAdapter','先保存執行意圖再啟動程序；崩潰後對帳，禁止盲目重跑'),
 ('GUARD','開發邊界','判定封包完整性、範圍與保護規則','Domain / Application','IEnvelopeCheck','IChangeReader','GitDiffReader','檢查結果綁定 envelope 與 diff 雜湊；語意疑慮交由審查'),
 ('EVID','驗證證據','擁有不可變測試紀錄、版本綁定與有效性判定','Domain / Application','IEvidenceCommands','ITestRunner, IEvidenceStore','ProcessTestRunner, ArtifactStore','先完整寫入證據再登錄索引；缺漏或版本不符不得判 PASS'),
 ('UI','工程控制台','呈現專案、Task、DAG、規格與部署狀態投影','Driving Adapter','UI Actions → Application Ports','ITypedClient','ElectronIpcClient','不擁有工程狀態；所有 mutation 由 use case 完成'),
 ('REL','部署與發布','擁有 Deployment Profile、發布核准與部署操作紀錄','Application','IReleaseCommands','IDeploymentTarget, IArtifactStore, IReleaseStore','WindowsInstallerAdapter；後續 SSH/Container/DCC adapters','部署每步有 checkpoint；失敗與回滾結果分開，不假設所有操作可逆'),
 ('REPORT','報告投影','生成系統／模組 HTML 與版本摘要','Application / Adapter','IReportQuery','ISpecReader, IEvidenceReader, IReportWriter','HtmlReportAdapter','只讀工程來源；生成新檔驗證後替換，不回寫規格'),
]
M = {x[0]:dict(zip(['id','name','responsibility','layer','input','output','adapter','transaction'],x)) for x in modules}
# A -> B means A depends on B's published input contract, never B's concrete adapter.
edges = [('UI',m) for m in ['SPEC','FLOW','WORK','GIT','EVID','REL','REPORT']] + [('FLOW',m) for m in ['SPEC','WORK','GUARD','EXEC','EVID']] + [('GUARD','SPEC'),('EXEC','WORK'),('GIT','WORK'),('REL','WORK'),('REL','EVID'),('REPORT','SPEC'),('REPORT','EVID')]
edges += [('HOST', m) for m in ['UI','FLOW','EXEC','WORK']]
tasks=[]
def task(id,mod,title,phase,deps,intent,scope,contract,given,when,then,badgiven,badwhen,badthen,boundgiven,boundwhen,boundthen,fixture,tests,ac,estimate='M'):
    scenarios=[]
    for n,(g,w,t) in enumerate([(given,when,then),(badgiven,badwhen,badthen),(boundgiven,boundwhen,boundthen)],1):
        scenarios.append(dict(id=f'BDD-{id}-{n:02}',given=g,when=w,then=t,invariant=f'INV-{id}-01',test=f'TDD-{id}-{n:02}',result='NOT RUN'))
    tasks.append(dict(id=id,module=mod,title=title,milestone=phase,depends_on=deps.split() if deps else [],intent=intent,allowed_scope=scope.split(),contract=contract,invariant=f'INV-{id}-01',bdd=scenarios,fixture=fixture,tdd_design=tests,acceptance=ac,effort=estimate,state='PLANNING',readiness='NOT_READY_FOR_IMPLEMENTATION',architecture_revision='DRAFT-0.1',approval='PENDING',results='NOT RUN',requirement='REQ-'+mod,protected_scope=['所有其他模組產品原始碼','已核准 Contract / BDD / Skeleton / 測試期待','使用者既有未提交檔案']))

task('SPEC-001','SPEC','ModuleSpec 與追溯模型','M1','', '建立人與 Agent 共用的結構化工程封包', 'packages/spec/** tests/spec/**', '每個 Task 恰有一個主要模組；BDD 必須追溯到 invariant 與 TDD；核准資料版本不可變', '一份包含架構、Contract、BDD、TDD 與範圍的完整封包','使用者驗證封包','列出有效追溯鏈且不自動核准架構','封包缺少 BDD 或參照不存在的 TDD','使用者驗證封包','拒絕實作資格並列出缺少欄位與斷鏈 ID','兩個 Task 使用相同 ID','使用者匯入封包','拒絕重複 ID 且保留原規格', {'valid_module':'sample','missing_bdd':True,'duplicate_id':'T-1'}, 'L0 schema、參照完整性；L2 input port 匯入交易；RED：缺漏或重複被錯誤接受', '完整封包可讀；缺漏/重複被拒；既有資料不變')
task('SPEC-002','SPEC','規格修訂與核准鎖定','M1','SPEC-001','防止實作期間悄悄變更骨架','packages/spec/** tests/spec/**','核准綁定內容雜湊；修訂不繼承先前核准','規格版本 v1 已核准','使用者建立 v2 草稿','v1 保持不可變且 v2 等待核准','Agent 正在實作已鎖定 v1','Agent 嘗試修改公開 Contract','拒絕修改並回報 REPLAN_REQUIRED','核准人正在檢視 v1 而草稿已更新為 v2','核准人送出 v1 的核准','僅核准 v1 且不得套用到 v2',{'revisions':['v1','v2'],'approval_hash':'fixture-hash'},'L0 revision/hash；L2 stale approval；RED：舊核准套用新內容','三情境通過；核准者、時間、版本完整')
task('WORK-001','WORK','專案登錄與資料夾驗證','M1','SPEC-001','選擇本機專案並隔離識別','packages/workspace/** tests/workspace/**','Project ID 穩定；實體 root 不得重複；失敗不部分登錄','存在可讀寫且名稱含中文空白的資料夾','使用者登錄專案','產生 Project ID 並保存正確完整路徑','目標不存在或不可存取','使用者登錄專案','顯示原因且未新增專案','同一路徑透過大小寫或 junction 別名已登錄','使用者再次登錄','導向既有專案且不產生重複',{'paths':['專案 A','missing','alias'],'permission_failure':'injected'},'L0 canonical identity；L3 Windows 路徑/別名；RED：同目錄重複登錄','中文空白、缺失、權限及別名案例通過')
task('WORK-002','WORK','切換、租約與重新定位','M1','WORK-001','防止 UI 切換改變 Agent 執行位置','packages/workspace/** tests/workspace/**','UI selection 與 Run binding 分離；活動租約保護 root','A 有活動 Run 且 B 已登錄','使用者切換到 B','畫面顯示 B 且 A 的 Run 維持原 root','A 有活動執行租約','使用者重新定位 A','拒絕重新綁定並指出活動 Run','A 已停止且搬移到新目錄','使用者驗證後重新定位','保持 Project ID 並將舊證據標記待核對',{'projects':['A','B'],'lease':'active','moved_root':'A-new'},'L2 selection/lease transaction；L3 relocated identity；RED：selection 改寫 Run root','切換無跨專案寫入；租約生效；搬移不沿用未驗證綠燈')
task('GUARD-001','GUARD','封包資格與範圍檢查','M1','SPEC-002','在實作前檢查批准與允許範圍','packages/guard/** tests/guard/**','路徑允許不覆蓋模組限制；未核准或無有效 RED 不得啟動產品實作','封包已核准且 RED 證據有效','執行器請求開始實作','回傳允許與 envelope hash','封包缺少批准或 RED 為編譯失敗','執行器請求開始實作','拒絕並指出未滿足閘門','允許檔案列表含有另一模組檔案但未宣告整合範圍','執行器檢查變更','回報 MODULE_BOUNDARY_ESCAPE',{'red':['behavioral','compile_error'],'foreign_module':'B'},'L0 gate truth table；L2 envelope port；RED：無有效 RED 被允許','所有拒絕原因可追溯；路徑穿越及模組越界不得通過')
task('FLOW-001','FLOW','執行狀態機與核准閘門','M1','SPEC-002 GUARD-001','將開發流程轉成可檢查的狀態轉移','packages/workflow/** tests/workflow/**','狀態只能透過合法事件轉移；審查前不得 COMPLETE','Task 在 TDD_RED 且有效 RED 已登錄','系統提交開始實作事件','Task 進入 IMPLEMENTATION','Task 尚未完成驗收','系統收到完成請求','拒絕 COMPLETE 並保留目前狀態','同一合法事件被重複送達','系統處理事件','只發生一次狀態轉移',{'events':['red_verified','start','complete'],'duplicate_event_id':'e1'},'L0 transition matrix；L2 persisted event/version check；RED：跳過驗收可完成','非法轉移全拒；重複事件冪等；所有狀態有時間與原因')
task('FLOW-002','FLOW','依賴排程與失敗停止','M2','FLOW-001 EXEC-001 EVID-001','只執行前置條件已滿足的工項','packages/workflow/** tests/workflow/**','Task DAG 與架構 DAG 獨立；依賴失敗不自動執行後續','A 已完成且 B 依賴 A','排程器選擇下一個工項','B 可排程並保存決策原因','A 未完成而 B 依賴 A','排程器選擇下一個工項','B 保持等待且不啟動 Agent','工項依賴形成 A 到 B 到 A','使用者驗證排程','顯示循環路徑並拒絕啟動',{'dag':[['A','B']],'cycle':[['A','B'],['B','A']],'concurrency':1},'L0 topo/cycle；L2 fake execution dispatch；RED：依賴未完成仍 dispatch','第一版並行上限 1；無循環；不超派或重複派工')
task('FLOW-003','FLOW','重新規劃與人工決策','M2','FLOW-001','結構變更強制返回規劃','packages/workflow/** tests/workflow/**','架構、Contract 或 BDD 變更需重新核准，不得自我批准','Agent 發現必要交易邊界不足','Agent 回報結構變更需求','Task 進入 REPLAN_REQUIRED 並停止後續產品修改','新規格未核准','使用者請求繼續實作','拒絕續跑並顯示待核准內容','只有保持 Contract 的私有函式整理','系統審查變更分類','允許在原 envelope 內繼續',{'classifications':['local','structural','behavior'],'new_approval':False},'L0 classification decision input；L2 stop/replan event；RED：結構變更直接繼續','報告含 trigger、影響範圍與選項；批准不能由 Agent 代填')
task('EXEC-001','EXEC','Agent Provider 邊界與模擬執行','M1','WORK-002 SPEC-001 GUARD-001','建立供不同 Agent 接入的執行協定','packages/execution/** tests/execution/**','Run 綁定 project/root/spec/commit；程序輸出不是完成權威','合格封包與模擬 Provider 已就緒','使用者啟動 Run','事件按序回填且每筆綁定相同 Run ID','Provider 不可用','使用者啟動 Run','回報失敗且不宣告工項完成','Provider 輸出完成但尚無測試證據','系統處理輸出','只保存候選結果而不將 Task 標綠',{'provider':'fake','events':['started','progress','candidate_result']},'L2 fake provider contract；L0 event validation；RED：provider done 直接 COMPLETE','mock 可重現；事件 schema 可驗；無測試不綠')
task('EXEC-002','EXEC','首個真實 Agent CLI Adapter','M2','EXEC-001 FLOW-001 EVID-001','接上經相容性驗證的 Agent 執行工具','packages/adapters/agent/** tests/agent/**','僅使用已驗證 CLI 非互動協定；未知認證/版本不得猜測','已選定 Provider 的版本、認證與事件格式通過 spike','使用者執行示範 Task','Agent 在指定 root 產生範圍內變更與可解析事件','登入失效或 CLI 版本不相容','使用者啟動 Agent','停止並回報 IMPLEMENTATION_BLOCKED 且不輸出憑證','CLI 輸出截斷或非協定文字','系統接收輸出','保存診斷並拒絕偽造成功',{'provider':'TBD approval D-02','sandbox_repo':'temporary','credentials':'external reference only'},'L2 recorded protocol fixtures；L3 real CLI smoke；RED：格式錯誤被當成功','先提交 CLI spike 報告；mock/真實證據分開；未知供應商協定保持阻塞','L')
task('EXEC-003','EXEC','取消、逾時與重啟對帳','M2','EXEC-002','避免失控子程序與重複執行','packages/execution/** packages/adapters/process/** tests/execution/**','取消涵蓋子程序樹；不確定外部效果不得盲目重跑','Run 與其子程序正在執行','使用者取消 Run','在設定的取消期限內終止程序樹並標記取消','程序拒絕正常結束','Run 到達逾時','執行升級終止並記錄結果而非成功','應用程式在外部命令完成與保存結果之間崩潰','使用者重新啟動','Run 標為待對帳且不自動重送命令',{'timeout_ms':5000,'cancel_grace_ms':2000,'child_tree':2,'crash_point':'before_result_commit'},'L3 Windows child process tree；L2 crash/recovery injection；RED：取消留下子程序','取消/逾時可觀測；無孤兒程序；未知結果黃色待核對','L')
task('GUARD-002','GUARD','變更保護與執行權限','M2','GUARD-001 EXEC-002','限制寫入並攔截不允許的變更','packages/guard/** packages/adapters/guard/** tests/guard/**','worktree 不是安全沙箱；無法強制執行的限制不得聲稱已保護','已套用且驗證 OS 或 Provider 寫入限制','Agent 嘗試寫入受保護檔案','寫入遭拒且留下審計紀錄','執行環境無法提供所需強制限制','使用者啟動要求該限制的 Task','拒絕自動實作並列出缺失能力','Agent 修改測試期待以讓測試通過','系統審查變更','攔截驗收並要求規格審查',{'protected':'contracts/approved.json','escape':'../other-project','assertion_change':True},'L3 actual write-denial probes；L2 diff evidence；RED：受保護檔可寫入','OS/Provider capability 報告必備；偵測與預防分開；不能靠 prompt 宣告隔離','L')
task('EVID-001','EVID','測試 Runner 與有效 RED','M1','SPEC-001 WORK-001','區分預期行為失敗與測試環境故障','packages/evidence/** packages/adapters/tests/** tests/evidence/**','RED 必須 test build 成功且因指定缺失行為失敗；空輸出不算 PASS','測試可建置且指定行為尚未實作','系統執行 RED 驗證','登錄 behavioral RED 並連結 BDD','測試因編譯或 fixture 損壞失敗','系統執行 RED 驗證','拒絕 RED 資格並分類失敗','命令 exit 0 但缺少必要測試結果','系統解析結果','標記未測得而非 PASS',{'outcomes':['behavioral_failure','compile_error','empty_output'],'expected_test_id':'case1'},'L0 result parser；L2 runner fake outputs；L3 tiny fixture runner；RED：empty exit0 被判 PASS','每次保存命令、cwd、版本、exit、結果；三類失敗不可混用')
task('EVID-002','EVID','證據失效與模組覆蓋','M2','EVID-001 SPEC-002','測試證據只適用於實際驗證版本','packages/evidence/** tests/evidence/**','結果綁定 spec hash 與工作樹指紋；passed count 不代表 BDD 完整','所有必要 BDD 有對應有效證據','系統計算模組覆蓋','呈現已驗證數與缺口為零','程式或規格在測試後改變','系統重新計算狀態','舊結果保留但不再支持當前綠燈','部分必要測試被 skip','系統計算完成資格','列出未驗證行為並拒絕完成',{'hashes':['before','after'],'test_states':['passed','skipped','not_run']},'L0 validity/coverage；L2 historical evidence queries；RED：版本變更仍有效','未知/skipped 不計通過；歷史不覆寫；B1–B12 均有評估')
task('GIT-001','GIT','Clone、Init 與程式庫摘要','M2','WORK-002','管理本機與遠端 Git 專案','packages/version-control/** packages/adapters/git/** tests/git/**','clone 失敗不登錄為完整專案；憑證不得出現在輸出','可用的本機 bare 遠端與空目標資料夾','使用者 clone','成功後登錄專案並顯示 branch 與 remote','遠端不可達或認證被拒','使用者 clone','顯示脫敏錯誤且不宣告 clone 成功','目標資料夾非空','使用者 clone','拒絕覆寫並保留既有資料',{'remote':'temporary bare repository','target':'temporary','credential_failure':'injected'},'L3 local bare git；L2 auth redaction；RED：失敗仍登錄成功','clone/init/status 有 BDD；無覆寫；本機離線測試不依賴外部服務')
task('GIT-002','GIT','Fetch、安全 Pull 與分支切換','M2','GIT-001','更新版本同時保護工作區','packages/version-control/** tests/git/**','默认 FF-only；分歧拒絕自動 merge/rebase；活動租約禁止切換','工作目錄乾淨且遠端可快轉','使用者 pull','更新到遠端提交並顯示新版本','分支分歧或更新會覆蓋本機變更','使用者 pull','停止並保留本機內容與提交','目前工作區有活動 Run','使用者切換分支','拒絕並指出佔用 Run',{'repositories':2,'cases':['fast_forward','diverged','dirty','lease']},'L3 local remote competing commits；L2 lease gate；RED：dirty overwrite','未追蹤檔也受保護；fetch 不改工作檔；衝突無自動丟棄')
task('GIT-003','GIT','審核式 Commit 與 Push','M3','GIT-002 FLOW-001 EVID-002','將合格工項交付為可追溯版本','packages/version-control/** tests/git/**','commit 需驗收；只納入選定範圍；push 需授權；禁自動 force','工項驗收通過且已選取範圍內變更','使用者提交並授權 push','建立可追溯 commit 並回報遠端結果','工作區含其他未選取 WIP','使用者提交此工項','提交只包含選定工項且保留 WIP','遠端已前進而拒絕 push','使用者 push','保留本機 commit 並顯示拒絕原因',{'selected':['task-file'],'unrelated':['wip-file'],'remote_advanced':True},'L3 partial staging/remote rejection；L2 acceptance gate；RED：混入 WIP','commit 與 push 狀態分開；push 不代表發布或測試通過')
task('UI-001','UI','專案切換與狀態看板','M2','WORK-002 FLOW-001 EVID-001','讓使用者看見真實進度與阻塞','apps/desktop/renderer/** tests/ui/**','stage 與 health 分離；顏色配文字圖示；UI 不改權威狀態','有待執行、執行中及待核准 Tasks','使用者開啟看板','顯示灰藍黃狀態及原因和下一步','載入專案失敗','使用者開啟看板','顯示錯誤且不殘留另一專案內容','搜尋沒有符合項目','使用者篩選 Tasks','顯示空狀態與清除篩選入口',{'tasks':['pending','running','approval'],'search':'no-match'},'L1 component；L5 keyboard/project switching；RED：錯專案卡片殘留','五色加文字；鍵盤可操作；無資料/錯誤/載入完整')
task('UI-002','UI','互動式模組架構 DAG','M2','UI-001 SPEC-001','用圖呈現核准架構及模組健康','apps/desktop/renderer/graph/** tests/ui/graph/**','A→B 代表 A 依賴 B；繪圖不修改核准架構；Task DAG 分開','合法模組 DAG 與模組 Tasks 已載入','使用者選取模組','顯示其責任、Ports、依賴與所屬 Tasks','架構含循環 A 到 B 到 A','使用者驗證架構','顯示循環路徑並禁止核准','模組沒有工項或證據','使用者查看節點','顯示未評估而非完成綠燈',{'nodes':['A','B','C'],'cycle':['A','B','A'],'empty_module':'C'},'L0 cycle；L1 graph selection；L5 zoom/keyboard alternative；RED：cycle 被接受','依賴方向固定；表格替代視圖；大圖性能門檻待基準 spike 定義')
task('UI-003','UI','BDD/TDD 工程封包與執行詳情','M2','UI-001 SPEC-002 EVID-002 EXEC-001','每個 Task 可檢視與交付給 Agent','apps/desktop/renderer/tasks/** tests/ui/tasks/**','顯示的封包 hash 必須等於啟動使用的 hash','完整 Task 已選取','使用者展開詳情','呈現 BDD、TDD、範圍、命令、證據及核准狀態','封包缺少必要資料','使用者查看 Task','啟動停用並列出缺漏','畫面載入後封包已改版','使用者啟動 Task','要求重新檢視而不使用舊核准',{'tabs':['overview','bdd','tdd','runs','diff','acceptance'],'stale_hash':True},'L1 accessible tabs；L2 start hash check；L5 stale UI；RED：舊畫面啟動新規格','顯示完整 Given/When/Then；證據連結可用；啟動理由明確')
task('REPORT-001','REPORT','統一模組 HTML 與系統總覽','M3','SPEC-002 EVID-002','生成可離線審閱的工程文件','packages/reporting/** tests/reporting/**','報告為投影；嵌入結構資料；不得偽造核准或測試結果','規格與證據均可讀','使用者產生報告','產生可離線開啟且含來源指紋的 HTML','測試結果尚未存在','使用者產生報告','清楚呈現 NOT RUN','規格含 HTML 特殊字元與 script 標記','使用者開啟報告','內容作為文字呈現而不執行注入',{'spec':'sample','results':[],'unsafe_text':'<script>test</script>'},'L0 escape/hash；L3 file offline；L5 reader checks；RED：缺結果被標 PASS','24 項模組資訊可查；版本過期可判定；無 CDN/fetch 依賴')
task('REL-001','REL','部署設定與版本產物追溯','M3','SPEC-002 EVID-002','部署明確版本的已驗證產物','packages/release/** tests/release/**','部署 profile 版本化；產物不可變且有 hash；secret 僅保存引用','具備環境、命令、檢查與復原策略的 profile','使用者建立部署候選','候選綁定 commit、artifact hash 與 profile revision','profile 缺少健康檢查或復原聲明','使用者驗證候選','阻止部署並列出缺口','產物內容在核准後被替換','使用者開始部署','雜湊不符而拒絕執行',{'target':'test','artifact_hash':'sha256-fixture','secret_ref':'credential-store/key'},'L0 profile validation；L2 artifact tamper；RED：替換產物仍可部署','test/prod 使用同產物；不把 Git push 算部署')
task('REL-002','REL','Windows 打包與靜默安裝驗證','M3','REL-001 UI-003 EXEC-003','建立第一個完整部署 Adapter','packages/adapters/deployment/windows/** tests/deployment/windows/**','精確 OS/installer 版本需 D-03 核准；命令成功還須安裝檢查','乾淨 Windows VM 與核准安裝包','系統執行靜默安裝','exit、log、檔案、捷徑、啟動與版本均符合 profile','安裝中途故障或權限不足','系統執行靜默安裝','標失敗並保存實際環境與可用復原步驟','同版本已安裝','系統重複安裝後卸載','符合冪等策略且卸載保留宣告的使用者資料',{'vm':'D-03 target pending','installer':'tool selection pending','cases':['clean','upgrade','repeat','uninstall']},'L3 installer VM failure injection；L5 launch smoke；RED：缺檔仍成功','靜默 install/uninstall、權限、環境、重複安裝均有證據；無 VM 則 BLOCKED','L')
task('REL-003','REL','發布核准、健康檢查與回滾','M3','REL-002 FLOW-003 GIT-003','正式部署可審核且能報告復原真相','packages/release/** tests/release/**','部署成功和回滾成功是不同結果；不可逆變更需明確處置','測試環境驗證完成且正式發布已核准','系統部署到正式環境','使用同一產物並在健康檢查通過後標記成功','部署命令成功但健康檢查失敗','系統驗證部署','部署標 FAIL 並依已核准策略復原','回滾過程也失敗','系統處理復原結果','回滾標 FAIL 並提供人工處置且保留環境狀態',{'deployment_exit':0,'health':'fail','rollback':['success','fail']},'L2 fake target sagas；L3 VM rollback；RED：exit0 忽略 health','核准綁定環境/產物/profile；無自動略過；恢復失敗不綠','L')
task('REL-004','REL','SSH、容器與 DCC 部署擴充規劃','M4','REL-003','逐種方式建立獨立核准與相容性矩陣','planning/deployment/**','此 Task 僅產出設計；不可宣告 Adapter 已支援','首個擴充目標及版本由使用者指定','規劃 Agent 產生擴充封包','每種方式各有 port mapping、BDD/TDD、回滾限制與新工項','尚未指定 OS 或 DCC 版本','規劃 Agent 檢查就緒度','標待決策且不進入產品實作','DCC 版本使用不同 Python/Qt 執行環境','規劃 Agent 定義相容性矩陣','分列 load/unload、環境隔離及 batch 驗證',{'targets':['SSH','Compose','DCC'],'versions':'TBD'},'文件 lint：每個 target 有版本/fixtures/失敗/復原；Adapter 實作測試留待新封包核准','本 Task 完成僅代表擴充規劃完成；新 Adapter 各走獨立 RED→GREEN','L')
task('HOST-001','HOST','可重現工具鏈與測試骨架','M1','','建立後續 Agent 可使用的建置與測試入口','package.json package-lock.json tsconfig*.json vitest.config.* cucumber.* playwright.config.* tools/** tests/host/**','版本固定且命令可重現；測試未發現不能回報通過；僅建立已核准模組骨架','乾淨 checkout 與核准工具版本已就緒','開發者安裝鎖定依賴並執行測試入口','相依版本符合 lockfile 並產生含案例 ID 的機器結果','指定工項沒有可執行測試','開發者執行該工項測試','回報無案例且不得偽造 GREEN','同一 fixture 測試在第二個乾淨工作目錄執行','開發者重複測試','案例數與結果一致且不依賴第一個目錄',{'fixture_suite':['pass','behavior_failure'],'empty_suite':'empty','roots':['clean-A','clean-B']},'L2 task-runner contract；無案例防誤綠先建立可運行 RED；工具安裝故障分類 infrastructure','記錄 Node/npm/框架版本；定義 test:task 入口；空 suite 不綠；CI/本機同命令')
task('HOST-002','HOST','Electron 宿主、受限 IPC 與組裝入口','M1','HOST-001 WORK-001 FLOW-001','讓 UI 與應用服務經核准邊界連接','apps/desktop/main/** apps/desktop/preload/** apps/desktop/composition/** tests/host/**','renderer 無任意檔案或 shell 權限；只允許經驗證命令；composition root 組裝 adapters','已核准的視窗與服務組裝設定','使用者啟動應用程式','顯示初始視窗且服務透過型別化橋接提供','呼叫來源或 IPC 輸入不符合契約','介面送出請求','拒絕操作且不執行檔案或 shell 副作用','服務在啟動中途失敗','使用者啟動應用程式','顯示診斷並釋放已建立資源',{'ipc':['valid','invalid','untrusted_sender'],'startup_failure':'injected'},'L2 bridge schema/permission；L3 startup cleanup；RED：非法 IPC 可觸發副作用','context isolation/sandbox 設定有測試；無 unrestricted shell API；關閉行為遵循 D-06')
next(t for t in tasks if t['id']=='SPEC-001')['depends_on']=['HOST-001']
next(t for t in tasks if t['id']=='UI-001')['depends_on'].append('HOST-002')
tasks.sort(key=lambda t: (t['milestone'], 0 if t['id']=='HOST-001' else 1, t['id']))

decisions=[
 ('D-01','技術與架構','建議 Electron + React + TypeScript；React Flow + ELK；XState 隔離於 workflow；SQLite 保存執行資料','核准前不能進入 skeleton/產品實作'),
 ('D-02','首個 Agent Provider','建議先評估 Codex CLI；須查核實際非互動協定、授權、取消與事件格式','阻塞 EXEC-002 及依賴項，其他規劃可繼續'),
 ('D-03','首版平台與安装器','Windows 本機優先；精確 OS build、架構、安裝器與簽章策略尚待選定','阻塞真實安裝相容性聲明'),
 ('D-04','核准與權限','首版單機單一使用者；人核准架構/驗收/正式發布；自動 push 預設停用','強隔離機制必須 spike 驗證，worktree 不等於沙箱'),
 ('D-05','儲存權威','每模組 module.html 內 module-spec JSON 為 canonical；UI 由其生成；SQLite 儲存 run/events，不複製規格权威','採 sidecar YAML 需另作 ADR；匯出 plan.json 是可重建快照'),
 ('D-06','程序續跑','第一版 UI 切換可不中斷；整個 App 結束後不保證背景繼續；重開先對帳','常駐 service / 多機 worker 留待後續架構'),
]
reqs=[('HOST','可重現建置、桌面宿主與受限 IPC'),('SPEC','每個 Task 有 BDD/TDD 與完整 Agent 工程封包'),('FLOW','可控狀態機、核准及重新規劃'),('WORK','多專案與資料夾切換'),('GIT','Git 下載、更新、提交與上傳'),('EXEC','Agent 自動執行與停止'),('GUARD','禁止越過核准骨架與模組範圍'),('EVID','以實際測試證據決定狀態'),('UI','紅綠黃看板與架構 DAG'),('REL','完整建置、安裝、部署與回滾流程'),('REPORT','統一人類可讀 HTML 與可追溯報告')]
for t in tasks:
    t['test_command']=f'npm run test:task -- --id {t["id"]}'
    t['command_status']='PLANNED — 尚無產品 runner，不可直接執行'
    t['working_directory']='<approved-worktree-root>'
    t['timeout_seconds']=600 if t['module']!='REL' else 1800
    t['retry_policy']='不自動重送 mutation；只允許明確宣告可重試的唯讀操作，最多 1 次'
    t['result_path']=f'.devworkflow/results/{t["id"]}/<run-id>/'
    t['execution_steps']=['確認 primary module、ADR 與封包核准版本','建立對應 skeleton/test seams；不得改已核准語意','依 fixtures 與 TDD 設計寫可建置測試','執行測試並證明是指定缺失行為造成 RED','只在 allowed_scope 實作','執行相同測試達 GREEN；禁止弱化 assertions','跑模組與相關回歸，分類每個失敗','審查 diff/Contract/BDD/架構與驗收，更新 module.html；待人核准 commit']
    t['regression_modules']=sorted(set([t['module']]+[d.split('-')[0] for d in t['depends_on']]))
    t['bdd_coverage_categories']={f'B{i}':{'state':'Applicable' if i in [1,2,3,4,6,12] else 'Deferred','reason':'本封包三個初步情境，完整案例需在 specification gate 補足' if i in [1,2,3,4,6,12] else '需在模組規格核准前依 transaction/lifecycle/cross-module/compatibility 適用性補齊或說明 N/A'} for i in range(1,13)}
    t['task_type']='PLANNING_DELIVERABLE' if t['id']=='REL-004' else 'IMPLEMENTATION_SLICE'
    t['tdd_cases']=[{'id':b['test'],'bdd':b['id'],'precondition':b['given'],'fixture_ref':'fixtures.json','action':b['when'],'assertions':[b['then'],'操作結果與 '+t['invariant']+' 一致；副作用不可超出核准範圍'],'seam_and_failure_injection':t['tdd_design'],'red_expected':'測試可建置且執行到斷言，但尚未實作的「'+b['then']+'」不成立；環境/fixture/編譯失敗均不接受','green_expected':'相同前置、操作與斷言全部通過，不修改測試期待','observed':'NOT RUN'} for b in t['bdd']]
    t['required_gates']=['D-01 architecture approval','task specification and skeleton approval','valid behavioral RED before production implementation']
    if t['milestone']=='M3':t['required_gates'].append('G-M2: all required M1/M2 tasks accepted, no unresolved P0/P1 or architecture escape')
    t['release_operation_gates']=['G-RELEASE: REPORT-001 accepted; build/install/regression/compatibility evidence complete; human release approval'] if t['id']=='REL-003' else []
    if t['task_type']=='PLANNING_DELIVERABLE':
        t['required_gates']=['規劃目標已指定；讀取既有部署架構與相容性資料','文件交付需完整性檢查與設計審查；不要求新 Skeleton/產品 RED 作為規劃前提']
        t['execution_steps']=['讀取已核准部署架構與目前相容性報告','確認使用者選定的部署目標與版本；缺少資料則列待決策','為每種 Adapter 草擬架構、Contract、BDD、測試策略與 fixtures','以文件檢查驗證目標、版本、失敗/復原和工項追溯完整性','提交擴充封包待人核准；不修改產品程式碼、不宣告 Adapter 已實作']
        t['test_command']='規畫文件檢查命令待 skeleton 定義；不執行產品測試'
        for c in t['tdd_cases']:
            c['red_expected']='文件驗證用缺漏 fixture 應被拒絕；這不是產品實作 RED gate'
        t['test_command']='文件完整性檢查（腳本待準備）；不執行產品測試'
    t['planning_gates']=t['required_gates'] if t['task_type']=='PLANNING_DELIVERABLE' else []
    t['implementation_gates']=t['required_gates'] if t['task_type']=='IMPLEMENTATION_SLICE' else []

meta={'product':'SGenAxis','version':'0.1','generated_at':datetime.now(timezone.utc).isoformat(),'state':'PLANNING','architecture_status':'PROPOSED / NOT APPROVED','implementation_status':'NOT STARTED','test_status':'NOT RUN','release_status':'DO NOT RELEASE','basis':'本次對話需求；架構為建議，非已核准設計','git':'目前交付未建立 Git commit'}
plan={'metadata':meta,'requirements':[{'id':'REQ-'+k,'module':k,'text':v} for k,v in reqs],'decisions':decisions,'modules':list(M.values()),'module_edges':edges,'tasks':tasks}

STYLE='''
:root{--bg:#f2f5f7;--ink:#172c39;--muted:#526876;--line:#dce4e9;--teal:#006f75;--gold:#a46305}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.75 "Segoe UI","Microsoft JhengHei",sans-serif}header{background:#102c3b;color:white;padding:50px max(5vw,24px) 38px}header p{color:#c4dbe1;max-width:880px}h1{font-size:40px;margin:10px 0}h2{font-size:26px;margin:0 0 18px}h3{font-size:18px}nav{position:sticky;top:0;background:#fff;z-index:4;border-bottom:1px solid var(--line);padding:12px 5vw;display:flex;gap:18px;flex-wrap:wrap}a{color:#00737b}nav a{text-decoration:none}main{max-width:1320px;margin:auto;padding:28px}section{background:#fff;border:1px solid var(--line);border-radius:16px;padding:28px;margin:0 0 24px;scroll-margin-top:90px}.eyebrow{letter-spacing:3px;font-size:12px;color:#86d7da}.badge{display:inline-block;padding:3px 10px;border-radius:20px;background:#eaf0f3;font-size:12px;color:#385563;margin:3px}.warn{background:#fff1d7;color:#875000}.good{background:#dff2e6;color:#155332}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:15px}.card{padding:20px;border:1px solid var(--line);border-radius:12px}.number{font-size:30px;font-weight:700}.muted{color:var(--muted)}table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px}th,td{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}th{background:#eef4f5}code{background:#edf2f4;padding:2px 5px;border-radius:4px;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6f8;padding:15px;border-radius:8px;font-size:13px}details{border:1px solid var(--line);border-radius:10px;margin:12px 0;padding:14px}summary{cursor:pointer;font-weight:650}details[open]>summary{margin-bottom:20px}label{display:inline-flex;align-items:center;gap:8px;margin-right:12px}input,select,button{font:inherit;padding:9px 12px;border:1px solid #adc0ca;border-radius:7px;background:#fff;color:var(--ink)}button{cursor:pointer}button:hover{background:#e8f4f4}:focus-visible{outline:3px solid #dd970d;outline-offset:3px}.note{border-left:4px solid #d99b33;background:#fff8e9;padding:14px 18px;margin:16px 0}.flow{display:flex;gap:8px;flex-wrap:wrap}.flow span{border:1px solid #b8d5d8;border-radius:7px;padding:8px 12px}.graph{overflow:auto}.graph svg{min-width:1000px;width:100%;height:auto}.node rect{fill:#edf7f7;stroke:#36848b;stroke-width:1.5}.node text{fill:#173945;font-size:14px}.node:hover rect{fill:#d3eeed}.node.selected rect{fill:#ffe6a9;stroke:#986111;stroke-width:3}.edge{stroke:#bccbd2;stroke-width:1.5;fill:none}.edge.active{stroke:#b06f05;stroke-width:3}.twocol{display:grid;grid-template-columns:1fr 1fr;gap:20px}.task.hidden{display:none}.footer{padding:20px;text-align:center;color:var(--muted)}.tablewrap{overflow:auto} @media(max-width:750px){main{padding:12px}section{padding:18px}h1{font-size:30px}.twocol{grid-template-columns:1fr}nav{position:static}}@media print{nav,.controls,button{display:none}body{background:#fff;font-size:11px}section{break-inside:avoid;border:0;padding:10px}header{background:#fff;color:#000;padding:15px}header p{color:#333}main{padding:0}.task.hidden{display:block}details{break-inside:avoid}.graph svg{min-width:0}}
'''
def table(headers,rows):
    return '<div class="tablewrap"><table><thead><tr>'+''.join('<th>'+E(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in r)+'</tr>' for r in rows)+'</tbody></table></div>'
def section(id,title,content): return f'<section id="{id}"><h2>{title}</h2>{content}</section>'
def escjson(x): return json.dumps(x,ensure_ascii=False,indent=2).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
def feature(t):
    s=f'@{t["id"]} @planning\nFeature: {t["id"]} {t["title"]}\n  Background:\n    Given 使用者已選定正確專案與規格版本\n\n  Rule: {t["contract"]}\n'
    for b in t['bdd']:
        s+=f'\n    @{b["id"]}\n    Scenario: {b["id"]}\n      Given {b["given"]}\n      When {b["when"]}\n      Then {b["then"]}\n'
    return s
def taskhtml(t):
    rows=[['主要模組／需求',E(t['module']+' / '+t['requirement'])],['意圖',E(t['intent'])],['狀態','PLANNING · NOT_READY_FOR_IMPLEMENTATION · Tests NOT RUN'],['前置工項',E(', '.join(t['depends_on']) or '無；仍需 D-01 架構核准')],['允許範圍（提議）','<br>'.join(map(E,t['allowed_scope']))],['保護範圍','<br>'.join(map(E,t['protected_scope']))],['Contract / Invariant',E(t['invariant']+' — '+t['contract'])],['TDD 設計與 RED 判準',E(t['tdd_design'])],['驗收標準',E(t['acceptance'])],['模組／相鄰回歸',E(', '.join(t['regression_modules']))],['規格核准','DRAFT-0.1；PENDING；不得進入產品實作'],['執行命令（規劃）','<code>'+E(t['test_command'])+'</code><br>runner 尚未建立；目前不得執行此命令'],['執行環境',E(t['working_directory'])+f'；timeout {t["timeout_seconds"]} s；'+E(t['retry_policy'])],['結果位置','<code>'+E(t['result_path'])+'</code>'],['真實發布操作閘門（不阻止功能開發）',E('；'.join(t['release_operation_gates']) or '此工項不授權正式發布')],['產物',f'<a href="../../tasks/{t["id"]}/task.json">task.json</a>（模組頁相對連結）；完整匯出見主頁工項包']]
    return f'<details class="task" id="task-{t["id"]}" data-module="{t["module"]}" data-phase="{t["milestone"]}"><summary>{t["id"]} · {E(t["title"])} <span class="badge">{t["milestone"]}</span><span class="badge warn">規劃／待核准</span></summary>'+table(['欄位','工程封包'],rows[:-1])+ '<p><strong>必要閘門：</strong>'+E('；'.join(t['required_gates']))+'</p><h3>BDD · 可匯出 Gherkin</h3><pre>'+E(feature(t))+'</pre><h3>TDD 追溯與案例</h3>'+table(['BDD','TDD','Invariant','結果'],[[b['id'],b['test'],b['invariant'],'NOT RUN'] for b in t['bdd']])+''.join('<details><summary>'+c['id']+' · 測試案例</summary><p>前置：'+E(c['precondition'])+'</p><p>操作：'+E(c['action'])+'</p><p>斷言：'+E('；'.join(c['assertions']))+'</p><p>Seam / injection：'+E(c['seam_and_failure_injection'])+'</p><p>RED：'+E(c['red_expected'])+'</p><p>GREEN：'+E(c['green_expected'])+'</p></details>' for c in t['tdd_cases'])+'<h3>Fixtures / test data</h3><pre>'+E(json.dumps(t['fixture'],ensure_ascii=False,indent=2))+'</pre><h3>Agent 執行順序</h3><ol>'+''.join('<li>'+E(s)+'</li>' for s in t['execution_steps'])+'</ol><p class="note">Pending automation：測試 runner、steps、fixtures 的真實環境配置、失敗注入與測試實作尚未完成。所有案例均未執行；不宣告 RED 或 GREEN。</p></details>'

def graph():
    pos={'HOST':(20,70),'UI':(20,300),'FLOW':(255,70),'GIT':(255,210),'REL':(255,350),'REPORT':(255,490),'EXEC':(500,40),'GUARD':(500,180),'EVID':(500,320),'SPEC':(770,200),'WORK':(770,440)}
    s='<div class="graph"><svg viewBox="0 0 1010 610" role="img" aria-label="提議模組依賴圖；箭頭 A 到 B 表示 A 依賴 B 的公開契約"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10" fill="#839da9"/></marker></defs>'
    for a,b in edges:
        x,y=pos[a];u,v=pos[b];x+=185;y+=30;v+=30
        s+=f'<path class="edge" data-a="{a}" data-b="{b}" d="M{x} {y} C{x+50} {y},{u-60} {v},{u} {v}" marker-end="url(#arrow)"/>'
    for k,(x,y) in pos.items():
        s+=f'<a href="#module-{k}" class="node" data-mod="{k}" aria-label="查看 {M[k]["name"]}"><rect x="{x}" y="{y}" width="185" height="65" rx="9"/><text x="{x+12}" y="{y+25}">{k} · {M[k]["name"]}</text><text x="{x+12}" y="{y+49}" style="font-size:12px">規劃 · 未核准 · 未測試</text></a>'
    return s+'</svg></div>'

intro='''<p>SGenAxis 是本機優先的自動化開發控制中心。使用者核准意圖、架構及驗收，Agent 在工程封包內完成測試、實作與驗證；系統以證據驅動狀態，並管理 Git 與部署。</p><div class="note"><strong>本文件是可審閱產品規畫，不是可執行產品。</strong>需求來自本次對話；技術、Ports、模組邊界與資料模型為提案。架構未核准、Skeleton 未建立、RED 未測得，因此所有產品實作均為 NOT STARTED。HTML 的搜尋、篩選、圖形選取屬文件互動。</div>'''
intro+='<div class="cards">'+''.join(f'<div class="card"><div class="muted">{a}</div><div class="number">{b}</div><div>{c}</div></div>' for a,b,c in [('產品模組',len(M),'明確責任與 Ports'),('可派工封包',len(tasks),'每項三個初步 BDD 情境'),('BDD / TDD 對應',len(tasks)*3,'規劃案例，全部 NOT RUN'),('發布資格','未具備','DO NOT RELEASE')])+'</div>'
scope='''<div class="twocol"><div><h3>使用者與核心旅程</h3><p>專案負責人：選專案 → 審閱架構 → 核准封包 → 啟動 Agent → 查看阻塞 → 驗收 → 發布核准。</p><p>開發者：查看 BDD/TDD、diff、Run log 與回歸證據。架構審查者：檢查 Ports、ownership、交易與越界。</p><p>價值指標：工項規格完整率、證據有效率、阻塞原因完整率、跨專案誤寫次數、可重現建置比例。數值為驗收要求，不是已測成效。</p></div><div><h3>首版範圍</h3><p>單機 Windows、多本機專案、單個同時執行的 Agent、Git CLI、看板、架構 DAG、工程封包、真實測試證據與 Windows 部署閉環。</p><h3>後續／非目標</h3><p>多使用者 RBAC、雲端 worker、多 Agent 並行、多機調度、任意外掛市場、SSH/容器/DCC 真實 Adapter 留待 M4。首版不承諾任意程式碼的完全語意判定或自動架構批准。</p></div></div>'''
tech=table(['層','建議','決策理由／限制'],[
 ['桌面','Electron','原生檔案選擇、IPC 與視窗；主程序只負責宿主與受限橋接'],['UI','React + TypeScript','Tasks、規格詳情、部署面板；不直接讀寫 Git 或 shell'],['圖形','React Flow + ELK.js','圖形互動與排版；循環驗證由領域規則負責'],['流程','XState（封裝）','實作核准狀態機；持久化不代表外部命令 exactly-once'],['執行','Node.js 獨立 worker + provider adapter','長命令不阻塞 UI；取消、崩潰對帳與安全界線需另作設計'],['規格','module.html 內 ModuleSpec JSON','每模組一份人類表面與機器資料；渲染 DOM 是投影'],['執行資料','SQLite + artifact files','run/event 交易與證據索引；大型 log 不塞 DB；禁止複製規格權威'],['測試候選','Vitest / Cucumber.js / Playwright','單元與 Contract／Gherkin／UI；實際版本在工具 spike 與 lockfile 固定']])
tech+='<p>此選型延續 Electron + React 建議；ComfyUI 的 Vue/Python 是參考，並未轉為本產品框架。第一版不必加入 HTTP 伺服器；UI 經 typed IPC 操作 use cases，將來遠端服務需另外核准。</p>'
hexview='''<pre>系統邊界：本機 SGenAxis
Driving Adapters：Electron / React UI、CLI（後續）、Tests
                      │ Input Ports
                      ▼
Application：Workspace / Workflow / Execution / Git / Release use cases
                      │
                      ▼
Domain：Task state、Envelope、Contracts、Evidence validity、DAG rules
                      │ 使用內部定義的 Output Ports
                      ▲ 實作
Driven Adapters：Git CLI、Agent CLI、Filesystem、SQLite、Installer
                      │
外部邊界：專案目錄、遠端 Git、Provider、OS 程序、部署目標

依賴向內：Adapter → Port；Application → Domain / Port。
Domain 禁止依賴 React、Electron、Node filesystem、SQLite、Git CLI 或具體 Provider。
所有 mutation 經 input port / use case；UI 與 HTML 不直接改權威資料。</pre>'''
arch='<p>以下為 <strong>PROPOSED</strong> 架構，不是 ARCHITECTURE_APPROVED。依賴箭頭 A → B 表示 A 使用 B 的公開契約；外部 Adapter 實作方向見六角形視圖。</p>'+hexview+'<h3>模組依賴 DAG</h3><p>可點節點高亮相連依賴並跳到模組說明。表格提供相同內容供鍵盤與離線閱讀。</p>'+graph()+table(['模組','責任／權威狀態','Input / Output Ports','Driven Adapter／交易'],[[f'<a id="module-{m["id"]}" href="modules/{m["id"]}/module.html">{m["id"]} · {m["name"]}</a>',E(m['responsibility']),E(m['input'])+'<br>'+E(m['output']),E(m['adapter'])+'<br>'+E(m['transaction'])] for m in M.values()])+table(['依賴來源','依賴目標'],[[a,b] for a,b in edges])
arch+='<h3>所有權與失敗原子性</h3><p>Spec 匯入：讀取 → 驗證完整模型 → 寫暫存檔 → 原子替換。Project 重新定位：探測身分 → 確认無租約 → 原子更換 binding。Run：保存 intent → 啟動外部程序 → 保存事件與結果；重啟以 operation ID 對帳。部署：step checkpoint + 明確補償；檔案、DB 與外部系統沒有虛構的跨系統 ACID 保證。</p><p>SQLite 中可存 spec hash / revision reference，不能保存可被獨立編輯的第二份規格。未提交的工作樹亦需指紋；只有 commit SHA 不足以表示實際測試內容。</p>'
ui=table(['畫面','控制項／預設','規則與成功','空／錯誤／停用','BDD 映射'],[
 ['專案切換','project picker、root、remote、branch；初始未選擇','切換僅改視圖；Run root 不變','不存在/權限不足顯示原因；活動 root 不可重綁','WORK-001 / WORK-002'],['Tasks 看板','階段、健康色、原因、下一步；預設全部','顏色配文字/圖示；篩選不改狀態','無結果提供清除；載入失敗不顯示舊專案','UI-001'],['架構 DAG','縮放、選取、依賴高亮、表格替代','顯示模組依賴；架構编辑需新草稿','循環列路徑；無證據不綠','UI-002'],['Task 詳情','Overview / BDD / TDD / Runs / Diff / Acceptance','顯示啟動 hash、命令、允許範圍','缺資料/未核准時啟動停用；版本過期要求重閱','UI-003'],['Git','clone/fetch/pull/commit/push；force 不提供自動入口','diff 與檔案選取後提交；發布獨立','dirty/diverged/lease 提示；認證脫敏','GIT-001..003'],['部署','profile、環境、版本、產物 hash、核准、rollback','核准綁定具體產物與目標','未具備 Adapter 顯示未支援；health 失敗不綠','REL-001..003']])
ui+='<p>所有互動有可讀標籤、鍵盤焦點與不依賴顏色的文字；執行 log 更新不搶焦點。危險操作顯示具體 project/root/target。首版操作者為本機使用者，不虛構多租戶權限系統。</p>'
states=table(['視覺健康','含義','判定'],[['灰 · NOT STARTED','未開始／等依賴','不算失敗，也不算完成'],['藍 · RUNNING','正在執行','有活動 Run 與最新事件'],['黃 · ATTENTION','待核准／重新規劃／過期／待對帳','顯示原因與下一步'],['紅 · FAILED / BLOCKED','非預期失敗、規格衝突或必要資源缺失','完整分類與證據'],['綠 · COMPLETE','核准範圍驗證與驗收完成','所有必要閘門滿足；發布另判']])
states+='<div class="flow">'+''.join('<span>'+s+'</span>' for s in ['PLANNING','ARCHITECTURE','SPECIFICATION','SKELETON','TDD_RED','IMPLEMENTATION','TDD_GREEN','REGRESSION','REVIEW','COMPLETE'])+'</div><p>結構改動 → REPLAN_REQUIRED → PLANNING。TDD_RED 的預期行為失敗是有效進度，不直接判成異常紅色。模組彙總優先序：紅阻塞 → 黃待處理 → 藍執行 → 灰未開始 → 全部必要工項合格才綠；零工項或未知覆蓋為未評估。部署／release status 與模組 health 分開。</p>'
milestones=[('M0','產品與架構核准','審閱本文件 D-01..06、A1..A14 與 UI schema；建立具版本核准紀錄','本文件完成 ≠ 架構批准'),('M1','可測試骨架','SPEC/WORK/GUARD/FLOW/EXEC/EVID 基礎封包；mock Agent 通過狀態與證據測試','模擬結果不能代表真實 Agent 完成'),('M2','真實開發閉環','Agent CLI + 看板/DAG + Git + RED→GREEN + 取消與越界保護','示範 repo 無跨專案写入，實際 BDD 覆蓋完整'),('M3','交付與部署閉環','驗收提交、報告、打包、靜默安裝、發布與回滾','乾淨 VM 證據、版本相容性報告與 release approval'),('M4','擴充部署','選定 SSH / 容器 / DCC 後各開獨立工項','目前僅規劃，不宣稱已支援')]
roadmap=table(['里程碑','目標','退出條件','界線'],milestones)+'<p>順序由依賴決定，未承諾日期或人日。工項 S/M/L 為相對複雜度，不是完成估算。每次 Sprint 記錄完成/未完成、Build Result、測試、阻塞與 carry-over；Milestone 另做功能、安裝、DCC、回歸及發布資格判定。</p>'
roadmap+='<div class="note"><strong>全域閘門優先於 Task DAG。</strong>G-M2：所有必要 M1/M2 工項驗收完成、無未解 P0/P1 或越界問題，才可執行 M3 產品工項。G-RELEASE：另須 REPORT-001 完成、建置/安裝/相容性/回歸證據齊備及人類發布核准。Task 前置完成不足以授權發布。HOST-001 是首個建置骨架工項；M0 架構批准仍是它的前提。</div>'
deploy='''<div class="flow">'''+''.join('<span>'+x+'</span>' for x in ['選定版本','規格與驗收閘門','Build','Package + Hash','測試環境','靜默安裝','環境/健康檢查','回歸與相容性','發布核准','正式部署','驗證 / 復原'])+'''</div><p>Profile 必須聲明 OS/DCC 版本、工具版本、命令、環境、secret reference、安裝位置、健康判準、timeout、備份、卸載與不可逆步驟。正式環境重用同一份已驗證產物，不重新建置。憑證由 credential helper／OS store 管理，日誌需脫敏。</p><p>Build Result：摘要、變更檔案、命令、branch/commit/tree、依賴版本、OS/DCC matrix、產物位置與雜湊、驗證結果、失敗、風險、回滾與 pending。結果詞彙固定 PASS / FAIL / BLOCKED / NOT RUN / PARTIAL。</p><p>第一版 Windows Installer；SSH、Container、DCC 是後續能力。Maya 等 DCC 必須另核對 API/Python/PySide、load/unload、環境變數、偏好隔離及 batch，不可借用桌面安裝成功證據。</p>'''
verification=table(['產品 AC','量測條件','證據／工項'],[
 ['AC-01 規格可執行','每個可啟動 Task 有已核准架構、BDD→Invariant→TDD、範圍與命令','SPEC-001/002；目前 100% 封包是草稿'],['AC-02 狀態真實','無有效 RED 不實作；缺驗收不 COMPLETE；Agent done 不直接綠','FLOW-001、EXEC-001、EVID-001'],['AC-03 專案隔離','A 執行中切 B，不改 A binding；禁止租約中重綁','WORK-002、GUARD-002'],['AC-04 故障可復原','取消無孤兒程序；重啟對帳不盲目重跑','EXEC-003'],['AC-05 Git 保護','dirty、untracked、diverged、remote rejection 皆保留資料','GIT-001..003'],['AC-06 部署可信','同產物追溯；exit 0 + health fail 為 FAIL；回滾失敗單獨報告','REL-001..003'],['AC-07 架構保護','依賴向內、模組 DAG 無環；越界拒絕；語意疑慮轉人工','GUARD、UI-002、architecture suite'],['AC-08 人類可審閱','离线 module.html 含完整規格、Tasks、結果與來源版本','REPORT-001']])
verification+='<p>測試層級：L0 Unit → L1 Component → L2 Module Contract → L3 Adapter Integration → L4 Cross-module → L5 System。回歸失敗分類：introduced / pre-existing / environment / flaky / specification mismatch / unrelated WIP。每模組 B1–B12 必須評估；本初稿情境不代表完整覆蓋。</p>'
risks=table(['風險／未知','處置','Owner / gate'],[['Agent CLI 協定與認證未知','先做版本固定 spike，不臆造 API','Execution owner / D-02'],['語意越界難以完全自動判斷','寫入限制 + diff 檢查 + 架構審查；不能只依賴 prompt','Guard owner / M2'],['任意命令與憑證外洩','型別化 IPC、命令 argv、capabilities、脫敏；不直接開 unrestricted shell 給 UI','Execution owner / M2'],['跨系統中斷與重跑','operation ID、checkpoint、對帳、不確定狀態待決策','Workflow owner / M2'],['部署權限與不可逆操作','隔離 VM 驗證，profile 明訂人工復原','Release owner / M3'],['大型圖與日誌效能未知','benchmark spike 決定數量/時間門檻，再核准 AC','UI owner / M2'],['產品全由多框架構成','版本 lockfile、dependency inventory、license review、可重現建置','Release owner / M3']])
sources='<ul>'+''.join(f'<li><a href="{u}">{n}</a></li>' for n,u in [('Electron process model','https://www.electronjs.org/docs/latest/tutorial/process-model'),('Electron security','https://www.electronjs.org/docs/latest/tutorial/security'),('React Flow layout','https://reactflow.dev/learn/layouting/layouting'),('XState persistence','https://stately.ai/docs/persistence'),('ComfyUI frontend（比較參考）','https://github.com/Comfy-Org/ComfyUI_frontend')])+'</ul><p>技術來源沿用本次對話已查核的官方文件；未鎖定套件版本。產品需求以本次使用者要求為依據，示範情境與 Ports 名稱均為設計提案。</p>'

body=section('overview','01 / 產品定位與交付狀態',intro)+section('scope','02 / 使用者、範圍與非目標',scope)+section('technology','03 / 技術基線',tech)+section('architecture','04 / 系統邊界與模組 DAG',arch)+section('ui','05 / UI Schema 與互動規格',ui)+section('state','06 / 狀態與 Agent 執行規則',states)+section('roadmap','07 / 里程碑與交付順序',roadmap)
body+=section('tasks','08 / 可執行工項封包', '<p>每個工項包含 3 個初步 BDD 情境與對應 TDD ID、fixture、RED 判準及驗收。此處「可執行」表示可交付給 Agent 進行規格／測試準備；產品實作必須等待架構與封包批准。估算 M/L 僅為複雜度。</p><div class="controls"><label>搜尋 <input id="search" placeholder="ID、標題、BDD 或模組" type="search"></label><label>模組 <select id="module-filter"><option value="">全部</option>'+''.join(f'<option>{k}</option>' for k in M)+'</select></label><label>階段 <select id="phase-filter"><option value="">全部</option>'+''.join(f'<option>M{i}</option>' for i in range(1,5))+'</select></label><button id="expand">全部展開</button> <button id="collapse">全部收合</button><p id="count" aria-live="polite"></p></div>'+table(['工項','模組','階段','前置工項','複雜度'],[[f'<a href="#task-{t["id"]}" class="task-link">{t["id"]} {t["title"]}</a>',t['module'],t['milestone'],E(', '.join(t['depends_on']) or '—'),t['effort']] for t in tasks])+''.join(taskhtml(t) for t in tasks))
body+=section('deployment','09 / 部署與發布流程',deploy)+section('acceptance','10 / 驗證策略與產品驗收',verification)+section('decisions','11 / 待核准決策',table(['ID','決策','建議','影響'],[[E(c) for c in d] for d in decisions]))+section('risks','12 / 風險與責任',risks)+section('sources','13 / 來源與工項包',sources+'<p><a href="plan.snapshot.json">規畫快照 JSON</a> · <a href="verification.json">文件結構檢查</a> · <a href="README.md">操作與生成說明</a></p><p>tasks/&lt;ID&gt;/ 內包含 task.json、behavior.feature、steps.ts、fixtures.json、pending-automation.md。steps 刻意回傳 pending，不提供虛假通過。modules/&lt;ID&gt;/module.html 是各模組的人類閱讀與結構資料入口。</p>')
JS='''const tasks=[...document.querySelectorAll('.task')];const q=document.querySelector('#search'),mf=document.querySelector('#module-filter'),pf=document.querySelector('#phase-filter');function filter(){let n=0;for(const t of tasks){let ok=(!mf.value||t.dataset.module===mf.value)&&(!pf.value||t.dataset.phase===pf.value)&&t.textContent.toLowerCase().includes(q.value.toLowerCase());t.classList.toggle('hidden',!ok);if(ok)n++;}document.querySelector('#count').textContent=`顯示 ${n} / ${tasks.length} 個工項；全部為規劃草稿，測試 NOT RUN。`;}[q,mf,pf].forEach(x=>x.addEventListener('input',filter));filter();document.querySelector('#expand').onclick=()=>tasks.filter(t=>!t.classList.contains('hidden')).forEach(t=>t.open=true);document.querySelector('#collapse').onclick=()=>tasks.forEach(t=>t.open=false);document.querySelectorAll('.task-link').forEach(a=>a.onclick=()=>{q.value='';mf.value='';pf.value='';filter();document.querySelector(a.getAttribute('href')).open=true;});document.querySelectorAll('.node').forEach(n=>n.addEventListener('click',()=>{document.querySelectorAll('.node').forEach(x=>x.classList.toggle('selected',x===n));document.querySelectorAll('.edge').forEach(e=>e.classList.toggle('active',e.dataset.a===n.dataset.mod||e.dataset.b===n.dataset.mod));}));window.addEventListener('beforeprint',()=>tasks.forEach(t=>t.open=true));'''
def page(title,body,data,script='',back=False):
    nav='<a href="../../index.html">← 系統產品規畫</a>' if back else ''.join(f'<a href="#{k}">{v}</a>' for k,v in [('overview','產品'),('architecture','架構 DAG'),('ui','UI'),('state','狀態'),('roadmap','里程碑'),('tasks','工項'),('deployment','部署'),('decisions','待決策')])
    return '<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+E(title)+'</title><style>'+STYLE+'</style></head><body><header><div class="eyebrow">SGenAxis / PRODUCT ENGINEERING PLAN</div><h1>'+E(title)+'</h1><p>讓規格約束 Agent，讓證據說明進度。多專案・模組 DAG・BDD/TDD・Git・部署</p><span class="badge warn">DRAFT 0.1 / 待架構核准</span><span class="badge">產品尚未實作</span></header><nav>'+nav+'</nav><main>'+body+'</main><div class="footer">SGenAxis · '+E(meta['generated_at'])+' · 文件草稿，不代表發布資格</div><script type="application/json" id="module-spec">'+escjson(data)+'</script><script>'+script+'</script></body></html>'

for m in M.values():
    own=[t for t in tasks if t['module']==m['id']]
    data={'metadata':meta,'module':m,'tasks':own,'decisions':decisions,'dependencies':[b for a,b in edges if a==m['id']]}
    p=OUT/'modules'/m['id'];p.mkdir(parents=True,exist_ok=True)
    txt=section('overview',m['name']+' / 模組工程規畫','<p>'+E(m['responsibility'])+'</p><p class="note">架構 PROPOSED；Contracts/BDD/TDD 為草稿；實作 NOT STARTED；回歸 NOT RUN；健康未評估。</p>')
    txt+=section('architecture','架構位置、所有權與 Ports',hexview+table(['欄位','提案'],[[E(k),E(v)] for k,v in m.items()])+ '<p>依賴目標：'+E(', '.join(data['dependencies']) or '無其他模組公開契約依賴')+'</p><p>完整模組 DAG 見 <a href="../../index.html#architecture">系統架構</a>。此模組只允許經自身 Input Port 修改其權威資料。禁止跨模組直接資料庫寫入及 Domain 基礎設施依賴。</p>')
    txt+=section('dependency','模組依賴視圖',graph().replace('href="#module-', 'href="../../index.html#module-'))
    txt+=section('tasks','工項、Contract、BDD、TDD 與驗收',''.join(taskhtml(t) for t in own))
    txt+=section('coverage','BDD 類別評估與回歸',table(['分類','初稿狀態','說明'],[[f'B{i} '+name,'Applicable / Pending scenarios' if i in [1,2,3,4,6,12] else 'Deferred', '需在規格核准前補完整案例或明確 N/A；初稿不宣告覆蓋完成'] for i,name in enumerate(['主要成功','輸入邊界','無效輸入','相依失敗','部分失敗','狀態一致性','交易','生命週期','復原/回滾','跨模組','相容性','重要回歸'],1)])+'<p>L0–L5 測試計畫見各 Task；目前所有結果 NOT RUN。無 build、package、install 或 DCC 接受證據。</p>')
    txt+=section('health','風險、決策與最終健康', '<p>規格與 Ports 未核准；Task 命令僅為規劃；步驟 stubs 未自動化。Module health：PLANNING / NOT VERIFIED。</p>'+table(['ID','決策','建議','影響'],[[E(c) for c in d] for d in decisions]))
    (p/'module.html').write_text(page(m['id']+' · '+m['name'],txt,data,back=True),encoding='utf-8')
for t in tasks:
    p=OUT/'tasks'/t['id'];p.mkdir(parents=True,exist_ok=True)
    (p/'task.json').write_text(json.dumps(t,ensure_ascii=False,indent=2),encoding='utf-8')
    (p/'tests.plan.json').write_text(json.dumps(t['tdd_cases'],ensure_ascii=False,indent=2),encoding='utf-8')
    (p/'behavior.feature').write_text(feature(t),encoding='utf-8')
    (p/'fixtures.json').write_text(json.dumps({'status':'PLANNED','task':t['id'],'data':t['fixture'],'environment':'temporary isolated fixtures; never use real user repo by default'},ensure_ascii=False,indent=2),encoding='utf-8')
    steps=['// Specification stub only. No test evidence. Load this file only for this task.','import { Given, When, Then } from "@cucumber/cucumber";']
    for kind,txt in [('Given','使用者已選定正確專案與規格版本')]+[(k,b[f]) for b in t['bdd'] for k,f in [('Given','given'),('When','when'),('Then','then')]]:
        steps.append(f'{kind}({json.dumps(txt,ensure_ascii=False)}, function () {{ return "pending"; }});')
    (p/'steps.ts').write_text('\n'.join(steps)+'\n',encoding='utf-8')
    (p/'pending-automation.md').write_text('# '+t['id']+' — pending automation\n\n- Architecture / contract / BDD approval: PENDING\n- Implement approved skeleton and test seams.\n- Configure task-specific runner; proposed npm command is not installed.\n- Replace pending steps with fixture setup, one action and observable assertions.\n- Run and capture behavioral RED, then unchanged-intent GREEN.\n- Run module and adjacent regressions; review architecture and acceptance.\n- Never treat pending/skipped as passed.\n\nOpen decisions: D-01..D-06 in system HTML.\n',encoding='utf-8')
(OUT/'index.html').write_text(page('SGenAxis 產品規畫書',body,plan,JS),encoding='utf-8')
(OUT/'plan.snapshot.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'README.md').write_text('''# SGenAxis product plan 0.1

Open index.html directly; no server, CDN or network is required for the document UI.
Modules have standalone module.html documents with embedded ModuleSpec JSON.
This is a proposed specification, not approved product architecture or running software.

## Generate
python docs/build_plan.py

The Python builder is documentation tooling only. It currently holds the draft authoring data.
Edit this builder to regenerate this draft; do not independently edit generated HTML or snapshots.
The proposed PRODUCT storage design (D-05) uses each module.html embedded ModuleSpec as canonical.
That runtime editor/storage system has NOT been implemented by this documentation generator.

## Agent handoff
Read module.html embedded module-spec and tasks/<ID>/task.json.
Observe dependency order. Before production changes obtain architecture/contract approval,
create approved skeleton, implement tests and observe valid RED.
Task npm commands are planned interfaces and do not exist yet.
Task steps.ts files deliberately return pending; they are not passing tests.
Load only the chosen task steps to avoid duplicate Background definitions across task packages.

## Status
Planning artifacts only. Product build/tests/install/DCC/release: NOT RUN.
Verification.json covers document structure and traceability only.
''',encoding='utf-8')

def acyclic(nodes,links):
    seen=set();active=set()
    def visit(n):
        assert n not in active, 'Cycle at '+n
        if n in seen:return
        active.add(n)
        for a,b in links:
            if a==n: visit(b)
        active.remove(n);seen.add(n)
    for n in nodes:visit(n)
ids=[t['id'] for t in tasks]
assert len(ids)==len(set(ids))
acyclic(M,edges)
assert all(d in ids for t in tasks for d in t['depends_on'])
acyclic(ids,[(t['id'],d) for t in tasks for d in t['depends_on']])
assert all(len(t['bdd'])==3 and t['results']=='NOT RUN' for t in tasks)
assert all(t['module'] in M and t['allowed_scope'] and t['acceptance'] for t in tasks)
for p in OUT.rglob('*.html'):
    text=p.read_text(encoding='utf-8');json.loads(text.split('<script type="application/json" id="module-spec">')[1].split('</script>')[0])
verification={'scope':'DOCUMENT ONLY','checked_at':meta['generated_at'],'checks':{'unique_task_ids':'PASS','task_dependency_references':'PASS','task_dag_acyclic':'PASS','module_dag_acyclic':'PASS','bdd_tdd_traceability':'PASS','embedded_json_parse':'PASS','task_packet_required_fields':'PASS'},'modules':len(M),'tasks':len(tasks),'bdd_scenarios':len(tasks)*3,'product_tests':'NOT RUN','browser_visual_check':'NOT RUN','architecture_approval':'PENDING'}
(OUT/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(verification,ensure_ascii=False))
