"""Review-local document interpreter/model; not production code or valid RED."""
import json,re,hashlib,subprocess
from pathlib import Path
D=Path(__file__).resolve().parent
W=next(p for p in D.parents if (p/'apps/sgenaxis-desktop').exists())
def read(n): return json.loads((D/n).read_text(encoding='utf-8'))
def validate(s,x,root):
 if '$ref' in s:
  v=root
  for k in s['$ref'][2:].split('/'):v=v[k.replace('~1','/').replace('~0','~')]
  return validate(v,x,root)
 if 'oneOf' in s:return sum(validate(v,x,root) for v in s['oneOf'])==1
 if 'const'in s and x!=s['const']:return False
 if 'enum'in s and x not in s['enum']:return False
 kinds={'object':isinstance(x,dict),'array':isinstance(x,list),'string':isinstance(x,str),'boolean':isinstance(x,bool),'null':x is None}
 t=s.get('type')
 if t and not any(kinds.get(k,False) for k in (t if isinstance(t,list)else[t])):return False
 if isinstance(x,str):
  if not s.get('minLength',0)<=len(x)<=s.get('maxLength',10**12):return False
  if 'pattern'in s and re.search(s['pattern'],x)is None:return False
 if isinstance(x,dict):
  if any(k not in x for k in s.get('required',[])):return False
  if s.get('additionalProperties')is False and any(k not in s.get('properties',{})for k in x):return False
  if any(k in x and not validate(v,x[k],root)for k,v in s.get('properties',{}).items()):return False
 if isinstance(x,list)and 'items'in s and any(not validate(s['items'],v,root)for v in x):return False
 return True

CAPTURE_KEYS={'project','document','session','generation','request','operation','issuer','revision','semantic','raw','previous_raw','target','transaction_id','pin_id','asset_versions','formal_root_id','projection_id'}
def versions(v):
 if not isinstance(v,list):return None
 pairs=[]
 for a in v:
  if not isinstance(a,dict)or set(a)!={'asset_id','content_digest'}:return None
  if not isinstance(a['asset_id'],str)or not a['asset_id']or not isinstance(a['content_digest'],str)or re.fullmatch('[0-9a-f]{64}',a['content_digest'])is None:return None
  pair=(a['asset_id'],a['content_digest'])
  if pair in pairs:return None
  pairs.append(pair)
 return sorted(pairs,key=lambda a:(a[0].encode('utf-8'),a[1].encode('ascii')))
def same_capture(c,sealed):
 return isinstance(c,dict)and isinstance(sealed,dict)and set(c)==CAPTURE_KEYS and set(sealed)==CAPTURE_KEYS and versions(c['asset_versions'])is not None and versions(c['asset_versions'])==versions(sealed['asset_versions'])and all(c[k]==sealed[k]for k in CAPTURE_KEYS-{'asset_versions'})
def model(x):
 # issuer_record is a trusted retained server record, not caller-provided proof.
 c=x['capture'];i=x['issuer_record'];f=x['file_receipt'];r=x['root_receipt'];a=x['ack'];cur=x['current']
 if not i.get('verified')or not i.get('proof_id')or not same_capture(c,i.get('sealed_capture')):return ('UnverifiedOutcome',0,'IssuerEvidenceMissing')
 if not isinstance(f,dict)or set(f)!={'target','previous_raw','raw','transaction_id'}or any(f[k]!=c[k]for k in f):return ('UnverifiedOutcome',0,'CommitOutcomeUnknown')
 identity=['project','document','session','generation','issuer']
 if not cur.get('attached'):return ('CommittedAckDeferred',0,'Detached')
 if not cur.get('authorized')or any(cur.get(k)!=c[k]for k in identity):return ('CommittedAckDeferred',0,'OwnerChanged')
 binding=['project','document','session','generation','request','operation','issuer','revision','semantic','raw','previous_raw','target','transaction_id','pin_id','formal_root_id','projection_id']
 if not isinstance(r,dict)or not r.get('verified')or r.get('proof_id')!=i['proof_id']or r.get('state')!='Transferred'or not r.get('transfer_id')or any(r.get(k)!=c[k]for k in binding)or versions(r.get('asset_versions'))is None or versions(r['asset_versions'])!=versions(c['asset_versions']):return ('CommittedAckDeferred',0,'ProofMismatch')
 if not isinstance(a,dict)or not a.get('accepted')or a.get('proof_id')!=i['proof_id']or a.get('transfer_id')!=r['transfer_id']or any(a.get(k)!=c[k]for k in binding)or versions(a.get('asset_versions'))is None or versions(a['asset_versions'])!=versions(c['asset_versions']):return ('CommittedAckDeferred',0,'AckRejected')
 return ('Saved',1,None)

def main():
 out={}
 for name in ['request','response']:
  root=read(name+'.schema.json');rows=[]
  for row in read(name+'-vectors.json'):
   got=validate(root,row['value'],root);assert got==row['expected'],row['id'];rows.append({'id':row['id'],'observed':got})
  out[name]=rows
 life=[]
 for row in read('lifecycle-vectors.json'):
  got=model(row['input']);assert list(got)==row['expected'],row['id'];life.append({'id':row['id'],'observed':got})
 out['lifecycle']=life
 refs={}
 for name in ['request','response']:
  root=read(name+'.schema.json');count=[0]
  def walk(x):
   if isinstance(x,dict):
    if '$ref'in x:
     assert x['$ref'].startswith('#/');v=root
     for k in x['$ref'][2:].split('/'):v=v[k.replace('~1','/').replace('~0','~')]
     count[0]+=1
    for v in x.values():walk(v)
   elif isinstance(x,list):
    for v in x:walk(v)
  walk(root);refs[name]=count[0]
 out['local_refs']=refs
 spec=read('module-spec.json')
 assert all(hashlib.sha256((W/p).read_bytes()).hexdigest()==h for p,h in spec['frozen_inputs'].items())
 baseline=json.loads((W/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf-8-sig'))
 assert all(hashlib.sha256((W/p).read_bytes()).hexdigest()==h for p,h in baseline['source_hashes'].items())
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()==spec['head']
 assert subprocess.check_output(['git','branch','--show-current'],cwd=W,text=True).strip()==spec['branch']
 out.update(verdict='DOCUMENT_MODEL_CHECKS_MATCH_PENDING_REACCEPTANCE_AND_OWNER',full_draft_validator='NOT RUN',product_tests_build_RED_GREEN_native='NOT RUN',product796_preserved=True)
 (D/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print({k:len(v) for k,v in out.items()if isinstance(v,list)},refs)
if __name__=='__main__':main()
