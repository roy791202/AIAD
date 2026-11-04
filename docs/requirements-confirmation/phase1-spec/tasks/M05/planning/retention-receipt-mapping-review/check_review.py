"""Fresh independent bounded document probes; run python -B check_review.py."""
from pathlib import Path
import copy, hashlib, importlib.util, json, subprocess
P=Path(__file__).resolve().parent
R=P.parents[6]
A=P.parent/'retention-receipt-mapping-proposal'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v): (P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
s=importlib.util.spec_from_file_location('reviewed_document_model',A/'model.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
base=read(A/'fixtures.json')[0]['input']; catalog=read(A/'immutable-catalog.json')
probes=[]
def probe(name,x=None,c=None,result='ProofMismatch',cas=0,lookup=None):
 ix=copy.deepcopy(base if x is None else x);ic=copy.deepcopy(catalog if c is None else c)
 frozen=copy.deepcopy((ix,ic));actual=m.evaluate(ix,ic)
 ok=actual['result']==result and actual['calls']['cas']==cas and all(actual['calls'][k]==0 for k in ('release','retry','ack'))
 ok=ok and (ix,ic)==frozen
 if lookup is not None: ok=ok and actual['calls']['lookup']==lookup
 if cas==0 and result!='SameReceipt': ok=ok and actual['before']==actual['after']
 probes.append({'id':'IMR-%03d'%(len(probes)+1),'name':name,'expected':{'result':result,'cas':cas,'lookup':lookup},'input':base if x is None else x,'catalog_override':c,'actual':actual,'pass':ok})
def changed(path,value,obj):
 v=copy.deepcopy(obj); t=v
 for key in path[:-1]: t=t[key]
 t[path[-1]]=value;return v
probe('fresh admitted full request',result='Transferred',cas=1,lookup=2)
probe('same key same body verified replay',changed(['catalog_phase'],'Transferred',base),result='SameReceipt',lookup=2)
for path,value in [(['request','body','expected_catalog_generation'],'8'),(['request','body','root_manifest','epoch'],'8'),(['request','body','root_manifest','assets',0,'size_bytes'],'8'),(['request','context','captured_revision'],'11'),(['request','body','pin_id'],'e'*32),(['request','body','external_proof','evidence_digest'],'a'*64)]:
 x=changed(path,value,base);probe('full-body conflict '+'.'.join(map(str,path)),changed(['catalog_phase'],'Transferred',x),result='ReplayConflict',lookup=0)
 probe('held phase rejects changed frozen '+'.'.join(map(str,path)),x,lookup=2)
for field in base:
 x=copy.deepcopy(base);del x[field];probe('required top field '+field,x,result='InvalidInput',lookup=0)
for field in base['request']['body']:
 x=copy.deepcopy(base);del x['request']['body'][field];probe('required body field '+field,x,result='InvalidInput',lookup=0)
for path,value in [(['permission'],1),(['request'],[]),(['request','body'],None),(['catalog_phase'],'released'),(['transport'],'Retry'),(['held_ref'],[]),(['request','body','expected_catalog_generation'],True),(['request','body','expected_catalog_generation'],'18446744073709551616')]:
 probe('malformed before lookup '+'.'.join(path),changed(path,value,base),result='InvalidInput',lookup=0)
probe('closed top object',dict(base,success=True),result='InvalidInput',lookup=0)
x=copy.deepcopy(base);x['request']['body']['purpose']='Save';probe('no request purpose enrichment',x,result='InvalidInput',lookup=0)
probe('permission gate',changed(['permission'],False,base),result='PermissionDenied',lookup=0)
for path,value in [(['held_ref','issuer'],'attacker'),(['formal_ref','issuer'],'attacker'),(['held_ref','receipt_id'],'unknown'),(['formal_ref','receipt_id'],'unknown'),(['transition_key',1],'other')]:
 probe('admission fixture lookup '+'.'.join(map(str,path)),changed(path,value,base),lookup=2)
for path,value in [(['held_receipt','pin','purpose'],'Cleanup'),(['held_receipt','pin','state'],'Released'),(['held_receipt','issuer'],'attacker'),(['formal_receipt','proof','issuer'],'attacker'),(['held_receipt','pin','context','owner_generation'],'9'),(['held_receipt','pin','versions',0,'digest'],'a'*64),(['formal_receipt','root','assets',0,'size_bytes'],'9'),(['request_digest'],'a'*64),(['receipt','external_proof','raw_digest'],'a'*64),(['receipt','context','owner_generation'],'9'),(['receipt','source_receipt_ids',0,'issuer'],'attacker')]:
 probe('defensive catalog consistency (trusted fixture premise) '+'.'.join(map(str,path)),c=changed(path,value,catalog),lookup=2)
for field,value,result,cas in [('catalog_phase','Unknown','Indeterminate',0),('catalog_phase','RestartMissing','UnverifiedOutcome',0),('transport','FailureBeforeCAS','Held',0),('transport','UnknownCAS','Indeterminate',1),('transport','PostCASProofLoss','Indeterminate',1)]:
 probe('outcome policy '+value,changed([field],value,base),result=result,cas=cas,lookup=2)
for p in probes:
 if p['name'].endswith('PostCASProofLoss'): p['pass'] &= p['actual']['after']==catalog['after'] and 'no rollback' in p['actual']['state_claim']
 if p['name'].endswith('UnknownCAS'): p['pass'] &= 'last known snapshot' in p['actual']['state_claim']
inventory=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
source={k:{'expected':v,'actual':sha(R/k) if (R/k).is_file() else None} for k,v in inventory['source_hashes'].items()}
independent_digest=hashlib.sha256(json.dumps(base['request'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
assert independent_digest==catalog['request_digest'] and base['request']==catalog['frozen_request']
assert len(source)==796
sealed={k:sha(A/k)==v for k,v in read(A/'seal.json')['files'].items()}
inputs={str(p.relative_to(R)).replace('\\','/'):sha(p) for p in list(A.glob('*')) if p.is_file()}
for name in ['retention-receipt-review/review.json','cx-revision-v3/shared-contract.json','current-state.json']:
 p=P.parent/name;inputs[str(p.relative_to(R)).replace('\\','/')]=sha(p)
schema=R/'docs/requirements-confirmation/phase1-spec/tasks/integration-contract-revision-v3/transition-request.schema.json'
inputs[str(schema.relative_to(R)).replace('\\','/')]=sha(schema)
choices=read(A/'owner-choices.json')
assert [x['id'] for x in choices]==['H1','H2','H3','H4'] and all(x['status']=='PROPOSED_PENDING_OWNER' for x in choices)
assert read(schema)==read(A/'request.schema.json')
assert all(sealed.values()) and all(v['expected']==v['actual'] for v in source.values())
write('fixtures.json',probes);write('inputs.json',inputs);write('source-verification.json',source)
report={'reviewer':'/root/m05_receipt_mapping_review','author':'/root/m05_receipt_mapping_packet','verdict':'PASS_DOCUMENT_ONLY_PENDING_OWNER' if all(p['pass'] for p in probes) else 'FINDINGS','passed':sum(p['pass'] for p in probes),'total':len(probes),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'inventory_head':inventory['head'],'inventory_files':len(source),'sealed_proposal':sealed,'historical_mapping_verification':read(P.parent/'retention-receipt-review/review.json')['mapping_verification'],'new_mapping_verification':'Actual candidate evaluate consumes full request and fixture lookup fields; fresh mutations establish bounded documentary guard behavior. Trusted immutable catalog assumed; no authentication/native persistence proof. Catalog perturbations are defensive consistency probes, not untrusted catalog admission claims.','owner_choices':choices,'findings':[p['id'] for p in probes if not p['pass']],'not_run':['native','build','product tests','valid RED/GREEN','full Draft2020-12','module acceptance'],'next_action':'Owner resolves H1-H4 and confirms architecture/contracts/BDD/Skeleton before production implementation. Parent remains Yellow.'}
write('review.json',report);write('results.json',{'passed':report['passed'],'total':len(probes),'failed':report['findings']})
write('trace.json',{'scope':'Independent review only; no original/product/board/current-state writes','new_cases':'IMR independently constructed; original 60 cases not rerun','command':'python -B check_review.py','source_pointers':read(A/'source-pointers.json'),'board_management_input':'docs/board.json separately hashed; not product inventory authority','board_sha256':sha(R/'docs/board.json')})
html='<!doctype html><meta charset="utf-8"><title>M05 independent mapping review</title><h1>M05 independent mapping review</h1><p>'+report['verdict']+' — '+str(report['passed'])+'/'+str(len(probes))+' fresh documentary probes.</p><p>Yellow parent; H1-H4 pending Owner. No module PASS. Historical NOT_PROVEN is unchanged. Trusted immutable fixture is a premise; native authenticity, persistence and restart remain unproved.</p><h2>Review evidence</h2><pre>'+__import__('html').escape(json.dumps(report,ensure_ascii=False,indent=2))+'</pre><script type="application/json" id="review-spec">'+json.dumps(report,ensure_ascii=False).replace('</','<\\/')+'</script>'
(P/'index.html').write_text(html,encoding='utf-8')
write('seal.json',{'files':{p.name:sha(p) for p in P.iterdir() if p.is_file() and p.name!='seal.json'}})
print(json.dumps({'passed':report['passed'],'total':len(probes),'findings':report['findings'],'source_files':len(source)}))
