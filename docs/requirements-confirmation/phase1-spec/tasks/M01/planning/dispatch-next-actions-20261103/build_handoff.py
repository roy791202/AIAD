"""Read-only source audit; writes only this new handoff directory."""
import hashlib, html, json, os, platform, subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[7]
OUT=Path(__file__).resolve().parent
TASKS=ROOT/'docs/requirements-confirmation/phase1-spec/tasks'
sources={}
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p): return p.relative_to(ROOT).as_posix()
def read(p):
    p=Path(p); sources[rel(p)]=digest(p)
    return json.loads(p.read_text(encoding='utf-8-sig'))
def write(name,value): (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def textsource(p):
    sources[rel(p)]=digest(p)
    return p.read_text(encoding='utf-8-sig')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
assert head=='5b709343a890503ebbe24a802e43cda5647df124'
textsource(ROOT/'AGENTS.md')
board=read(ROOT/'docs/board.json'); items={x['id']:x for x in board['items']}
y=read(TASKS/'yellow-dispatch-gates-20261103/audit.json')
g=read(TASKS/'gray-dispatch-scope-20261103/audit.json')
authority=read(TASKS/'M01/planning/s2-green/source-current.json')
drift=[k for k,v in authority['source_hashes'].items() if not (ROOT/k).exists() or digest(ROOT/k)!=v]
assert len(authority['source_hashes'])==796 and not drift

yellow=[]
for a in y['actions']:
    original_path=TASKS/(a['card']+'.json')
    original=read(original_path) if original_path.exists() else items[a['card']]['legacyTask']
    refs=[]
    for s in a.get('references',[]):
        p=ROOT/s
        if p.exists():
            textsource(p); refs.append(s)
    if a['module']!='IO-PREREQ':
        state=read(TASKS/a['module']/'planning/current-state.json')
        reviewed_note=[n for n in items[a['card']].get('notes',[]) if 'Independent' in n.get('text','')][-1]
        next_action='Owner 對現有精確候選 adopt / return with changed fields / defer；採納後另派 Skeleton＋有效 RED，接受後才適用 standing implementation authority。'
        new_prep={'status':'NO_NEW_UNCOVERED_LOCAL_PREP_ESTABLISHED','reason':'最新候選及獨立文件審查均已交付；本次未找到足以派新本模組準備包的未覆蓋需求。這不等於原PREP禁止繼續。不得重跑既過PASS、複製既有full packet或用新wrapper當行為進展。','resume_if':'新具體反例、Owner退回欄位、可證明未覆蓋原REQ或新外部輸入到達時，僅對差額準備。'}
    else:
        state={'accepted':'historical implementation scoped PASS, full platform PARTIAL','native_eligibility':'current OS build '+platform.version()+'; Win11 acceptance not supplied'}
        reviewed_note={'text':textsource(TASKS/'IO-PREREQ/implementation/acceptance/index.html')[:1400]}
        next_action='提供Windows11 x64隔離執行環境及IO-A-F1 reparse/8.3 native fixtures，再由不同驗證角色執行既有剩餘矩陣；不重跑目前Win10已過案例。'
        new_prep={'status':'EXTERNAL_RUNTIME_ACQUISITION','reason':'目前觀測 OS build 19045；不能充當Windows11。無新Owner設計採納要求。','resume_if':'Win11 runner及原生alias fixtures可用。'}
    yellow.append({'id':a['card'],'module':a['module'],'live_light':items[a['card']]['light'],'original_source':rel(original_path) if original_path.exists() else 'docs/board.json#/items/'+a['card']+'/legacyTask','allowed_files':original.get('allowed_files',['existing acceptance packet native scope only; no new product changes']),'dependencies':original.get('dependencies',[]),'original_contract':original.get('contract'),'original_bdd':original.get('bdd'),'original_acceptance':original.get('acceptance'),'latest_candidate':a.get('candidate'),'latest_review':a.get('review'),'limited_pass_evidence':reviewed_note,'current_state':state,'exact_missing_gate':a['missing_gate'],'next_concrete_action':next_action,'other_original_scope_action':new_prep,'product_ready':False,'refs':refs})

feature_evidence=[]
for i in range(1,13):
    fid=f'F{i:02}'; card=f'PD-P1-{fid}-DELIVERY-01'
    base=TASKS/fid
    if i==12: base=TASKS/'M07/F12'
    prep=base/('feature-trace-correction' if i==5 else 'feature-trace-preparation')
    review=base/('feature-trace-correction-review' if i==5 else 'feature-trace-review')
    payload=[]
    # Actually consume latest trace/recipe/review JSON, without executing passed checkers.
    for folder in [prep,review]:
        for p in folder.glob('*.json'):
            if p.name in ['source-current-check.json','source-integrity.json']: continue
            data=read(p)
            payload.append({'path':rel(p),'top_level_keys':list(data) if isinstance(data,dict) else 'list','sha256':sources[rel(p)]})
    feature_evidence.append({'feature':fid,'card':card,'trace_directory':rel(prep),'review_directory':rel(review),'latest_review_note':items[card].get('notes',[])[-1],'consumed_payloads':payload,'admission':'DOCUMENT_PREPARATION_ACCEPTED_NOT_PRODUCT_DELIVERY','native_result':'NOT RUN'})

gray_red=[]
for r in g['rows']:
    cid=r['id']; packet=TASKS/(cid+'.json')
    original=read(packet) if packet.exists() else r['legacy']
    row={'id':cid,'live_light':items[cid]['light'],'classification':r['classification'],'original_source':rel(packet) if packet.exists() else 'docs/board.json#/items/'+cid+'/legacyTask','original_scope':original.get('allowed_files',original.get('note')),'dependencies':original.get('dependencies',[]),'contract':original.get('contract'),'bdd':original.get('bdd'),'tdd':original.get('tdd'),'acceptance':original.get('acceptance'),'missing_condition':r['missing_condition'],'next_action':r['preparation'],'product_ready':False}
    if cid.startswith('PD-P1-F'):
        f=next(x for x in feature_evidence if x['card']==cid)
        row['completed_since_prior_audit']=f['latest_review_note']
        row['next_action']='保留已過精確Feature trace審查，不重跑。現有pending recipes為未執行提案；先收該Feature相依Owner精確採納與approved envelope，再另行Skeleton/有效RED及獨立驗收。將本Feature已審trace作M08輸入admission盤點，不稱產品交付。'
    if cid.startswith('PD-P1-G'):
        gate=cid.split('-')[2]; destination=TASKS/'decisions'/gate
        witness=read(TASKS/'gray-dispatch-scope-20261103'/(gate+'-decision-witness.json'))
        row['canonical_destination_exists_now']=destination.exists(); row['already_completed_witness']=witness
        row['next_action']='可立即派原scope文件製備：把已有候選／review按精確JSON pointer、hash、失敗語意、相容／衝突列三份canonical deliverables；不複製模組設計、不自採納。前輪只完成destination witness，本次確認canonical交付仍未存在。'
    if cid=='PD-P1-M08-VERIFY-01':
        row['next_action']='可立即派 VERIFY 原步驟1 的新輸入admission crosswalk：消費剛完成F01..F12精確trace/recipes，逐項連A01..A08/N01..N16及未滿足gate；不重開已結PREP、不建立harness、不啟動native、不build。'
    gray_red.append(row)

m08state=read(TASKS/'M08/planning/current-state.json')
m08dec=read(TASKS/'M08/planning/precision-correction/decisions.json')
for name in ['case-matrix.json']:
    read(TASKS/'M08/planning/native-evidence-plan'/name)
read(TASKS/'M08/planning/harness-contract/module-prerequisites.json')

g01=read(TASKS/'PD-P1-G01-DEC-01.json')
g01packet={'task_name':'PD-P1-G01-DEC-01 / canonical decision submission preparation','primary_module':'requirements-governance','execution_mode':'PLANNING_DOCUMENT_ONLY','status':'DISPATCHABLE_ORIGINAL_SCOPE_PREPARATION_NOT_OWNER_APPROVAL','original_scope_source':rel(TASKS/'PD-P1-G01-DEC-01.json'),'why_new':'前輪僅G01-decision-witness；canonical三交付尚不存在。F01..F12 trace審查現已完成，可把確切需求差額納入決策提交，不重做PASS。','allowed_files':[f'docs/requirements-confirmation/phase1-spec/tasks/decisions/G01/{n}' for n in ['decision-request.json','failure-matrix.json','approved-envelope-proposal.json','index.html','source-hashes.json','seal.json']],'protected':['all product/tests/spec/confirmed requirements','board.json','roles/hooks','existing module candidates and reviews','other decisions'],'dependencies':g01['dependencies'],'input_sources':['docs/board.json',rel(TASKS/'PD-P1-G01-DEC-01.json'),rel(TASKS/'gray-dispatch-scope-20261103/G01-decision-witness.json')]+[a['latest_candidate'] for a in yellow if a.get('latest_candidate')]+[f['trace_directory'] for f in feature_evidence], 'steps':['逐G01 intent欄位列ESS/architecture/UI/BIN schema、ID/version/external-dependency/standalone-assets對應候選hash及JSON pointer。','decision-request逐項列existing proposal vs confirmed requirement、Owner adopt/return/defer選項；不能採納缺Owner意見的default。','failure-matrix把每個候選失敗前後狀態／錯誤／資料保全及相容遷移與已審trace對應；無定義則OPEN，不猜新語意。','approved-envelope-proposal只投影已存在候選精確file list/ports；狀態PROPOSED_PENDING_OWNER，approval=null。列跨G02/G03/G04依賴與衝突，不能擅自解決。','獨立文件審查檢查hash/pointer/需求不縮減；Owner才可作精確處置。'],'contract':g01['contract'],'bdd':g01['bdd'],'fixture':'existing candidates, G01 witness and accepted feature traces; no fabricated native evidence','document_checks':['每項G01 intent有候選pointer或OPEN','三份原deliverable齊全且references hash可重算','adoption/approvedSkeleton/validRED不得由document PASS推導','Owner未批准時red/status不改；no product/test/board writes'],'valid_RED':'NOT APPLICABLE: documentation task; product RED NOT RUN','acceptance':g01['acceptance'],'role_separation':{'author':'new document-preparation agent','verifier':'separately started read-only agent distinct from author','decision_owner':'human Owner only','product_developer':'not dispatched'},'follow_up':'G02..G04可各自依原scope同法製備；不是G01必須先完成的依賴。'}

m08packet={'task_name':'PD-P1-M08-VERIFY-01 / F01-F12 input admission crosswalk','status':'DISPATCHABLE_STEP1_DOCUMENT_PREPARATION_ONLY','primary_module':'M08','original_scope_source':rel(TASKS/'PD-P1-M08-VERIFY-01.json'),'allowed_files':['docs/requirements-confirmation/phase1-spec/tasks/M08/verification/input-admission-20261103/'+n for n in ['feature-input-matrix.json','native-case-crosswalk.json','missing-inputs.json','index.html','source-hashes.json','seal.json']],'protected':['M08 PREP and existing accepted documents','all product/tests/harness','user projects/artifacts','board/roles/hooks/spec'],'dependency_semantics':'F01-F12 product acceptance is required for native execution, not for this read-only step1 inventory. The twelve document trace PASS are eligible inventory inputs, not satisfied native dependencies.','input_sources':[f['trace_directory'] for f in feature_evidence]+[f['review_directory'] for f in feature_evidence]+[rel(TASKS/'M08/planning/native-evidence-plan/case-matrix.json'),rel(TASKS/'M08/planning/precision-correction/decisions.json')],'steps':['逐F01..F12精確REQ/AC/BDD/recipe列來源pointer及hash，不用同模組全部BDD替代Feature差額。','對照既有A01..A08/N01..N16；無精確映射留OPEN，不改已批准語意或自創case。','逐列列product acceptance、artifact SHA/version/build metadata、Win11、provider、observability、M08-PD1..PD3未滿足條件；每項NOT RUN有原因。','保留prospective recipe與confirmed BDD、historical source test與native result的差別；獨立read-only review。'],'bdd':{'Given':'F01..F12已審文件trace、既有M08驗收case與未交付產品輸入','When':'製作VERIFY第一步輸入盤點','Then':'每個case具有確切來源與缺條件；文件PASS不變成產品/native PASS'},'fixture':'twelve latest accepted trace/recipe JSON + existing case matrix; no native fixture creation','checks':['恰12features，每個至少1trace+1review pointer','每個原N/A case均映射或明示缺口，不縮門檻','admission結果對缺產品/Win11/artifact者BLOCKED_NOT_RUN','no new harness/public schema/metrics/approval'],'acceptance':['不重開PREP','case matrix原語意保持','差額可精確派後續輸入提供者','新文件檢查與native驗收區分'],'valid_RED':'NOT APPLICABLE: document inventory only; no aggregate RED invented','role_separation':{'author':'new M08 document-preparer, not F01-F12 developer','verifier':'distinct read-only document reviewer','native_verifier':'future independent eligible verifier after all native gates'}}

for row in yellow:
    row['action_attempt_this_round']={'attempt':'Read original packet/live board, current-state, candidate/review and accepted evidence; check runtime eligibility for IO. No passed checker rerun.', 'result':row['other_original_scope_action']['status']}
for row in gray_red:
    row['action_attempt_this_round']={'attempt':'Inspect live original card scope/dependencies; read latest accepted Feature trace payloads or decision witness and canonical destination as applicable.', 'result':('NO_REDISPATCH' if row['classification']=='SUPERSEDED_NOT_REDISPATCH' else 'DOCUMENT_PREPARATION_DISPATCHABLE' if row['id'].startswith('PD-P1-G') or row['id']=='PD-P1-M08-VERIFY-01' else 'TRACE_REVIEW_ALREADY_ACCEPTED_PRODUCT_GATE_PENDING')}

matrix={'kind':'NEW_ACTIONABLE_HANDOFF_NOT_APPROVAL','author':'/root/yellow_next_action_audit','generated_at':datetime.now(timezone.utc).isoformat(),'branch':branch,'live_head':head,'historical_inventory_head':authority['head'],'same_head':False,'796_product_hashes':{'count':796,'mismatches':drift},'owner_heartbeat_context':{'timestamp':'2026-11-03T11:17:04.036Z','source':'parent supplied Owner instruction; not invented board note','rule':'Yellow→Gray→Red逐卡逐動作；原scope prep直接推進，不重跑PASS；產品需Owner adopted envelope + acceptedSkeleton + validRED；不改roles/hooks/no commit'},'board_snapshot_at':board['updatedAt'],'yellow':yellow,'gray_red':gray_red,'feature_evidence':feature_evidence,'m08_current':m08state,'m08_owner_decisions':m08dec,'next_dispatch':[m08packet,g01packet],'ordering':'Yellow無新增已證明未覆蓋local prep；IO外部Win11 gate。Gray VERIFY新step1可派；Red G01..4原三文件仍可製備。此處只準備可執行封包，不跨本次allowedfiles實際寫canonical目的地。','not_run':['product tests','build/package/native','valid RED/GREEN','full module acceptance','independent acceptance of this handoff'],'scope':'Only this new directory. No status/board/product/spec/test/hooks/roles/commit mutation.'}
write('action-matrix.json',matrix); write('next-g01-task.json',g01packet); write('next-m08-task.json',m08packet)
write('source-hashes.json',{'sources':sources,'product_authority':rel(TASKS/'M01/planning/s2-green/source-current.json'),'product_count':796,'mismatches':drift})
e=lambda x:html.escape(str(x))
parts=['<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>下一步派工｜逐卡差額</title><style>body{font:16px/1.6 system-ui;background:#f4f6fa;color:#15283b;margin:0}main{max-width:1250px;margin:auto;padding:28px}section,article{background:white;border:1px solid #dbe2eb;border-radius:10px;padding:20px;margin:16px 0}table{border-collapse:collapse;width:100%}td,th{padding:9px;border:1px solid #ccd6e0;vertical-align:top;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#245c9b}.badge{color:#8a5800}</style><main><h1>逐卡下一動作｜2026-11-03</h1><p>沒有新產品開工授權；存在可立即派的原scope文件製備。8 Yellow的最新文件審查已過，不重跑。12 Feature trace現已全部審查完成，與早先Gray盤點有具體差額。</p><p>優先派Gray M08 VERIFY第一步輸入crosswalk；Red G01～G04 canonical原三交付亦仍可製備，前輪只有witness。這些文件工作不等待產品Owner採納，不代表產品/native gates通過。</p><p>Live '+e(head)+'；歷史 inventory '+e(authority['head'])+'，不是same HEAD。796產品hash零差異。當前OS '+e(platform.version())+'，非Win11驗收證據。</p><p><a href="action-matrix.json">machine action matrix</a> · <a href="next-g01-task.json">G01最小原scope包</a> · <a href="next-m08-task.json">M08下一包</a> · <a href="source-hashes.json">sources</a> · <a href="seal.json">seal</a></p><section><h2>8 Yellow：PASS範圍、精確缺口、下一動作</h2>']
for r in yellow:
    parts+=['<article><h3>'+e(r['id'])+'</h3><p>'+e(r['exact_missing_gate'])+'</p><p><b>下一動作：</b>'+e(r['next_concrete_action'])+'</p><p><b>同卡其他準備：</b>'+e(r['other_original_scope_action'])+'</p><details><summary>原scope／依賴／受限PASS／current state</summary><pre>'+e(json.dumps(r,ensure_ascii=False,indent=2))+'</pre></details></article>']
parts+=['</section><section><h2>18 Gray / 5 Red：逐卡原scope剩餘動作</h2><table><tr><th>卡片</th><th>分類／缺條件</th><th>具體下一動作</th></tr>']
for r in gray_red: parts+=['<tr><td>'+e(r['id'])+'<br>'+e(r['live_light'])+'</td><td>'+e(r['classification'])+'<br>'+e(r['missing_condition'])+'</td><td>'+e(r['next_action'])+'</td></tr>']
parts+=['</table></section><section><h2>可派最小文件包</h2><p>角色：製備者、獨立文件驗證者、Owner決策者分離；本文件作者不自驗收。依賴原卡與精確allowedfiles見下列封包。</p><details open><summary>M08 VERIFY step1</summary><pre>'+e(json.dumps(m08packet,ensure_ascii=False,indent=2))+'</pre></details><details><summary>G01 canonical deliverables</summary><pre>'+e(json.dumps(g01packet,ensure_ascii=False,indent=2))+'</pre></details></section><section><h2>驗證界線</h2><p>本次只讀來源、hash／文件一致性檢查。不執行已過checker，不建立Skeleton，不採納schema/defaults，不寫產品。產品測試、build/native、有效RED、獨立驗收均NOT RUN。所有superseded卡保留且不重派。</p></section><script id="module-spec" type="application/json">'+json.dumps(matrix,ensure_ascii=False).replace('<','\\u003c')+'</script></main></html>']
(OUT/'index.html').write_text(''.join(parts),encoding='utf-8')
checks={'kind':'AUTHOR_DOCUMENT_CHECK_ONLY','yellow':len(yellow),'gray':sum(r['live_light']=='Gray' for r in gray_red),'red':sum(r['live_light']=='Red' for r in gray_red),'feature_traces':len(feature_evidence),'product_hashes':796,'product_drift':drift,'sources':len(sources),'unexecuted_pass_suites':True,'independent_acceptance':'NOT RUN'}
assert checks['yellow']==8 and checks['gray']==18 and checks['red']==5
assert all(not (TASKS/'decisions'/f'G{i:02}').exists() for i in range(1,5))
assert not (TASKS/'M08/verification/input-admission-20261103').exists()
assert all(digest(ROOT/s)==h for s,h in sources.items())
write('check-result.json',checks)
write('seal.json',{'kind':'PAYLOAD_SHA256_NOT_ACCEPTANCE','files':{p.name:digest(p) for p in OUT.iterdir() if p.is_file() and p.name!='seal.json'}})
print(json.dumps(checks))
