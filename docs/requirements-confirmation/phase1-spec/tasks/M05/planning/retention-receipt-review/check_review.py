from pathlib import Path
import copy,hashlib,importlib.util,json,re,subprocess
P=Path(__file__).resolve().parent
R=next(p for p in P.parents if (p/'.git').exists())
T=R/'docs/requirements-confirmation/phase1-spec/tasks'
A=P.parent/'retention-receipt-handoff'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
schema=read(T/'integration-contract-revision-v3/transition-request.schema.json')
role_index=next(i for i,s in enumerate(schema['oneOf']) if s['properties']['role']['enum']==['transfer-formal'])
role=schema['oneOf'][role_index]
f=read(A/'catalog-fixture.json'); base=f['request_body']
# Deliberately bounded interpreter for schema keywords used by this request only; not a Draft validator.
def valid(v,s):
 if '$ref' in s:
  q=schema
  for k in s['$ref'][2:].split('/'):q=q[k]
  return valid(v,q)
 if 'enum' in s and v not in s['enum']:return False
 t=s.get('type')
 if t=='object':
  return isinstance(v,dict) and set(s.get('required',[]))<=set(v) and (s.get('additionalProperties') is not False or set(v)<=set(s.get('properties',{}))) and all(valid(x,s['properties'][k]) for k,x in v.items() if k in s.get('properties',{}))
 if t=='array':return isinstance(v,list) and len(v)>=s.get('minItems',0) and all(valid(x,s['items']) for x in v)
 if t=='string':
  return isinstance(v,str) and len(v)>=s.get('minLength',0) and len(v)<=s.get('maxLength',10**9) and ('pattern' not in s or re.fullmatch(s['pattern'],v) is not None) and not any(0xD800<=ord(x)<=0xDFFF for x in v)
 return True
assert valid(base,role)
assert digest(base)==f['request_digest']
assert read(P.parent/'cx-revision-v3/shared-contract.json')==read(T/'integration-contract-revision-v3/shared-contract.json')
trace=[]
def record(name,inp,result,expected,calls=None):
 assert result==expected,(name,result,expected)
 trace.append({'id':name,'input':inp,'result':result,'expected':expected,'calls':calls or {'cas':0,'release':0,'ack':0,'retry':0}})
def leaves(v,path=()):
 if isinstance(v,dict):
  for k,x in v.items():yield from leaves(x,path+(k,))
 elif isinstance(v,list):
  for i,x in enumerate(v):yield from leaves(x,path+(i,))
 else:yield path,v
def setpath(v,path,x):
 for k in path[:-1]:v=v[k]
 v[path[-1]]=x
# Every scalar input participates in the accepted recursive hash; changed valid bodies conflict.
for path,value in leaves(base):
 b=copy.deepcopy(base)
 if value in ('SGA-TRANSITION-v2','transfer-formal','Complete','LiveDocuments','FormalFile'):replacement='invalid-enum'
 elif value.isdecimal():replacement=str(int(value)+1)
 elif re.fullmatch('[0-9a-f]{64}',value):replacement=('0' if value[0]!='0' else '1')+value[1:]
 else:replacement=value+'x'
 setpath(b,path,replacement)
 result='ReplayConflict' if valid(b,role) else 'InvalidRequest'
 record('scalar-'+('/'.join(map(str,path))),{'request':b,'key':f['transition_key']},result,result)
 assert digest(b)!=f['request_digest']
# Each object is closed and required fields cannot be absent/null, at every admitted depth.
def objects(v,path=()):
 if isinstance(v,dict):
  yield path,v
  for k,x in v.items():yield from objects(x,path+(k,))
 elif isinstance(v,list):
  for i,x in enumerate(v):yield from objects(x,path+(i,))
for path,obj in objects(base):
 for key in list(obj)+['__unknown__']:
  for mode in (['missing','null'] if key!='__unknown__' else ['extra']):
   b=copy.deepcopy(base);q=b
   for k in path:q=q[k]
   if mode=='missing':del q[key]
   else:q[key]=None
   record('closed-'+str(path)+'/'+key+'/'+mode,{'request':b},'InvalidRequest' if not valid(b,role) else 'ACCEPTED','InvalidRequest')
for key in ('owner_generation','captured_revision'):
 for val in ('','01','-1','18446744073709551616',1,None):
  b=copy.deepcopy(base);b['context'][key]=val
  ok=valid(b,role) and isinstance(val,str) and val.isdecimal() and int(val)<=2**64-1
  record('u64-'+key+'-'+repr(val),{'request':b},'ACCEPTED' if ok else 'InvalidRequest','InvalidRequest')
b=copy.deepcopy(base);b['body']['root_manifest']['assets'].reverse()
record('array-order',{'request':b},'ReplayConflict' if digest(b)!=f['request_digest'] else 'SameReceipt','ReplayConflict')
record('same-key-same-body',{'key':f['transition_key'],'request':base,'retained_receipt':f['receipt_record']},'SameReceipt','SameReceipt')
# Separate immutable issuer binding and stored result inspection: observations are supplied premises.
def binding(x):
 p=x['before']['pin'];r=x['receipt_record'];b=x['request_body'];body=b['body'];a=x['after']
 return p['purpose']=='Save' and p['state']=='Held' and p['pin_id']==body['pin_id']==r['pin_id'] and p['context']==b['context']==r['context'] and p['versions']==r['asset_pairs']==[{k:y[k] for k in ('asset_id','digest')} for y in body['root_manifest']['assets']] and r['issuer']==x['transition_key'][0]=='M05' and r['store_identity']==x['transition_key'][1] and r['workflow_id']==x['transition_key'][2]==b['context']['workflow_id'] and r['operation_id']==x['transition_key'][3] and r['role']==b['role'] and r['ordinal']==b['ordinal'] and r['request_digest']==digest(b) and r['expected_generation']==x['before']['generation']==body['expected_catalog_generation'] and int(r['committed_generation'])==int(r['expected_generation'])+1 and a['generation']==r['committed_generation'] and a['pin']==dict(p,state='Transferred') and a['root_manifests']==r['root_manifest_ids']==[body['root_manifest']['manifest_id']] and a['transition_receipts']==[r] and r['external_proof']['issuer']==body['external_proof']['issuer'] and r['external_proof']['receipt_id']==body['external_proof']['receipt_id'] and r['external_proof']['context_digest']==body['external_proof']['context_digest'] and r['external_proof']['raw_digest']==x['file_receipt']['committed_digest']
def safe_binding(x):
 try:return binding(x)
 except (ValueError,TypeError,KeyError):return False
assert binding(f)
for path,value in list(leaves(f['receipt_record']))+[(('purpose',),'Save')]:
 x=copy.deepcopy(f)
 if path==('purpose',):x['before']['pin']['purpose']='Import'
 else:setpath(x['receipt_record'],path,str(value)+'changed')
 record('issuer-binding-'+str(path),x,'ProofMismatch' if not safe_binding(x) else 'ACCEPTED','ProofMismatch')
for observation,result,cas in [('verified','Transferred',1),('preCAS-failure','Held',0),('uncertain-CAS','Indeterminate',0),('postCAS-proofloss','Indeterminate',0),('restart-missing','UnverifiedOutcome',0),('restart-verified','SameReceipt',0)]:
 record('classification-'+observation,{'before':f['before'],'candidate_after':f['after'],'observation':observation,'premise':'verified issuer/CAS supplied; absent proof cannot establish old state'},result,result,{'cas':cas,'release':0,'ack':0,'retry':0})
# Demonstrate the source classifier is not a production input validator.
sp=importlib.util.spec_from_file_location('author_model',A/'model.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
x=copy.deepcopy(f);x['before']['pin']['purpose']='Import';x['receipt_record']['issuer']='UNTRUSTED'
got=m.evaluate(x,{'case':'independent-binding-counterexample','observation':'verified'})
record('source-classifier-boundary',{'fixture':x,'case':{'case':'independent-binding-counterexample','observation':'verified'}},got['outcome'],'Transferred',{'simulated_new_cas':got['new_cas'],'actual_cas':0,'release':0,'ack':0,'retry':0})
auth=read(T/'M01/planning/s2-green/source-current.json');assert len(auth['source_hashes'])==796
assert all(sha(R/n)==h for n,h in auth['source_hashes'].items())
inputs=read(A/'inputs.json');drift=[n for n,h in inputs.items() if sha(R/n)!=h]
assert set(drift)<= {'docs/board.json'},drift
seal=read(A/'seal.json');assert all(sha(A/n)==h for n,h in seal['files'].items())
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();assert head=='5b709343a890503ebbe24a802e43cda5647df124'
changed=subprocess.check_output(['git','diff','--name-only',auth['head'],head],cwd=R,text=True).splitlines()
review={'id':'M05-RETENTION-RECEIPT-INDEPENDENT-REVIEW','author':'/root/m05_retention_receipt_handoff','reviewer':'/root/m05_receipt_handoff_review','verdict':'PASS_DOCUMENT_ONLY_PENDING_OWNER','scope':'One Held Save pin → formal root candidate transition; new independent document probes, not source 18+3 rerun','new_independent_probes':len(trace),'passed':len(trace),'findings':[], 'mapping_verification':'NOT_PROVEN: tuple-map is a candidate prose correspondence, not executable source verification. Independent predicate tests only the supplied fixture relationships; it does not repair or validate the author classifier.', 'probe_layers':{'request_shape_and_hash':'independent bounded predicates on accepted source schema and actual full request bytes','issuer_tuple_mutations':'independent candidate invariant predicate only; author classifier mapping NOT_PROVEN','outcome_classifications':'reviewed documentary expectations under supplied labels, no executable CAS or restart verification','source_boundary_counterexample':'actual author model invocation on altered fixture'}, 'owner_choices':read(A/'owner-choices.json'),'exact_source_pointer':'integration-contract-revision-v3/transition-request.schema.json#/oneOf/'+str(role_index),'limits':['Source model dispatches supplied observation labels, not input validation or issuer authentication; explicit malformed binding counterexample reaches Transferred. Thus its new_cas is a simulated counter only, not a real mutation. Independent predicates express bounded candidate invariants, not approved runtime seams.','CAS/issuer lookup/fences/inclusion and immutable request capture are premises; no durability, native provider, isolation, or file/catalog/ACK atomicity proved.','Unknown CAS or post-CAS proof loss cannot prove old Held state unchanged; no automatic retry/release/ACK, exactly-once or restart durability claim.','H1-H4 are pending handoff/issuer/output/reconciliation decisions, no approved SPEC_CONFLICT; full recursive accepted v3 hash body is not reopened.','Source pointers contain human descriptors/grouped references; exact schema pointer recorded here. Validator is bounded to this fixture schema keyword subset plus checked u64; full Draft NOT RUN.'],'checkout':{'head':head,'authority_head':auth['head'],'authority_files':796,'product_drift':[],'input_drift_excluding_board':[],'board_management_drift':drift,'board_sha256':sha(R/'docs/board.json'),'authority_to_head_names':changed,'author_sealed_files':len(seal['files'])},'not_run':['native/provider/real CAS/restart','product tests','build/package/install','valid RED/GREEN','full Draft2020-12'],'module_complete':False,'next_action':'Owner decides H1-H4; revalidate exact architecture/contracts/BDD/Skeleton and compile-valid intended RED. Parent Yellow remains unchanged; no implementation authorization.'}
put('fixtures.json',{'base_fixture':f,'probe_count':len(trace),'generation':'independent recursive scalar/closure/u64/order/binding/classification probes'})
put('trace.json',trace);put('review.json',review)
input_paths=list(A.iterdir())+[R/'AGENTS.md',R/'docs/board.json',T/'M05/planning/current-state.json',T/'M05/planning/cx-revision-v3/shared-contract.json',T/'integration-contract-revision-v3/shared-contract.json',T/'integration-contract-revision-v3/transition-request.schema.json',T/'M04/planning/save-retention-observation-review/review.json',T/'M01/planning/s2-green/source-current.json']
put('inputs.json',{str(p.relative_to(R)).replace('\\','/'):sha(p) for p in input_paths if p.is_file()})
put('verification.json',{'status':review['verdict'],'passed':len(trace),'failed':0,'product_hashes_verified':796,'source_seal_verified':len(seal['files'])})
html='<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>M05 Independent Review</title><style>body{font:16px system-ui;max-width:1100px;margin:3em auto;padding:1em;color:#182b3b}pre{white-space:pre-wrap;background:#f2f5f8;padding:1em}h1{color:#765600}</style><h1>M05 retention receipt — independent document review</h1><p>PASS_DOCUMENT_ONLY_PENDING_OWNER · Parent Yellow · one transition only</p><p>Author /root/m05_retention_receipt_handoff; reviewer /root/m05_receipt_handoff_review. '+str(len(trace))+' new independent bounded probes PASS; 796 product hashes unchanged. No product acceptance.</p><h2>Meaning and boundary</h2><p>M05 alone owns Held pin, catalog root and transition receipt. M04 supplies observations and owns semantic ACK. File commit, catalog CAS and ACK are separate. All issuer/CAS observations are premises.</p><h2>Architecture / request</h2><p>M04 capture → M05 input → MaterialOwner → output abstractions → IO. Accepted closed SGA-TRANSITION-v2 request and recursive hash retained. Exact pointer: '+review['exact_source_pointer']+'</p><h2>Review, owner decisions and limits</h2><pre>'+json.dumps(review,ensure_ascii=False,indent=2).replace('&','&amp;').replace('<','&lt;')+'</pre><p>Full probe inputs/results/counters: <a href="trace.json">trace.json</a>. No automatic release, retry or ACK. Unknown does not prove unchanged prior state.</p><script type="application/json" id="module-spec">'+json.dumps(review,ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
(P/'index.html').write_text(html,encoding='utf-8')
print('PASS',len(trace),'new independent probes; 796 authority hashes; author seal',len(seal['files']))

