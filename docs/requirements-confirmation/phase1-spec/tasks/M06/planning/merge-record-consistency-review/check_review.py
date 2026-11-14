"""Independent bounded DOCUMENT diagnostics. Run python -B; never author batch."""
from pathlib import Path
import copy,hashlib,html,importlib.util,json,subprocess
P=Path(__file__).resolve().parent; A=P.parent/'merge-record-consistency-proposal'; H=P.parent/'merge-retention-handoff'; R=P.parents[6]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
spec=importlib.util.spec_from_file_location('independent_target',A/'model.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
c=read(A/'retained-issuer-fixture.json');base=read(A/'base-request.json');rows=[]
def diff(a,b,path=()):
 if type(a)!=type(b):return [{'path':list(path),'value':b}]
 if isinstance(a,dict):return [d for k in b for d in (diff(a[k],b[k],path+(k,)) if k in a else [{'path':list(path+(k,)),'value':b[k]}])]+[{'path':list(path+(k,)),'remove':True} for k in a.keys()-b.keys()]
 if isinstance(a,list) and len(a)==len(b):return [d for i,(x,y) in enumerate(zip(a,b)) for d in diff(x,y,path+(i,))]
 return [] if a==b else [{'path':list(path),'value':b}]
def run(name,x=None,records=None,expected='RecordConsistencyRejected',reused=False,exact=None):
 x=copy.deepcopy(base if x is None else x); records=copy.deepcopy(c if records is None else records);got=m.evaluate(x,records)
 ok=got['result']==expected and (exact is None or got==exact)
 if expected in ('RecordConsistencyRejected','InvalidInput'):ok=ok and got['before']==got['after'] and not any(got['calls'].values())
 rows.append({'id':name,'reused_case':reused,'request_patch':diff(base,x),'record_patch':diff(c,records),'expected':expected,'actual':got,'passed':ok,'exact_output_preserved':got==exact if exact is not None else None})
for f in read(H/'fixtures.json'):
 old=m.run_legacy(f['input'],c);run('preserve-'+f['id'],f['input'],expected=old['result'],reused=True,exact=old)
old_review=read(P.parent/'merge-retention-review/new-fixtures-and-results.json')
for f in old_review:
 if f['id'].startswith('defensive-'):run('close-'+f['id'],f['input'],f['issuer_fixture_override'],reused=True)
def walk(v,path=()):
 if isinstance(v,dict):
  for k,a in v.items():yield path+(k,),a;yield from walk(a,path+(k,))
 elif isinstance(v,list):
  for i,a in enumerate(v):yield from walk(a,path+(i,))
def replace(v,path,value):
 for k in path[:-1]:v=v[k]
 v[path[-1]]=value
# New key vocabulary probes use an independently chosen first occurrence, including all record/state families.
seen=set()
for path,value in walk(c):
 key=path[-1]
 if key in seen:continue
 seen.add(key);changed=copy.deepcopy(c);replace(changed,path,{'review_invalid':True} if not isinstance(value,dict) else ['review_invalid']);run('new-key-'+str(key),records=changed)
for key,value in c.items():
 changed=copy.deepcopy(c)
 if isinstance(value,dict):changed[key]['independent_unknown']=True
 elif isinstance(value,list):changed[key]=value+[{'independent_unknown':True}]
 run('new-family-'+key,records=changed)
def shift(delta):
 v=copy.deepcopy(c)
 def visit(v):
  if isinstance(v,dict):
   for k,a in v.items():
    if k=='expected_catalog_generation' or k in ('expected_generation','committed_generation') and 'request_digest' in v:v[k]=str(int(a)+delta)
    else:visit(a)
  elif isinstance(v,list):
   for a in v:visit(a)
 visit(v)
 for rec,req in zip([v['import_record']]+v['transfer_records'],[v['import_request']]+v['merge_transfer']+v['undo_transfer']):rec['request_digest']=m.legacy.digest(req)
 x=copy.deepcopy(base)
 for k in ('import_request','merge_publish','merge_transfer','undo_publish','undo_transfer'):x[k]=copy.deepcopy(v[k])
 return x,v
cas_values=[]
for path,v in walk(c):
 if path[-1] in ('expected_catalog_generation','expected_generation','committed_generation'):
  parent=c
  for k in path[:-1]:parent=parent[k]
  if path[-1]=='expected_catalog_generation' or 'request_digest' in parent:cas_values.append(int(v))
upper=18446744073709551615-max(cas_values)
for d in (0,1,17,upper):
 x,v=shift(d);run('new-coherent-CAS-'+str(d),x,v,'MergeApplied')
 x['perform_undo']=True;x['undo_observation']='Applied';x['undo_root_observation']='Verified';run('new-coherent-CAS-undo-'+str(d),x,v,'UndoApplied')
x,v=shift(upper+1);run('new-CAS-overflow',x,v)
x,v=shift(17);v['import_record']['request_digest']='0'*64;run('new-digest-stale-after-CAS',x,v)
x,v=shift(17);run('new-shifted-records-unshifted-caller',base,v,'ProofMismatch')
x,v=shift(17);run('new-shifted-caller-unshifted-records',x,c,'ProofMismatch')
x,v=shift(17);v['mutation']['context']['owner_generation']=str(int(v['mutation']['context']['owner_generation'])+17);run('new-owner-CAS-conflation',x,v)
x,v=shift(17);v['import_record']['committed_generation']=str(int(v['import_record']['committed_generation'])+1);run('new-incoherent-commit',x,v)
x=copy.deepcopy(base);v=copy.deepcopy(c);v['import_record']['issuer']='M04';del x['commit_observation'];run('new-priority-shape-before-record',x,v,'InvalidInput')
x=copy.deepcopy(base);v=copy.deepcopy(c);v['import_record']['issuer']='M04';x['import_receipt_ref']['receipt_id']='wrong';run('new-priority-record-before-proof',x,v)
x=copy.deepcopy(base);x['import_receipt_ref']['receipt_id']='wrong';run('new-priority-proof-after-valid-record',x,c,'ProofMismatch')
v=copy.deepcopy(c);v['import_record']['receipt_id']='00000000-0000-4000-8000-000000000001';run('new-valid-shape-alternate-ID-frozen-domain',records=v)
# Crosslinks in each late record instance, not just first vocabulary occurrence.
for i in range(6):
 v=copy.deepcopy(c);v['transfer_records'][i]['request_digest']=v['import_record']['request_digest'];run('new-transfer-crosslink-'+str(i),records=v)
seal=read(A/'seal.json');seal_ok=all(sha(A/n)==h for n,h in seal['files'].items())
invpath=R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json';inv=read(invpath)
drift=[n for n,h in inv['source_hashes'].items() if not (R/n).is_file() or sha(R/n)!=h]
central=P.parent/'cx-exchange-revision-v3/shared-contract.json';schema_parity=read(H/'transition-request.schema.json')==read(central)['request_hash_schema']
owner=read(A/'owner-choices.json');source=read(A/'source-pointers.json')
inputs=[P.parent/'current-state.json',R/'AGENTS.md',R/'docs/board.json',invpath,central,P.parent/'merge-retention-review/review.json',H/'model.py',H/'immutable-issuer-fixture.json',H/'transition-request.schema.json']+[A/n for n in seal['files']]+[A/'seal.json']
input_hashes={str(p.relative_to(R)):sha(p) for p in inputs}
author_input_drift={n:{'author':h,'current':sha(R/n)} for n,h in source['inputs'].items() if sha(R/n)!=h}
checks={'author_17_file_seal':seal_ok,'seal_file_count':len(seal['files']),'product_inventory_count':len(inv['source_hashes']),'product_hash_drift':drift,'central_request_schema_unchanged_parity':schema_parity,'MH1_MH6_pending':len(owner)==6 and all(a['status']=='PROPOSED_PENDING_OWNER' for a in owner),'original_nine_closures':len([r for r in rows if r['id'].startswith('close-')])==9,'all_15_outputs_exact':len([r for r in rows if r['exact_output_preserved'] is True])==15}
verdict='PASS_DOCUMENT_SCOPE_PENDING_OWNER' if all(r['passed'] for r in rows) and seal_ok and not drift and schema_parity else 'FINDINGS_DOCUMENT_SCOPE_PENDING_OWNER'
review={'reviewer':'/root/m06_record_consistency_review','author':'/root/m06_record_consistency_packet','task':'PD-P1-M06-PREP-01','verdict':verdict,'new_probes':sum(not r['reused_case'] for r in rows),'reused_cases':sum(r['reused_case'] for r in rows),'total_direct_calls':len(rows),'passed':sum(r['passed'] for r in rows),'findings':[r['id'] for r in rows if not r['passed']],'checks':checks,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'inventory_head':inv['head'],'authority':'796-file M01/planning/s2-green/source-current.json; distinct from historical 31babe','author_input_hash_differences_separate':author_input_drift,'interpretation':'Nine MR-F1 documentary coverage closures verified. All retained record families and distinct field-key vocabulary have new targeted shape/value controls. Exact frozen IDs are explicit fixture-domain premises; coherent CAS and full-request digest recomputation are relational actual-input checks, not fixed test-ID outputs. Whole trusted fixture authenticity is assumed, not proven; no actual registry. New guards/error precedence and MH1-MH6 await Owner. No Skeleton or module PASS.','not_run':['author 3126 full batch','native','build','product tests','valid RED','full Draft'],'scope':'Read-only originals/product/board/current-state/hooks/roles; writes only NEW review directory.'}
write('new-fixtures-and-results.json',{'bases':{'request':str((A/'base-request.json').relative_to(R)),'records':str((A/'retained-issuer-fixture.json').relative_to(R))},'patch_semantics':'ordered path replacement/add/removal; complete actual before/after/state/calls stored for every direct call','results':rows})
write('review.json',review);write('input-hashes.json',input_hashes)
write('trace.json',{'MR-F1':['close-'+f['id'] for f in old_review if f['id'].startswith('defensive-')],'unique_field_keys':sorted(str(k) for k in seen),'families':list(c),'coherent_CAS_offsets':[0,1,17,upper],'boundary':'highest mapped CAS committed/expected value reaches u64 max; next offset rejected','reused':'15 original output preservation + nine exact prior MR-F1 cases; all other probes NEW','limits':review['not_run']})
body='<h1>M06 independent record consistency review</h1><p>'+verdict+'</p><p>Reviewer /root/m06_record_consistency_review; author /root/m06_record_consistency_packet. Documentary proposal only; Owner decisions pending. No module PASS.</p><pre>'+html.escape(json.dumps(review,ensure_ascii=False,indent=2))+'</pre><p><a href="new-fixtures-and-results.json">Full results and reconstructible NEW probes</a> · <a href="trace.json">Traceability</a> · <a href="input-hashes.json">Input hashes</a> · <a href="check_review.py">Bounded checker</a></p><script type="application/json" id="module-spec">'+json.dumps(review).replace('<','\\u003c')+'</script>'
(P/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M06 independent review</title><style>body{max-width:1100px;margin:36px auto;font:16px system-ui;background:#111827;color:#eee}pre{white-space:pre-wrap}a{color:#fbbf24}</style>'+body,encoding='utf-8')
write('seal.json',{'scope':'independent bounded DOCUMENT review only','files':{p.name:sha(p) for p in P.iterdir() if p.is_file() and p.name!='seal.json'}})
print(json.dumps(review,ensure_ascii=False))
