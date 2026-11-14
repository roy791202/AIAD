from pathlib import Path
import hashlib,json,re
from model import evaluate,digest,canonical
P=Path(__file__).resolve().parent
R=next(a for a in P.parents if (a/'.git').exists())
def read(n):return json.loads((P/n).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=read('module-spec.json');f=read('catalog-fixture.json');cases=read('fixtures.json')
assert f['request_body']['protocol']=='SGA-TRANSITION-v2'
assert digest(f['request_body'])==f['request_digest']==f['receipt_record']['request_digest']
assert canonical(f['request_body']).decode()==f['request_canonical_utf8']
assert set(f['request_body'])=={'protocol','issuer','role','ordinal','context','body'}
assert set(f['request_body']['body'])=={'pin_id','store_identity','root_manifest','external_proof','expected_catalog_generation'}
assert f['before']['pin']['state']=='Held' and f['after']['pin']['state']=='Transferred'
assert len(f['after']['transition_receipts'])==len(f['after']['root_manifests'])==1
assert f['before']['pin']['versions']==f['after']['pin']['versions']
results=[]
for c in cases:
    got=evaluate(f,c);assert got['outcome']==c['expected'];assert got['release']==got['ack']==0
    results.append(dict(id=c['id'],**got))
# New valid complete-body alterations each change hash; no old projection hashing.
mutations=[('pin_id','other'),('root_manifest',dict(f['request_body']['body']['root_manifest'],provider_id='other')),('external_proof',dict(f['request_body']['body']['external_proof'],evidence_digest='0'*64))]
import copy
for k,v in mutations:
    b=copy.deepcopy(f['request_body']);b['body'][k]=v;assert digest(b)!=f['request_digest']
inputs=read('inputs.json');assert all((R/p).exists() and sha(R/p)==h for p,h in inputs.items())
auth=json.loads((R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf-8-sig'))
assert len(auth['source_hashes'])==796
assert all((R/p).exists() and sha(R/p)==h for p,h in auth['source_hashes'].items())
embedded=re.search(r'<script type="application/json" id="module-spec">(.*?)</script>',(P/'index.html').read_text(encoding='utf-8'),re.S)
assert json.loads(embedded[1])==spec
assert not spec['module_complete'] and all(x['status']=='PROPOSED_PENDING_OWNER' for x in spec['choices'])
v=read('verification.json');v.update(status='PASS_DOCUMENT_ONLY_PENDING_OWNER',witnesses=len(results),fullbody_mutation_probes=3,product_hashes_verified=796,input_files_verified=len(inputs),model_results=results)
(P/'verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS document only:',len(results),'witnesses; 3 body hash probes; 796 unchanged product files')
