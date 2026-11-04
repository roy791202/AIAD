"""Bounded DOCUMENT oracle: immutable fixture semantics, no native proof."""
from pathlib import Path
import copy, hashlib, html, json, re, uuid
P=Path(__file__).resolve().parent
ROOT=P.parents[6]
def read(n):return json.loads((P/n).read_text(encoding='utf-8-sig'))
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def valid(v,s):
 if 'oneOf' in s:return sum(valid(v,t) for t in s['oneOf'])==1
 if 'const' in s and (type(v)!=type(s['const']) or v!=s['const']):return False
 if 'enum' in s and v not in s['enum']:return False
 t=s.get('type')
 if t=='object':return type(v)==dict and set(s['required'])<=set(v) and set(v)<=set(s['properties']) and all(valid(a,s['properties'][k]) for k,a in v.items())
 if t=='array':return type(v)==list and len(v)<=s['maxItems'] and all(valid(a,s['items']) for a in v)
 if t=='string':
  if type(v)!=str or len(v)<s.get('minLength',0) or len(v)>s.get('maxLength',100000):return False
  if 'pattern' in s and re.fullmatch(s['pattern'],v) is None:return False
  return not s.get('description','').startswith('Checked runtime') or int(v)<=18446744073709551615
 if t=='null':return v is None
 if t=='boolean':return type(v)==bool
 raise AssertionError('Unsupported schema keyword type: '+str(t))

def evaluate(x,f):
 q=x.get('request');s=copy.deepcopy(x['state'])
 calls=dict(ack=0,retry=0,release=0)
 out=dict(result='Rejected',state=s,calls=calls,local_integrity_ready=True,published=False)
 def finish(result):out['result']=result;return out
 if not valid(q,read('request.schema.json')):return finish('Rejected')
 b=q['body'];ctx=q['context']
 if not x['proof_available']:return finish('UnverifiedOutcome')
 if x['root_state']=='Unknown':return finish('UnverifiedOutcome')
 if x['root_state']!='Transferred':return finish('Deferred')
 c=f['capture'];i=f['index'];e=i['evidence'];t=f['transfer'];tr=f['transfer_request'];h=f['held']
 # These are concrete equality and full-body hash checks; no verified=True flag.
 if c['context']!=ctx or any(s[k]!=ctx[k] for k in ('project_uuid','document_uuid','session_id','owner_generation')):return finish('Rejected')
 if any(b[k]!=c[k] for k in ('source_owner_handle','capture_handle','attempt_id','snapshot_id')):return finish('Rejected')
 if b['captured_recovery_fingerprint']!=c['fingerprint'] or b['material_versions']!=c['materials']:return finish('Rejected')
 if e['context']!=ctx or e['attempt_id']!=c['attempt_id'] or e['snapshot_id']!=c['snapshot_id']:return finish('Rejected')
 if e['materials']!=c['materials'] or e['recovery_fingerprint']!=c['fingerprint']:return finish('Rejected')
 for key in ('payload_raw_digest','index_expected_prior_raw_digest','index_committed_raw_digest','index_transaction_id'):
  if b[key]!=e[key]:return finish('Rejected')
 if b['index_target_identity']!=e['target_identity']:return finish('Rejected')
 ir=i['proof']
 if b['index_receipt']!=ir or ir['issuer']!='M07' or ir['kind']!='RecoveryIndex' or ir['context_digest']!=digest(ctx) or ir['evidence_digest']!=digest(e):return finish('Rejected')
 ref=b['transfer_receipt']
 if ref!=dict(issuer='M05',receipt_id=t['receipt_id'],kind='RecoveryTransfer',context_digest=digest(ctx),evidence_digest=digest(t)):return finish('Rejected')
 if t['issuer']!='M05' or t['role']!='transfer-recovery' or t['result']!='Transferred' or t['context']!=ctx:return finish('Rejected')
 if tr['context']!=ctx or tr['issuer']!='M05' or tr['role']!='transfer-recovery' or tr['protocol']!=t['request_protocol']:return finish('Rejected')
 if t['workflow_id']!=ctx['workflow_id'] or t['ordinal']!='0' or t['operation_id']!=str(uuid.uuid5(uuid.UUID(ctx['workflow_id']),'transfer-recovery/0')) or t['request_digest']!=digest(tr):return finish('Rejected')
 tb=tr['body'];ep=t['external_proof'];rm=tb['root_manifest']
 if tb['external_proof']!=ir or t['pin_id']!=tb['pin_id'] or h['pin_id']!=t['pin_id']:return finish('Rejected')
 if h['issuer']!='M05' or h['purpose']!='Recovery' or h['state']!='Held' or h['context']!=ctx or h['assets']!=e['materials']:return finish('Rejected')
 if t['source_receipt_ids']!=[dict(issuer='M05',receipt_id=h['receipt_id']),dict(issuer='M07',receipt_id=ir['receipt_id'])]:return finish('Rejected')
 if t['asset_pairs']!=[dict(asset_id=a['asset_id'],digest=a['digest']) for a in e['materials']] or rm['assets']!=e['materials']:return finish('Rejected')
 if t['root_manifest_ids']!=[rm['manifest_id']] or rm['kind']!='RecoverySnapshots' or rm['completeness']!='Complete':return finish('Rejected')
 if t['expected_generation']!=tb['expected_catalog_generation'] or int(t['committed_generation'])!=int(t['expected_generation'])+1:return finish('Rejected')
 if t['store_identity']!=tb['store_identity'] or t['target_identity']!=e['target_identity'] or t['store_identity']!=e['target_identity']:return finish('Rejected')
 if ep!=dict(issuer='M07',receipt_id=ir['receipt_id'],kind='RecoveryIndex',context_digest=digest(ctx),target_identity=e['target_identity'],raw_digest=e['index_committed_raw_digest'],projection_digest=digest(e)):return finish('Rejected')
 old=s['recovery_baseline']
 if old is not None and int(old['revision'])>int(ctx['captured_revision']):return finish('Superseded')
 if int(s['live_revision'])<int(ctx['captured_revision']):return finish('Rejected')
 if old is not None and int(old['revision'])==int(ctx['captured_revision']) and old['fingerprint']!=c['fingerprint']:return finish('Rejected')
 s['recovery_baseline']=dict(revision=ctx['captured_revision'],fingerprint=c['fingerprint'])
 calls['ack']=1;out['published']=True
 return finish('CapturedRecoveryAcknowledged')
