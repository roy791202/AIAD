"""Document projection only; never executes or invents a product test runner."""
import hashlib, html, json, pathlib, re, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[7]
OUT = pathlib.Path(__file__).resolve().parent
BASE = ROOT / 'docs/requirements-confirmation/phase1-spec'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

task = read(BASE/'tasks/PD-P1-F12-DELIVERY-01.json')
feature_text = (BASE/'phase1.feature').read_text(encoding='utf-8-sig')
blocks = {int(m.group(1)):m.group(0).rstrip() for m in re.finditer(r'  @BDD-(\d+)[\s\S]*?(?=\n  @BDD-|\Z)', feature_text)}
head = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT,text=True).strip()
branch = subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
inventory_path=BASE/'tasks/M01/planning/s2-green/source-current.json'
inventory=read(inventory_path)
source_check=[{'path':p,'expected':h,'actual':digest(ROOT/p) if (ROOT/p).is_file() else None} for p,h in inventory['source_hashes'].items()]
source_mismatch=[x for x in source_check if x['expected']!=x['actual']]
board=read(ROOT/'docs/board.json')
def find(x):
    if isinstance(x,dict):
        if x.get('id')==task['id'] and 'legacyTask' in x:return x
        for v in x.values():
            y=find(v)
            if y:return y
    if isinstance(x,list):
        for v in x:
            y=find(v)
            if y:return y
card=find(board)
write('board-readonly.json',{'card':card,'note':'Management snapshot only; migrated text may be mojibake. Original task/feature retained as semantic authority; no board mutation.'})

rows=[]
for n in range(22,31):
    direct=n in [27,28,29]
    rows.append({'bdd':f'BDD-{n}','verbatim':blocks[n], 'relation':'F12_DIRECT' if direct else 'SHARED_CONTEXTUAL_REGRESSION', 'feature_evidence':'NOT RUN','original_fixture':f'fixtures.json#scenarios/{n-1}', 'prospective_cases':{27:['F12-P08'],28:['F12-P03','F12-P04','F12-P05'],29:['F12-P07']}.get(n,[]),'limit':'S1 pure policy or module-wide proposal cases do not establish this F12 native behavior.'})

recipes=[
('History entry','既有完整快照S與另一專案同名快照T','從最近檔案選S','正確專案/版本可辨識，不混入T；預覽前不改編輯內容','AC12 prospective; REQ-22'),
('Preview time/location/material integrity','固定UTC時間、原路徑、實際快照位置、完整/缺一素材兩組','預覽S','顯示時間、位置、完整性；缺素材逐項揭露，不聲稱完整復原','AC12 prospective; REQ-22'),
('Open unsaved','完整S、現有草稿A與原檔bytes O','開啟復原S','內容等於S且顯示未保存；原檔O不變，取消/失敗不替換A','BDD-28 direct + AC12 prospective'),
('Save original versus Save As','復原後內容R、可寫原檔O與空目標N兩組','各自明確選保存原檔或另存N','僅選定目標變為R；另存不改O；快照保持；權限/覆寫確認遵循未來批准保存契約','AC12 prospective; BDD-27/28'),
('Offline and read-only originals','完整S；原磁碟離線與原檔唯讀兩個獨立fixture','開S並另存至可寫N','未保存開啟後N含完整R；原處不寫入，不把原處不可寫誤判成不可另存','BDD-28 direct; AC12 prospective'),
('Portable relocation','Win11 x64免安裝目錄A、固定隔離使用者資料區U、成功S','結束程式，移A到B後啟動並開S','U中的S仍可找到與復原；記錄前後實體位置與摘要，不把搬目錄當已復原','AC12 prospective; BDD-32 contextual M08'),
('Remove history only','歷史項H、正式文件O、S payload/index與素材摘要清單','移除H','H不再列出；O/S/素材bytes與存在性不變；不觸發物理清理','BDD-29 direct; AC12 prospective'),
('Formal save preserves snapshots','S與後續編輯R、獨立正式/快照基準','成功正式保存R','正式保存成功；S仍在且bytes不變；快照基準不變，無即時刪除','BDD-27 direct; AC12 prospective'),
('Fresh-launch Undo empty','結束上一程序，其Undo非空，完整S','新程序從歷史開S','只恢復內容；Undo/Redo不能還原上一程序操作；快照未刪','AC12 prospective; F12 boundary'),
('Missing material and stale path truth','S缺一素材M；另一歷史原路徑失效但S完整','查看兩者預覽','M限制明列、不報完整成功；失效原路徑保留並解釋，完整S仍可走另存','AC12 prospective; F12 failure'),
('Save failure preserves edit and snapshot','開S後再編輯R、原檔O，注入目標拒寫/提交失敗','保存R','回報失敗；R與dirty仍在，S與O不受破壞，不報已保存','AC12 prospective; F12 failure'),
]
cases=[]
for i,(title,given,when,then,relation) in enumerate(recipes,1):
    cases.append({'id':f'F12-P{i:02}','title':title,'classification':relation,'given':given,'when':when,'then':then,'fixture_recipe':'生成隔離TEMP_ROOT；預先記錄內容/素材/原檔/快照摘要及存在性；禁止使用真實使用者資料。'+given,'oracle_recipe':then+'；前後獨立比對canonical內容、階層、關係、bindings、素材identity/hash與未受影響文件，保存失敗另比dirty。','test_level':'L2 future approved input/output ports + L3 real adapters + L5 native Windows where applicable','automation':'PENDING_OWNER_ENVELOPE_SKELETON_RUNNER_FIXTURE','product_command':None,'result':'NOT RUN','step_stub':{'Given':'PENDING: construct and self-check fixture after adoption','When':'PENDING: bind approved public action after adoption','Then':'PENDING: independent observer and exact oracle after adoption'}})
write('pending-fixture-oracle-recipes.json',{'purpose':'Recipes and documentary step stubs only; not executable tests or new approved BDD','cases':cases,'valid_red':'Only accepted compilable Skeleton and self-checked fixture failing for missing intended behavior qualifies. Missing provider, compile/setup failure, document checks are not valid RED.','pending_automation':['Owner exact F12 envelope and UI schema acceptance','Bind actual current test runner/target and concrete fixture/provider seams','Native Win11 history/preview/recovery/save/portable failure observations','Independent verification by different identity']})

spec={'task':task['id'],'module':'M07','feature':'F12','author':'/root/f12_feature_trace_packet','state':'FEATURE_TRACE_PREPARATION_PENDING_INDEPENDENT_REVIEW_AND_OWNER','implementation':'BLOCKED_PENDING_APPROVED_ENVELOPE_AND_VALID_RED','module_complete':False,'authority':{'branch':branch,'live_head':head,'expected_parent_head':'5b709343a890503ebbe24a802e43cda5647df124','historical_inventory_head':inventory['head'],'product_hash_count':len(source_check),'mismatches':source_mismatch},'intent':task['intent'],'contracts_verbatim':task['contract'],'acceptance_verbatim':task['acceptance'],'trace':rows,'prospective_cases':[c['id'] for c in cases],'separation':{'F12_direct':['BDD-27','BDD-28','BDD-29'],'shared_contextual':['BDD-22','BDD-23','BDD-24','BDD-25','BDD-26','BDD-30'],'AC12_prospective':'F12-P01..P11; no authority to alter original BDD; BDD-32 remains M08 cross-module relocation obligation'},'evidence_limits':['Accepted S1 only pure policy supplied trusted Published; no timer/capture/pinning/durable payload/index or recovery UI','Recovery ACK correction PASS_BOUNDED_CORRECTION_ONLY_PENDING_OWNER is document guard evidence, not native history/recovery/save lifecycle','No build, product test, valid RED/GREEN, native UI, package, install or module acceptance run','S1 historical acceptance identifies same assistant later readonly turn, not delegated independent acceptance under current role rule'],'owner_pending':['D01 permanent retention of unhandled snapshots remains proposal pending Owner; no retention policy selected','M07-D1..D7 joint adoption and CXv3 remain pending Owner','Recovery ACK ordinal /0 illustrative versus fixed-zero schema remains pending Owner','PH-G2 index issuer/provider, PH-G3 material/root receipts, PH-G4 restart lookup remain pending','No new schema, port, ACK protocol, root registration or physical GC authorization'],'architecture_projection':{'hexagonal':'History UI → approved input boundary (future binding) → M07 orchestration/policy → declared output abstractions → storage/material adapters. This is an existing proposal summary, not new interface approval.','dependency':'M07 coordinates M04 document owner and M05 material owner through pending approved boundaries; M08 owns portable environment validation.','ownership':'M04 authoritative live document and formal/recovery baseline; M07 immutable snapshot/history observations; M05 materials/pins/roots; UI projection only.','mutation':'Opening recovery must pass M04 mutation boundary; no UI filesystem/state bypass. Exact seam pending Owner.','transaction':'Restore validate/prepare before owner commit; formal save and recovery publication retain distinct boundaries; exact durable rollback/ACK semantics remain pending.','sources':['tasks/M07/planning/cx-revision-v3/shared-contract.json','tasks/M07/planning/recovery-ack-contract-correction/module-spec.json']},'scope':{'allowed':'this directory only','protected':'product/tests/original specs/board/hooks/commit','no_dispatch':True},'acceptance_for_this_packet':['Original BDD22..30 preserved verbatim','Direct/contextual/prospective coverage disjoint and explicit','All F12 recipe results NOT RUN and commands unbound','796 historical source hashes checked against live files','Independent reviewer required; author checks static integrity only']}
spec['current_owner_instruction']={'at':'2026-11-03T10:57:03.220Z','source':'Current user heartbeat relayed by parent /root; no verified filesystem path','rules':['board.json sole management authority; Yellow→Gray→Red priority','Proceed original-scope document preparation; Owner adoption still gate','Do not rerun historical PASS as progress','Product needs approved envelope + accepted Skeleton + valid RED','No commit/push/role-hook mutation; 796 inventory authority unchanged'],'old_heartbeat':'2026-10-26 file is historical context only, not latest Owner authority'}
spec['ui_schema_preparation']={'status':'PROSPECTIVE_PENDING_OWNER_NOT_IMPLEMENTATION_AUTHORITY','role':'Author','controls':['Recent files/recovery entry: project name + recovery marker + snapshot time','Preview: time/location/material completeness + explicit unavailable reason','Open recovery: unsaved content; no implicit save','Save original and Save As are distinct explicit choices','Remove history is separate from cleanup; cleanup proposal remains pending'],'states':['empty history','loading/preview unavailable','invalid original path retained with explanation','missing material with accurate limits','opened unsaved','save failure preserving edits and snapshot'],'validation':['Do not claim complete restore with missing material','No automatic original overwrite or cleanup','No forged path/DTO authority'],'accessibility':'Pending exact UI review: keyboard reachable controls, visible focus, labels, announced failure; no native proof','mapping':'F12-P01..P11 recipe interactions; no new approved BDD'}
spec['diagrams']={'hexagonal_existing_proposal_projection':'External history UI → Input boundary (pending binding) → [M07 application/policy] → Output abstractions (pending adoption) ← Storage / M05 adapters','module_dependency_existing_proposal_projection':'UI → M07 history/recovery orchestration → M04 document owner (mutation/baselines)\nM07 → M05 material/pin/root owner\nM08 portable environment → M07 recovery discovery verification\nNo UI→filesystem or UI→mutable document bypass','authority':'Projected only from cx-v3 shared-contract + recovery ACK correction; does not invent or approve new architecture'}
spec['lessons_applied']=['Pure S1 trusted Published is not durable native recovery proof','Bounded ACK admission witnesses do not prove response relation/replay/restart/atomic baseline; malformed trusted issuer fixture remains a known unproved provider seam','Never promote dictionary/hash checks or proposal case totals to F12 functional evidence','Historical S1 same-assistant acceptance identity limitation remains disclosed under current independence rule']
write('feature-trace.json',spec)
write('source-current-check.json',{'historical_head':inventory['head'],'live_head':head,'count':len(source_check),'mismatches':source_mismatch,'files':source_check,'note':'Hash equivalence only, no runtime or clean-checkout claim.'})
inputs=[ROOT/'AGENTS.md',ROOT/'docs/board.json',BASE/'index.html',BASE/'phase1.feature',BASE/'fixtures.json',BASE/'tasks/PD-P1-F12-DELIVERY-01.json',inventory_path,BASE/'tasks/M07/planning/current-state.json',BASE/'tasks/M07/s1/green/acceptance/review.json',BASE/'tasks/M07/planning/cx-revision-v3/module-spec.json',BASE/'tasks/M07/planning/cx-revision-v3/shared-contract.json',BASE/'tasks/M07/planning/recovery-ack-contract-correction/module-spec.json',BASE/'tasks/M07/planning/recovery-ack-correction-review/review.json',ROOT/'reports/rust-improvements/continuous/coordination/heartbeat-latest.json']
write('input-hashes.json',{str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for p in inputs})
sections=''
for title,value in [('Intent and authority',spec['intent']),('Current Owner instruction',spec['current_owner_instruction']),('UI schema preparation',spec['ui_schema_preparation']),('Architecture diagrams projection',spec['diagrams']),('Lessons applied',spec['lessons_applied']),('Status / verification limits',spec['evidence_limits']),('Architecture projection (pending adoption)',spec['architecture_projection']),('Contracts (original)',spec['contracts_verbatim']),('Acceptance (original)',spec['acceptance_verbatim']),('Owner pending / no authorization',spec['owner_pending']),('Feature trace',rows),('Pending fixture and oracle recipes',cases),('Scope and acceptance',spec['acceptance_for_this_packet'])]:
    sections+='<section><h2>'+html.escape(title)+'</h2><pre>'+html.escape(json.dumps(value,ensure_ascii=False,indent=2))+'</pre></section>'
payload=json.dumps(spec,ensure_ascii=False).replace('</','<\\/')
(OUT/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>F12 feature trace preparation</title><style>body{font:16px/1.7 system-ui;background:#f4f6f8;color:#203047;max-width:1120px;margin:30px auto;padding:20px}section,header{background:white;padding:22px;margin-bottom:18px;border:1px solid #bccbd8}pre{white-space:pre-wrap;overflow-wrap:anywhere}h1,h2{line-height:1.3}.status{color:#805500}</style><header><h1>F12 歷史入口、復原與保留</h1><p class="status">文件準備完成待獨立審查／Owner；產品 BLOCKED；所有功能證據 NOT RUN。</p><p>Direct: BDD27/28/29。Shared contextual: BDD22–26/30。AC12 prospective recipes不改原BDD、不授權新介面。</p><p>作者 /root/f12_feature_trace_packet 不可自驗收。本頁可離線閱讀，embedded ModuleSpec為文件投影。</p></header>'+sections+'<script type="application/json" id="module-spec">'+payload+'</script></html>',encoding='utf-8')
checks={'kind':'AUTHOR_STATIC_DOCUMENT_CHECKS_ONLY_NOT_ACCEPTANCE','original_bdd_exact':all(r['verbatim']==blocks[int(r['bdd'].split('-')[1])] for r in rows),'bdd_count':len(rows),'recipes':len(cases),'no_product_commands':all(c['product_command'] is None for c in cases),'all_recipes_not_run':all(c['result']=='NOT RUN' for c in cases),'inventory_count':len(source_check),'inventory_mismatches':len(source_mismatch),'head_matches_parent':head==spec['authority']['expected_parent_head'],'independent_acceptance':'NOT RUN'}
assert checks['original_bdd_exact'] and checks['bdd_count']==9 and checks['recipes']==11 and checks['no_product_commands'] and checks['inventory_count']==796 and not source_mismatch and checks['head_matches_parent']
write('static-document-checks.json',checks)
write('seal.json',{'kind':'SHA256 documentary integrity; not approval','files':{p.name:digest(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='seal.json'}})
print(json.dumps(checks,ensure_ascii=False))

