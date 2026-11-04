"""DOCUMENT oracle only: immutable fixture issuer lookup is a premise, not native authentication."""
from pathlib import Path
import json,copy,hashlib,re,uuid
P=Path(__file__).resolve().parent
def read(n):return json.loads((P/n).read_text(encoding='utf-8-sig'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def valid(v,s,root):
 if '$ref' in s:
  target=root
  for k in s['$ref'].split('#',1)[1].strip('/').split('/'):
   if k:target=target[k]
  return valid(v,target,root)
 if 'oneOf' in s:return sum(valid(v,a,root) for a in s['oneOf'])==1
 if 'anyOf' in s:return any(valid(v,a,root) for a in s['anyOf'])
 if 'enum' in s and v not in s['enum']:return False
 if 'const' in s and v!=s['const']:return False
 t=s.get('type')
 if t=='object':
  if type(v)!=dict or not set(s.get('required',[]))<=set(v):return False
  props=s.get('properties',{})
  return not(s.get('additionalProperties') is False and set(v)-set(props)) and all(valid(a,props[k],root) for k,a in v.items() if k in props)
 if t=='array':return type(v)==list and len(v)>=s.get('minItems',0) and len(v)<=s.get('maxItems',10**9) and all(valid(a,s.get('items',{}),root) for a in v)
 if t=='string':return type(v)==str and s.get('minLength',0)<=len(v)<=s.get('maxLength',10**9) and ('pattern' not in s or re.search(s['pattern'],v) is not None) and (not s.get('description','').startswith('Checked runtime u64') or int(v)<=18446744073709551615)
 if t=='null':return v is None
 if t=='boolean':return type(v)==bool
 return t is None

def evaluate(x):
 c=read('immutable-issuer-fixture.json');before=copy.deepcopy(c['before']);after=copy.deepcopy(before);calls={'import_lookup':0,'merge_commit':0,'publish':0,'transfer':0,'undo_commit':0,'release':0,'retry':0,'rollback':0,'formal_save':0,'formal_ack':0}
 def out(result):return {'result':result,'before':before,'after':copy.deepcopy(after),'other_document':c['other_document'],'pin':c['held_pin'],'undo_pin':c['undo_held_pin'],'calls':copy.deepcopy(calls),'claim':'last known state only' if result=='UnverifiedOutcome' else 'trusted documentary fixture only'}
 shape=read('fixture-input.schema.json');schema=read('transition-request.schema.json')
 if not valid(x,shape,shape):return out('InvalidInput')
 requests=[x['import_request'],x['undo_request']]+x['merge_publish']+x['merge_transfer']+x['undo_publish']+x['undo_transfer']
 if not all(valid(r,schema,schema) for r in requests):return out('ProofMismatch')
 calls['import_lookup']=1
 ir=c['import_record'];req=x['import_request'];m=x['mutation'];mp=x['mutation_proof'];um=x['undo_mutation'];up=x['undo_proof']
 # Full frozen request equality consumes every validated field, with independently retained complete request digest.
 matched=req==c['import_request'] and digest(req)==ir['request_digest'] and x['import_receipt_ref']=={k:ir[k] for k in ['issuer','receipt_id']}
 matched=matched and m==c['mutation'] and digest(m)==mp['evidence_digest'] and mp==c['mutation_proof'] and mp['issuer']=='M04' and mp['kind']=='DocumentMutation' and mp['context_digest']==digest(m['context'])
 matched=matched and m['mapping_digest']==digest(m['mapping']) and m['candidate_digest']==digest(c['after_merge']['content']) and m['before_digest']==digest(before['content']) and m['pin_id']==c['held_pin']['pin_id'] and c['held_pin']['purpose']=='Import' and c['held_pin']['state']=='Held' and req['context']==m['context']==ir['context']==c['held_pin']['context']
 matched=matched and um==c['undo_mutation'] and up==c['undo_proof'] and up['evidence_digest']==digest(um) and up['kind']=='DocumentMutation' and up['issuer']=='M04' and up['context_digest']==digest(um['context']) and x['undo_request']==c['undo_request']
 matched=matched and c['undo_held_pin']['context']==um['context'] and c['undo_held_pin']['purpose']=='Undo' and c['undo_held_pin']['state']=='Held' and c['undo_held_pin']['pin_id']==um['pin_id']
 for phase,proof in [('merge',mp),('undo',up)]:
  for family in ['publish','transfer']:
   rs=x[phase+'_'+family];frozen=c[phase+'_'+family]
   matched=matched and rs==frozen and len(rs)==3
   for i,r in enumerate(rs):
    if family=='publish':
     matched=matched and r['body']['expected_epoch']==r['body']['manifest']['epoch'] and r['body']['manifest']['completeness']=='Complete'
    else:
     records=[a for a in c['transfer_records'] if a['request_digest']==digest(r)]
     matched=matched and len(records)==1 and r['body']['external_proof']==proof and r['context']==proof_context(c,phase) and r['body']['pin_id']==(m['pin_id'] if phase=='merge' else um['pin_id'])
     if len(records)==1:
      a=records[0];root=r['body']['root_manifest'];pairs=[{k:v[k] for k in ['asset_id','digest']} for v in sorted(root['assets'],key=lambda v:(v['asset_id'],v['digest']))]
      matched=matched and a['context']==r['context'] and a['role']=='transfer-live' and a['request_protocol']==r['protocol'] and a['source_receipt_ids']==[proof] and a['external_proof']['projection_digest']==proof['evidence_digest'] and a['root_manifest_ids']==[root['manifest_id']] and a['asset_pairs']==pairs and a['target_identity']==r['body']['store_identity'] and a['external_proof']['kind']=='DocumentMutation'
 if not matched:return out('ProofMismatch')
 if x['commit_observation']=='KnownNotAttempted':return out('RejectedBeforeMutation')
 calls['merge_commit']=1
 if x['commit_observation']=='Unknown':return out('UnverifiedOutcome')
 after=copy.deepcopy(c['after_merge']);calls['publish']=3
 if x['root_observation']=='Verified':calls['transfer']=3
 result='MergeApplied' if x['root_observation']=='Verified' else 'MergeAppliedRetentionDeferred'
 if not x['perform_undo']:return out(result)
 calls['undo_commit']=1
 if x['undo_observation']=='Unknown':return out('UnverifiedOutcome')
 after=copy.deepcopy(c['after_undo']);calls['publish']+=3
 if x['undo_root_observation']=='Verified':calls['transfer']+=3
 return out('UndoApplied' if x['undo_root_observation']=='Verified' else 'UndoAppliedRetentionDeferred')
def proof_context(c,phase):return c['mutation' if phase=='merge' else 'undo_mutation']['context']


