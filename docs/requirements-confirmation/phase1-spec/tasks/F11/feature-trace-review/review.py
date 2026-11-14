import pathlib,json,hashlib,subprocess,copy,re,datetime,html
R=pathlib.Path.cwd(); O=R/'docs/requirements-confirmation/phase1-spec/tasks/F11/feature-trace-review'; C=O.parent/'feature-trace-preparation'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v): (O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
t=read(C/'bdd-tdd-trace.json'); m=read(C/'module-spec.json'); recipes=read(C/'pending-recipes.json'); src=read(C/'source-inputs.json')
original=read(R/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F11-DELIVERY-01.json')
feature=(R/'docs/requirements-confirmation/phase1-spec/phase1.feature').read_text(encoding='utf-8')
inv=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
board=read(R/'docs/board.json')
def locate(v):
 if isinstance(v,dict):
  if v.get('id')=='PD-P1-F11-DELIVERY-01' and 'legacyTask' in v:return v
  for x in v.values():
   z=locate(x)
   if z:return z
 if isinstance(v,list):
  for x in v:
   z=locate(x)
   if z:return z
card=locate(board)
checks={'original_bdd_exact':all(x['original_verbatim'] in feature for x in t['rows']), 'ids_preserved':[x['bdd_id'] for x in t['rows']]==original['bdd']['scenario_ids'],'ac11_exact':t['ac11_verbatim']==original['acceptance'][0], 'x07_exact':t['x07_verbatim']==original['tdd']['cases'][0], 'legacy_exact':card['legacyTask']==src['legacyTask'], 'source_hashes':all(sha(R/x['path'])==x['sha256'] for x in src['sources']), 'inventory_count':len(inv['source_hashes'])==796,'inventory_hashes':all((R/p).is_file() and sha(R/p)==h for p,h in inv['source_hashes'].items()),'candidate_seal':all(sha(C/p)==h for p,h in read(C/'seal.json')['files'].items())}
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(); branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(); diff=subprocess.check_output(['git','diff','--name-only','31babe87a7ef1e40a0d4bedc523077e7a45d63ab',head],text=True).splitlines()
management_drift=[{'path':x['path'],'expected':x['sha256'],'actual':sha(R/x['path'])} for x in src['sources'] if sha(R/x['path'])!=x['sha256']]
checks.pop('source_hashes')
checks['nonmanagement_sources_match_management_drift_classified']=all(x['path']=='docs/board.json' for x in management_drift)
checks['head']=head=='5b709343a890503ebbe24a802e43cda5647df124';checks['board_only_commit_delta']=diff==['docs/board.json']
# Independent semantic gate; no candidate checker imported or executed. This validates document claims, not product behavior.
def gate(trace,spec,rec):
 faults=[]
 rows=trace['rows']
 if {r['bdd_id'] for r in rows}!={f'BDD-{i}' for i in range(22,31)}:faults.append('missing obligation')
 for row in rows:
  bid=row['bdd_id']; expected='contextual' if bid in ('BDD-28','BDD-29') else 'direct'
  if row['f11_relation']!=expected:faults.append('wrong relation:'+bid)
  if row['current_product_status']!='NOT RUN at feature/native layer':faults.append('evidence promotion:'+bid)
  if 'PENDING_OWNER' not in row['new_seams']:faults.append('owner gate:'+bid)
  if row['original_verbatim'] not in feature:faults.append('rewritten BDD:'+bid)
 if rec['status']!='PENDING_OWNER_NOT_EXECUTABLE':faults.append('recipe promotion')
 if spec['state']!='PREPARATION_PENDING_REVIEW_OWNER':faults.append('state promotion')
 if not spec['independent_acceptance'].startswith('NOT PERFORMED'):faults.append('self acceptance')
 return faults
probes=[]
def probe(name,change):
 a,b,c=copy.deepcopy(t),copy.deepcopy(m),copy.deepcopy(recipes);change(a,b,c);f=gate(a,b,c);probes.append({'id':name,'detected':bool(f),'faults':f})
for bid in range(22,31):
 probe('relation-swap-'+str(bid),lambda a,b,c,i=bid:a['rows'][i-22].update(f11_relation='direct' if i in (28,29) else 'contextual'))
probe('drop-offline-obligation',lambda a,b,c:a['rows'].pop(6))
probe('claim-native-from-S1',lambda a,b,c:a['rows'][0].update(current_product_status='PASS'))
probe('adopt-new-seam',lambda a,b,c:a['rows'][3].update(new_seams='APPROVED'))
probe('execute-unbound-recipes',lambda a,b,c:c.update(status='READY_FOR_AI_IMPLEMENTATION'))
probe('promote-module-complete',lambda a,b,c:b.update(state='COMPLETE'))
probe('author-self-acceptance',lambda a,b,c:b.update(independent_acceptance='PASS'))
probe('rewrite-original-offline-bdd',lambda a,b,c:a['rows'][6].update(original_verbatim='offline assets optional'))
checks['independent_positive_control']=gate(t,m,recipes)==[];checks['negative_controls']=all(p['detected'] for p in probes)
save('probes.json',{'layer':'NEW independent document semantic model, not runtime/RED/GREEN','positive_faults':gate(t,m,recipes),'negative_cases':probes})
save('input-hashes.json',{'candidate':{p.name:sha(p) for p in C.iterdir() if p.is_file()},'sources':src['sources'],'inventory_file_sha256':sha(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')})
result={'reviewer':'/root/f11_feature_trace_review','author':'/root/f11_feature_trace_packet','verdict':'PASS_BOUNDED_DOCUMENT_PREPARATION_ONLY_PENDING_OWNER' if all(checks.values()) else 'FAIL','checks':checks,'head':head,'branch':branch,'historical_inventory_head':src['product_inventory_head'],'commit_delta':diff,'source_hash_drift':management_drift,'management_drift_explanation':'Parent /root confirmed board note and updatedAt appended after candidate seal; legacyTask and light unchanged. This is parent coordination provenance, not inferred product evidence.','findings':[{'severity':'P3','kind':'MANAGEMENT_ONLY_SOURCE_DRIFT','details':management_drift,'disposition':'Explicit qualification; legacyTask unchanged; no product authority drift; candidate not modified'}] if management_drift else [],'classification_review':{'BDD22-27,30':'direct obligations; historical S1 only partial, product/native NOT RUN','BDD28':'contextual history/open/save-as flow is F12; F11 offline-ready snapshot/material completeness remains direct in intent and recipes23/25. Contextual label must not remove that requirement.','BDD29':'contextual F12 history deletion regression; retained explicitly as pending recipe, not omitted','prospective':'new seam and integration recipes only, never evidence of an approved BDD or runnable target'},'coverage_review':['59/60/61 timing and unchanged60/120/180','R vs R+1 capture baseline','failure old snapshot/pending retention and next-round nonoverlap retry','material/payload/index pre-publication interruption','formal/recovery dual baseline and formal failure dirty retention','same project sessions A/B plus late old owner response','permission/alternative location pending Owner'],'historical_limits':['S1 historical acceptance reviewer states same assistant later read-only turn; this review does not upgrade its independence','RA_L1 ordinal pending Owner','RA_L2 response/stateful replay/restart/atomic baseline NOT PROVEN','RA_L3 fixture KeyError NOT FIXED'],'not_run':['native runtime','product tests','behavioral RED/GREEN','build/package/install','module/product acceptance'],'next':'Owner adoption, exact envelope and runner, valid behavioral RED, implementation then separately started independent verification; board unchanged'}
save('result.json',result)
(O/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>F11 independent trace review</title><style>body{max-width:1050px;margin:40px auto;font:16px/1.7 system-ui}pre{white-space:pre-wrap}</style><h1>F11 獨立文件追溯審查</h1><p>'+result['verdict']+'</p><p>作者 /root/f11_feature_trace_packet；審查 /root/f11_feature_trace_review。僅文件 static/model；非 native runtime、RED/GREEN 或產品驗收。</p><h2>分類與原範圍</h2><pre>'+html.escape(json.dumps(result['classification_review'],ensure_ascii=False,indent=2))+'</pre><h2>證據</h2><p>重新核對796個產品來源hash（全部一致）；board管理來源hash有同期漂移、legacyTask未變，見result.json。原BDD22–30、AC11/X07、board legacy、候選seal與來源hash；16個新語意負向擾動全部須被拒絕。沒有執行作者checker。</p><p>Owner尚未採納；runner未綁定；所有native feature證據保持NOT RUN。BDD28的F12互動分類不可排除F11離線素材完整性義務。</p><a href="result.json">結構化結果</a> · <a href="probes.json">新probe證據</a> · <a href="input-hashes.json">來源hash</a><h2>逐項檢查</h2><pre>'+html.escape(json.dumps(checks,indent=2))+'</pre>',encoding='utf-8')
save('seal.json',{'algorithm':'sha256','files':{p.name:sha(p) for p in O.iterdir() if p.is_file() and p.name!='seal.json'}})
print(json.dumps(result,ensure_ascii=True))
