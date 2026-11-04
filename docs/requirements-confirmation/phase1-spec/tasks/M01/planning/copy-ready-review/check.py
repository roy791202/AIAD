"""Independent document review; never invoke candidate main or production IO."""
import pathlib, json, hashlib, copy, importlib.util, subprocess, html
P=pathlib.Path(__file__).resolve().parent
C=P.parent/'copy-ready-handoff'
ROOT=P.parents[6]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf8'))
def write(n,v): (P/n).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
spec=importlib.util.spec_from_file_location('candidate',C/'check.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
base=read(C/'fixtures.json')[0]['fixture']
cases=[]
def probe(name,change,expected,reseal=True):
 f=copy.deepcopy(base); change(f)
 if reseal:
  f['request_digest']=m.digest(f['request'])
  f['issuer_records']['ready-1']['request_digest']=f['request_digest']
 try: actual=m.classify(f)
 except Exception as e: actual=type(e).__name__+': '+str(e)
 cases.append({'id':'IR-'+str(len(cases)+1).zfill(2),'name':name,'expected':expected,'actual':actual,'pass':actual==expected,'fixture':f,'state_calls':{'candidate_classifier':1,'document_mutation':0,'native_IO':0,'retry':0,'cleanup':0},'trace':'copy-ready-handoff/check.py:classify'})
for key in ['definition_raw','document_raw','catalog_generation','manifest_raw','source_snapshot_digest','native_lease_id']:
 probe('unbound '+key,lambda f,k=key:f['request']['body'].__setitem__(k,'unrelated-but-rehashed'),'ProofMismatch')
probe('unknown body field',lambda f:f['request']['body'].__setitem__('unexpected',True),'RejectedBeforeMutation')
probe('unknown protocol',lambda f:f['request'].__setitem__('protocol','UNRECOGNIZED'),'RejectedBeforeMutation')
probe('wrong request issuer',lambda f:f['request'].__setitem__('issuer','M06'),'RejectedBeforeMutation')
probe('ordinal does not match operation',lambda f:f['request'].__setitem__('ordinal','999'),'RejectedBeforeMutation')
probe('missing body field',lambda f:f['request']['body'].pop('document_raw'),'RejectedBeforeMutation')
probe('wrong boolean type owner',lambda f:f.__setitem__('owner_current','false'),'RejectedBeforeMutation')
probe('wrong boolean type ACK',lambda f:f.__setitem__('source_ack','false'),'RejectedBeforeMutation')
probe('unknown Ready receipt identity',lambda f:f['issuer_records']['ready-1'].__setitem__('receipt_id','different'),'ProofMismatch')
probe('native identity issuer mismatch',lambda f:f['issuer_records']['provider-1']['target_native_identity'].__setitem__('file_id','different'),'DependencyNotReady')
probe('catalog bytes mismatch',lambda f:f['issuer_records']['catalog-1'].__setitem__('catalog_index_raw','different'),'ProofMismatch')
probe('blob mismatch',lambda f:f['issuer_records']['copy-1'].__setitem__('blob_manifest_digest','different'),'ProofMismatch')
probe('material root mismatch',lambda f:f['issuer_records']['copy-1'].__setitem__('material_root_digest','different'),'ProofMismatch')
probe('request context mismatch',lambda f:f['request']['context'].__setitem__('session_id','different'),'ProofMismatch')
probe('Ready path mismatch',lambda f:f['issuer_records']['ready-1'].__setitem__('target_path','elsewhere'),'ProofMismatch')
probe('target already exists',lambda f:f.__setitem__('target_existing',True),'RejectedBeforeMutation')
probe('incomplete children',lambda f:f['issuer_records']['copy-1'].__setitem__('status','Incomplete'),'RejectedBeforeMutation')
probe('catalog unknown',lambda f:f['issuer_records']['catalog-1'].__setitem__('status','Unknown'),'DependencyNotReady')
probe('Ready CAS unknown',lambda f:f.__setitem__('ready_cas','Unknown'),'UncertainPublication')
probe('confirmed Ready owner loss',lambda f:f.__setitem__('owner_current',False),'DeliveryDeferred')
probe('confirmed Ready ACK deferred',lambda f:f.__setitem__('source_ack',False),'CommittedAckDeferred')
def moved_path(f):
 b=f['request']['body'];b['final_canonical_path']='C:\\elsewhere';b['marker_path']=b['final_canonical_path']+'\\.sgenaxis\\copy-state.v1.json';f['issuer_records']['ready-1']['target_path']=b['marker_path']
probe('unbound final path with matching Ready DTO',moved_path,'ProofMismatch')
def empty_native(f):
 f['request']['body']['target_native_identity']={}
 for name in ['provider-1','ready-1']:f['issuer_records'][name]['target_native_identity']={}
probe('empty native identity consistently echoed',empty_native,'RejectedBeforeMutation')
probe('missing required context field',lambda f:f['request']['context'].pop('workflow_id'),'RejectedBeforeMutation')
probe('unknown provider status enum',lambda f:f['issuer_records']['provider-1'].__setitem__('status','FutureStatus'),'RejectedBeforeMutation')
bindings=read(C/'source-bindings.json');seal=read(C/'seal.json');inventory=read(ROOT/bindings['authority_inventory'])
checks={label:{'count':len(mapping),'mismatches':[n for n,h in mapping.items() if sha(root/n)!=h]} for label,root,mapping in [('source_bindings',ROOT,bindings['source_hashes']),('candidate_seal',C,seal['artifacts']),('protected_inventory',ROOT,inventory['source_hashes'])]}
write('new-fixtures.json',cases)
report={'reviewer':'/root/m01_copy_ready_review','author':'/root/m01_copy_ready_handoff','task':'PD-P1-M01-PREP-01','verdict':'FINDINGS_DOCUMENT_REVIEW_ONLY','scope':'One final-path QuarantinedCopy to Ready transition only','head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'historical_inventory_head':inventory['head'],'checks':checks,'probes':len(cases),'passed':sum(c['pass'] for c in cases),'counterexamples':[{'id':c['id'],'name':c['name'],'expected':c['expected'],'actual':c['actual']} for c in cases if not c['pass']],'findings':[{'id':'F1','priority':'P2','issue':'Full request hashing does not establish semantic field consumption. Resealed changes to document/definition/manifest/source snapshot/catalog generation/native lease pass with unchanged issuer evidence. Provider records contain no lease/path or document bytes binding; catalog records contain no generation binding.','next':'Specify issuer-owned binding fields and compare them; do not treat checksum coverage as semantic verification.'},{'id':'F2','priority':'P2','issue':'No closed shape/type/enum guard before classifier consumption. Unknown fields/protocol/issuer/ordinal, absent document_raw, string booleans and mismatched Ready receipt identity can still report VerifiedPublished.','next':'Owner-confirm exact candidate closed types; add independent negative vectors before document mutation. These are document oracle defects, not production corruption evidence.'}],'publish_boundary':{'existing_required':['registration_id','provider_capability_id','expected_epoch','manifest','expected_catalog_generation'],'additionalProperties':False,'candidate_admitted':False,'owner_pending':['CR-D1','CR-D2','CR-D3']},'limits':['Issuer trust, held native lease and native atomicity are fixture premises, not runtime proof.','FileCommitReceipt has target_path/previous_digest/committed_digest/transaction_id, no native lease or Ready issuer. No staged rename or journal move authority.','State/deferred probes call pure classifier only: no modeled marker mutation, Ready state, no-replace IO, retry/cleanup or inherited approval is behaviorally proven.','Board management changes are separate from 796 product inventory; board source binding is checked separately.'],'verification':dict.fromkeys(['native','build','product','valid_RED','full_Draft'],'NOT RUN'),'module_pass':False,'next_action':'Author correct document oracle and issuer binding proposal in a new revision, independently re-review, then Owner decide exact CR-D1..D3; no Skeleton or implementation dispatch.'}
write('review.json',report)
write('management-diff.json',{'path':'docs/board.json','candidate_bound_sha256':bindings['source_hashes']['docs/board.json'],'observed_sha256':sha(ROOT/'docs/board.json'),'comparison':'Management input hash drift, separate from unchanged 796 product authority; no board writes by reviewer.','git_diff_stat':subprocess.check_output(['git','diff','--stat','--','docs/board.json'],cwd=ROOT,text=True).strip()})
(P/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M01 independent Copy Ready review</title><h1>M01 independent document review — findings</h1><p>Author and reviewer are distinct. Owner approval remains pending. No module PASS.</p><pre>'+html.escape(json.dumps(report,indent=2,ensure_ascii=False))+'</pre><script type="application/json" id="review-spec">'+json.dumps(report,ensure_ascii=False).replace('</','<\\/')+'</script>',encoding='utf8')
write('input-hashes.json',{'candidate':{p.name:sha(p) for p in C.iterdir() if p.is_file()},'authority':bindings['source_hashes']})
write('seal.json',{'reviewer':report['reviewer'],'verdict':report['verdict'],'scope':report['scope'],'probes':len(cases),'passes':report['passed'],'counterexamples':len(report['counterexamples']),'next_action':report['next_action'],'artifacts':{p.name:sha(p) for p in P.iterdir() if p.is_file() and p.name!='seal.json'}})
print(json.dumps({'probes':len(cases),'passed':report['passed'],'counterexamples':len(report['counterexamples']),'checks':checks},indent=2))
