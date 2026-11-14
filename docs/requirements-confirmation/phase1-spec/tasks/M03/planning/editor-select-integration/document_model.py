"""Document-only proposed selection reducer. Native trust/atomicity are premises."""
from copy import deepcopy
import re
MAX=18446744073709551615
U='abcdef01-abcd-4abc-8abc-abcdef012345'
KEYS=('binding_ref','document_uuid','session_uuid','project_uuid','root_instance','runtime_epoch','window_instance','generation')
def u64(x):return type(x)is str and re.fullmatch(r'0|[1-9][0-9]*',x)is not None and len(x)<=20 and int(x)<=MAX
def fresh():
 identity={k:U for k in KEYS};identity.update(root_instance='root-1',runtime_epoch='epoch-1',window_instance='editor-1',generation='7')
 return dict(identity=identity,revision='9',selection=None,nodes=[{'node_id':'node-1','document_uuid':U}],content='immutable',history=['H0'],dirty=False,baseline='F0',pins=['P0'],ack='A0')
def run(case,valid_request):
 s=deepcopy(case['before']);r=case['request'];p=case['provider'];calls=[]
 def finish(code=None,details=None):
  response={'ok':True,'value':{'node_id':r['node_id'],'content_changed':False,'revision':s['revision']},'replayed':False} if code is None else {'ok':False,'error':{'code':code,'details':details or {}},'replayed':False}
  delivered=type(p)is dict and p.get('delivery')==s['identity']
  return dict(response=response,state=s,calls=calls,delivered=delivered,ui='SelectionUpdated' if delivered and code is None else ('Rejected' if delivered else 'Discarded'),automatic_retry=False)
 if not valid_request(r):return finish('InvalidRequest',{'field':'/','reason':'Type'})
 if not u64(r['expected_generation']) or not u64(r['expected_revision']):return finish('InvalidRequest',{'field':'/','reason':'OutOfRange'})
 calls.append('native.caller.observe')
 if type(p)is not dict or set(p)!={'capture','delivery','role','origin','native_live','ready','outcome'}:return finish('DependencyNotReady',{'dependency':'M04_OWNER_INTEGRATION'})
 if any(type(p[k])is not str for k in ('role','origin','outcome')) or type(p['delivery'])is not dict or set(p['delivery'])!=set(KEYS) or any(type(p['delivery'][k])is not str or len(p['delivery'][k])==0 for k in KEYS) or not u64(p['delivery']['generation']) or type(p['native_live'])is not bool or type(p['ready'])is not bool or type(p['capture'])is not dict or set(p['capture'])!=set(KEYS) or any(type(p['capture'][k])is not str or len(p['capture'][k])==0 for k in KEYS) or not u64(p['capture']['generation']):return finish('ProofMismatch')
 if p['role']not in ('main','ui-editor') or p['origin']!='tauri://localhost' or p['native_live']is not True:return finish('UnauthorizedCaller')
 if p['capture']!=s['identity']:return finish('MissingBinding')
 if r['binding_ref']!=s['identity']['binding_ref']:return finish('MissingBinding')
 if r['expected_generation']!=s['identity']['generation']:return finish('StaleOwner')
 if r['expected_revision']!=s['revision']:return finish('StaleRevision',{'expected':r['expected_revision'],'observed':s['revision']})
 if p['ready']is not True:return finish('DependencyNotReady',{'dependency':'M04_OWNER_INTEGRATION'})
 if type(s['nodes'])is not list or any(type(n)is not dict or set(n)!={'node_id','document_uuid'} or any(type(n[k])is not str or len(n[k])==0 for k in n) for n in s['nodes']):return finish('ProofMismatch')
 ids=[n['node_id'] for n in s['nodes']]
 if len(ids)!=len(set(ids)):return finish('IdentityConflict',{'reference':r['node_id'] or ''})
 if r['node_id']is not None and not any(n['node_id']==r['node_id'] and n['document_uuid']==s['identity']['document_uuid'] for n in s['nodes']):return finish('IdentityConflict',{'reference':r['node_id']})
 calls.append('owner.select_ephemeral')
 if p['outcome']!='Selected':return finish('DependencyNotReady',{'dependency':'M04_OWNER_INTEGRATION'})
 s['selection']=r['node_id']
 return finish()
