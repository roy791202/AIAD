"""Candidate composition mapper only. Owner adoption and native atomicity NOT proved."""
import copy, importlib.util, pathlib
P=pathlib.Path(__file__).resolve().parent
def load(package,name):
 s=importlib.util.spec_from_file_location(package+'_'+name,P.parent/package/(name+'.py'))
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
BEGIN=load('preview-begin-correction','document_model')
INTENT=load('viewer-action-typed-correction','document_model')
REFRESH=load('viewer-refresh-integration','document_model')
CLOSE=load('viewer-close-integration','document_model')
EVAL=load('viewer-refresh-integration','schema_eval')
FIELDS=CLOSE.TUPLE
ROOT=('project_uuid','root_instance','runtime_epoch','document_uuid','session_uuid')
def read(package,file):
 import json
 return json.loads((P.parent/package/file).read_text(encoding='utf-8-sig'))
def schema(package,file):
 root=read(package,file);return lambda x:EVAL.valid(root,x)
def identity(authority,handle):
 return {**{k:authority[k] for k in FIELDS if k!='preview_session'},'preview_session':handle,'native_live':True,'revoked':False}
def admit(authority,entry,capture,delivery):
 """Proposed pre-dispatch guard avoids lossy legacy boolean aliases. No IO."""
 if not CLOSE.identity(capture) or not CLOSE.identity(delivery):return 'DependencyNotReady'
 expected=identity(authority,entry['handle'])
 for observed in (capture,delivery):
  if not observed['native_live'] or observed['revoked']:return 'PreviewClosed'
  for keys,code in [(('consumer','window_instance'),'UnauthorizedCaller'),(ROOT,'MissingBinding'),(('generation',),'StaleOwner'),(('preview_session',),'PreviewClosed')]:
   if any(observed[k]!=expected[k] for k in keys):return code
 return None
def refresh_identity(authority,obs):
 return {'consumer':obs['consumer'],'window':obs['window_instance'],'document':obs['document_uuid'],'session':obs['session_uuid'],'generation':obs['generation'],'revision':authority['revision'],'closed':not obs['native_live'] or obs['revoked']}
def begin_case(authority,projection):
 c=copy.deepcopy(read('preview-begin-correction','fixtures.json')[0])
 c['before'].update(generation=authority['generation'],revision=authority['revision'],consumer_instance=authority['consumer'],document_identity=authority['document_uuid'],preview_count=0)
 c['request'].update(expected_generation=authority['generation'],expected_revision=authority['revision'])
 c['provider_projection']=copy.deepcopy(projection)
 return c
def refresh_case(authority,entry,projection,capture,delivery):
 c=copy.deepcopy(read('viewer-refresh-integration','new-fixtures.json')[0])
 c['before'].update(refresh_identity(authority,capture));c['before'].update(preview_session=entry['handle'],sequence=entry['sequence'],projection=copy.deepcopy(entry['projection']),preview_count=1,retired=[])
 c['request']={'preview_session':entry['handle'],'expected_revision':authority['revision']}
 c['provider'].update(capture=refresh_identity(authority,capture),delivery=refresh_identity(authority,delivery),projection=copy.deepcopy(projection))
 return c
def from_projection(authority,projection):
 """Explicit proposed derived-state projection; not a document registry."""
 return {'handle':projection['preview_session'],'sequence':projection['expected_sequence'],'projection':copy.deepcopy(projection),'identity':identity(authority,projection['preview_session']),'active':True,'mock':{n['node_id']:copy.deepcopy(n['value']) for n in projection['mock_state']},'capabilities':copy.deepcopy(projection['capabilities'])}
def intent_case(authority,entry,handle):
 c=copy.deepcopy(read('viewer-action-integration','fixtures.json')[0])
 c['request'].update(preview_session=handle,expected_revision=authority['revision'],sequence=entry['sequence'],node_id='button',action='Activate',payload={})
 c['before'].update(preview_session=entry['handle'],generation=authority['generation'],revision=authority['revision'],sequence=entry['sequence'],closed=not entry['active'],mock=copy.deepcopy(entry['mock']))
 c['premises'].update(trusted_local=True,consumer_matches=True,owner_present=True,document_matches=True,observed_generation=authority['generation'],observed_revision=authority['revision'],provider_ready=True,delivery_change='none')
 return c
def close_case(authority,entry,capture,delivery,outcome='Closed'):
 c=copy.deepcopy(read('viewer-close-integration','fixtures.json')[0])
 c['request']={'preview_session':entry['handle']}
 c['before'].update(identity=copy.deepcopy(entry['identity']),preview_active=entry['active'],mock=copy.deepcopy(entry['mock']),capabilities=copy.deepcopy(entry['capabilities']),slots=1)
 c['provider'].update(capture=copy.deepcopy(capture),delivery=copy.deepcopy(delivery),outcome=outcome,closed_observation={**{k:capture[k] for k in FIELDS},'closed':True,'mock_discarded':True})
 return c
