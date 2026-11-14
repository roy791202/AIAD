"""Executable DOCUMENT oracle. Trusted fixture membership is not native authentication."""
from pathlib import Path
import copy,json,hashlib,re
P=Path(__file__).resolve().parent
def read(n):return json.loads((P/n).read_text(encoding='utf-8-sig'))
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def digest(v):return hashlib.sha256(canonical(v)).hexdigest()
def valid(v,s,root):
 if '$ref' in s:
  ref=s['$ref'];doc=root
  if ref.startswith('request.schema.json'):doc=read('request.schema.json')
  target=doc
  for k in ref.split('#',1)[1].strip('/').split('/'):
   if k:target=target[int(k)] if type(target)==list else target[k]
  return valid(v,target,doc)
 if 'oneOf' in s:return sum(valid(v,a,root) for a in s['oneOf'])==1
 if 'const' in s and v!=s['const']:return False
 if 'enum' in s and v not in s['enum']:return False
 t=s.get('type')
 if t=='object':
  if type(v)!=dict:return False
  if not set(s.get('required',[]))<=set(v):return False
  props=s.get('properties',{})
  if s.get('additionalProperties') is False and not set(v)<=set(props):return False
  return all(valid(a,props[k],root) for k,a in v.items() if k in props)
 if t=='array':
  return type(v)==list and len(v)>=s.get('minItems',0) and len(v)<=s.get('maxItems',10**9) and all(valid(a,s.get('items',{}),root) for a in v)
 if t=='boolean':return type(v)==bool
 if t=='string':
  if type(v)!=str:return False
  if not s.get('minLength',0)<=len(v)<=s.get('maxLength',10**9):return False
  if 'pattern' in s and not re.search(s['pattern'],v):return False
  if s.get('description','').startswith('Checked runtime u64') and int(v)>18446744073709551615:return False
  return True
 if t is not None:raise AssertionError('unsupported document schema keyword/type '+str(t))
 return True

def evaluate(x,catalog=None):
 c=copy.deepcopy(catalog if catalog is not None else read('immutable-catalog.json')); before=copy.deepcopy(c['before']); calls={'lookup':0,'cas':0,'release':0,'retry':0,'ack':0}; after=copy.deepcopy(before)
 def out(result,claim='unchanged candidate before'):
  return {'result':result,'before':before,'after':after,'calls':copy.deepcopy(calls),'state_claim':claim,'receipt':c['receipt'] if result in ('Transferred','SameReceipt') else None}
 s=read('fixture-input.schema.json')
 if not valid(x,s,s):return out('InvalidInput')
 if not x['permission']:return out('PermissionDenied')
 request=x['request'];rd=digest(request)
 if x['catalog_phase']=='Transferred' and x['transition_key']==c['transition_key'] and rd!=c['request_digest']:return out('ReplayConflict')
 calls['lookup']=2
 h=c['held_receipt']; f=c['formal_receipt']; pin=h['pin']; body=request['body']; context=request['context']; roots=body['root_manifest']
 pairs=[{k:a[k] for k in ('asset_id','digest')} for a in roots['assets']]
 matched=(x['held_ref']=={k:h[k] for k in ('issuer','receipt_id')} and h['issuer']=='M05' and x['formal_ref']=={k:f['proof'][k] for k in ('issuer','receipt_id')} and f['proof']['issuer']=='IO' and pin['purpose']=='Save' and pin['state']=='Held' and pin['pin_id']==body['pin_id'] and pin['context']==context and pin['versions']==pairs and f['proof']==body['external_proof'] and f['context']==context and f['root']==roots and f['store_identity']==body['store_identity'] and x['transition_key']==c['transition_key'] and request==c['frozen_request'] and rd==c['request_digest']==h['request_digest']==c['receipt']['request_digest'] and c['receipt']['issuer']=='M05' and c['receipt']['context']==context and c['receipt']['pin_id']==pin['pin_id'] and c['receipt']['asset_pairs']==pairs and c['receipt']['root_manifest_ids']==[roots['manifest_id']] and c['receipt']['source_receipt_ids']==[x['held_ref'],x['formal_ref']] and c['receipt']['external_proof']['raw_digest']==f['commit']['committed_digest'] and c['receipt']['external_proof']['context_digest']==digest(context) and c['receipt']['external_proof']['issuer']==f['proof']['issuer'] and c['receipt']['external_proof']['receipt_id']==f['proof']['receipt_id'])
 if not matched:return out('ProofMismatch')
 if x['catalog_phase']=='Unknown':return out('Indeterminate','unknown; no prior-state assertion')
 if x['catalog_phase']=='RestartMissing':return out('UnverifiedOutcome','restart evidence absent; no prior-state assertion')
 if x['catalog_phase']=='Transferred':
  after=copy.deepcopy(c['after']);return out('SameReceipt','verified fixture inclusion only')
 if x['transport']=='FailureBeforeCAS':return out('Held')
 calls['cas']=1
 if x['transport']=='UnknownCAS':return out('Indeterminate','attempt outcome unknown; after field is last known snapshot only')
 after=copy.deepcopy(c['after'])
 if x['transport']=='PostCASProofLoss':return out('Indeterminate','candidate write occurred; proof unavailable; no rollback assertion')
 return out('Transferred','candidate after under trusted fixture premises only')

