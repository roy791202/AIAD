import json,hashlib,copy,re,subprocess
from pathlib import Path
R=Path('D:/AIAD'); O=R/'docs/requirements-confirmation/phase1-spec/tasks/F03/feature-trace-review'; P=O.parent/'feature-trace-preparation'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,x): (O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
f=read(P/'feature-trace.json'); original=read(R/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F03-DELIVERY-01.json'); bindings=read(P/'source-bindings.json')
def check(x):
 e=[]
 if x['original_contract']!=original['contract']: e.append('contract')
 if x['original_acceptance']!=original['acceptance']: e.append('acceptance')
 if x['original_bdd']!=original['bdd']: e.append('bdd')
 for i,t in enumerate(x['trace']):
  if t['requirement']!='REQ-04' or t['acceptance']!='AC03': e.append('trace identity')
  if t['bdd']!=['BDD-03','BDD-04','BDD-04','BDD-04 + AC03 explicit failure clause'][i]: e.append('trace BDD')
  if t['original_clause']!=['條件不足只保存','條件齊備產物符合預覽','未實作區明示','生成失敗不破壞原有效內容'][i]: e.append('AC clause')
  if t['status']!='PLANNED_NOT_RUN': e.append('unsupported execution')
  if t['existing_evidence']!=f['trace'][i]['existing_evidence']: e.append('test pointer')
 if x['state']!='PREPARATION_ONLY_PENDING_ADOPTION_ENVELOPE_SKELETON': e.append('unsupported Feature PASS')
 if x['layers']!=f['layers']: e.append('unsupported native/golden claim')
 return e
cases=[]
def mutate(name,fn):
 x=copy.deepcopy(f); fn(x); errors=check(x); cases.append({'id':name,'rejected':bool(errors),'errors':errors})
mutate('wrong-source-REQ',lambda x:x['trace'][0].update(requirement='REQ-05'))
mutate('wrong-BDD',lambda x:x['trace'][0].update(bdd='BDD-04'))
mutate('wrong-AC',lambda x:x['trace'][1].update(acceptance='AC04'))
mutate('weakened-AC-clause',lambda x:x['trace'][3].update(original_clause='failure may destroy old content'))
mutate('wrong-test-pointer',lambda x:x['trace'][1].update(existing_evidence=['unrelated_test.rs:1']))
mutate('unsupported-Feature-PASS',lambda x:x.update(state='FEATURE_PASS'))
mutate('current-native-claim',lambda x:x['layers'].update(native_transaction='PASS_CURRENT'))
mutate('current-golden-claim',lambda x:x['layers'].update(golden='PASS_CURRENT'))
mutate('historical-as-executed',lambda x:x['trace'][0].update(status='GREEN'))
seal=read(P/'seal.json'); seal_drift=[n for n,h in seal['files'].items() if sha(P/n)!=h]
source_drift=[n for n,h in bindings.items() if sha(R/n)!=h]
wrong_hash=dict(bindings); wrong_hash[next(iter(wrong_hash))]='0'*64
cases.append({'id':'wrong-source-hash','rejected':any(sha(R/n)!=h for n,h in wrong_hash.items())})
inv=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')['source_hashes']
product_drift=[n for n,h in inv.items() if not (R/n).exists() or sha(R/n)!=h]
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
checks={'baseline_semantics':check(f),'author_seal_drift':seal_drift,'bound_source_drift':source_drift,'inventory_count':len(inv),'product_drift':product_drift,'HEAD':head,'historical_inventory_HEAD':'31babe87a7ef1e40a0d4bedc523077e7a45d63ab','board_management_diff':'Separate from 796 product authority; no board write or inventory promotion.'}
put('semantic-mutations.json',cases); put('source-checks.json',checks); put('source-bindings.json',{str(p.relative_to(R)).replace('\\','/'):sha(p) for p in [*map(lambda n:R/n,bindings),P/'feature-trace.json',P/'seal.json']})
review={'status':'PASS_PREPARATION_ONLY' if not check(f) and not seal_drift and not source_drift and not product_drift and all(c['rejected'] for c in cases) else 'FINDINGS','reviewer':'/root/f03_feature_trace_review','author':'/root/f03_feature_trace_packet','independent':True,'fresh_semantic_mutations':len(cases),'rejected':sum(c['rejected'] for c in cases),'scope':'F03 preparation document only; original REQ-04 / BDD-03,04 / AC03 thresholds retained','findings':[],'observations':['Four recipes derive the four exact AC03 clauses. Failure clause comes explicitly from AC03, not an invented BDD-04 promise.','Existing source prepare_generation:90 and validate_plan_binding:239 are pure plan policy. Test line 200 compares bindings/intents and immutable inputs; it does not render, publish, save definition or prove UI behavior.','73 focused / 222 WORK / 84 HOST are historical 2026-11-01 at 31babe, not executed now. Historical acceptance record discloses same-assistant later turn, not delegated independent acceptance.','Candidate generation exact design and activation correction remain pending Owner; provider authenticity, golden14/transitive lock/projector/native gates remain open.','Exact future feature runner intentionally unbound; existing cargo commands are policy/regression commands only. Valid RED requires approved envelope/Skeleton, compiling test and fixture self-check then missing observable behavior assertion, never setup failure.'],'health':'GRAY_RETAINED','feature_PASS':False,'module_PASS':False,'Skeleton_authority':False,'owner_approval':'NOT GRANTED','product_tests':'NOT RUN','build':'NOT RUN','native':'NOT RUN','valid_RED':'NOT RUN','full_Draft':'NOT RUN','next':'Owner adoption and exact approved envelope/Skeleton/runner before four planned AC03 tests.'}
put('review.json',review)
html='<!doctype html><meta charset="utf-8"><title>F03 independent preparation review</title><style>body{font:16px/1.7 system-ui;max-width:1050px;margin:40px auto;padding:20px;background:#f3f5f8}section{background:white;padding:20px;margin:15px 0}pre{white-space:pre-wrap}</style><h1>F03 獨立文件審查</h1><section><h2>'+review['status']+'</h2><p>Gray retained. No Feature/module PASS, Owner adoption or Skeleton authority.</p><p>REQ-04 → BDD-03/04 → AC03 → four planned recipes. Product/build/native/valid RED/full Draft NOT RUN.</p></section><section><h2>Evidence and limits</h2>'+''.join('<p>'+v+'</p>' for v in review['observations'])+'</section><section><h2>Fresh semantic mutations</h2><pre>'+json.dumps(cases,ensure_ascii=False,indent=2)+'</pre></section><script type="application/json" id="review-spec">'+json.dumps(review,ensure_ascii=False).replace('</','<\\/')+'</script>'
(O/'index.html').write_text(html,encoding='utf-8')
put('results.json',{'status':review['status'],'fresh_mutations':len(cases),'rejected':sum(c['rejected'] for c in cases),'baseline':checks,'old_847_checker':'NOT RERUN'})
put('seal.json',{'algorithm':'sha256','payload_count':len([p for p in O.iterdir() if p.is_file() and p.name!='seal.json']),'files':{p.name:sha(p) for p in sorted(O.iterdir()) if p.is_file() and p.name!='seal.json'}})
print(json.dumps({'status':review['status'],'mutations':len(cases),'inventory':len(inv),'drift':product_drift,'source_drift':source_drift}))
