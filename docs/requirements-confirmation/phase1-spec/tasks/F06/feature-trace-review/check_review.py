import copy,hashlib,json,pathlib,re,subprocess
P=pathlib.Path(__file__).resolve().parent
R=P.parents[5]
A=P.parent/'feature-trace-preparation'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(n,v): (P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
m=read(A/'module-spec.json'); recipes=read(A/'pending-test-recipes.json'); pointers=read(A/'source-pointers.json')
original=read(R/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F06-DELIVERY-01.json')
expected_oracles=[
'Merged newly added asset is referenced by successful snapshot; undo merge retracts live reference; cleanup assessment retains snapshot asset.',
'Add image/video, preview type and information, copy into project, share across components; read/decode/conversion failure preserves component and references.',
'Rename does not break references; preview replacement impact before applying.',
'A snapshot across versions still reads the old material.',
'Unknown format explicitly shown; SVG script/external references, zero byte/corrupt/over-limit handling require approved exact matrix; restricted playback exposes manual entry, not missing-asset claim.',
'Unknown roots retain; existing S1 identity eligibility never authorizes physical GC.']
inputs=read(A/'inputs.json')['sources']; seal=read(A/'seal.json')['files']
bundle={'spec':m,'recipes':recipes,'pointers':pointers,'sources':inputs,'claim':{'catalog':'PROPOSED_PENDING_OWNER','feature':'NOT RUN','native':'NOT RUN'}}
def evaluate(b):
 s=b['spec']; t=s['trace']; failures=[]
 def ck(n,v):
  if not v: failures.append(n)
 ck('six original trace relations',len(t)==6 and [x['id'] for x in t]==['F06-TRACE-%02d'%i for i in range(1,7)])
 ck('original task unchanged',s['original_packet']==original)
 ck('BDD31 exact not AC06 equivalence',t[0]['bdd']=='BDD-31' and t[0]['acceptance']=='Original BDD-31 outcome; contextual AC10/AC11, not AC06 equivalence' and t[0]['tdd']=='TDD-31 (original fixture plan)' and t[0]['classification']=='EXACT_ORIGINAL_SCENARIO_OBLIGATION')
 ck('five prospective AC06 X05 no invented original BDD',all(x['bdd'] is None and x['acceptance']=='AC06 proposal / X05 original obligations' and x['classification']=='PROSPECTIVE_AC06_X05_RECIPE_NOT_APPROVED_BDD' for x in t[1:]))
 ck('six approved-meaning oracles retained',[x['oracle'] for x in t]==expected_oracles)
 ck('recipes preserve trace oracles',[x['assertion_oracle'] for x in b['recipes']]==expected_oracles)
 ck('recipes gated not execution',len(b['recipes'])==6 and all(x['status']=='PLANNED_NOT_RUN' and x['command'].startswith('BLOCKED') and 'compiles' in x['valid_red'] and 'fixture errors invalid' in x['valid_red'] for x in b['recipes']))
 ck('preparation no approval',s['state']=='PLANNED_NOT_RUN' and s['board']=='Gray / Backlog retained' and b['claim']=={'catalog':'PROPOSED_PENDING_OWNER','feature':'NOT RUN','native':'NOT RUN'})
 ck('source paths hashes not exchanged',b['sources']==inputs)
 ck('test source semantic context not exact',b['pointers']==pointers and all('exact original F06 execution evidence' in x['evidence'] for x in t[1:]) and 'partial policy context only' in t[0]['evidence'])
 ck('current and historical heads distinct',s['head']=='5b709343a890503ebbe24a802e43cda5647df124' and s['inventory_head']=='31babe87a7ef1e40a0d4bedc523077e7a45d63ab' and s['inventory_count']==796 and s['inventory_authority'].endswith('M01/planning/s2-green/source-current.json'))
 return failures
checks=[]
def check(n,v): checks.append({'check':n,'pass':bool(v)})
check('independent baseline predicate',not evaluate(bundle))
check('sealed author package',all(sha(A/p)==h for p,h in seal.items()))
source_results=[]
for p,h in inputs.items():
 actual=sha(R/p); source_results.append({'path':p,'expected':h,'actual':actual,'same':actual==h,'layer':'board management separate' if p=='docs/board.json' else 'source'})
check('all nonboard input hashes',all(x['same'] for x in source_results if x['path']!='docs/board.json'))
auth=read(R/m['inventory_authority']); hashes=auth['source_hashes']
check('796 live product hashes',len(hashes)==796 and all((R/p).is_file() and sha(R/p)==h for p,h in hashes.items()))
check('current HEAD',subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==m['head'])
feature=(R/'docs/requirements-confirmation/phase1-spec/phase1.feature').read_text(encoding='utf-8')
check('original exact Given When Then',all(s in feature for s in ['@BDD-31 @M05 @REQ-16','假如 合併新增素材已被成功快照引用','當 Undo合併並執行素材清理評估','那麼 活文件引用撤回但快照所需素材保留']))
fix=read(R/'docs/requirements-confirmation/phase1-spec/fixtures.json')
check('original fixture remains planned', '"bdd": "BDD-31"' in json.dumps(fix,ensure_ascii=False) and '活文件引用撤回但快照所需素材保留' in json.dumps(fix,ensure_ascii=False))
src=(R/pointers[0]['path']).read_text(encoding='utf-8'); tests=(R/pointers[1]['path']).read_text(encoding='utf-8')
check('source pure identity decision limit',all(s in src for s in ['No physical cleanup behavior','Eligibility is never permission to delete','pub fn evaluate_asset_retention']))
check('existing test names real',all(n in tests for n in pointers[1]['tests']))
check('snapshot undo tests supplied projections',all(n in tests for n in ['m05_retained_snapshot_retains','m05_undo_history_retains','m05_missing_provider_is_not_complete_empty']))
s1=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M05/s1/green/acceptance/review.json')
check('S1 historical not module or independent',s1['head']==m['inventory_head'] and s1['module_complete'] is False and 'no delegated independent reviewer' in s1['reviewer'])
cx=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M05/planning/cx-revision-v3/envelope.json')
check('CX candidate unapproved',cx['status']=='RR_REVISED_CANDIDATE_PENDING_OWNER')
rmap=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M05/planning/retention-receipt-mapping-review/review.json')
check('receipt review does not adopt H1 H4',rmap['verdict']=='PASS_DOCUMENT_ONLY_PENDING_OWNER' and len(rmap['owner_choices'])==4 and all(x['status']=='PROPOSED_PENDING_OWNER' for x in rmap['owner_choices']))
ui=(R/'apps/sgenaxis-desktop/ui/app.js').read_text(encoding='utf-8')
check('UI metadata pointers real',all(s in ui for s in ['<assetRefs>','assetRefs > assetRef','node.assetRefs = parseArchLineList']))
for p in pointers[4:]:
 text=(R/p['path']).read_text(encoding='utf-8'); check('historical log exists '+p['path'], bool(text.strip()))
h=(A/'index.html').read_text(encoding='utf-8'); embedded=json.loads(re.search(r'<script type="application/json" id="module-spec">(.*?)</script>',h,re.S).group(1))
check('author HTML projects same structured model',embedded==m)
mutations=[]
def mutation(name,fn):
 b=copy.deepcopy(bundle); fn(b); reasons=evaluate(b); mutations.append({'id':name,'expected':'REJECT','observed':'REJECT' if reasons else 'ACCEPT','reasons':reasons})
mutation('wrong-original-AC',lambda b:b['spec']['trace'][0].update(acceptance='AC06 proposal / X05 original obligations'))
mutation('wrong-original-BDD',lambda b:b['spec']['trace'][0].update(bdd='BDD-32'))
mutation('wrong-original-TDD',lambda b:b['spec']['trace'][0].update(tdd='TDD-30'))
mutation('prospective-context-as-exact',lambda b:b['spec']['trace'][2].update(bdd='BDD-31',classification='EXACT_ORIGINAL_SCENARIO_OBLIGATION'))
mutation('S1-context-as-exact-feature-evidence',lambda b:b['spec']['trace'][0].update(evidence='Exact feature implementation PASS'))
mutation('wrong-test-name',lambda b:b['pointers'][1]['tests'].__setitem__(0,'m05_full_import_native_pass'))
mutation('wrong-source-path',lambda b:b['pointers'][0].update(path='apps/sgenaxis-desktop/ui/app.js'))
mutation('wrong-input-hash',lambda b:b['sources'].__setitem__('apps/sgenaxis-desktop/ui/app.js','0'*64))
mutation('proposed-catalog-as-adopted',lambda b:b['claim'].update(catalog='APPROVED'))
mutation('current-Feature-PASS',lambda b:b['claim'].update(feature='PASS'))
mutation('native-PASS',lambda b:b['claim'].update(native='PASS'))
mutation('recipe-fixture-failure-as-valid-RED',lambda b:b['recipes'][0].update(valid_red='Missing runner counts as RED'))
mutation('invent-capacity-threshold',lambda b:b['spec']['trace'][4].update(oracle='Reject over 1 MB'))
mutation('historical-792-authority',lambda b:b['spec'].update(inventory_count=792))
mutation('Owner-approved-Skeleton',lambda b:b['spec'].update(state='READY_FOR_AI_IMPLEMENTATION'))
check('fresh semantic mutations reject',all(x['observed']=='REJECT' for x in mutations))
not_run=['product tests','build','native UI','valid RED/GREEN','full Draft2020-12','feature/module acceptance','Skeleton approval']
review={'reviewer':'/root/f06_feature_trace_review','author':'/root/f06_feature_trace_packet','verdict':'PASS_PREPARATION_ONLY' if all(x['pass'] for x in checks) else 'FAIL','checks_passed':sum(x['pass'] for x in checks),'checks_total':len(checks),'mutations_rejected':sum(x['observed']=='REJECT' for x in mutations),'mutations_total':len(mutations),'head':m['head'],'inventory_head':m['inventory_head'],'inventory_count':796,'board':'Gray retained; dependencies unchanged; management hash reported separately','findings':[],'meaning':'Six trace rows accurately separate the one original BDD-31 obligation from five prospective AC06/X05 recipes. Exact refers to original obligation identity, never execution equivalence. Existing source/tests/logs remain pure S1 historical/context evidence. No Owner approval granted.','limits':['This checker uses fixed independent semantic expectations; it is bounded document verification, not a generic natural-language proof.','No author checker rerun. No approval of proposed architecture, UI, contract, BDD, Skeleton or production envelope.'],'not_run':not_run,'feature_pass':False,'module_pass':False,'checks':checks}
dump('mutation-fixtures.json',mutations); dump('source-hashes.json',source_results); dump('review.json',review)
html='<!doctype html><html lang="en"><meta charset="utf-8"><title>F06 independent preparation review</title><style>body{font:16px system-ui;max-width:1050px;margin:40px auto;color:#172334}pre{white-space:pre-wrap;background:#eef2f7;padding:20px}table{border-collapse:collapse}td,th{padding:10px;border:1px solid #bbc}</style><h1>F06 independent preparation review</h1><h2>'+review['verdict']+'</h2><p>'+review['meaning']+'</p><p>Gray retained. Original thresholds unchanged. Product tests, build, native UI, valid RED/GREEN and full Draft2020-12: NOT RUN.</p><p>'+str(review['checks_passed'])+'/'+str(len(checks))+' independent checks; '+str(len(mutations))+'/'+str(len(mutations))+' new semantic mutations rejected.</p><table><tr><th>Row</th><th>Relation</th><th>Unproved behavior / next gate</th></tr>'
for row in m['trace']: html+='<tr><td>'+row['id']+'</td><td>'+row['classification']+'</td><td>'+row['gap']+'</td></tr>'
html+='</table><h2>Authority and limitations</h2><p>796 source hashes: M01/planning/s2-green/source-current.json. Current HEAD '+m['head']+' is distinct from historical '+m['inventory_head']+'. S1 cleanup identity decision is not catalog/provider/pin/UI/native deletion permission. Receipt H1-H4 and CXv3 remain pending Owner.</p><h2>Review evidence</h2><pre>'+json.dumps(review,ensure_ascii=False,indent=2)+'</pre><script type="application/json" id="review-spec">'+json.dumps(review,ensure_ascii=False).replace('</','<\\/')+'</script></html>'
(P/'index.html').write_text(html,encoding='utf-8')
files={p.name:sha(p) for p in P.iterdir() if p.is_file() and p.name!='seal.json'}
dump('seal.json',{'status':'SEALED_INDEPENDENT_DOCUMENT_REVIEW','files':files,'counts':{'checks':len(checks),'mutations':len(mutations)},'feature_pass':False})
print(review['verdict'],review['checks_passed'],len(checks),len(mutations)); print(json.dumps([x for x in checks if not x['pass']]))
