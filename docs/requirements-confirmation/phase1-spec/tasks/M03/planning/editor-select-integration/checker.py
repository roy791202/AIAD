"""Author document checks only, never independent or native acceptance."""
from pathlib import Path
import json,hashlib
from copy import deepcopy
from document_model import run
from schema_eval import valid,audit
P=Path(__file__).parent
def read(n):return json.loads((P/n).read_text(encoding='utf-8-sig'))
req=read('request.schema.json');resp=read('response.schema.json')
audit(req);audit(resp)
checks=0
provider_schema=read('provider-observation.schema.json');audit(provider_schema)
for c in read('fixtures.json'):
 p=c['provider']
 expected=type(p)is dict and set(p)==set(provider_schema['required']) and all(type(p[k])is str for k in ('role','origin','outcome')) and all(type(p[k])is bool for k in ('native_live','ready')) and all(type(p[k])is dict and set(p[k])==set(provider_schema['properties'][k]['required']) and all(type(v)is str and len(v)>0 for v in p[k].values()) for k in ('capture','delivery'))
 if expected and any(not __import__('document_model').u64(p[k]['generation']) for k in ('capture','delivery')):expected=False
 # Physical schema lexical validation and semantic u64 are separate.
 physical=valid(provider_schema,p)
 if expected:assert physical,c['id']
 checks+=1
for c in read('fixtures.json'):
 got=run(c,lambda x:valid(req,x));assert got==c['expected'],c['id'];checks+=1
 assert valid(resp,got['response']),c['id'];checks+=1
 before=deepcopy(c['before']);after=deepcopy(got['state']);before.pop('selection');after.pop('selection');assert before==after,c['id'];checks+=1
 assert set(got['calls'])<= {'native.caller.observe','owner.select_ephemeral'};checks+=1
 if got['response']['ok']is False:assert got['state']==c['before'];checks+=1
for c in read('root-probes.json'):
 assert valid(req if c['kind']=='request' else resp,c['value'])is c['valid'],c;checks+=1
preserved=read('preserved-inputs.json')
for name,h in preserved.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,name;checks+=1
source=read('source-current.json');product={}
for v in source.values():
 if isinstance(v,dict):
  for name,h in v.items():
   if isinstance(h,str) and len(h)==64:product[name]=h
for name,h in product.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,name;checks+=1
result=dict(status='PASS_AUTHOR_DOCUMENT_CHECKS_ONLY',fixtures=len(read('fixtures.json')),root_probes=len(read('root-probes.json')),assertions=checks,product_hashes=len(product),preserved_inputs=len(preserved),independent='NOT RUN',native='NOT RUN',build='NOT RUN',product_tests='NOT RUN',valid_RED='NOT RUN',full_Draft2020='NOT RUN',owner='PENDING')
(P/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
