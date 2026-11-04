"""Author document checks only, never independent acceptance or production tests."""
import copy,hashlib,html,json,pathlib,subprocess,sys
sys.dont_write_bytecode=True
P=pathlib.Path(__file__).resolve().parent
ROOT=next(x for x in P.parents if (x/'.git').exists())
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(n,x):(P/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
from document_model import fixtures,reduce,success,error,UID,deliver,root_type,AUTHORITY_FIELDS
basecases=fixtures();seed=basecases[1];projection=seed['expected_response']['value'];pending={k:projection[k] for k in ['binding_ref','document_uuid','session_uuid','owner_generation']}
pending.update(instance='native-main-1',project_uuid=seed['state']['trusted_project_uuid'],root_instance='root-instance-1',runtime_epoch='runtime-1')
authority={};deliveries=[]
def add_delivery(name,change=None,expected='InstalledProjectionOnly',missing=None,wire=None,rev='10'):
 obs=dict(pending,attachment_active=True,native_live=True);obs.update(change or {})
 if missing:obs.pop(missing)
 authority[name]=obs
 current={'observation_ref':name,'observation':copy.deepcopy(obs)}
 if wire:current.update(wire)
 v=copy.deepcopy(projection);v['revision']=rev
 deliveries.append({'id':'COR-R2-'+name,'display':projection,'pending':pending,'response':success(v),'current':current,'expected_status':expected,'expected_display':v if expected=='InstalledProjectionOnly' else projection})
add_delivery('current')
add_delivery('older',expected='DiscardOlderProjection',rev='8')
add_delivery('external-revoked-live',{'attachment_active':False},'DiscardRevokedAttachment',wire={'attachment_active':True})
add_delivery('retired',{'native_live':False},'DiscardRetiredInstance')
for k in AUTHORITY_FIELDS:add_delivery('changed-'+k,{k:pending[k]+'-replacement'},'DiscardStaleAuthority')
for k in AUTHORITY_FIELDS+['attachment_active','native_live']:
 add_delivery('missing-'+k,expected='DiscardMissingTrustedObservation',missing=k)
 for value,label in [(None,'null'),(False,'bool'),(17,'number'),([], 'array'),({},'object')]:
  if k in ['attachment_active','native_live'] and value is False:continue
  add_delivery('typed-'+k+'-'+label,{k:value},'DiscardMissingTrustedObservation')
 if k in ['attachment_active','native_live']:add_delivery('typed-'+k+'-stringfalse',{k:'false'},'DiscardMissingTrustedObservation')
# Wire-provided flags cannot mint a fixture-owned current observation.
add_delivery('forged');deliveries[-1]['current']={'observation_ref':'absent','attachment_active':True,'native_live':True};deliveries[-1]['expected_status']='DiscardMissingTrustedObservation';deliveries[-1]['expected_display']=projection
add_delivery('tamper');deliveries[-1]['current']['observation']['attachment_active']=False;deliveries[-1]['expected_status']='DiscardMissingTrustedObservation';deliveries[-1]['expected_display']=projection
for label,current in [('root-null',None),('root-array',[]),('root-string','x'),('ref-null',{'observation_ref':None}),('ref-array',{'observation_ref':[]}),('ref-object',{'observation_ref':{}}),('observation-null',{'observation_ref':'current','observation':None})]:
 c=copy.deepcopy(deliveries[0]);c.update(id='COR-R2-context-'+label,current=current,expected_status='DiscardMissingTrustedObservation',expected_display=projection);deliveries.append(c)
write('delivery-authority.json',{'trust':'Fixture-owned internal authenticated observation result. This is NOT a caller DTO, runtime registry, production issuer or approved port. Lookup equality is a test seam only.','observations':authority})
write('new-delivery-fixtures.json',deliveries)
# Restore inherited delivery checks through corrected trusted fixtures, then replay full lexical baseline.
from check_documents import run
run()
from schema_subset import Draft202012Validator
new=[];rootcases=[]
values=[None,False,True,0,17,-1,1.25,'','trusted-document',[],[1],['document_reference']]
for command in ['open','get']:
 schema=read(P/f'h2-design_binding_{command}-request.schema.json')
 response_schema=read(P/f'h2-design_binding_{command}-response.schema.json')
 for i,value in enumerate(values):
  c=copy.deepcopy(seed);c.update(command=command,request=value)
  before=copy.deepcopy(c['state']);after,result,calls=reduce(c['state'],command,value,c['caller'],c['evidence'])
  expected=error('InvalidRequest',{'field':'','reason':'Type','rootType':root_type(value)})
  assert result==expected and after==before and calls==[],(command,value,result)
  Draft202012Validator(response_schema).validate(result)
  new.append({'id':f'COR-R1-{command}-{i}','request':value,'response':result,'state_unchanged':True,'calls':calls,'exception':False})
  # Unauthorized must win over malformed input and reveal no type/context detail.
  caller=dict(c['caller'],origin='https://invalid.example')
  a,r,cs=reduce(c['state'],command,value,caller,c['evidence']);assert r==error('UnauthorizedCaller') and cs==[] and a==before
  new.append({'id':f'COR-R1-unauthorized-{command}-{i}','response':r,'state_unchanged':True,'calls':cs})
# all four complete root invalid JSON types, including response roots
for name in read(P/'module-spec.json')['roots']:
 schema=read(P/name)
 for i,v in enumerate(values):
  try:Draft202012Validator(schema).validate(v);accepted=True
  except AssertionError:accepted=False
  assert not accepted
  rootcases.append({'id':f'COR-root-{name}-{i}','schema':name,'instance':v,'accepted':accepted})
# Replay the new complete-root type negatives through actual Node grammar validator too.
lex=read(P/'lexical-fixtures.json')
lex.extend({'id':c['id'],'schema':c['schema'],'instance':c['instance'],'expected_accept':False} for c in rootcases)
write('lexical-fixtures.json',lex)
node_new=json.loads(subprocess.check_output(['node',str(P/'probe.cjs')],text=True));assert not node_new['mismatches']
write('new-node-results.json',node_new)
# Unknown then missing then property type then lexical, after caller authentication.
for command in ['open','get']:
 field='document_reference' if command=='open' else 'binding_ref'
 for request,details in [({'z':None},{'field':'/z','reason':'UnknownField'}),({}, {'field':'/'+field,'reason':'MissingField'}),({field:None},{'field':'/'+field,'reason':'Type'})]:
  a,r,cs=reduce(seed['state'],command,request,seed['caller'],seed['evidence']);assert r==error('InvalidRequest',details) and cs==[] and a==seed['state']
  new.append({'id':'COR-precedence-'+command+'-'+details['reason'],'request':request,'response':r,'calls':cs})
write('new-reducer-results.json',new);write('new-root-cases.json',rootcases)
# Frozen old package documents are read-only. Compare actual source hashes to original M01 authority.
authpath=P.parents[2]/'M01/planning/s2-green/source-current.json';auth=read(authpath);actual={n:sha(ROOT/n) if (ROOT/n).is_file() else None for n in auth['source_hashes']}
drift=[n for n,h in actual.items() if h!=auth['source_hashes'][n]]
write('source-current.json',{'HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'historical_M01_HEAD':auth['head'],'authority_count':len(actual),'authority':str(authpath.relative_to(ROOT)),'current_hashes':actual,'drift':drift})
old=P.parent/'binding-lifecycle-integration';review=P.parent/'binding-open-get-review'
write('source-hashes.json',{str(f.relative_to(ROOT)):sha(f) for folder in [old,review] for f in folder.iterdir() if f.is_file()})
spec=read(P/'module-spec.json');spec.update(author='/root/m03_open_get_correction',revision='binding-open-get-correction-v1',status='PROPOSED_PENDING_INDEPENDENT_REVIEW_AND_OWNER',independent_acceptance='NOT RUN')
spec['tasks'][0]['allowed_files']=['M03/planning/binding-open-get-correction/**'];spec['tasks'][0]['TDD']='check_correction.py; document model only, product valid RED NOT RUN'
spec['tasks'][0]['BDD']='correction.feature + schema.feature + inherited module.feature/case-scenarios.feature'
spec['tasks'][0]['status']='AUTHOR_DOCUMENT_CHECKED_PENDING_INDEPENDENT_REVIEW'
spec['tasks'][0]['id']='BG-OPEN-GET-CORRECTION'
spec['primary_new_evidence']={'BG-R1':'54 new reducer/precedence + 48 complete-root type cases','BG-R2':'81 new trusted delivery cases','regression_only':'408 complete roots + 335 physical pattern definitions + 35 reducer cases'}
spec['diagnostic_policy']={'status':'PROPOSED_PENDING_OWNER','precedence':['native caller authorization','request root type','lexicographically sorted unknown fields','schema required order missing fields','property types','lexical UUID','binding lookup','dependency availability','trusted observation identity'],'non_object':{'field':'','reason':'Type','rootType':'null|boolean|number|string|array'},'DTO_change':'Add rootType only for non-object requests. Existing object InvalidRequest field/reason shape unchanged. rootType is JSON root type; no Python exception text or authority metadata.'}
spec['trusted_delivery_seam']={'status':'PROPOSED_PENDING_OWNER_NOT_PRODUCT_SKELETON','fields':AUTHORITY_FIELDS+['attachment_active:boolean','native_live:boolean'],'provider':'Current authenticated internal attachment/M04/native observation at delivery; not pending snapshot, UI flag or label. Missing or malformed observation fails closed. No liveness-as-authority inference.','invalidation':'External attachment revocation discards even when native_live=true. runtime epoch, project, root instance, native instance, binding, document, session, generation compared independently.','commands':'close and transfer definitions remain deferred; no new lifecycle implementation authorized.'}
spec['contract']['C7']+=' Current trusted attachment_active=false independently revokes delivery even while native window remains live; missing typed current observation discards.'
spec['UI_schema']['success']='Install only after trusted current attachment authority and complete tuple comparison, then nondecreasing revision.'
write('module-spec.json',spec)
schema_changes=[]
for name in spec['roots']:
 old_root=read(old/name);new_root=read(P/name)
 if '-request.' in name:assert old_root==new_root
 else:
  old_copy=copy.deepcopy(old_root);new_copy=copy.deepcopy(new_root)
  for root in [old_copy,new_copy]:
   for variant in root['$defs']['Error']['oneOf']:
    if variant['properties']['code'].get('enum')==['InvalidRequest']:variant['properties']['details']={}
  assert old_copy==new_copy,'Unrelated schema change '+name
 schema_changes.append({'root':name,'before_sha256':sha(old/name),'after_sha256':sha(P/name),'before':old_root,'after':new_root,'only_change':'InvalidRequest details adds closed non-object rootType branch; reason remains Type' if old_root!=new_root else 'byte-semantic unchanged'})
write('schema-before-after.json',schema_changes)
write('new-policy-choices.json',[{'id':'COR-P1','status':'PROPOSED_PENDING_OWNER','change':'Existing InvalidRequest.details field/reason object is preserved; add separate closed field-empty reason-Type rootType branch for non-object root only. This IS a new DTO shape, not an adopted contract.'},{'id':'COR-P2','status':'PROPOSED_PENDING_OWNER','change':'Internal trusted current typed attachment observation seam at delivery. Fixture-owned equality oracle is only a document model; no new product API, provider implementation or Skeleton is approved.'}])
write('source-input-hashes.json',{str(f.relative_to(ROOT)):sha(f) for f in [ROOT/'AGENTS.md',P.parent/'envelope.json',P.parent/'current-state.json',authpath]})
write('before-after.json',[{'finding':'BG-R1','before':'Non-object root rejection diagnostic crashes while iterating/indexing root','after':'Typed InvalidRequest reason=Type, field empty, rootType; no calls or mutations; authorization precedes validation','policy':'New optional typed diagnostic branch PROPOSED pending Owner'},{'finding':'BG-R2','before':'native live and old tuple may install after external attachment revocation','after':'Current trusted observation checks attachment_active independently; revoked-live discarded; every tuple field and typed presence checked','policy':'New internal observation seam PROPOSED, not implementation skeleton'}])
write('lessons.json',{'BG-R1':'Validation failure diagnostics must accept every JSON root type; rejection is not proof diagnostics cannot throw.','BG-R2':'Window liveness and matching historical owner tuple do not establish current attachment authority; require current trusted revocation observation.','boundary':'Author checks are not acceptance. Close/transfer remain deferred.'})
v=read(P/'verification.json');v.update(author=spec['author'],new_reducer_cases=len(new),new_complete_root_cases=len(rootcases),new_delivery_cases=len(deliveries),new_node=node_new,source_count=len(actual),source_drift=len(drift),independent_acceptance='NOT RUN',Owner='NOT RUN / NOT ADOPTED');write('verification.json',v)
write('acceptance.json',{'author':spec['author'],'independent_verifier':None,'status':'PENDING','Owner':'NOT ADOPTED','implementation':'NOT_READY','criteria':['BG-R1 all non-object JSON roots return typed error without oracle exception/call/mutation','BG-R2 externally revoked live attachment discarded','All complete authority tuple changes discard; missing and wrongly typed observations fail closed','Four strict schema roots and seven DomainRejected shapes retained','No old package/product/board/current-state writes']})
feature='Feature: Corrected complete open and get observation\n  Background:\n    Given the correction remains proposed pending Owner adoption\n  Rule: Invalid roots cannot affect document state\n'
for c in new:
 feature+=f"    Scenario: {c['id']}\n      Given an authorized view or the unauthorized condition explicitly named by this case\n      When the view submits the fixture request\n      Then the exact safe diagnostic is reported\n      And document state remains unchanged\n"
feature+='  Rule: Delivery requires current attachment authority\n'
for c in deliveries:
 feature+=f"    Scenario: {c['id']}\n      Given a projection is pending and the trusted current condition is {c['id']}\n      When the response arrives\n      Then the delivery outcome is {c['expected_status']}\n      And no document acknowledgement or document mutation occurs\n"
(P/'correction.feature').write_text(feature)
(P/'schema.feature').write_text('Feature: All four complete wire roots reject non-object JSON roots\n  Background:\n    Given the complete open and get candidate schemas\n  Rule: An object contract rejects every non-object root\n'+''.join('    Scenario: '+c['id']+'\n      Given the candidate '+c['schema']+' root contract\n      When the non-object fixture is validated\n      Then the complete root is rejected without a validator exception\n' for c in rootcases),encoding='utf8')
(P/'steps.py').write_text('"""Product/native step-definition stubs. Not bound or run; no acceptance claim."""\ndef given_current_attachment(context, fixture_id):\n    raise NotImplementedError("Pending approved native/current attachment observation adapter")\ndef when_view_requests_projection(context):\n    raise NotImplementedError("Pending approved product Skeleton and valid RED")\ndef then_exact_diagnostic_without_mutation(context):\n    raise NotImplementedError("Pending independent product verification")\ndef when_pending_response_arrives(context):\n    raise NotImplementedError("Pending real UI delivery race automation")\ndef then_only_current_authority_may_install(context):\n    raise NotImplementedError("Pending independent native verification")\n',encoding='utf8')
write('step-definition-stubs.json',{'document_execution':'check_correction.py exercises reducer, deliver and generic schema grammar against concrete fixtures','product_steps':'steps.py; intentionally unbound pending approved Skeleton/RED; NOT RUN','fixture_files':['fixtures.json','new-delivery-fixtures.json','delivery-authority.json','new-root-cases.json','new-reducer-results.json']})
write('pending-automation.json',['Owner approval of rootType diagnostic DTO and trusted current observation seam','Approved skeleton and valid product RED','Real authenticated native revocation delivery race','Product/module/cross-module tests','Full Draft 2020-12 engine validation','Independent document reacceptance'])
write('traceability-correction.json',[{'BDD':c['id'],'finding':'BG-R1','test':'check_correction.py reducer','result':'AUTHOR_CHECKED'} for c in new]+[{'BDD':c['id'],'finding':'BG-R2','test':'document_model.deliver through trusted fixture observation','result':'AUTHOR_CHECKED'} for c in deliveries])
body='<h1>M03 Open/Get correction v1</h1><p>PROPOSED · Pending independent review and Owner · Planning only · Yellow preserved</p><h2>Purpose</h2><p>Correct malformed complete-root diagnostics and revoke pending projections using current attachment authority. M04 remains sole owner; M03 is a derived facade.</p><h2>Hexagonal system boundary</h2><pre>Native UI → trusted caller adapter → M03 open/get facade → M04 attach/get input port → sole M04 S1 owner\nCurrent trusted attachment/native/M04 observation → delivery fence → immutable UI projection</pre><h2>Module dependencies and ownership</h2><pre>UI → Tauri boundary → M03 → M04 contract; M01 supplies trusted identity\nM04 owns document/session/history/baselines/generation; M03 owns derived attachments only\nNo reverse domain-to-native dependency, no direct S1 or filesystem access</pre><h2>Transaction</h2><p>Authenticate → validate complete root → lookup → observe M04 → verify → derive attachment. Delivery separately re-observes current authority → compares tuple → checks revision → installs projection. Failure preserves content/history/baselines/revision. No close/transfer command implementation.</p><h2>Verification</h2><p>Author document model checks only; full Draft engine, native, product, valid RED, build, Owner adoption and independent acceptance NOT RUN.</p>'
for name in ['verification.json','before-after.json','module-spec.json','new-reducer-results.json','new-delivery-fixtures.json','acceptance.json','pending-automation.json','lessons.json']:
 body+='<details open><summary>'+name+'</summary><pre>'+html.escape((P/name).read_text(encoding='utf8'))+'</pre></details>'
body+='<h2>Primary new evidence</h2><p>BG-R1: 54 reducer/precedence cases and 48 new all-four-root type cases. BG-R2: 81 current authority delivery cases. The inherited 408 root, 335 physical definition and 35 reducer checks are regression evidence only. New schema negatives are also replayed by the generic Node validator (456 total roots).</p>'
body+='<h2>Complete artifacts</h2>'+''.join('<p><a href="'+f.name+'">'+f.name+'</a></p>' for f in sorted(P.iterdir()) if f.is_file())
(P/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>M03 Open/Get correction</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;background:#101820;color:#e3edf5}h1,h2{color:#83d8d0}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#8adcf0}details{padding:12px;border:1px solid #426070}</style>'+body+'<script type="application/json" id="module-spec">'+json.dumps(spec).replace('</','<\/')+'</script></html>',encoding='utf8')
write('artifact-hashes.json',{f.name:sha(f) for f in P.iterdir() if f.is_file() and f.name!='artifact-hashes.json'})
print(json.dumps(v))

