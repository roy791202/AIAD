"""Bounded documentary oracle, never native authentication or valid product RED."""
from pathlib import Path
import json,hashlib,copy,re,uuid
P=Path(__file__).resolve().parent
def read(n):return json.loads((P/n).read_text(encoding='utf-8-sig'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def valid(v,s,root):
 if '$ref' in s:
  ref=s['$ref']
  if ref=='request.schema.json':return valid(v,read(ref),read(ref))
  target=root
  for k in ref.split('#',1)[1].strip('/').split('/'):
   if k:target=target[int(k)] if type(target)==list else target[k]
  return valid(v,target,root)
 for union in ['oneOf','anyOf']:
  if union in s:
   count=sum(valid(v,a,root) for a in s[union]);return count==1 if union=='oneOf' else count>0
 if 'const' in s and v!=s['const']:return False
 if 'enum' in s and v not in s['enum']:return False
 t=s.get('type')
 if t=='object':
  if type(v)!=dict:return False
  props=s.get('properties',{})
  return set(s.get('required',[]))<=set(v) and (s.get('additionalProperties') is not False or set(v)<=set(props)) and all(valid(a,props[k],root) for k,a in v.items() if k in props)
 if t=='array':return type(v)==list and all(valid(a,s.get('items',{}),root) for a in v)
 if t=='boolean':return type(v)==bool
 if t=='null':return v is None
 if t=='string':
  if type(v)!=str or len(v)<s.get('minLength',0) or len(v)>s.get('maxLength',10**6):return False
  if 'pattern' in s and not re.search(s['pattern'],v):return False
  if s.get('description','').startswith('Checked runtime u64') and int(v)>18446744073709551615:return False
  return True
 if t is not None:raise AssertionError('Unsupported schema subset: '+str(t))
 return True
def evaluate(x,c):
 calls=dict(transfer=0,ack=0,retry=0,release=0)
 out=dict(local_integrity_ready=False,source_ack=False,recovery_baseline_revision='5',formal_baseline_revision='6',live_revision=x.get('live_revision'),calls=calls,pin_state='Held')
 def finish(status):out['status']=status;return out
 s=read('fixture-input.schema.json')
 if not valid(x,s,s):return finish('InvalidInput')
 q=x['request'];e=c['index_proof']['evidence'];proof=c['index_proof']['proof'];r=c['transfer_receipt'];ctx=q['context']
 if q!=c['frozen_request'] or x['attempt_id']!=e['attempt_id'] or x['snapshot_id']!=e['snapshot_id'] or x['index_proof_ref']!=proof or x['transition_key']!=c['transition_key']:return finish('ProofMismatch')
 assert proof['context_digest']==digest(ctx) and proof['evidence_digest']==digest(e)
 assert c['held']['purpose']=='Recovery' and c['held']['context']==ctx and c['held']['pin_id']==q['body']['pin_id']
 assert c['held']['issuer']=='M05' and c['held']['state']=='Held' and c['held']['assets']==e['materials']==q['body']['root_manifest']['assets']
 assert e['context']==ctx and e['target_identity']==q['body']['store_identity']
 assert proof['issuer']=='M07' and proof['kind']=='RecoveryIndex' and q['body']['external_proof']==proof
 assert r['request_digest']==digest(q) and r['operation_id']==str(uuid.uuid5(uuid.UUID(ctx['workflow_id']),'transfer-recovery/0'))
 assert r['issuer']=='M05' and r['context']==ctx and r['workflow_id']==ctx['workflow_id'] and r['role']==q['role'] and r['ordinal']==q['ordinal']
 assert r['pin_id']==c['held']['pin_id'] and r['store_identity']==q['body']['store_identity'] and r['target_identity']==q['body']['store_identity']
 assert r['expected_generation']==q['body']['expected_catalog_generation'] and int(r['committed_generation'])==int(r['expected_generation'])+1
 assert r['request_protocol']==q['protocol'] and r['result']=='Transferred'
 assert r['source_receipt_ids']==[dict(issuer='M05',receipt_id=c['held']['receipt_id']),dict(issuer='M07',receipt_id=proof['receipt_id'])]
 assert r['external_proof']['issuer']==proof['issuer'] and r['external_proof']['receipt_id']==proof['receipt_id'] and r['external_proof']['kind']==proof['kind'] and r['external_proof']['context_digest']==proof['context_digest'] and r['external_proof']['target_identity']==e['target_identity']
 assert r['external_proof']['raw_digest']==e['index_committed_raw_digest'] and r['external_proof']['projection_digest']==digest(e)
 assert r['asset_pairs']==[{k:a[k] for k in ('asset_id','digest')} for a in e['materials']]
 assert r['root_manifest_ids']==[q['body']['root_manifest']['manifest_id']]
 if not x['issuer_record_available']:return finish('UnverifiedOutcome')
 if not x['payload_verified'] or not x['materials_verified'] or x['index_outcome']=='Failed':return finish('NotReady')
 if x['index_outcome']=='Unknown':out['pin_state']='Unknown';return finish('UncertainPublication')
 out['local_integrity_ready']=True;calls['transfer']=1
 if x['root_outcome']!='Transferred':return finish('SourceRetentionDeferred')
 out['pin_state']='Transferred'
 if x['owner_generation']!=ctx['owner_generation'] or not x['captured_ack_requested']:return finish('CommittedAckDeferred')
 calls['ack']=1;out['source_ack']=True;out['recovery_baseline_revision']=ctx['captured_revision']
 return finish('PublicationAcknowledged')
def main():
 c=read('immutable-issuer.json');traces=[]
 for case in read('fixtures.json'):
  actual=evaluate(case['input'],c);assert actual['status']==case['expected'],case['id']
  assert actual['calls']['retry']==actual['calls']['release']==0
  assert actual['formal_baseline_revision']=='6' and actual['live_revision']==case['input']['live_revision']
  if actual['source_ack']:assert actual['recovery_baseline_revision']=='10'
  traces.append(dict(id=case['id'],actual=actual,pass_document_only=True))
 base=read('fixtures.json')[0]['input']; probes=0
 for path in [('request','body','extra'),('request','body','root_manifest','extra')]:
  x=copy.deepcopy(base);at=x
  for k in path[:-1]:at=at[k]
  at[path[-1]]='forged';assert evaluate(x,c)['status']=='InvalidInput';probes+=1
 for key in ['attempt_id','snapshot_id']:
  x=copy.deepcopy(base);x[key]='other';assert evaluate(x,c)['status']=='ProofMismatch';probes+=1
 x=copy.deepcopy(base);x['request']['body']['external_proof']['evidence_digest']='f'*64;assert evaluate(x,c)['status']=='ProofMismatch';probes+=1
 write=lambda n,v:(P/n).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
 write('trace.json',traces)
 write('verification.json',dict(status='PASS_DOCUMENTARY_WITNESS_ONLY',cases=len(traces),negative_probes=probes,validator='bounded used-keyword subset; full Draft NOT RUN',independent='NOT RUN',native='NOT RUN',build='NOT RUN',product='NOT RUN',valid_red='NOT RUN',owner='PENDING',skeleton='NOT AUTHORIZED',module_pass=False))
 print('8 documentary cases + 5 negative probes PASS; no product/native/independent/RED claim')
if __name__=='__main__':main()
