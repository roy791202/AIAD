"""Document-only candidate reducer; no runtime API or product implementation."""
from copy import deepcopy
UUID='abcdef01-abcd-4abc-8abc-abcdef012345'
TUPLE=('binding_ref','document_uuid','session_uuid','project_uuid','root_instance','runtime_epoch','instance','owner_generation')
class Authority:
 def __init__(self):self.records={}
 def mint(self,observation):
  token=object(); self.records[token]=deepcopy(observation);return token
 def read(self,token):return deepcopy(self.records.get(token))
def fresh():
 observation=dict(binding_ref=UUID,document_uuid=UUID,session_uuid=UUID,project_uuid=UUID,root_instance='root-1',runtime_epoch='epoch-1',instance='editor-1',owner_generation='7',attachment_active=True,native_live=True)
 return {'observation':observation,'revision':'9','dirty':False,'writer':False,'binding':True,'candidates':['candidate-1'],'previews':['preview-1'],'replay_disclosure':['install-1'],'inflight':['save-1','install-1'],'tombstones':{},'capacity':2,'document':{'content':'immutable source','history':['H0','H1'],'revision':'9','formal_baseline':'F0','live_roots':['R1'],'history_roots':['R0'],'writer_generation':'7','closed':False},'calls':{'detach':0,'formal_IO':0,'ACK':0,'material_roots':0,'S1':0}}
def typed(o):
 return type(o)is dict and all(type(o.get(k))is str and bool(o[k]) for k in TUPLE) and type(o.get('attachment_active'))is bool and type(o.get('native_live'))is bool
def delivery(authority,token,issued):
 o=authority.read(token)
 return bool(typed(o) and o['attachment_active'] and o['native_live'] and all(o[k]==issued[k] for k in TUPLE))
def close(state,request,caller,authority,owner_token,integration=True,owner_decision=True):
 if caller['role']not in ('main','ui-editor') or caller['origin']!='tauri://localhost' or not caller['native_live'] or caller['instance']!='editor-1':return 'UnauthorizedCaller'
 if request['binding_ref']!=state['observation']['binding_ref'] or caller['instance']!=state['observation']['instance']:return 'MissingBinding'
 capture=tuple(request[k] for k in ('expected_generation','expected_revision','discard_unsaved'))
 key=(request['binding_ref'],caller['instance'],state['observation']['runtime_epoch'])
 if not state['binding']:return 'Closed' if state['tombstones'].get(key)==capture else 'MissingBinding'
 if not integration or not owner_decision:return 'DependencyNotReady'
 o=authority.read(owner_token)
 if not typed(o) or any(o[k]!=state['observation'][k] for k in TUPLE) or o['attachment_active'] or not o['native_live']:return 'ProofMismatch'
 if request['expected_generation']!=state['observation']['owner_generation']:return 'StaleOwner'
 if request['expected_revision']!=state['revision']:return 'StaleRevision'
 if state['dirty'] and state['writer'] and not request['discard_unsaved']:return 'Busy'
 if len(state['tombstones'])>=state['capacity']:return 'CapacityExceeded'
 state['calls']['detach']+=1
 state['binding']=False;state['observation']['attachment_active']=False
 state['candidates']=[];state['previews']=[];state['replay_disclosure']=[];state['tombstones'][key]=capture
 return 'Closed'
def exercise(mode):
 s=fresh();a=Authority();r=dict(binding_ref=UUID,expected_generation='7',expected_revision='9',discard_unsaved=False);c=dict(role='ui-editor',origin='tauri://localhost',instance='editor-1',native_live=True)
 issued=deepcopy(s['observation']); revoked=deepcopy(issued);revoked['attachment_active']=False
 integration=True;decision=True
 if mode=='viewer':c['role']='ui-viewer'
 if mode=='remote':c['origin']='https://remote.invalid'
 if mode=='replacement':c['instance']='editor-2'
 if mode=='foreign':c['role']='main';s['observation']['instance']='other-editor'
 if mode=='missing':r['binding_ref']='00000000-0000-4000-8000-000000000000'
 if mode=='dependency':integration=False
 if mode=='generation':r['expected_generation']='6'
 if mode=='revision':r['expected_revision']='8'
 if mode=='dirty':s['dirty']=True;s['writer']=True
 if mode=='m04-refusal':decision=False
 if mode=='discard-without-owner':s['dirty']=True;s['writer']=True;r['discard_unsaved']=True;decision=False
 if mode=='writer':s['dirty']=True;s['writer']=True;r['discard_unsaved']=True
 if mode=='capacity':s['tombstones']={('old1',):(),('old2',):()}
 if mode=='bad-detach':revoked['session_uuid']='wrong'
 before=deepcopy(s);result=close(s,r,c,a,a.mint(revoked),integration,decision)
 if mode in ('repeat','changed'):
  assert result=='Closed'
  if mode=='changed':r['discard_unsaved']=True
  before=deepcopy(s)
  result=close(s,r,c,a,a.mint(revoked))
 if mode=='epoch':
  s=fresh();s['binding']=False;s['observation']['runtime_epoch']='epoch-2';before=deepcopy(s);result=close(s,r,c,a,a.mint(revoked))
 if mode in ('late-get','late-install','late-ack','missing-observation','forged-observation','delivery-generation','typed-observation'):
  o=deepcopy(s['observation'])
  if mode=='delivery-generation':o['owner_generation']='8';o['attachment_active']=True
  if mode=='typed-observation':o['attachment_active']='false'
  token=a.mint(o)
  if mode=='missing-observation':token=None
  if mode=='forged-observation':token=object()
  result='Delivered' if delivery(a,token,issued) else 'Discarded'
 assert s['document']==before['document'],'close changed authoritative document'
 assert all(s['calls'][k]==0 for k in ('formal_IO','ACK','material_roots','S1'))
 if result not in ('Closed','Discarded'):assert s==before,'failed close changed state'
 if result=='Closed':assert not s['binding'] and not s['candidates'] and not s['previews'] and not s['replay_disclosure'] and s['inflight']==before['inflight']
 return {'result':result,'document_unchanged':True,'formal_IO_ACK_material_S1_calls':0,'detach_calls':s['calls']['detach']}
