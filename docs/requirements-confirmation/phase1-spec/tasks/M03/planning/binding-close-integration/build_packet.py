import json,pathlib,copy,hashlib,subprocess,html,datetime
P=pathlib.Path(__file__).resolve().parent; R=pathlib.Path('D:/AIAD'); B=P.parent
J=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def put(n,x): (P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
src=B/'cx-h2-revision-v3/module-spec.json'; effective=J(src)['effective_spec']; base=J(B/'candidate-prepare-correction/request.schema.json'); response=J(B/'candidate-prepare-correction/response.schema.json')
req={k:copy.deepcopy(v) for k,v in base.items() if k in ['$schema','$defs']};req['$id']='urn:sga:proposed:design_binding_close:request';req.update(copy.deepcopy(effective['dto']['requests']['design_binding_close']))
for k in ['binding_ref','expected_generation','expected_revision']:req['properties'][k]=copy.deepcopy(base['properties'][k])
response['$id']='urn:sga:proposed:design_binding_close:response';response['oneOf'][0]['properties']['value']={'$ref':'#/$defs/Close'}
put('request.schema.json',req);put('response.schema.json',response)
for n in ['schema_subset.py']:(P/n).write_bytes((B/'candidate-prepare-correction'/n).read_bytes())
choices=[
('CL-P1','Close command main/editor own native attachment only; viewer denied by original ACL. Main writer cannot name another consumer binding through arbitrary cross-window dispatch. Whether nonwriter editor may detach its own attachment requires Owner decision.'),
('CL-P2','Retained same-instance same-epoch tombstone returns closed true/content_changed false/replayed false for identical generation/revision/discard capture. No request_id: this is idempotent detach, not mutation replay or durable exactly-once. Different capture fails MissingBinding. Missing unknown binding fails MissingBinding.'),
('CL-P3','M04 exact detach_view observation must certify attachment_active=false for the exact trusted tuple. Writer detachment authority, dirty discard confirmation and generation retirement stay M04. No last-view document destruction or transfer is inferred.'),
('CL-P4','Local document model tombstone capacity parameter=2 only for boundary fixture. Production capacity unresolved. Refuse before detach when full; no eviction/TTL/silent retry. Owner must decide capacity and retention. New runtime epoch loses cache, old binding MissingBinding; revoke delivery authority regardless cache retention.'),
('CL-P5','Trusted typed current attachment observation is the restricted open/get correction document-model seam. Runtime API/Skeleton not approved. Missing, malformed or foreign observation blocks delivery; caller JSON cannot assert attachment_active or native_live.'),
('CL-P6','Non-object InvalidRequest rootType branch copied from prepare correction remains a proposed DTO choice, not adopted. Seven typed DomainRejected variants remain exact objects.'),
('CL-P7','Detach commit linearizes only upon M04 revoked-attachment observation. Started save/install effects are not cancelled or rolled back by close; late results cannot deliver to revoked view. Original issuer/M04 owns formal ACK and completion evidence; close neither acknowledges nor resubmits.')]
put('owner-choices.json',[{'id':i,'status':'PROPOSED_PENDING_OWNER','choice':v} for i,v in choices])
contracts={
'C1':'Native main/editor identity and origin and live instance checked before dependency/cache lookup; viewer/remote/replaced native denied.',
'C2':'M04 sole S1 owner; close detaches derived binding only, never closes document or mutates content/history/revision/baselines/formal IO ACK/material roots.',
'C3':'Validate complete closed request and expected generation/revision before new detach; M04 observed tuple must match bound document/session/project/root/runtime/native instance.',
'C4':'On confirmed detach revoke binding candidates/previews and replay disclosure authority; in-flight late completion cannot reactivate attachment or install a UI projection.',
'C5':'No request_id accepted. Other operation replay records cannot be read/resubmitted through close; no automatic retry or TTL.',
'C6':'Trusted delivery observation must be current, typed and minted by fixture authority, with active attachment/native liveness and full tuple equality.',
'C7':'Capacity failure is pre-detach and preserves attachment; tombstones are fixture-derived state, not a second document owner.',
'C8':'Missing dependency, stale generation/revision, dirty unconfirmed writer or malformed observation leaves all model state unchanged.'}
scenarios=[
('CL-01','Authorized editor detaches its own derived binding','valid','Closed'),
('CL-02','Viewer cannot close a binding','viewer','UnauthorizedCaller'),
('CL-03','Remote origin cannot close a binding','remote','UnauthorizedCaller'),
('CL-04','Replacement native instance cannot reuse a binding','replacement','UnauthorizedCaller'),
('CL-05','Main cannot arbitrarily detach another editor attachment','foreign','MissingBinding'),
('CL-06','Unknown binding fails closed','missing','MissingBinding'),
('CL-07','Absent M04 integration cannot detach','dependency','DependencyNotReady'),
('CL-08','Stale owner generation preserves attachment','generation','StaleOwner'),
('CL-09','Stale revision preserves attachment','revision','StaleRevision'),
('CL-10','Unconfirmed dirty writer cannot detach','dirty','Busy'),
('CL-11','M04 refusal cannot be interpreted as detach','m04-refusal','DependencyNotReady'),
('CL-12','Confirmed writer detach leaves document live and history intact','writer','Closed'),
('CL-13','Repeated identical close is idempotent within fixture retention','repeat','Closed'),
('CL-14','Changed close capture is not a replay','changed','MissingBinding'),
('CL-15','Full tombstone cache refuses before M04 detach','capacity','CapacityExceeded'),
('CL-16','New runtime epoch cannot disclose old close state','epoch','MissingBinding'),
('CL-17','Closed attachment blocks late get delivery while window lives','late-get','Discarded'),
('CL-18','Closed attachment blocks late mutation result delivery','late-install','Discarded'),
('CL-19','Close does not apply a late formal ACK','late-ack','Discarded'),
('CL-20','Missing current observation blocks delivery','missing-observation','Discarded'),
('CL-21','Caller-forged observation cannot authorize delivery','forged-observation','Discarded'),
('CL-22','Wrong current owner generation blocks delivery','delivery-generation','Discarded'),
('CL-23','Wrong attachment flag type blocks delivery','typed-observation','Discarded'),
('CL-24','Close revokes candidates previews and replay disclosure','revocation','Closed'),
('CL-25','Malformed M04 detach observation has no partial effect','bad-detach','ProofMismatch'),
('CL-26','Caller discard flag cannot replace missing M04 dirty decision','discard-without-owner','DependencyNotReady')]
put('fixtures.json',[{'id':i,'behavior':t,'mode':m,'expected':e,'policy_status':'PROPOSED_PENDING_OWNER'} for i,t,m,e in scenarios])
feature='Feature: Detach a derived design binding safely\n  Background:\n    Given a live document with one authoritative owner and a trusted attached native view\n  Rule: Closing a view preserves the document and revokes that view authority\n'
for i,t,m,e in scenarios:feature+=f'\n    @{i}\n    Scenario: {i} {t}\n      Given the {m} attachment condition\n      When the attachment lifecycle action is requested\n      Then the observable outcome is {e}\n      And the document content and history remain unchanged\n'
(P/'module.feature').write_text(feature,encoding='utf-8')
put('step-definition-stubs.json',[{'scenario':i,'given':'Create isolated fixture authority and M04 owner double', 'when':f'Exercise document model mode {m}', 'then':f'Assert {e}, untouched document snapshot and zero formal IO/ACK/root calls','production_automation':'PENDING'} for i,t,m,e in scenarios])
(P/'steps.py').write_text('"""Production/native BDD step stubs; never counts as acceptance."""\ndef given_trusted_attachment(context):\n    raise NotImplementedError("Needs approved native/M04 fixture")\ndef when_close_binding(context):\n    raise NotImplementedError("Needs approved close input port")\ndef then_document_preserved(context):\n    raise NotImplementedError("Independent native verification pending")\n',encoding='utf-8')
put('traceability.json',[{'BDD':i,'contract':list(contracts),'TDD':'checker.py model case '+m,'fixture':'fixtures.json#'+i,'result_layer':'DOCUMENT_MODEL_ONLY','production':'NOT RUN'} for i,t,m,e in scenarios])
put('before-after.json',{'before':'Open/get correction external revocation observation only; close command deferred. Existing review PASS not rerun.', 'after':'Separate close-only exact request/response candidate with trusted detach and delivery model; no product authorization.', 'unchanged':'Transfer remains DEFERRED. Old packages/product/board/current-state protected.'})
put('pending-automation.json',['Owner adopt exact close consumer/writer/discard semantics and capacity/retention/missing policy','Native command origin/instance/ACL tests after approved Skeleton and valid production RED','M04 detach linearization and dirty confirmation integration','Real inflight save/install ACK authority reconciliation and revoked UI delivery','Cross-module regressions, build, package, platform compatibility'])
put('lessons.json',[{'cause':'A local close can be confused with document teardown or global writer transfer','rule':'M04 owns document/discard; facade only revokes exact derived attachment. Cross-window authority not inferred.'},{'cause':'An ACK may complete after a UI view closes','rule':'Do not roll back committed effects or call formal ACK from close. Separate issuer evidence from delivery.'},{'cause':'Fixture tombstones can silently invent production retry guarantees','rule':'No request_id, no TTL, capacity and missing/alreadyclosed decisions explicit pending Owner.'}])
mod={'module':'M03','task':'PD-P1-M03-PREP-01','slice':'design_binding_close ONLY; transfer DEFERRED','author':'/root/m03_binding_close_packet','status':'PROPOSED_PENDING_INDEPENDENT_REVIEW_AND_OWNER','implementation_gate':'NOT_READY_FOR_IMPLEMENTATION','independent_acceptance':'NOT RUN','owner_adoption':'NOT RUN','full_draft':'NOT COMPLETE','product_native_RED':'NOT RUN','build':'NOT RUN','architecture':{'context':'Native design view consumes one M04-owned document; closing attachment leaves document live.','hexagonal':'Trusted native caller adapter → M03 close input port → derived attachment facade → M04 detach_view(handle) → sole M04 owner','dependency':'UI → Tauri native guard → M03 → M04 input contract; no direct S1/IO access','input_ports':['design_binding_close exact closed request'],'output_ports':['Existing proposed M04.detach_view(handle); exact observation contract still proposed','Restricted trusted current attachment observation at delivery; fixture-only seam'],'driving_adapters':['Native main/editor guard','Document model test driver'],'driven_adapters':['M04 sole owner double; native implementation NOT RUN'],'state_ownership':'M04 owns S1 content/history/revision/baselines/writer generation. M03 owns derived binding/candidate/preview/replay-disclosure caches only.','mutation':'Only exact attached-view derived authority revoked after M04 confirmation; no content mutation.','transaction':'Native auth → root validation → trusted binding/owner observation → preflight capacity and fences → M04 detach confirmation → revoke derived attachment/candidate/preview/disclosure. Failure precommit unchanged. Native atomicity and postcommit loss unresolved Owner seam.','external_boundary':'Native identity and M04 remain external dependencies; missing integration fails closed.','forbidden':['new owner registry','S1 constructor','document close','history/content mutation','formal IO/ACK','material pin/root release','writer transfer','cross-window arbitrary dispatch']},'contracts':contracts,'owner_choices':'owner-choices.json; all new exact policy choices PROPOSED_PENDING_OWNER','permissions':effective['permissions'],'UI_schema':{'component':'Existing design binding view','roles':'main/editor only by closed ACL; viewer denied','controls':'Existing close action only; no new UI controls','constraints':'No caller identity/observation flags in request','confirmation':'Dirty writer explicit confirmation observed by M04; exact detach decision pending Owner','loading':'Disable duplicate close while pending; do not clear active document speculatively','success':'Clear only detached view projection and revoke its previews/candidates','error':'Preserve prior view, plain-text diagnostic, no automatic retry','empty':'Unknown binding MissingBinding under proposed policy','accessibility':'Announce status without focus steal'},'BDD_categories':{f'B{i}':('Deferred: production compatibility/regression NOT RUN' if i in [11,12] else 'Applicable: fixtures.json covers success/boundary/failure/state/transaction/lifecycle/cross-module document model') for i in range(1,13)},'tasks':[{'id':'CL-CLOSE-PLAN','primary_module':'M03','layer':'Planning document','allowed_scope':'binding-close-integration/** only','protected':'All old packets/product/board/current-state','BDD':[x[0] for x in scenarios],'TDD':'checker.py document model; product RED NOT RUN','acceptance':['Complete self-contained root schemas','All physical lexical patterns actual parsed/audited','Typed seven DomainRejected maintained','Document lifecycle invariants checked','Owner choices and native evidence limits explicit'],'status':'AUTHOR_CANDIDATE_ONLY'}]}
put('module-spec.json',mod)
# Freeze exact sources and authority separately from current product hashes.
inputs=[R/'AGENTS.md',B/'current-state.json',src,B/'cx-h2-revision-v3/shared-contract.json',B/'candidate-prepare-correction/request.schema.json',B/'candidate-prepare-correction/response.schema.json',B/'binding-open-get-correction/module-spec.json',B/'binding-open-get-correction/delivery-authority.json',B/'binding-open-get-correction-review/review.json',B/'binding-open-get-correction-review/verification.json',B/'binding-open-get-review/review.json']
put('source-input-hashes.json',{str(p.relative_to(R)):sha(p) for p in inputs})
authority=R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json';a=J(authority)
put('authority-source.json',{'path':str(authority.relative_to(R)),'sha256':sha(authority),'historical':a})
historical=J(B/'binding-open-get-correction/source-current.json');current={};drift=[]
for n,old in a['source_hashes'].items():
 p=R/n; h=sha(p) if p.exists() else None;current[n]=h
 if h!=old:drift.append({'file':n,'old':old,'current':h})
put('source-current.json',{'branch':subprocess.check_output(['git','branch','--show-current'],cwd=R,text=True).strip(),'HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'authority_count':len(current),'authority':'M01/planning/s2-green/source-current.json','current_hashes':current,'drift_vs_M01_s2_green_authority':drift,'historical_open_get_HEAD':historical['HEAD'],'historical_branch_HEAD_5b70934':'Historical evidence only; not current verification'})
print('Generated close candidate')
