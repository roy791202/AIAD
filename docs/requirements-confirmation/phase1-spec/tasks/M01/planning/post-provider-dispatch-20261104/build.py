import json,hashlib,subprocess,html,copy,os
from pathlib import Path
from datetime import datetime
ROOT=Path.cwd(); BASE=Path('docs/requirements-confirmation/phase1-spec/tasks'); OUT=BASE/'M01/planning/post-provider-dispatch-20261104'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def bind(p,pointer=''):return {'path':str(p).replace('\\','/'),'sha256':sha(p),'pointer':pointer}
board=read('docs/board.json'); oldpath=BASE/'M01/planning/current-action-blockers-20261103/actions.json'; prior=read(oldpath); by={x['id']:(i,x) for i,x in enumerate(prior['cards'])}
latest={
'M01':('provider-source-map-20261104/module-spec.json','provider-source-map-review-20261104/results.json'),
'M02':('golden14-candidate-20261104/candidate.json','golden14-candidate-correction-review-20261104/results.json'),
'M03':('media-capability-options-20261104/module-spec.json','media-capability-options-review-20261104/results.json'),
'M04':('provider-source-map-20261104/module-spec.json','provider-source-map-review-20261104/results.json'),
'M05':('provider-source-map-20261104/module-spec.json','provider-source-map-review-20261104/results.json'),
'M06':('provider-source-map-20261104/module-spec.json','provider-source-map-review-20261104/results.json'),
'M07':('provider-source-map-correction-20261104/module-spec.json','provider-source-map-correction-review-20261104/results.json')}
module_sources={m:[bind(BASE/m/'planning'/p) for p in pp] for m,pp in latest.items()}
# All source payloads are read, not merely asserted from the existence of report filenames.
for ss in module_sources.values():
 for s in ss:read(s['path'])
summary={
'M01':('CR-D1 lease issuer / CR-D2 durable Ready restart proof / CR-D3 publish shape disposition','Native identity tuple and authenticated lease issuer; durable Ready/index lifetime; exact adopted envelope and accepted Skeleton/intended RED before product','M01 readiness + native IO provider; Owner only exact pending semantics'),
'M02':('GT-D1 shell controls; GT-D2 identity/version; GT-D3 pins/toolchain; GT-D4 window/CSP/no-bundle/schema; activation Busy/Defer and AF2/AF3','Golden14 candidate bytes and full standalone lock are PRESENT, not missing. Formal golden admission, approved real definition/design revisions, actual projector/output semantics and native activation fence remain absent; product build/native NOT RUN','M02 template/projector + independent toolchain verifier; Owner exact GT/activation choices'),
'M03':('MM01..MM08 exact supported subset/policy; C1/H2 adoption remains pending','Renderer/decoder exact fixture bytes/provenance and native support proof; unknown formats/SDK/threshold remain null; M04 persistence provider','Media fixture/renderer + M05 blob authority + M04 persistence; Owner exact supported subset'),
'M04':('G1..G4 observation/capture/Held/errors/ACK sequence','Raw file receipt vs semantic ACK/root-transfer bridges; authenticated Held issuer/fence and exact full codec/envelope','M04 transaction/ACK owner + native IO issuer + M05 root provider'),
'M05':('H1..H4 request/proof/response/reconciliation','Caller strings/completeness projections are not authenticated Held/inclusion/fence; identity-only Eligible is not cleanup authority; real issuer and uncertain-CAS reconciliation provider','M05 catalog/root authority + authenticated issuer/fence provider'),
'M06':('MH1..MH6; BDD19 complete restoration preserved, deferred retention requires explicit BEHAVIOR_CHANGE','Mutation issuer, root registration/fence, Undo-purpose Held, typed ESS projector and transaction compensation seam; local Undo is not distributed rollback','M06 merge/Undo + M04 commit/ACK + M05 retention + ESS projector providers'),
'M07':('RA-O1/O2 protocol and exact ordinal formula/version disposition','Immutable RecoveryIndex issuer; M05 root transfer; atomic replay/baseline and restart proof; CapturedAttempt has no ordinal formula and Published is trusted HOST input','M07 recovery + M04 sole ACK owner + M05 root + immutable index/native restart providers')}
fmap={'F01':'M01','F02':'M02','F03':'M02','F04':'M03','F05':'M04','F06':'M05','F07':'M06','F08':'M06','F09':'M06','F10':'M04','F11':'M07','F12':'M07'}
rows=[]; original_read=[]
for light in ['Yellow','Gray','Red']:
 for idx,item in enumerate(board['items']):
  if item['light']!=light:continue
  cid=item['id'];pi,p=by[cid];original=BASE/(cid+'.json')
  if original.exists(): o=read(original); ob=bind(original)
  else: o=item['legacyTask']; ob=bind('docs/board.json','/items/'+str(idx)+'/legacyTask')
  original_read.append(ob)
  r={'id':cid,'light':light,'status':item['status'],'selected':None,'board':bind('docs/board.json','/items/'+str(idx)),'board_at_read':{'updatedAt':item.get('updatedAt'),'lightReason':item.get('lightReason')},'original_task':ob,'prior_dispatch':bind(oldpath,'/cards/'+str(pi)),'attempts':[],'evidence':[]}
  if cid.startswith('PD-P1-ESS-'):
   r.update(disposition='SUPERSEDED_PRESERVE_NO_REDISPATCH',attempts=['Read original task and current legacy-preserving board reason; verify replacement scope rather than restart superseded planning.'],missing_conditions='No new legacy execution requested; replacement module/decision tasks remain authoritative.',provider='Coordinator retains card; replacement module owners execute within their own scope.',semantic_decision='None requested on superseded card',technical_work='No repeat consolidation or historical PASS rerun.')
  elif cid=='PD-P1-IO-PREREQ-IMPL-01':
   r.update(disposition='BLOCKED_ENVIRONMENT',attempts=['Read original task and native remaining matrix requirement.','Live Get-CimInstance Win32_OperatingSystem: Windows 10 Pro 10.0.19045 x64; cannot execute Windows11 admission on this host.'],missing_conditions='Windows11 x64 isolated machine plus native reparse/8.3 fixtures; no new design adoption required.',provider='Win11 machine/fixture provider and distinct verification agent',semantic_decision='None: existing IO design must not be asked again.',technical_work='Provide native machine and fixtures; independent remaining matrix execution only.')
  elif cid=='PD-P1-M08-VERIFY-01':
   r.update(disposition='BLOCKED_ADMISSION',attempts=['Read original task and prior exact admission correction/review bindings; current board still Backlog/Gray.','Check current F01..F12 lifecycle: all Gray; no completed product delivery claimed by new provider maps.'],missing_conditions=p['missing_conditions'],provider=p['provider'],semantic_decision='M08-PD1..PD3 exact harness design choices remain separate.',technical_work='Admitted versioned portable artifact/native harness plus accepted F01..F12 deliveries, not synthetic projection.')
   r['evidence']=[p['review']]
  elif '-G0' in cid:
   g=cid.split('-')[2];dp=BASE/'decisions'/g/'decision-request.json';dec=read(dp)
   r.update(disposition='BLOCKED_EXACT_DISPOSITION',attempts=['Read original task, canonical decision packet and current board; exact approval remains pending.','Do not redispatch already reviewed canonical consolidation.'],missing_conditions='Exact revision/field selection in canonical packet; candidate publication and source maps do not adopt it.',provider='Owner exact field disposition; named technical module providers after semantics are explicit.',semantic_decision=p['missing_conditions'],technical_work='Follow module-specific provider conditions; no blanket product authority from document PASS.');r['evidence']=[bind(dp)]
  else:
   key=cid.split('-')[2];m=fmap.get(key,key);sem,tech,provider=summary[m]
   r.update(disposition='BLOCKED_CURRENT_EXECUTION_GATES',module=m,attempts=['Read original scope/current card and prior exact gate record.','Inspect newly sealed module candidate/provider evidence and independent review; known source mapping preparation already delivered; do not rerun its PASS.','Check next requested product/acceptance action against exact unresolved semantics, provider proof, approved envelope, accepted Skeleton and intended RED; current source/document package does not satisfy those gates.'],semantic_decision=sem,technical_work=tech,missing_conditions=sem+'; '+tech,provider=provider,evidence=module_sources[m])
   if key.startswith('F'):r['attempts'].append('Feature wrapper remains Gray; module document preparation is not feature product delivery.');r['technical_work']+='; feature acceptance requires module contract/regression/architecture/acceptance evidence.'
  rows.append(r)
authority=read(BASE/'M01/planning/s2-green/source-current.json')['source_hashes'];drift=[p for p,h in authority.items() if not Path(p).exists() or sha(p)!=h]
assert not drift and len(authority)==796
payload={'author':'/root/dispatch_post_provider_audit','status':'AUTHOR_ROUTING_AUDIT_PENDING_INDEPENDENT_REVIEW','generated_at':datetime.now().astimezone().isoformat(),'heartbeat':'2026-11-03T17:28:11.169Z','branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(),'live_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'historical_product_head':'31babe87a7ef1e40a0d4bedc523077e7a45d63ab','authority_count':796,'authority_drift':drift,'board_sha256':sha('docs/board.json'),'counts':{c:sum(i['light']==c for i in board['items']) for c in ['Yellow','Gray','Red','Green','Blue']},'ordering':['Yellow','Gray','Red'],'rows':rows,'known_action_window':'No presently admitted next product/native action executable from supplied inputs after checking all31 active Gray/Yellow/Red cards. This is not a claim that all possible future candidate preparation is blocked. New exact semantic disposition, technical fixture/provider input or environment creates a new bounded action. Do not mint more source-map wrappers as progress.','new_delta':'Golden14 actual candidate bytes+standalone lock now present; M01/M04/M05/M06/M07 provider boundary facts and M03 capability source facts incorporated, not misreported as pending authorship or adopted product.','selected':None,'product_pass':False,'not_run':['historical PASS rerun','product implementation','product build/native acceptance','commit/push/release'],'memory_used':'No memory-derived project state used; all routing from current workspace sources.'}
(OUT/'audit.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'source-bindings.json').write_text(json.dumps({'original_tasks':original_read,'latest':module_sources,'authority':bind(BASE/'M01/planning/s2-green/source-current.json'),'prior':bind(oldpath)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
checks=[('31_exact_unique',len(rows)==31 and len({r['id'] for r in rows})==31),('ordered', [r['light'] for r in rows]==['Yellow']*8+['Gray']*18+['Red']*5),('6_superseded',sum(r['disposition']=='SUPERSEDED_PRESERVE_NO_REDISPATCH' for r in rows)==6),('all_attempt_provider_missing',all(r['attempts'] and r['provider'] and r['missing_conditions'] for r in rows)),('no_adoption',all(r['selected'] is None for r in rows)),('796_zero',len(authority)==796 and not drift),('golden_present',all('PRESENT' in r['technical_work'] for r in rows if r.get('module')=='M02')),('all_original_tasks_read',len(original_read)==31)]
assert all(v for _,v in checks)
(OUT/'checks.json').write_text(json.dumps({'layer':'new routing document self-check only','checks':[{'name':n,'pass':v} for n,v in checks]},indent=2)+'\n',encoding='utf-8')
body=''.join('<tr><td>'+html.escape(r['id'])+'</td><td>'+r['light']+'</td><td>'+html.escape(' / '.join(r['attempts']))+'</td><td>'+html.escape(r['semantic_decision'])+'</td><td>'+html.escape(r['technical_work'])+'</td><td>'+html.escape(r['provider'])+'</td><td>'+''.join('<a href="../../../../../../../../'+s['path']+'">'+html.escape(s['path'])+'</a><br>' for s in r['evidence'])+'</td></tr>' for r in rows)
page='<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Post-provider dispatch audit</title><style>body{font:15px system-ui;margin:28px;color:#173047}table{border-collapse:collapse}td,th{border:1px solid #bbc;padding:9px;vertical-align:top}a{overflow-wrap:anywhere}th{background:#eef}</style><h1>31 卡：最新 provider 交付後的派工條件</h1><p>Yellow 8 → Gray 18 → Red 5；Green305／Blue0。作者文件盤點，待獨立審查。不是採納、產品PASS或全域停止。</p><p>'+html.escape(payload['known_action_window'])+'</p><p>'+html.escape(payload['new_delta'])+'</p><p>已採納方向保留；Owner 不需手填 hash/schema。六張 superseded 卡不重派、不刪藏。產品 gate 缺件只阻擋受影響 slice；技術 provider 仍可提供具體輸入。</p><table><tr><th>卡號</th><th>燈</th><th>本輪逐卡嘗試</th><th>待產品語意</th><th>缺技術條件</th><th>提供角色</th><th>最新證據</th></tr>'+body+'</table><p>live HEAD '+payload['live_head']+'；歷史產品HEAD '+payload['historical_product_head']+'；796 authority零漂移，兩HEAD不可當sameHEAD。Win10 19045非Win11。歷史PASS未重跑。</p></html>'
(OUT/'index.html').write_text(page,encoding='utf-8')
seal={f.name:sha(f) for f in OUT.iterdir() if f.is_file() and f.name!='seal.json'}
(OUT/'seal.json').write_text(json.dumps({'author':payload['author'],'files':seal,'status':'SEALED_AUTHOR_DOCUMENT_ONLY'},indent=2)+'\n',encoding='utf-8')
print('sealed',len(rows),len(seal),checks)


