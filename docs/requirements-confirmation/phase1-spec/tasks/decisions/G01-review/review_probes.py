import json, pathlib, hashlib, copy, subprocess, datetime, collections, html, functools
ROOT=pathlib.Path.cwd(); OUT=ROOT/'docs/requirements-confirmation/phase1-spec/tasks/decisions/G01-review'; P=OUT.parent/'G01'
def load(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'))
@functools.lru_cache(maxsize=None)
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
cache={}
def resolve(s):
 p=s['path'];
 if p not in cache: cache[p]=load(ROOT/p)
 v=cache[p]
 for t in s.get('pointer','').split('/')[1:]:
  t=t.replace('~1','/').replace('~0','~'); v=v[int(t)] if isinstance(v,list) else v[t]
 return v
d=load(P/'decision-request.json'); e=load(P/'approved-envelope-proposal.json'); f=load(P/'failure-matrix.json'); sources=load(P/'source-hashes.json'); seal=load(P/'seal.json'); checks=[]
def check(n,b,detail=None): checks.append(dict(name=n,passed=bool(b),detail=detail))
check('Five sealed payload bytes intact',all(sha(P/k)==v for k,v in seal['files'].items()))
drift=[p for p,h in sources['sources'].items() if not (ROOT/p).exists() or sha(ROOT/p)!=h];check('311 current source bindings except classified management board',len(sources['sources'])==311 and drift==['docs/board.json'],drift)
inv=load(ROOT/sources['inventory_authority']['path']); pd=[p for p,h in inv['source_hashes'].items() if not (ROOT/p).exists() or sha(ROOT/p)!=h];check('796 authority product bytes unchanged',len(inv['source_hashes'])==796 and not pd,pd)
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();check('Live versus historical HEAD explicit',head==sources['head']=='5b709343a890503ebbe24a802e43cda5647df124' and inv['head']==sources['historical_inventory_head'])
bad=[]; refs=0
def walk(v):
 global refs
 if isinstance(v,dict):
  if 'path' in v and 'sha256' in v:
   refs+=1
   try:
    if sha(ROOT/v['path'])!=v['sha256']:bad.append(v)
    if v.get('pointer'):resolve(v)
   except Exception as ex:bad.append(dict(reference=v,error=str(ex)))
  if isinstance(v.get('source'),dict) and 'path' in v['source']:
   for key in ['existing_proposal_verbatim','verbatim','value']:
    if key in v and resolve(v['source'])!=v[key]:bad.append(dict(reason='projection differs',source=v['source'],key=key))
  for x in v.values():walk(x)
 elif isinstance(v,list):
  for x in v:walk(x)
for x in [d,e,f]:walk(x)
check('All source pointers and semantic projection equality',not bad,dict(references=refs,mismatches=bad[:12]))
rowbad=[]
for r in f['cases']:
 src=resolve(r['source'])
 if r['expected_outcome_verbatim']!=src.get('expected'):rowbad.append(r['case_id'])
 if r['pre_state_or_injection'] != {'status':'OPEN'} and any(k not in src or src[k]!=v for k,v in r['pre_state_or_injection'].items()):rowbad.append(r['case_id']+':pre')
check('3595 source-addressed outcomes; supplied inputs exact or explicitly OPEN; no native coverage promotion',len(f['cases'])==3595 and not rowbad and all(r['evidence_layer']=='EXISTING_DOCUMENT_FIXTURE_NOT_PRODUCT_PROOF' for r in f['cases']),rowbad[:15])
def guard(d,e,f):
 return len(d['intent_items'])==10 and len(d['module_candidates'])==7 and len(d['feature_traceability'])==12 and d['approval'] is None and all(i['owner_selection'] is None and i['approval'] is None for i in d['intent_items']) and all(m['exact_adopted_product_file_list']=='OPEN' and m['approved_skeleton'] is None and m['valid_RED']=='NOT RUN' for m in e['module_envelopes']) and all(x['resolution'] is None for x in d['cross_decision_dependencies']) and f['full_runtime_failure_model'].startswith('OPEN')
check('Owner choices, format/failure model, G02-04 and implementation gates remain open',guard(d,e,f))
probes=[]
for name,mut in [('preselected_owner',lambda a,b,c:a['intent_items'][0].update(owner_selection='adopt')),('approved_file_envelope',lambda a,b,c:b['module_envelopes'][0].update(exact_adopted_product_file_list=['src/new.rs'])),('invented_RED',lambda a,b,c:b['module_envelopes'][0].update(valid_RED='GREEN')),('resolved_G02',lambda a,b,c:a['cross_decision_dependencies'][0].update(resolution='G01 wins')),('native_failure_promotion',lambda a,b,c:c.update(full_runtime_failure_model='NATIVE_PROVEN')),('lost_identity_requirement',lambda a,b,c:a['intent_items'].pop())]:
 a,b,c=map(copy.deepcopy,[d,e,f]);mut(a,b,c);probes.append(dict(name=name,rejected=not guard(a,b,c),layer='in-memory reviewer semantic negative probe'))
check('Six new authority/semantic mutations rejected',all(x['rejected'] for x in probes),probes)
board=load(ROOT/'docs/board.json');card=next(x for x in board['items'] if x['id']==d['task']);check('Original red and legacy requirement retained',card['light']=='Red' and card['status']=='In Progress' and card['legacyTask']['zone']=='red' and 'ESS' in card['legacyTask']['note'])
results=dict(verdict='PASS_BOUNDED_DECISION_PROPOSAL_DOCUMENT' if all(x['passed'] for x in checks) else 'FAIL_DOCUMENT_REVIEW',reviewer='/root/g01_decision_submission_review',author=d['author'],generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks=checks,product_tests='NOT RUN',owner_adoption=None,source_creation_heartbeat=d['owner_heartbeat'],current_owner_heartbeat_context='2026-11-03T12:27:04.821Z supplied by coordinator; distinct from candidate creation timestamp',board_drift=dict(source_sha=sources['sources']['docs/board.json'],current_sha=sha(ROOT/'docs/board.json'),classification='MANAGEMENT_NOTE_TIMESTAMP_DRIFT',visible_delta='G01 coordinator preparation note at 20:21:22.310964+08:00 plus G01/root updatedAt; original red/status/legacy retained',limitation='No original board byte snapshot available; only-append delta not independently reconstructed. Coordinator assertion is not byte proof.'))
for n,v in [('results.json',results),('probes.json',probes)]: (OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2)[:10000])



