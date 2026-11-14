import json,re,hashlib,subprocess,importlib.util
from pathlib import Path
D=Path(__file__).resolve().parent; W=next(p for p in D.parents if (p/'apps/sgenaxis-desktop').exists())
def read(n):return json.loads((D/n).read_text(encoding='utf-8'))
s=read('response.schema.json')
def validate(z,x,root):
 if '$ref'in z:
  assert z['$ref'].startswith('#/')
  cur=root
  for t in z['$ref'][2:].split('/'):cur=cur[t.replace('~1','/').replace('~0','~')]
  if z['$ref']=='#/$defs/U64Decimal' and (not isinstance(x,str)or not re.fullmatch('0|[1-9][0-9]*',x)or len(x)>20 or (len(x)==20 and x>'18446744073709551615')):return False
  return validate(cur,x,root)
 if 'oneOf'in z:return sum(validate(a,x,root) for a in z['oneOf'])==1
 if 'const'in z and x!=z['const']:return False
 if 'enum'in z and x not in z['enum']:return False
 typ=z.get('type')
 def istype(t):return {'object':isinstance(x,dict),'array':isinstance(x,list),'string':isinstance(x,str),'boolean':isinstance(x,bool),'null':x is None}.get(t,False)
 if typ and not any(istype(t)for t in (typ if isinstance(typ,list) else [typ])):return False
 if isinstance(x,str):
  if len(x)<z.get('minLength',0) or len(x)>z.get('maxLength',10**12):return False
  if 'pattern'in z and re.search(z['pattern'],x)is None:return False
 if isinstance(x,dict):
  if any(k not in x for k in z.get('required',[])):return False
  props=z.get('properties',{})
  if z.get('additionalProperties')is False and any(k not in props for k in x):return False
  if any(k in x and not validate(v,x[k],root)for k,v in props.items()):return False
 if isinstance(x,list) and 'items'in z and any(not validate(z['items'],v,root)for v in x):return False
 return True
refs=[]
def walk(z,root):
 if isinstance(z,dict):
  if '$ref'in z:
   ref=z['$ref'];assert ref.startswith('#/');cur=root
   for t in ref[2:].split('/'):cur=cur[t.replace('~1','/').replace('~0','~')]
   refs.append(ref)
  for v in z.values():walk(v,root)
 elif isinstance(z,list):
  for v in z:walk(v,root)
walk(s,s)
rows=[]
for v in read('response-vectors.json'):
 observed=validate(s,v['response'],s);assert observed==v['expected_schema_admitted'],v['id'];rows.append({'id':v['id'],'observed':observed,'expected':v['expected_schema_admitted']})
life=[]
for v in read('lifecycle-vectors.json'):
 c=v['capture'];r=v['receipt'];good=r['target_path']==c['canonical_target']and r['previous_digest']==c['expected_previous_raw']and r['committed_digest']==c['encoded_raw']and bool(r['transaction_id'])
 if not good:o='UnverifiedOutcome';ack=0
 elif v['condition']=='acked':o='Saved';ack=1
 else:o='CommittedAckDeferred';ack=0
 assert o==v['expected']and ack==v['expected_ack_calls'],v['id']
 if ack:assert v['expected_ack_revision']==c['revision']and v['expected_ack_digest']==c['semantic_digest']and c['semantic_digest']!=c['encoded_raw']
 life.append({'id':v['id'],'outcome':o,'ack_calls':ack})
spec=read('module-spec.json');assert all(hashlib.sha256((W/p).read_bytes()).hexdigest()==h for p,h in spec['frozen_inputs'].items())
b=json.loads((W/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf-8-sig'));assert all(hashlib.sha256((W/p).read_bytes()).hexdigest()==h for p,h in b['source_hashes'].items())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()==spec['head'];assert subprocess.check_output(['git','branch','--show-current'],cwd=W,text=True).strip()==spec['branch']
m=read('io-outcome-map.json');assert len([r for r in m if r['source']=='Storage'])==13;assert len(m)==22
result={'verdict':'PASS_DOCUMENT_MODEL_CHECKS_ONLY_PENDING_REACCEPTANCE_AND_OWNER','schema_cases':rows,'lifecycle_model_cases':life,'local_refs_resolved':len(refs),'io_mapping_rows':len(m),'frozen_inputs':len(spec['frozen_inputs']),'source796_unchanged':True,'full_draft2020_validator':'NOT RUN','jsonschema_available':bool(importlib.util.find_spec('jsonschema')),'product_tests_build_RED_GREEN_native':'NOT RUN','checker_limits':'Restricted review-local schema interpreter and deterministic document lifecycle model only; no production parser, adapter, mutation, pin transfer, sender authorization or runtime ACK executed.'}
(D/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items()if k not in ['schema_cases','lifecycle_model_cases']},ensure_ascii=False))
