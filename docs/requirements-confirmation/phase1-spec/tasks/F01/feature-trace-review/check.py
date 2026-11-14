import copy, hashlib, html, json, pathlib, re, subprocess
O=pathlib.Path(__file__).resolve().parent
R=next(p for p in O.parents if (p/'apps/sgenaxis-desktop/Cargo.toml').exists())
P=O.parent/'feature-trace-preparation'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,d): (O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
d=read(P/'trace.json'); packet=read(R/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F01-DELIVERY-01.json')
# Independent expected mappings derive from original BDD-01/02 and AC01, not the author's checker.
rows=[('F01-AC01-a','REQ-03','BDD-01',['TDD-01','X01'],'六步可保存重開'),('F01-AC01-b','REQ-03','BDD-01',['TDD-01','X01'],'生成被阻擋時仍可保存'),('F01-AC01-c','REQ-08','BDD-02',['TDD-02','X01'],'衝突的既有目錄逐位元不變')]
codec='apps/sgenaxis-desktop/crates/sgenaxis-host/tests/phase1_project_definition_codec.rs'
host='apps/sgenaxis-desktop/crates/sgenaxis-host/tests/phase1_project_definition.rs'
names=['t001_basics','t001_delivery','t001_topology','t001_requirements','t001_technology_ui','t001_preview','t002_draft','t057_file','t058_empty','t059_nonempty','t060_race','t061_skip','t070_readonly_open','t072_read_denied']
def validate(x):
 e=[]
 if x['original_contracts']!=packet['contract'] or x['original_acceptance']!=packet['acceptance']: e.append('original_threshold')
 for row,expected in zip(x['trace'],rows):
  if (row['id'],row['requirement'],row['bdd'],row['original_tdd'],row['criterion'])!=expected: e.append('original_trace')
 if len(x['trace'])!=3: e.append('row_count')
 expected_sources=[ 'docs/requirements-confirmation/phase1-spec/phase1.feature:8-13','docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F01-DELIVERY-01.json#/acceptance/0','docs/requirements-confirmation/phase1-spec/phase1.feature:15-20']
 if [r['source'] for r in x['trace']]!=expected_sources: e.append('wrong_source')
 if [t['name'] for t in x['tests']]!=names: e.append('wrong_test')
 for t in x['tests']:
  expected=codec if t['name'] in names[:7] else host
  if t['source']!=expected: e.append('test_source')
  lines=(R/expected).read_text(encoding='utf-8').splitlines()
  if not lines[t['line']-1].startswith('fn '+t['name']+'('): e.append('pointer')
  if t['executed_this_run'] is not False: e.append('unsupported_execution')
 if any(not r['verdict'].startswith('PARTIAL_HISTORICAL_') for r in x['trace']): e.append('unsupported_PASS')
 if any(x['evidence_boundaries'][k]!='NOT RUN' for k in ['product_tests_this_run','build','RED','native_this_run']): e.append('unsupported_PASS')
 if x['evidence_boundaries']['windows']!='Historical native M01 roundtrip Windows10 build19045 only; Windows11/native aliases NOT RUN. Neither proves full S3 wizard UI/IPC.': e.append('native_mislabel')
 if x['state']!='PLANNING_ONLY' or x['board_zone']!='gray': e.append('authority_escape')
 return sorted(set(e))
failures=validate(d); mutations=[]
cases=[('wrong original source',lambda x:x['trace'][0].update(source='docs/unrelated.feature:1'),'wrong_source'),('wrong BDD',lambda x:x['trace'][2].update(bdd='BDD-03'),'original_trace'),('wrong test',lambda x:x['tests'][0].update(name='t072_missing_root'),'wrong_test'),('unsupported row PASS',lambda x:x['trace'][0].update(verdict='PASS'),'unsupported_PASS'),('unsupported runtime PASS',lambda x:x['evidence_boundaries'].update(product_tests_this_run='PASS'),'unsupported_PASS'),('Win10 relabelled Win11',lambda x:x['evidence_boundaries'].update(windows='Windows11 native PASS'),'native_mislabel'),('unapproved implementation',lambda x:x.update(state='READY_FOR_AI_IMPLEMENTATION'),'authority_escape')]
fixtures=[]
for title,mutate,error in cases:
 x=copy.deepcopy(d); mutate(x); errors=validate(x); ok=error in errors
 mutations.append({'case':title,'expected_error':error,'observed_errors':errors,'detected':ok})
 fixtures.append({'name':title,'mutated_trace':x,'expected_error':error})
 if not ok: failures.append(title)
save('negative-fixtures.json',fixtures)
inv_path=R/d['inventory_authority']; inv=read(inv_path); inventory=inv['source_hashes']
drift=[p for p,h in inventory.items() if not (R/p).is_file() or sha(R/p)!=h]
if len(inventory)!=796 or drift: failures.append('product_inventory')
inputs={p:{'expected':h,'actual':sha(R/p),'match':sha(R/p)==h} for p,h in d['sources'].items()}
nonboard=[p for p,v in inputs.items() if not v['match'] and p!='docs/board.json']
failures.extend(nonboard)
seal=read(P/'seal.json'); seal_checks={n:sha(P/n)==h for n,h in seal['files'].items()}
if not all(seal_checks.values()): failures.append('preparation_seal')
page=(P/'index.html').read_text(encoding='utf-8'); embedded=json.loads(re.search(r'<script type="application/json" id="feature-trace">(.*?)</script>',page,re.S).group(1))
if embedded!=d: failures.append('author_embedded_data')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
if head!='5b709343a890503ebbe24a802e43cda5647df124': failures.append('unexpected_HEAD')
save('source-hashes.json',{'actual_head':head,'historical_inventory_head':inv['head'],'inventory_authority':d['inventory_authority'],'inventory_authority_sha256':sha(inv_path),'product_count':len(inventory),'product_drift':drift,'input_bindings':inputs,'board_management_drift_separate':not inputs['docs/board.json']['match'],'author_seal_checks':seal_checks,'review_inputs':{str(p.relative_to(R)).replace('\\','/'):sha(p) for p in [R/'AGENTS.md',R/'docs/requirements-confirmation/phase1-spec/tasks/yellow-dispatch-gates-20261103/audit.json',P/'trace.json',P/'seal.json']}})
result={'reviewer':'/root/f01_feature_trace_review','author':'/root/f01_feature_trace_packet','verdict':'PASS_PREPARATION_TRACE_REVIEW_ONLY' if not failures else 'CHANGES_REQUIRED','failures':failures,'counts':{'feature':1,'original_BDD':2,'AC01_rows':3,'existing_test_pointers':14,'planned_recipes':2,'new_negative_mutations':len(cases),'mutations_detected':sum(v['detected'] for v in mutations),'product_hashes':len(inventory),'product_drift':len(drift)},'mutations':mutations,'scope':'Document review only; no Feature PASS or module PASS. Gray retained.','NOT_RUN':['product tests','build','native Windows11','valid RED','full Draft UI/IPC','module acceptance'],'next_gates':d['pending_gates'],'planned_commands_NOT_RUN':d['next_actions'],'semantic_review':{'six_steps':'t001_* only codecs six saved-step variants using roundtrip exact decoded object, deterministic encoding, untouched input; no actual wizard navigation.','blocked_generation':'t002 asserts missing_generation_requirements nonempty while codec roundtrip accepts Draft. t061 tests preference skip preservation, only supporting save scope, not generation UI.','conflict':'t057 file/t058 empty/t059 protected bytes reject ExistingTarget and compare fake trees; t060 permits externally raced root creation then compares expected tree, not byte-identical nonexistent root.','open':'t070 Saved view/read-only tree equality; t072_read_denied error and unchanged tree are supporting lifecycle/error evidence, not wizard.','recipes':'PLAN-01 covers original AC01 a/b and BDD-01; PLAN-02 covers AC01 c/BDD-02 with exact inventory/three choices. Both planned only. X01 other invalid-name/path/double-click cases remain module regression obligations, not newly claimed covered by these 2 recipes.','authority':'S2 PASS_IMPLEMENTED_SCOPE_ONLY historical 2026-11-01, same assistant separate phase. S3 exact D1-D8 PENDING_OWNER; latest M01 copy-ready correction and CX remain document proposals. No new Skeleton/test source authorized.','native':'Historical verification explicitly Windows10 build19045, not Windows11 acceptance.'}}
save('review.json',result)
payload=json.dumps(result,ensure_ascii=False).replace('</','<\\/')
body='<h1>F01 獨立追溯文件審查</h1><p>'+html.escape(result['verdict'])+'</p><p>原始 1 Feature / 2 BDD / AC01 三列 / 14 現有測試指標 / 2 計畫配方。Gray 保留；未批准 Skeleton 或實作。</p>'
for title,val in [('審查結論與證據邊界',result),('來源與 hash',read(O/'source-hashes.json'))]: body+='<section><h2>'+title+'</h2><pre>'+html.escape(json.dumps(val,ensure_ascii=False,indent=2))+'</pre></section>'
(O/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>F01 independent trace review</title><style>body{font:16px/1.6 system-ui;max-width:1100px;margin:40px auto;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere}section{border-top:1px solid #aaa}</style>'+body+'<script type="application/json" id="review-spec">'+payload+'</script></html>',encoding='utf-8')
check_embedded=json.loads(re.search(r'id="review-spec">(.*?)</script>',(O/'index.html').read_text(encoding='utf-8'),re.S).group(1))
assert check_embedded==result
save('seal.json',{'scope':'independent F01 preparation review only','files':{p.name:sha(p) for p in sorted(O.iterdir()) if p.is_file() and p.name!='seal.json'}})
print(json.dumps({'verdict':result['verdict'],'counts':result['counts'],'failures':failures},ensure_ascii=False))
raise SystemExit(bool(failures))
