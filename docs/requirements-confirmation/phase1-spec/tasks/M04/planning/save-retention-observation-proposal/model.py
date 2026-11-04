"""Proposed document oracle only. No provider, persistence or production Skeleton."""
import re
KEYS=set('project document session generation request operation issuer revision semantic raw previous_raw target transaction_id pin_id asset_versions formal_root_id projection_id'.split())
def capture(c):
 if not isinstance(c,dict) or set(c)!=KEYS:return False
 for k in KEYS-{'asset_versions','previous_raw'}:
  if type(c[k]) is not str or not c[k]:return False
 for k in ['revision','generation']:
  if not re.fullmatch(r'0|[1-9][0-9]*',c[k]) or int(c[k])>2**64-1:return False
 for k in ['semantic','raw']:
  if not re.fullmatch('[0-9a-f]{64}',c[k]):return False
 if c['previous_raw'] is not None and (type(c['previous_raw'])is not str or not re.fullmatch('[0-9a-f]{64}',c['previous_raw'])):return False
 v=c['asset_versions']
 return type(v)is list and all(type(a)is dict and set(a)=={'asset_id','content_digest'} and type(a['asset_id'])is str and bool(a['asset_id']) and type(a['content_digest'])is str and re.fullmatch('[0-9a-f]{64}',a['content_digest']) for a in v) and len({(a['asset_id'],a['content_digest'])for a in v})==len(v)
def same(a,b):
 return capture(a) and capture(b) and all(a[k]==b[k]for k in KEYS-{'asset_versions'}) and sorted((x['asset_id'],x['content_digest'])for x in a['asset_versions'])==sorted((x['asset_id'],x['content_digest'])for x in b['asset_versions'])
def valid(x):
 if type(x)is not dict or set(x)!=set('capture seal held file root ack current formal_revision live_semantic snapshot'.split()):return False
 if not capture(x['capture']) or not capture(x['seal']):return False
 for name,fields,states in [('held',{'state','issuer','receipt_id','trusted','fence','capture'},['Held','Transferred','Released','Unknown']),('root',{'state','issuer','receipt_id','trusted','fence','capture'},['Transferred','Released','Unknown','Failed']),('ack',{'state','capture'},['Accepted','Rejected','Unknown']),('file',{'state','receipt'},['Committed','PrecommitFailure','Uncertain']),('current',{'attached','authorized'},None)]:
  o=x[name]
  if type(o)is not dict or set(o)!=fields:return False
  if states and o['state'] not in states:return False
  if name in ['held','root'] and (type(o['trusted'])is not bool or type(o['fence'])is not bool or type(o['issuer'])is not str or type(o['receipt_id'])is not str or not capture(o['capture'])):return False
  if name=='ack' and not capture(o['capture']):return False
 if any(type(x['current'][k])is not bool for k in ['attached','authorized']):return False
 f=x['file']['receipt']
 if type(f)is not dict or set(f)!={'target_path','previous_digest','committed_digest','transaction_id'}:return False
 return type(x['formal_revision'])is str and re.fullmatch(r'0|[1-9][0-9]*',x['formal_revision']) is not None and int(x['formal_revision'])<=2**64-1 and type(x['live_semantic'])is str and re.fullmatch('[0-9a-f]{64}',x['live_semantic'])is not None and type(x['snapshot'])is str and all(type(f[k])is str and bool(f[k])for k in ['target_path','committed_digest','transaction_id']) and (f['previous_digest']is None or type(f['previous_digest'])is str)
def evaluate(x):
 out={'outcome':'RejectedMalformed','root_calls':0,'ack_calls':0,'release_calls':0,'retention':'NOT_PROVEN','formal_revision':None,'snapshot':None,'delivery':False}
 if not valid(x):return out
 c=x['capture'];h=x['held'];r=x['root'];f=x['file'];a=x['ack']
 out.update(formal_revision=x['formal_revision'],snapshot=x['snapshot'],delivery=x['current']['attached'] and x['current']['authorized'])
 proof=lambda o: o['issuer']=='M05' and o['trusted'] and o['fence'] and bool(o['receipt_id']) and same(c,o['capture'])
 if h['state']=='Held' and proof(h):out['retention']='HeldObserved'
 out['outcome']='UnverifiedOutcome'
 if not same(c,x['seal']) or out['retention']!='HeldObserved':return out
 if f['state']=='PrecommitFailure':out['outcome']='SaveRejected';return out
 if f['state']!='Committed':return out
 expected={'target_path':c['target'],'previous_digest':c['previous_raw'],'committed_digest':c['raw'],'transaction_id':c['transaction_id']}
 if f['receipt']!=expected:return out
 out['outcome']='CommittedAckDeferred'
 if not out['delivery']:return out
 out['root_calls']=1
 if r['state']!='Transferred' or not proof(r):return out
 out['retention']='TransferredObserved'
 if a['state']!='Accepted' or not same(c,a['capture']) or int(c['revision'])<int(x['formal_revision']):return out
 out.update(outcome='Saved',ack_calls=1,formal_revision=c['revision'],dirty=x['live_semantic']!=c['semantic'])
 return out
