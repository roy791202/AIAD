"""PROPOSED_PENDING_OWNER document reducer, not a native provider implementation."""
from copy import deepcopy
import re
MAX=18446744073709551615
UUID=r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
TUPLE=('consumer','window_instance','project_uuid','root_instance','runtime_epoch','document_uuid','session_uuid','generation','preview_session')
def u64(x):return type(x)is str and re.fullmatch(r'0|[1-9][0-9]*',x)is not None and len(x)<=20 and int(x)<=MAX
def identity(x):
 return type(x)is dict and set(x)==set(TUPLE)|{'native_live','revoked'} and all(type(x[k])is str and len(x[k])>0 for k in TUPLE) and u64(x['generation']) and all(re.fullmatch(UUID,x[k]) is not None for k in ('project_uuid','document_uuid','session_uuid','preview_session')) and type(x['native_live'])is bool and type(x['revoked'])is bool
def close(case,valid_request,valid_error):
 s=deepcopy(case['before']); p=case['provider']; r=case['request'];calls=['native.caller.observe']
 ui='CloseUncertain'
 def finish(code=None,details=None,delivered=False):
  response={'ok':True,'value':{'closed':True,'content_changed':False},'replayed':False} if code is None else {'ok':False,'error':{'code':code,'details':details or {}},'replayed':False}
  return {'response':response,'state':s,'calls':calls,'ui':('Closed' if delivered else ui),'delivered':delivered,'automatic_retry':False}
 def dependency():return finish('DependencyNotReady',{'dependency':'M04_OWNER_INTEGRATION'})
 if type(p)is not dict or set(p)!={'trusted_local','role','origin','capture','delivery','ready','outcome','closed_observation'} or type(p['trusted_local'])is not bool or type(p['ready'])is not bool or type(p['role'])is not str or type(p['origin'])is not str or not identity(p['capture']) or not identity(p['delivery']):return dependency()
 c=p['capture']
 if not p['trusted_local'] or p['role']not in ('main','ui-editor','ui-viewer') or p['origin']not in ('tauri://localhost','http://tauri.localhost','https://tauri.localhost') or not c['native_live']:return finish('UnauthorizedCaller')
 if not valid_request(r):
  if type(r)is not dict:return finish('InvalidRequest',{'field':'/','reason':'Type'})
  unknown=sorted(set(r)-{'preview_session'})
  if unknown:return finish('InvalidRequest',{'field':'/'+unknown[0].replace('~','~0').replace('/','~1'),'reason':'UnknownField'})
  if 'preview_session'not in r:return finish('InvalidRequest',{'field':'/preview_session','reason':'MissingField'})
  return finish('InvalidRequest',{'field':'/preview_session','reason':'Type' if type(r['preview_session'])is not str else 'InvalidUuid'})
 calls.append('native.preview.resolve')
 if r['preview_session']!=s['identity']['preview_session'] or not s['preview_active'] or c['revoked']:return finish('PreviewClosed')
 for keys,code in [(('consumer','window_instance'),'UnauthorizedCaller'),(('project_uuid','root_instance','runtime_epoch','document_uuid','session_uuid'),'MissingBinding'),(('generation',),'StaleOwner'),(('preview_session',),'PreviewClosed')]:
  if any(c[k]!=s['identity'][k] for k in keys):return finish(code)
 if not p['ready']:return dependency()
 calls.append('provider.preview.close')
 outcome=p['outcome']
 if type(outcome)is str and outcome=='ResponseLostAfterCommit':
  # Explicit failure-injection premise: provider committed but supplied no proof.
  # This is NOT a successful closed observation and must never deliver Closed.
  calls.append('preview.retire.unacknowledged')
  s['preview_active']=False;s['mock']={};s['capabilities']=[];s['slots']-=1
  return dependency()
 if type(outcome)is dict:
  if not valid_error(outcome) or outcome['code']not in ('PreviewClosed','Busy','StaleOwner','MissingBinding','DependencyNotReady'):return dependency()
  return finish(outcome['code'],deepcopy(outcome['details']))
 if type(outcome)is not str or outcome!='Closed':return dependency()
 proof=p['closed_observation']
 if type(proof)is not dict or set(proof)!=set(TUPLE)|{'closed','mock_discarded'} or any(type(proof[k])is not str or proof[k]!=c[k] for k in TUPLE) or proof['closed']is not True or proof['mock_discarded']is not True:return dependency()
 # This models an authenticated atomic provider result. It cannot establish that
 # real provider authenticity, atomicity or slot accounting exists.
 calls.append('preview.retire.observed')
 s['preview_active']=False;s['mock']={};s['capabilities']=[];s['slots']-=1
 calls.append('native.delivery.recheck')
 d=p['delivery']
 if not d['native_live'] or d['revoked']:return finish('PreviewClosed')
 for keys,code in [(('consumer','window_instance'),'UnauthorizedCaller'),(('project_uuid','root_instance','runtime_epoch','document_uuid','session_uuid'),'MissingBinding'),(('generation',),'StaleOwner'),(('preview_session',),'PreviewClosed')]:
  if any(d[k]!=c[k] for k in keys):return finish(code)
 calls.append('ui.closed.deliver')
 return finish(delivered=True)
