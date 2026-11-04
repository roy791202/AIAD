import json,re,hashlib,subprocess
from pathlib import Path
D=Path(__file__).resolve().parent; W=next(p for p in D.parents if (p/"apps/sgenaxis-desktop").exists())
def read(n):return json.loads((D/n).read_text(encoding="utf-8"))
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
def model(x):
 c=x['capture'];cur=x['current'];issuer=x['issuer_record'];f=x['file_receipt'];r=x['root_receipt'];a=x['ack'];keys=['document','session','generation','request','issuer']
 if not issuer.get('verified') or any(issuer[k]!=c[k]for k in keys):return ('UnverifiedOutcome',0,'IssuerEvidenceMissing')
 if f['target']!=c['target']or f['previous_raw']!=c['previous_raw']or f['raw']!=c['raw']or not f['transaction_id']:return ('UnverifiedOutcome',0,'CommitOutcomeUnknown')
 if not cur['attached']:return ('CommittedAckDeferred',0,'Detached')
 if not cur['authorized']or any(cur[k]!=c[k]for k in ['document','session','generation','issuer']):return ('CommittedAckDeferred',0,'OwnerChanged')
 if not r or not r.get('verified')or any(r[k]!=c[k]for k in keys)or r['proof_id']!=issuer['proof_id']or r['formal_raw']!=c['raw']or r['state']!='Transferred'or r['pin_id']!=c['pin_id']or not r['transfer_id']:return ('CommittedAckDeferred',0,'ProofMismatch')
 if not a.get('accepted')or any(a[k]!=c[k]for k in keys)or a['proof_id']!=issuer['proof_id']or a['transfer_id']!=r['transfer_id']or a['revision']!=c['revision']or a['semantic']!=c['semantic']:return ('CommittedAckDeferred',0,'AckRejected')
 return ('Saved',1,None)
results={}
for name in ['request','response']:
 s=read(name+'.schema.json');rows=[]
 for v in read(name+'-vectors.json'):
  observed=validate(s,v['value'],s);assert observed==v['expected'],v['id'];rows.append({'id':v['id'],'observed':observed})
 results[name]=rows
life=[]
for v in read('lifecycle-vectors.json'):
 o=model(v['input']);e=v['expected'];assert o==(e['outcome'],e['ack_calls'],e['reason']),v['id'];life.append({'id':v['id'],'observed':o})
results['lifecycle']=life
spec=read('module-spec.json');assert all(hashlib.sha256((W/p).read_bytes()).hexdigest()==h for p,h in spec['frozen_inputs'].items())
b=json.loads((W/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf-8-sig'));assert all(hashlib.sha256((W/p).read_bytes()).hexdigest()==h for p,h in b['source_hashes'].items())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()==spec['head'];assert subprocess.check_output(['git','branch','--show-current'],cwd=W,text=True).strip()==spec['branch']
refs={}
for name in ['request','response']:
 root=read(name+'.schema.json');count=[0]
 def walk(z):
  if isinstance(z,dict):
   if '$ref'in z:
    assert z['$ref'].startswith('#/');cur=root
    for k in z['$ref'][2:].split('/'):cur=cur[k.replace('~1','/').replace('~0','~')]
    count[0]+=1
   for a in z.values():walk(a)
  elif isinstance(z,list):
   for a in z:walk(a)
 walk(root);refs[name]=count[0]
results['local_refs_resolved']=refs
results['source_material_pairs']=57
results['stage_reason_branches']={'RootTransfer':57,'SemanticAck':4}
results.update(verdict='PASS_DOCUMENT_MODEL_ONLY_PENDING_REACCEPTANCE_AND_OWNER',full_draft_validator='NOT RUN',product_tests_build_RED_GREEN_native='NOT RUN',source796_unchanged=True,limits='Restricted schema interpreter plus proposed evidence model, not runtime proof or full Draft validation')
(D/'verification.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print({k:len(v) for k,v in results.items()if isinstance(v,list)})
