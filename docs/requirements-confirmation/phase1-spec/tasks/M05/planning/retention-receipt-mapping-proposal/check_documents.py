from pathlib import Path
import json,hashlib,copy,re,importlib.util
from model import evaluate,read,digest,canonical
P=Path(__file__).resolve().parent;R=next(x for x in P.parents if (x/'.git').exists())
def write(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
c=read('immutable-catalog.json');results=[]
assert digest(c['frozen_request'])==c['request_digest']
for case in read('fixtures.json'):
 original=copy.deepcopy(case); cat=case.get('catalog_override',c); cs=copy.deepcopy(cat)
 got=evaluate(case['input'],cat);assert got['result']==case['expected'],(case['name'],got['result'],case['expected'])
 assert case==original and cat==cs
 assert got['calls']['release']==got['calls']['retry']==got['calls']['ack']==0
 if got['result'] in ('InvalidInput','PermissionDenied','ProofMismatch','ReplayConflict','Held','UnverifiedOutcome'):assert got['calls']['cas']==0
 assert got['before']==cat['before']
 if got['result'] in ('Transferred','SameReceipt') or case['input'].get('transport')=='PostCASProofLoss':assert got['after']==cat['after']
 else:assert got['after']==cat['before']
 if got['result'] in ('Transferred','SameReceipt'):assert got['receipt']==cat['receipt']
 else:assert got['receipt'] is None
 results.append({'id':case['id'],'name':case['name'],**got})
# Execute historical bypass in original untouched oracle, then new oracle on actual pin purpose / issuer mutation.
old=P.parent/'retention-receipt-handoff';sp=importlib.util.spec_from_file_location('old_document_model',old/'model.py');mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
f=json.loads((old/'catalog-fixture.json').read_text(encoding='utf-8-sig'));f['before']['pin']['purpose']='Import';f['receipt_record']['issuer']='UNTRUSTED'
old_result=mod.evaluate(f,{'case':'transfer','observation':'verified'})
assert old_result['outcome']=='Transferred'
new_catalog=copy.deepcopy(c);new_catalog['held_receipt']['pin']['purpose']='Import';new_catalog['held_receipt']['issuer']='UNTRUSTED'
new_result=evaluate(read('fixtures.json')[0]['input'],new_catalog);assert new_result['result']=='ProofMismatch' and new_result['calls']['cas']==0
write('before-after.json',{'historical_scope':'Original source classifier counterexample; does not rewrite historical scoped review','old_actual':old_result,'mutation':'purpose Import + issuer UNTRUSTED','new_actual':new_result})
inputs=read('inputs.json');assert all(hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in inputs.items())
a=json.loads((R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf-8-sig'));assert len(a['source_hashes'])==796
assert all(hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in a['source_hashes'].items())
write('results.json',results)
write('verification.json',{'status':'PASS_DOCUMENT_ONLY_PENDING_OWNER','cases':len(results),'passed':len(results),'historical_bypass_pairs':1,'product_hashes':796,'sealed_input_files':len(inputs),'authority_head':'31babe87a7ef1e40a0d4bedc523077e7a45d63ab','checkout_head':'5b709343a890503ebbe24a802e43cda5647df124','not_run':read('module-spec.json')['not_run'],'remaining_gates':read('module-spec.json')['remaining_gates'],'module_complete':False})
print('PASS',len(results),'new DOCUMENT cases; 1 before/after pair; 796 hashes unchanged')
