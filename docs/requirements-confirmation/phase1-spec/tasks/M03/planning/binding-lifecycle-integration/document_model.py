"""Pure proposed document oracle, not an implementation Skeleton or runtime owner."""
import copy, json, pathlib
P=pathlib.Path(__file__).resolve().parent
UID='abcdef01-abcd-4abc-8abc-abcdef012345'
DOC='abcdef02-abcd-4abc-8abc-abcdef012345'
SESSION='abcdef03-abcd-4abc-8abc-abcdef012345'
PROJECT='abcdef04-abcd-4abc-8abc-abcdef012345'
def error(code,details=None):return {'ok':False,'error':{'code':code,'details':details or {}},'replayed':False}
def success(value):return {'ok':True,'value':copy.deepcopy(value),'replayed':False}
def deliver(display,pending,response,current):
 """Pure UI projection ordering oracle; never applies any owner mutation/ACK."""
 before=copy.deepcopy(display)
 if not response['ok']:return before,'DiagnosticOnly'
 value=response['value']
 if not current['live'] or pending['instance']!=current['instance']:return before,'DiscardRetiredInstance'
 for field in ['binding_ref','document_uuid','session_uuid','owner_generation']:
  if pending[field]!=current[field] or value[field]!=current[field]:return before,'DiscardStaleAuthority'
 if int(value['revision'])<int(display['revision']):return before,'DiscardOlderProjection'
 return copy.deepcopy(value),'InstalledProjectionOnly'
def delivery_fixtures():
 projection={'binding_ref':UID,'document_uuid':DOC,'session_uuid':SESSION,'owner_generation':'7','revision':'9','design_json':'{"nodes":[]}','dirty':True,'can_edit':False,'unsupported':[],'selection':None,'persistence_ready':False}
 current={k:projection[k] for k in ['binding_ref','document_uuid','session_uuid','owner_generation']};current.update(instance='native-main-1',live=True)
 pending=copy.deepcopy(current);cases=[]
 def add(id,change=None,revision=None,expected='InstalledProjectionOnly'):
  c=copy.deepcopy(current);c.update(change or {});v=copy.deepcopy(projection)
  if revision:v['revision']=revision
  after=v if expected=='InstalledProjectionOnly' else projection
  cases.append({'id':id,'display':copy.deepcopy(projection),'pending':copy.deepcopy(pending),'response':success(v),'current':c,'expected_display':copy.deepcopy(after),'expected_status':expected,'formal_ACK':'NOT CALLED','material_pin':'NOT CALLED','save_proof':'NOT APPLICABLE'})
 add('BG-delivery-current')
 add('BG-delivery-newer',revision='9007199254740993')
 add('BG-delivery-older',revision='8',expected='DiscardOlderProjection')
 add('BG-delivery-replaced',{'instance':'native-main-2'},expected='DiscardRetiredInstance')
 add('BG-delivery-closed',{'live':False},expected='DiscardRetiredInstance')
 add('BG-delivery-transfer',{'owner_generation':'8'},expected='DiscardStaleAuthority')
 add('BG-delivery-root-switch',{'document_uuid':'abcdef08-abcd-4abc-8abc-abcdef012345'},expected='DiscardStaleAuthority')
 add('BG-delivery-restart-session',{'session_uuid':'abcdef09-abcd-4abc-8abc-abcdef012345'},expected='DiscardStaleAuthority')
 return cases
def reduce(state,command,request,caller,evidence):
 """No authoritative mutation. Dependencies are immutable fixture observations only."""
 from schema_subset import Draft202012Validator
 out=copy.deepcopy(state);calls=[]
 allowed=['main','ui-editor'] if command=='open' else ['main','ui-editor','ui-viewer']
 if caller['role']not in allowed or caller['origin']not in ['tauri://localhost','http://tauri.localhost','https://tauri.localhost'] or not caller['live_native_instance']:
  return out,error('UnauthorizedCaller'),calls
 schema=json.loads((P/('h2-design_binding_'+command+'-request.schema.json')).read_text(encoding='utf8'))
 try:Draft202012Validator(schema).validate(request)
 except AssertionError:
  unknown=next((k for k in request if k not in schema['properties']),None)
  missing=next((k for k in schema['required']if k not in request),None)
  field='/'+(unknown or missing or next(iter(schema['properties'])))
  malformed=next(iter(schema['properties']))
  reason='UnknownField' if unknown else 'MissingField' if missing else 'Type' if not isinstance(request.get(malformed),str) else 'InvalidUuid'
  return out,error('InvalidRequest',{'field':field,'reason':reason}),calls
 if command=='get':
  binding=out['attachments'].get(request['binding_ref'])
  if not binding:return out,error('MissingBinding'),calls
  if binding['instance']!=caller['instance']:return out,error('UnauthorizedCaller'),calls
  if not binding['active']:return out,error('MissingBinding'),calls
 else:
  binding=None
  if request['document_reference']not in ['trusted-document']:return out,error('MissingBinding'),calls
 if not evidence['dependency_ready']:return out,error('DependencyNotReady',{'dependency':'M04_OWNER_INTEGRATION'}),calls
 calls.append('M04.attach_document' if command=='open' else 'M04.get_projection')
 # Local trusted fixture authority is an oracle input, never a proposed runtime registry.
 authority=json.loads((P/'trusted-fixture-authority.json').read_text(encoding='utf8'))
 trusted=authority['observations'].get(evidence['observation_ref'])
 if trusted is None or trusted!=evidence['observation']:return out,error('ProofMismatch'),calls
 observation=trusted
 if observation['native_instance']!=caller['instance']:return out,error('UnauthorizedCaller'),calls
 if observation['project_uuid']!=out['trusted_project_uuid'] or observation['document_uuid']!=out['trusted_document_uuid']:
  return out,error('IdentityConflict',{'reference':'trusted-document'}),calls
 if not observation['adopted_identity']:return out,error('MissingBinding'),calls
 if binding and (binding['session_uuid']!=observation['session_uuid'] or binding['owner_generation']!=observation['owner_generation']):return out,error('StaleOwner'),calls
 projection=copy.deepcopy(observation['projection'])
 if any(projection[k]!=observation[k] for k in ['document_uuid','session_uuid','owner_generation']):return out,error('ProofMismatch'),calls
 if projection['revision']!=out['revision']:return out,error('ProofMismatch'),calls
 if binding and projection['binding_ref']!=request['binding_ref']:return out,error('ProofMismatch'),calls
 # can_edit is derived from current M04 writer + supported content, never from a UI label.
 projection['can_edit']=observation['writer_instance']==caller['instance'] and not projection['unsupported'] and observation['has_form']
 if command=='open':
  ref=projection['binding_ref']
  existing=out['attachments'].get(ref)
  proposed={'instance':caller['instance'],'session_uuid':observation['session_uuid'],'owner_generation':observation['owner_generation'],'active':True,'opaque_handle':observation['opaque_handle']}
  if existing is not None and existing!=proposed:return out,error('IdentityConflict',{'reference':'trusted-document'}),calls
  out['attachments'][ref]=proposed
 return out,success(projection),calls
def fixtures():
 projection={'binding_ref':UID,'document_uuid':DOC,'session_uuid':SESSION,'owner_generation':'7','revision':'9','design_json':'{"nodes":[{"id":"root","type":"Form"}]}','dirty':True,'can_edit':True,'unsupported':[],'selection':None,'persistence_ready':False}
 observation={'native_instance':'native-main-1','project_uuid':PROJECT,'document_uuid':DOC,'session_uuid':SESSION,'owner_generation':'7','adopted_identity':True,'opaque_handle':'fixture-m04-handle-A','writer_instance':'native-main-1','has_form':True,'projection':projection}
 authority={'meaning':'Immutable fixture-owned authenticated M04 observations only; no runtime registry or production issuer capability proposed','trust_boundary':'Wire bodies cannot mint observation_ref or replace native sender. Fixture lookup simulates internal M04 input result and authenticated context comparison. Real issuer/native verification NOT RUN.','observations':{'attached-main':copy.deepcopy(observation)}}
 def obs(ref,changes):
  v=copy.deepcopy(observation)
  for k,val in changes.items():v[k]=copy.deepcopy(val)
  authority['observations'][ref]=v
 obs('nonwriter',{'writer_instance':'native-editor-2'})
 p=copy.deepcopy(projection);p['unsupported']=[{'node_id':'alien','type':'Unknown','reason':'unsupported'}];p['design_json']='{"nodes":[{"id":"alien","type":"Unknown","opaque":1}]}'
 obs('unsupported',{'projection':p})
 p=copy.deepcopy(projection);p['design_json']='{"nodes":[]}'
 obs('missing-form',{'has_form':False,'projection':p})
 obs('foreign-project',{'project_uuid':'abcdef05-abcd-4abc-8abc-abcdef012345'})
 obs('foreign-document',{'document_uuid':'abcdef06-abcd-4abc-8abc-abcdef012345'})
 obs('not-adopted',{'adopted_identity':False})
 p=copy.deepcopy(projection);p['owner_generation']='8'
 obs('transferred',{'owner_generation':'8','projection':p,'writer_instance':'native-editor-2'})
 p=copy.deepcopy(projection);p['session_uuid']='abcdef07-abcd-4abc-8abc-abcdef012345'
 obs('new-session',{'session_uuid':p['session_uuid'],'projection':p})
 p=copy.deepcopy(projection);p['owner_generation']='8'
 obs('projection-mismatch',{'projection':p})
 viewer=copy.deepcopy(observation);viewer['native_instance']='native-viewer-1';viewer['writer_instance']='native-main-1';authority['observations']['attached-viewer']=viewer
 (P/'trusted-fixture-authority.json').write_text(json.dumps(authority,indent=2)+'\n',encoding='utf8')
 base={'trusted_project_uuid':PROJECT,'trusted_document_uuid':DOC,'content':{'immutable_fixture':'content-A'},'history':['history-A'],'baselines':{'formal':'formal-A','recovery':'recovery-A'},'revision':'9','attachments':{}}
 caller={'role':'main','origin':'tauri://localhost','instance':'native-main-1','live_native_instance':True}
 attached=copy.deepcopy(base);attached['attachments'][UID]={'instance':'native-main-1','session_uuid':SESSION,'owner_generation':'7','active':True,'opaque_handle':'fixture-m04-handle-A'}
 cases=[]
 def add(id,command='open',state=None,request=None,who=None,ref='attached-main',ready=True,response=None,after=None,calls=None,tamper=None):
  state=copy.deepcopy(base if state is None else state);e={'dependency_ready':ready,'observation_ref':ref,'observation':copy.deepcopy(authority['observations'].get(ref,observation))}
  if tamper:e['observation'].update(tamper)
  cases.append({'id':id,'BDD':id,'command':command,'state':state,'request':request if request is not None else {'document_reference':'trusted-document'} if command=='open' else {'binding_ref':UID},'caller':who or copy.deepcopy(caller),'evidence':e,'expected_response':response or success(projection),'expected_after':copy.deepcopy(state if after is None else after),'expected_calls':calls if calls is not None else ['M04.attach_document' if command=='open' else 'M04.get_projection']})
 add('BG-01-open',after=attached)
 add('BG-02-get',command='get',state=attached)
 add('BG-03-repeat-open',state=attached,after=attached)
 add('BG-04-repeat-get',command='get',state=attached)
 add('BG-05-missing-integration',ready=False,response=error('DependencyNotReady',{'dependency':'M04_OWNER_INTEGRATION'}),calls=[])
 for id,request in [('empty',{'document_reference':''}),('unknown',{'document_reference':'unbound'}),('path',{'document_reference':'D:/secret/design.json'})]:add('BG-reference-'+id,request=request,response=error('MissingBinding'),calls=[])
 for id,change in [('remote',{'origin':'https://example.invalid'}),('port',{'origin':'http://tauri.localhost:8080'}),('dev',{'origin':'http://localhost:1420'}),('retired',{'live_native_instance':False}),('role',{'role':'ui-viewer'})]:
  c=copy.deepcopy(caller);c.update(change);add('BG-native-'+id,who=c,response=error('UnauthorizedCaller'),calls=[])
 add('BG-unknown-field',request={'document_reference':'trusted-document','request_id':UID},response=error('InvalidRequest',{'field':'/request_id','reason':'UnknownField'}),calls=[])
 add('BG-missing-field',request={},response=error('InvalidRequest',{'field':'/document_reference','reason':'MissingField'}),calls=[])
 add('BG-type-field',request={'document_reference':7},response=error('InvalidRequest',{'field':'/document_reference','reason':'Type'}),calls=[])
 add('BG-get-invalid-uuid',command='get',state=attached,request={'binding_ref':UID+'\n'},response=error('InvalidRequest',{'field':'/binding_ref','reason':'InvalidUuid'}),calls=[])
 add('BG-get-unknown-request-id',command='get',state=attached,request={'binding_ref':UID,'request_id':UID},response=error('InvalidRequest',{'field':'/request_id','reason':'UnknownField'}),calls=[])
 for id,ref in [('project','foreign-project'),('document','foreign-document')]:add('BG-identity-'+id,ref=ref,response=error('IdentityConflict',{'reference':'trusted-document'}))
 add('BG-no-adoption',ref='not-adopted',response=error('MissingBinding'))
 add('BG-forged-observation',tamper={'writer_instance':'attacker'},response=error('ProofMismatch'))
 add('BG-unknown-issuer-record',ref='fake-record',response=error('ProofMismatch'))
 for id,ref in [('generation','transferred'),('session','new-session')]:add('BG-stale-'+id,command='get',state=attached,ref=ref,response=error('StaleOwner'))
 add('BG-projection-mismatch',ref='projection-mismatch',response=error('ProofMismatch'))
 add('BG-get-missing',command='get',response=error('MissingBinding'),calls=[])
 c=copy.deepcopy(caller);c['instance']='native-main-replacement';add('BG-instance-replaced',command='get',state=attached,who=c,response=error('UnauthorizedCaller'),calls=[])
 closed=copy.deepcopy(attached);closed['attachments'][UID]['active']=False;add('BG-external-closed',command='get',state=closed,response=error('MissingBinding'),calls=[])
 add('BG-restart-old-reference',command='get',response=error('MissingBinding'),calls=[])
 for id,ref in [('nonwriter','nonwriter'),('unsupported','unsupported'),('missing-form','missing-form')]:
  p=copy.deepcopy(authority['observations'][ref]['projection']);p['can_edit']=False;add('BG-readonly-'+id,ref=ref,response=success(p),after=attached)
 viewer_state=copy.deepcopy(attached);viewer_state['attachments'][UID]['instance']='native-viewer-1';c=copy.deepcopy(caller);c.update(role='ui-viewer',instance='native-viewer-1');p=copy.deepcopy(projection);p['can_edit']=False
 add('BG-viewer-explicit-read',command='get',state=viewer_state,who=c,ref='attached-viewer',response=success(p))
 add('BG-viewer-no-attachment',command='get',who=c,ref='attached-viewer',response=error('MissingBinding'),calls=[])
 return cases
