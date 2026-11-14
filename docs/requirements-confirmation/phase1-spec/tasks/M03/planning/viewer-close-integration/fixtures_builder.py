"""Enumerate expectations independently of reducer execution."""
import copy,json,pathlib
from document_model import TUPLE
P=pathlib.Path(__file__).resolve().parent
U='abcdef01-abcd-4abc-8abc-abcdef012345'
V='00000000-0000-4000-8000-000000000000'
ID=dict(consumer='consumer-1',window_instance='native-window-1',project_uuid=U,root_instance='root-1',runtime_epoch='epoch-1',document_uuid=U,session_uuid=U,generation='7',preview_session=U,native_live=True,revoked=False)
before={'identity':ID,'preview_active':True,'stale':False,'slots':1,'mock':{'toggle':True},'capabilities':['SetToggle'],'binding_attached':True,'document_open':True,'content':'unchanged','history':['h0','h1'],'revision':'11','dirty':True,'formal_baseline':'f0','snapshot_baseline':'s0','ACK':'none','pins':['p1'],'live_roots':['r1'],'undo_roots':['r0']}
provider={'trusted_local':True,'role':'ui-viewer','origin':'tauri://localhost','capture':copy.deepcopy(ID),'delivery':copy.deepcopy(ID),'ready':True,'outcome':'Closed','closed_observation':{**{k:ID[k] for k in TUPLE},'closed':True,'mock_discarded':True}}
template={'request':{'preview_session':U},'provider':provider,'before':before}
cases=[]
def add(name,edit=lambda c:None,code=None,details=None,stage='success',retired=False):
 c=copy.deepcopy(template);edit(c);s=copy.deepcopy(c['before']);calls=['native.caller.observe']
 if stage not in ('admission','request'):calls.append('native.preview.resolve')
 if stage in ('provider','proof','late','success','lost'):calls.append('provider.preview.close')
 if stage=='lost':
  s['preview_active']=False;s['mock']={};s['capabilities']=[];s['slots']-=1
  calls.append('preview.retire.unacknowledged')
 if retired or stage=='success':
  s['preview_active']=False;s['mock']={};s['capabilities']=[];s['slots']-=1
  calls.extend(['preview.retire.observed','native.delivery.recheck'])
 if stage=='success':calls.append('ui.closed.deliver')
 response={'ok':True,'value':{'closed':True,'content_changed':False},'replayed':False} if code is None else {'ok':False,'error':{'code':code,'details':details or {}},'replayed':False}
 bdd=8 if stage=='lost' else (7 if name=='repeat removed handle' else (2 if 'four-slot' in name else (5 if stage=='late' or name.startswith('late ') else (4 if stage=='request' else (6 if stage in ('provider','proof') or code=='DependencyNotReady' else (3 if code is not None else 1))))))
 c.update(id='CLOSE-'+str(len(cases)+1).zfill(3),name=name,bdd='CLOSE-'+str(bdd).zfill(3),expected={'response':response,'state':s,'calls':calls,'ui':'Closed' if stage=='success' else 'CloseUncertain','delivered':stage=='success','automatic_retry':False});cases.append(c)
dep={'dependency':'M04_OWNER_INTEGRATION'}
add('same-consumer close')
add('stale-preview cleanup',lambda c:c['before'].update(stale=True))
add('full four-slot close releases one',lambda c:c['before'].update(slots=4))
for role in ('main','ui-editor'):add('same-consumer '+role,lambda c,role=role:c['provider'].update(role=role))
for origin in ('http://tauri.localhost','https://tauri.localhost'):add(origin,lambda c,origin=origin:c['provider'].update(origin=origin))
for name,edit in [('untrusted',lambda c:c['provider'].update(trusted_local=False)),('remote',lambda c:c['provider'].update(origin='https://remote.invalid')),('dev-port',lambda c:c['provider'].update(origin='http://tauri.localhost:1420')),('role',lambda c:c['provider'].update(role='other')),('destroyed',lambda c:c['provider']['capture'].update(native_live=False))]:add(name,edit,'UnauthorizedCaller',stage='admission')
for key in ('trusted_local','ready'):
 for value in (None,0,1,'true',[],{}):add('typed '+key+' '+repr(value),lambda c,k=key,v=value:c['provider'].update({k:v}),'DependencyNotReady',dep,'admission')
for part in ('capture','delivery'):
 for key in ID:
  add('missing '+part+'/'+key,lambda c,p=part,k=key:c['provider'][p].pop(k),'DependencyNotReady',dep,'admission')
 for key in ('native_live','revoked'):
  for value in (1,'false',None):add('typed '+part+'/'+key+' '+repr(value),lambda c,p=part,k=key,v=value:c['provider'][p].update({k:v}),'DependencyNotReady',dep,'admission')
 for value in ('-1','01','18446744073709551616','7\n',7):add('u64 '+part+' '+repr(value),lambda c,p=part,v=value:c['provider'][p].update(generation=v),'DependencyNotReady',dep,'admission')
 add('extra '+part,lambda c,p=part:c['provider'][p].update(extra=True),'DependencyNotReady',dep,'admission')
for name,r,field,reason in [('root',[], '/', 'Type'),('missing',{},'/preview_session','MissingField'),('unknown',{'preview_session':U,'discard_unsaved':True},'/discard_unsaved','UnknownField'),('typed',{'preview_session':True},'/preview_session','Type'),('empty',{'preview_session':''},'/preview_session','InvalidUuid'),('newline',{'preview_session':U+'\n'},'/preview_session','InvalidUuid')]:add(name,lambda c,r=r:c.update(request=r),'InvalidRequest',{'field':field,'reason':reason},'request')
add('wrong handle',lambda c:c['request'].update(preview_session=V),'PreviewClosed',stage='resolve')
add('repeat removed handle',lambda c:c['before'].update(preview_active=False,mock={},capabilities=[],slots=0),'PreviewClosed',stage='resolve')
add('revoked preview',lambda c:c['provider']['capture'].update(revoked=True),'PreviewClosed',stage='resolve')
for key in TUPLE:
 code='UnauthorizedCaller' if key in ('consumer','window_instance') else ('StaleOwner' if key=='generation' else ('PreviewClosed' if key=='preview_session' else 'MissingBinding'))
 value='8' if key=='generation' else (V if key.endswith('_uuid') or key=='preview_session' else 'other')
 add('capture mismatch '+key,lambda c,k=key,v=value:c['provider']['capture'].update({k:v}),code,stage='resolve')
 add('late mismatch '+key,lambda c,k=key,v=value:c['provider']['delivery'].update({k:v}),code,stage='late',retired=True)
add('provider unavailable',lambda c:c['provider'].update(ready=False),'DependencyNotReady',dep,'resolve')
for code,details in [('PreviewClosed',{}),('Busy',{}),('StaleOwner',{}),('MissingBinding',{}),('DependencyNotReady',dep)]:add('provider rejected '+code,lambda c,code=code,d=details:c['provider'].update(outcome={'code':code,'details':d}),code,details,'provider')
for value in (None,True,'closed',{}, {'code':'PreviewClosed','details':{'extra':1}}):add('malformed outcome '+repr(value),lambda c,v=value:c['provider'].update(outcome=v),'DependencyNotReady',dep,'provider')
for key in (*TUPLE,'closed','mock_discarded'):
 add('missing proof '+key,lambda c,k=key:c['provider']['closed_observation'].pop(k),'DependencyNotReady',dep,'proof')
 value='8' if key=='generation' else (V if key.endswith('_uuid') or key=='preview_session' else 'wrong')
 add('wrong proof '+key,lambda c,k=key,v=value:c['provider']['closed_observation'].update({k:v}),'DependencyNotReady',dep,'proof')
for key in ('closed','mock_discarded'):
 for value in (False,1,'true',None):add('typed proof '+key+' '+repr(value),lambda c,k=key,v=value:c['provider']['closed_observation'].update({k:v}),'DependencyNotReady',dep,'proof')
add('extra proof',lambda c:c['provider']['closed_observation'].update(extra=True),'DependencyNotReady',dep,'proof')
add('late revoked',lambda c:c['provider']['delivery'].update(revoked=True),'PreviewClosed',stage='late',retired=True)
add('late destroyed',lambda c:c['provider']['delivery'].update(native_live=False),'PreviewClosed',stage='late',retired=True)
add('provider committed then response lost',lambda c:c['provider'].update(outcome='ResponseLostAfterCommit',closed_observation=None),'DependencyNotReady',dep,'lost')
(P/'fixtures.json').write_text(json.dumps(cases,indent=2)+'\n',encoding='utf-8')
