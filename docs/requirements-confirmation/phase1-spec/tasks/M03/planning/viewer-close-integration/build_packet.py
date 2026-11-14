"""Create a bounded planning artifact. Run python -B; no product writes."""
import copy, hashlib, html, json, pathlib
P=pathlib.Path(__file__).resolve().parent
ROOT=P.parents[6]
BASE=P.parent
CX=ROOT/'docs/requirements-confirmation/phase1-spec/tasks/integration-contract-revision-v3'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(n,x): (P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
original={n:read(CX/('h2-design_viewer_close-'+n+'.schema.json')) for n in ('request','response')}
diff=[]
for n,s in original.items():
 c=copy.deepcopy(s)
 # Python/ECMAScript $ admits a trailing newline. Explicit negative lookahead
 # expresses physical end in both engines. A proposal, never silently approved.
 def strict(v,path=''):
  if isinstance(v,dict):
   for k,x in v.items():
    if k=='pattern' and x.endswith('$'):
     v[k]=x[:-1]+'(?![\\s\\S])';diff.append({'schema':n,'pointer':path+'/pattern','before':x,'after':v[k],'status':'PROPOSED_PENDING_OWNER'})
    else:strict(x,path+'/'+k)
  elif isinstance(v,list):
   for i,x in enumerate(v):strict(x,path+'/'+str(i))
 strict(c);write(n+'.schema.json',c)
write('schema-before-after.json',diff)
uuid_pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![\s\S])'
tuple_names=('consumer','window_instance','project_uuid','root_instance','runtime_epoch','document_uuid','session_uuid','generation','preview_session')
tuple_props={k:({'type':'string','pattern':uuid_pattern} if k.endswith('_uuid') or k=='preview_session' else {'type':'string','minLength':1}) for k in tuple_names}
tuple_props['generation']={'type':'string','pattern':r'^(0|[1-9][0-9]*)(?![\s\S])','maxLength':20,'description':'Runtime u64 bound also checked in model'}
def closed_object(props):return {'type':'object','properties':props,'required':list(props),'additionalProperties':False}
identity=closed_object({**tuple_props,'native_live':{'type':'boolean'},'revoked':{'type':'boolean'}})
proof=closed_object({**tuple_props,'closed':{'const':True},'mock_discarded':{'const':True}})
defs=copy.deepcopy(original['response']['$defs'])
allowed={'PreviewClosed','Busy','StaleOwner','MissingBinding','DependencyNotReady'}
defs['CloseProviderError']={'oneOf':[copy.deepcopy(b) for b in defs['Error']['oneOf'] if b['properties']['code']['enum'][0] in allowed]}
provider_schema={'$defs':defs,**closed_object({'trusted_local':{'type':'boolean'},'role':{'type':'string'},'origin':{'type':'string'},'capture':identity,'delivery':identity,'ready':{'type':'boolean'},'outcome':{'oneOf':[{'enum':['Closed','ResponseLostAfterCommit']},{'$ref':'#/$defs/CloseProviderError'}]},'closed_observation':{'oneOf':[proof,{'type':'null'}]}})}
write('provider-observation.schema.json',provider_schema)
sources=[ROOT/'AGENTS.md',ROOT/'docs/board.json',BASE/'current-state.json',ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json']
for folder in ('h2-exact-design','cx-h2-revision-v3','viewer-refresh-review','viewer-action-typed-review','binding-close-review'):
 sources += [p for p in (BASE/folder).iterdir() if p.is_file()]
sources += [CX/('h2-design_viewer_close-'+n+'.schema.json') for n in original]
write('preserved-inputs.json',{str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for p in sources})
write('source-current.json',{'head':'5b709343a890503ebbe24a802e43cda5647df124','historical_head':'31babe87a7ef1e40a0d4bedc523077e7a45d63ab','authority':'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json','authority_sha256':digest(sources[3]),'expected_source_count':796})
policies=[
 ('wire','Original preview_session-only request; complete success/error roots; no request_id.','Original Close value retained; strict-end lexical proposal recorded separately.'),
 ('identity','PreviewSession binds consumer nonce, binding/session/generation/revision.','Closed native capture and delivery tuple adds explicit project/root/runtime epoch; local origins and labels derived from H2 caller policy. All precision PROPOSED_PENDING_OWNER.'),
 ('observation','Original close result {closed:true,content_changed:false}.','Require authenticated provider closed observation tied to captured preview and owner; exact bool closed/mock_discarded; no truthiness.'),
 ('repeat','Only commands carrying request_id have replay records; close has no request_id.','PROPOSED_PENDING_OWNER: removed handle returns PreviewClosed, replayed=false. No retained-success tombstone or capacity allocation; reject this option if Owner requires idempotent close.'),
 ('capacity','Original four previews per binding.','PROPOSED_PENDING_OWNER: close removes exactly one existing slot, including at capacity; no new slot, request record or tombstone. Runtime atomic accounting remains unproved.'),
 ('failure','Revocation and no late response install required.','PROPOSED_PENDING_OWNER: no retry on missing/malformed/postcommit lost observation; mark UI close uncertain and disable mock actions. A lost reply cannot undo provider close.'),
 ('preservation','Detached mock only; no content edits.','No binding detach/document close, content/history/formalSave/baselines/ACK/pin/material-root calls or changes.'),
 ('precedence','Native caller then strict DTO then binding/window/generation.','PROPOSED_PENDING_OWNER exact model trace and errors: native/capture admission, request, preview resolution, provider close, closed proof, delivery admission. Eager type admission may change earlier call traces.'),
]
spec={'module':'M03','task':'PD-P1-M03-PREP-01','command':'design_viewer_close','status':'PROPOSED_PENDING_OWNER','scope':'Only this new viewer-close-integration folder; author document checks only','architecture':{'hexagonal':'Viewer driving adapter → design_viewer_close Tauri input → DispatchHost application preview owner → detached mock record; native identity and provider close observations enter through declared test seams','dependencies':'UI → command → DispatchHost → preview record. DocumentSession remains sole content/history/baseline SSOT; no new product port approved. Native/provider seams here are proposed document contracts.','ownership':'Application owns preview records; native lifecycle owns actual consumer/window/session/epoch. UI owns only mirror.','mutation':'Only preview active/mock/capabilities slot may retire; document remains live and bound.','transaction':'resolve same native tuple → provider atomic retire one preview → typed closed proof → recheck current delivery tuple → UI Closed. Late/missing response never reopens or retries. Provider commit atomicity is a premise.','forbidden':['binding.detach','document.close','S1.commit','formalSave','FileCommit','ACK','pin','material roots','filesystem','automatic retry']},'contracts':['CLOSE-1 exact original wire root and typed booleans','CLOSE-2 matching native consumer/window/project/root/epoch/document/owner session/generation/preview only','CLOSE-3 close retires detached mock only','CLOSE-4 no stale/revoked/late response installation','CLOSE-5 no automatic retry or fabricated success'], 'policy_rows':[{'area':a,'before':b,'after':c,'status':'PROPOSED_PENDING_OWNER'} for a,b,c in policies], 'acceptance':['All new fixture expected response/state/calls independently enumerated in fixtures.json and checked','Every original root branch exercised plus missing/extra/type negatives','All 796 authority hashes match; preserved inputs unchanged','Human HTML embeds same ModuleSpec; independent acceptance NOT RUN'], 'decisions':['Owner must adopt exact identity tuple, error precedence, observation seam, repeat/replay policy, no tombstone policy, capacity accounting and response-loss behavior before product Skeleton/RED.','Existing dirty document close confirmation is irrelevant to preview-only close; never infer discard_unsaved from preview close.'],'limits':['Bounded schema keyword evaluator only; not full Draft2020 validation.','Trusted native/provider authenticity and atomic retirement/slot accounting unproved.','Model cannot prove real command registration, Tauri ACL, OS lifecycle, races or provider failure atomicity.'],'verification':{k:'NOT RUN' for k in ['independent_review','native','build','product_tests','valid_RED','GREEN','module_acceptance','release']},'module_complete':False,'parent_light':'Yellow'}
spec['bdd_categories']={
 'B1':'Applicable: close current preview', 'B2':'Applicable: one/four-slot state, strict UUID/U64',
 'B3':'Applicable: missing/empty/extra/malformed input', 'B4':'Applicable: missing provider/native observation',
 'B5':'Applicable: provider commit then lost reply', 'B6':'Applicable: document/content/history preservation',
 'B7':'Applicable: provider atomic retire premise, no rollback claim', 'B8':'Applicable: revoked/destroyed/replaced/epoch/generation',
 'B9':'Applicable: no automatic retry; uncertain UI, no fabricated reopen',
 'B10':'Applicable: native provider/delivery boundary, no binding detach/document close',
 'B11':'Deferred: cross-platform native behavior requires approved implementation and native harness; wire schemas preserved except explicit lexical proposals',
 'B12':'Applicable: no formalSave/ACK/pin/history mutations'}
spec['tasks']=[{'id':'M03-PLAN-VIEWER-CLOSE','primary_module':'M03','layer':'Application/Driving Adapter document proposal','status':'PLANNING_DELIVERED_PENDING_REVIEW_OWNER','allowed':'this new viewer-close-integration folder only','protected':'all original documents, product/tests, board/current-state/hooks/roles','skeleton':'NOT_STARTED','tests':'python -B checker.py; document model only','regression':'original preserved inputs + 796 authority hashes; product adjacent regression NOT RUN','estimate':'bounded author planning slice; no product estimate or implementation authorization','next':'independent document review, Owner decisions, approved Skeleton and valid RED before any production work'}]
spec['test_levels']={'L0':'bounded lexical/type evaluator author checks','L1':'document model close cases only','L2':'complete wire root/schema probes only; real module contract NOT RUN','L3':'native/provider integration NOT RUN','L4':'cross-module product regression NOT RUN','L5':'system acceptance NOT RUN'}
write('module-spec.json',spec)
write('before-after.json',spec['policy_rows'])
write('ui-schema.json',{'component':'Viewer preview Close','role':'trusted same consumer instance','control':'Close preview; explicit click only','states':['PreviewActive','PreviewStale','Closing','Closed','CloseUncertain'],'defaults':'retain prior display while pending, disable mock actions','success':'Only admitted typed closed observation transitions to Closed and clears local mock controls; binding/document remain open','error':'inert text, aria-live; no success toast, no automatic retry, no close of new preview','late':'ignore old capture after navigation/reload/replacement/generation/epoch change; never close replacement preview','validation':'no raw identity input or privilege carried in UI payload','accessibility':'keyboard Close, focusable inline error summary','mapped_bdd':'CLOSE-001..CLOSE-008','status':'PROPOSED_PENDING_OWNER'})
write('pending-automation.json',{'NOT RUN':['native caller/origin/nonce registry','provider close atomicity + failure-before-commit + lost-after-commit','native concurrency/lifecycle and slot accounting','product command/ACL/IPC tests','build','valid RED','independent acceptance'],'valid_RED':'After Owner adoption, approved Skeleton compiles; intended missing close behavior fails assertions. Compile/fixture/environment failures are not RED.'})
sections=''.join('<h2>'+html.escape(k)+'</h2><pre>'+html.escape(json.dumps(v,ensure_ascii=False,indent=2))+'</pre>' for k,v in spec.items())
diagrams='<h2>Hexagonal system view</h2><pre>Viewer UI → Tauri close input → DispatchHost preview owner → detached mock\n                              ↑ native identity / close observation seams\nDocumentSession SSOT (content/history/baselines): unchanged</pre><h2>Module dependency view</h2><pre>Viewer mirror → command → application PreviewSession\nNative lifecycle → identity observation → application\nProvider close → typed proof → delivery gate → Viewer Closed\nNo edge to binding detach / document close / storage / ACK / pin</pre>'
(P/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>M03 Viewer Close planning</title><style>body{max-width:1050px;margin:2rem auto;font:16px system-ui;background:#101723;color:#e6edf6}pre{white-space:pre-wrap;background:#1c2738;padding:1rem}h1,h2{color:#8ac4ff}a{color:#8ac4ff}</style><h1>M03 · Close detached Viewer preview</h1><p>Yellow · PROPOSED_PENDING_OWNER · Author document checks only. No product/native/RED acceptance.</p>'+diagrams+sections+'<h2>Executable evidence</h2><p><a href="fixtures.json">Fixtures with complete expected response/state/calls</a> · <a href="results.json">author results</a> · <a href="traceability.json">traceability</a></p><script type="application/json" id="module-spec">'+json.dumps(spec,ensure_ascii=False).replace('</','<\\/')+'</script></html>',encoding='utf-8')
