import json,hashlib,pathlib,copy,subprocess,html
R=pathlib.Path('D:/AIAD'); O=R/'docs/requirements-confirmation/phase1-spec/tasks/F05/feature-trace-review'; P=O.parent/'feature-trace-preparation'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,v): (O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
spec=json.loads((P/'module-spec.json').read_text(encoding='utf-8'))
inputs=json.loads((P/'source-inputs.json').read_text(encoding='utf-8'))['sources']
auth=R/spec['authority']['authority_file']; hashes=json.loads(auth.read_text(encoding='utf-8'))['source_hashes']
drift=[p for p,h in hashes.items() if not (R/p).is_file() or sha(R/p)!=h]
seal=json.loads((P/'seal.json').read_text(encoding='utf-8'))
seal_drift=[n for n,h in seal['artifacts'].items() if sha(P/n)!=h]
source_drift=[x['path'] for x in inputs if sha(R/x['path'])!=x['sha256']]
# Independent semantic rules use original AC and exact Given/When/Then, not preparer's checker.
def check(s):
 e=[]; rows=s['trace']; ids=[r['test_id'] for r in rows]
 if ids!=['F05-P01','F05-P02','F05-P03','F05-P04','F05-P05','F05-R20','F05-R21']: e.append('test identity/order')
 if s['identity']['zone']!='gray' or s['identity']['feature_verdict']!='NOT_PROVEN': e.append('unauthorized completion')
 for i,r in enumerate(rows):
  if r['status']!='PLANNED_NOT_RUN': e.append('current PASS claim')
  if i<5 and (r['requirement']!='REQ-07' or not r['acceptance_clause'].startswith('AC05')): e.append('wrong AC/requirement')
  if i>=5 and (r['requirement']!='REQ-15' or r['bdd']!=['BDD-'+str(20+i-5)] or 'not new F05 AC' not in r['acceptance_clause']): e.append('shared regression as feature proof')
  if i in (0,3,4) and 'BDD-07' in r['bdd']: e.append('semantic BDD mismatch:'+r['test_id'])
  if r['test_target']!='PENDING_OWNER_ENVELOPE_AND_SKELETON': e.append('invented executable test')
 for x in s['evidence']:
  if x['id']=='E-UI' and x['kind']!='CURRENT_SOURCE_INSPECTION_ONLY': e.append('native claim')
 return sorted(set(e))
base=check(spec)
mut=[]
for name,fn in [
 ('wrong_ac',lambda s:s['trace'][1].update(acceptance_clause='AC10')),
 ('wrong_bdd',lambda s:s['trace'][5].update(bdd=['BDD-07'])),
 ('wrong_test',lambda s:s['trace'][1].update(test_id='invented')),
 ('current_pass',lambda s:s['trace'][1].update(status='PASS')),
 ('native_claim',lambda s:s['evidence'][2].update(kind='NATIVE_PASS')),
 ('shared_as_feature',lambda s:s['trace'][6].update(acceptance_clause='AC05 full feature'))]:
 s=copy.deepcopy(spec);fn(s);new=sorted(set(check(s))-set(base));mut.append({'id':name,'detected':bool(new),'diagnostics':new})
# Actual evidence path and hash mutations, independent of trace text.
for name,path,digest in [('wrong_path','apps/does-not-exist.rs','0'*64),('wrong_hash',inputs[0]['path'],'0'*64)]:
 p=R/path;mut.append({'id':name,'detected':not p.is_file() or sha(p)!=digest,'diagnostics':['source identity/hash mismatch']})
put('mutation-fixtures.json',mut)
finding={'id':'F05-TRACE-01','severity':'P2','location':'module-spec.json trace[F05-P01/F05-P04/F05-P05].bdd','counterexample':'BDD-07 requires dirty document, save failure, and selecting save during project-switch prompt; its Then preserves old file, edits and current project. P01 successful close/reopen, P04 owner identity fencing, and P05 successful semantic ACK do not execute that scenario. They derive valid prospective cases from AC05 but currently label BDD-07 as their scenario without extension/reference semantics.','impact':'The seven-row matrix is not exact BDD-to-TDD traceability; a reviewer/tool may count failure-only BDD-07 as covering successful roundtrip/isolation/ACK. All rows remain planned, so this is a preparation trace defect, not a product failure.','resolution':'Retain original BDD-07/08/20/21 unchanged. Mark BDD-07 on P01/P04/P05 as contextual reference only, with explicit missing/planned feature scenario IDs requiring approval; bind exact future Given/When/Then before tests. Preserve AC05 and all envelope/Skeleton/valid RED gates.'}
review={'reviewer':'/root/f05_feature_trace_review','author':'/root/f05_feature_trace_packet','verdict':'FINDING_PREPARATION_TRACE_ONLY','findings':[finding],'counts':{'rows':7,'feature_plans':5,'adjacent_regressions':2,'new_mutations':len(mut),'detected':sum(x['detected'] for x in mut)},'checkout':{'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'historical_authority_head':'31babe87a7ef1e40a0d4bedc523077e7a45d63ab','authority_files':len(hashes),'product_drift':drift,'candidate_seal_drift':seal_drift,'source_input_drift':source_drift,'board_management_sha256':sha(R/'docs/board.json'),'board_separate_from_product_authority':True},'semantic_baseline_diagnostics':base,'observations':['Original task Gray BLOCKED_PENDING_APPROVED_ENVELOPE_AND_VALID_RED; dependencies unchanged.','S1 historical 73 work tests plus seven probes is pure domain only; actual m04_ex01 history target/log exists.','IO historical 220 cases remains PARTIAL_PENDING_WINDOWS11_AND_NATIVE_ALIAS_GATES. No current product execution.','Current app.js:513 two-confirm leave flow catches save errors; app.js:1090 encodes XML, invokes scene_save, persists draft and clears dirty. file_save is HostSettings only. These are static source facts, not full F05 proof.','Retention review 704 model probes is document-only pending Owner G1-G4; raw receipt and semantic ACK differ, durable issuer/root/owner identity and codec adoption remain dependencies. No native authenticity or atomic file/catalog/ACK proof.','P02 preserves truthful committed/uncertain byte observations and requires adopted failure mapping; this does not authorize weakening original failed-save AC05.','All seven recipes remain PLANNED_NOT_RUN. R20/R21 are adjacent REQ-15 obligations, not F05 proof.'], 'not_run':['product tests','build/package/install','native/UI/IPC','valid RED/GREEN','full Draft 2020-12 validation'],'authority':'No Feature/module PASS, Skeleton authority, dispatch, acceptance, board promotion or implementation authorization.'}
put('review.json',review)
put('source-inputs.json',{'inputs':inputs,'candidate_seal_sha256':sha(P/'seal.json'),'authority_sha256':sha(auth),'checked_at':'2026-11-03 Asia/Taipei'})
(O/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>F05 independent trace review</title><h1>F05 independent trace review</h1><p>FINDING_PREPARATION_TRACE_ONLY · Gray retained · product NOT RUN</p><pre>'+html.escape(json.dumps(review,ensure_ascii=False,indent=2))+'</pre><script type="application/json" id="review-spec">'+json.dumps(review,ensure_ascii=False).replace('</','<\\/')+'</script>',encoding='utf-8')
put('seal.json',{'artifacts':{p.name:sha(p) for p in sorted(O.iterdir()) if p.is_file() and p.name!='seal.json'},'final_counts':review['counts'],'status':'SEALED_REVIEW_ONLY'})
print(json.dumps({'verdict':review['verdict'],'authority':len(hashes),'drift':drift,'source_drift':source_drift,'mutations':review['counts']},ensure_ascii=False))
