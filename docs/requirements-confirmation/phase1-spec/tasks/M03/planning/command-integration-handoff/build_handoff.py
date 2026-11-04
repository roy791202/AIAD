"""Bounded document reconciliation. Never invokes or rewrites prior checkers."""
import copy, hashlib, html, importlib.util, json, pathlib, re, subprocess
P=pathlib.Path(__file__).resolve().parent
B=P.parent
ROOT=P.parents[6]
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def put(n,v): (P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
MAP=[('design_binding_open','binding-open-get-correction','binding-open-get-correction-review'),('design_binding_get','binding-open-get-correction','binding-open-get-correction-review'),('design_binding_transfer','binding-transfer-correction','binding-transfer-correction-review'),('design_candidate_prepare','candidate-prepare-correction','candidate-prepare-correction-review'),('design_candidate_install','candidate-install-correction','candidate-install-correction-review'),('design_document_undo','undo-response-correction','undo-correction-review'),('design_document_save','save-proof-correction','save-proof-review'),('design_editor_select','editor-select-integration','editor-select-review'),('design_viewer_begin','preview-begin-correction','preview-begin-correction-review'),('design_viewer_intent','viewer-action-typed-correction','viewer-action-typed-review'),('design_viewer_refresh','viewer-refresh-integration','viewer-refresh-review'),('design_viewer_close','viewer-close-integration','viewer-close-review'),('design_binding_close','binding-close-integration','binding-close-review')]
def leaves(x,path=''):
 if isinstance(x,dict):
  for k,v in x.items(): yield from leaves(v,path+'/'+str(k))
 elif isinstance(x,list):
  for k,v in enumerate(x): yield from leaves(v,path+'/'+str(k))
 else: yield path,x
def evidence(folder):
 out=[]
 for n in ['review.json','review-result.json','results.json','verification.json','seal.json','acceptance.json']:
  f=B/folder/n
  if f.exists():
   d=read(f);out.append({'file':folder+'/'+n,'sha256':sha(f),'claims':[{'pointer':k,'value':v} for k,v in leaves(d) if any(t in k.lower() for t in ['status','verdict','finding','author','reviewer','owner','independent','module_complete','native','red','drift'])]})
 return out
def main():
 inputs={}
 for cmd,cand,rev in MAP:
  for folder in [cand,rev]:
   for f in (B/folder).glob('*'):
    if f.is_file():inputs[str(f.relative_to(ROOT)).replace('\\','/')]=sha(f)
 for n in ['current-state.json','h2-exact-design/module.feature','h2-exact-design/traceability.json','h2-exact-design/dto-errors.json','cx-h2-revision-v3/module-spec.json']:
  inputs[str((B/n).relative_to(ROOT)).replace('\\','/')]=sha(B/n)
 original=read(B/'h2-exact-design/dto-errors.json')['requests'];assert list(original)==[r[0] for r in MAP]
 rows=[]
 for cmd,cand,review in MAP:
  root=[]; f=B/cand/'response.schema.json'
  if not f.exists(): f=B/cand/('h2-'+cmd+'-response.schema.json')
  if f.exists():
   schema=read(f)
   root=[{'pointer':k,'value':v} for k,v in leaves(schema) if (k.endswith('/const') or '/enum/' in k) and isinstance(v,(str,bool))]
  outcomes=[]
  for n in ['io-outcome-map.json','material-outcome-matrix.json','owner-choices.json','new-policy-choices.json','decisions-before-after.json','before-after.json','changes.json','work-error-map.json']:
   f=B/cand/n
   if f.exists():outcomes.append({'file':cand+'/'+n,'content':read(f)})
  specfile=B/cand/'module-spec.json'
  snapshots=[{'pointer':k,'value':v} for k,v in leaves(read(specfile)) if any(t in k.lower() for t in ['provider','premise','root','error','io','decision','choice','outcome','retention','ack','filecommit'])]
  rows.append({'command':cmd,'original_request_pointer':'h2-exact-design/dto-errors.json#/requests/'+cmd,'effective_candidate':cand,'independent_scoped_review':review,'candidate_evidence':evidence(cand),'review_evidence':evidence(review),'response_root_source':str(f.relative_to(B)).replace('\\','/'),'response_root_constants':root,'provider_contract_pointers':snapshots,'provider_IO_and_deviations':outcomes,'adoption':'PROPOSED_PENDING_OWNER','module_verification':'NOT RUN','remaining':'Owner must adopt exact candidate with its overlay predecessors and shared error/provider seams; review PASS is scoped document evidence only.'})
 put('command-coverage.json',rows)
 trace=read(B/'h2-exact-design/traceability.json'); original_rows=trace['rows'] if 'rows' in trace else next(v for v in trace.values() if isinstance(v,list))
 assert len(original_rows)==62
 feature=(B/'h2-exact-design/module.feature').read_text(encoding='utf-8')
 coverage=[]
 for row in original_rows:
  bid=row['bdd'];block=next((x for x in feature.split('  Rule: ') if x.startswith(bid)), '')
  linked=[]
  for cmd,cand,review in MAP:
   for n in ['traceability.json','correction-traceability.json','module-spec.json','module.feature']:
    f=B/cand/n
    if f.exists() and bid in f.read_text(encoding='utf-8-sig'):
     linked.append({'command':cmd,'source':cand+'/'+n,'text_match_only':True})
  number=int(bid[-3:])
  relevant=([0,1] if number<=4 else [0,2,3,4] if number==5 else [3] if number<=12 else [3,4] if number<=24 else [4] if number==25 else [5] if number==26 else [4,5] if number==27 else [9] if number<=43 else [3,4,6] if number<=49 else [12] if number==50 else [2,10,11,12] if number==51 else [10] if number==52 else [2] if number<=54 else [0,2,7,8,10,11,12] if number==55 else [6] if number==56 else [3,8,10] if number==57 else [] if number<=60 else [7] if number==61 else [5])
  thematic=[{'command':MAP[i][0],'candidate_pointer':MAP[i][1]+'/module-spec.json','review_folder':MAP[i][2],'link_kind':'MANUAL_BEHAVIOR_RECONCILIATION_NOT_PROOF'} for i in relevant]
  coverage.append({'original':row,'original_behavior':block.strip(),'original_pointer':'h2-exact-design/module.feature Rule '+bid,'explicit_mentions':linked,'candidate_behavior_links':thematic,'verdict':'PARTIAL_DOCUMENT_RECONCILIATION' if thematic else 'SINGLE_COMMAND_MIGRATION_GAP','gap':'Original IDs absent from selected packet trace files; thematic mapping is a handoff, not inherited test coverage. No composed module-port/native evidence.' if thematic else 'Legacy typed ingress fail-closed commands have no dedicated recent command integration/review in the13-command candidate set; original B058-B060 remain independently unclosed.'})
 put('original-62-trace.json',coverage)
 categories=[]
 descriptions=['Primary success','Input boundaries','Invalid input','Dependency failure','Partial failure','State consistency','Transactions','Lifecycle','Recovery/rollback','Cross-module interaction','Compatibility','Regression-critical']
 for i,label in enumerate(descriptions,1):categories.append({'id':'B'+str(i),'category':label,'applicability':'Applicable','document_evidence':[x['command'] for x in rows],'module_status':'DEFERRED','reason':'Separate command proposals are not one adopted module model. '+('Cross-command state/provider reconciliation is missing; see composition-gaps.json.' if i in [5,6,7,8,9,10] else 'Exact original-scenario links and command roots retained, but no module acceptance or native evidence.')})
 put('bdd-categories.json',categories)
 # Actual new ordered witness, using only declared reducers and validators.
 refresh=load('handoff_refresh',B/'viewer-refresh-integration/document_model.py'); schema=load('handoff_schema',B/'viewer-refresh-integration/schema_eval.py');close=load('handoff_close',B/'viewer-close-integration/document_model.py')
 req=read(B/'viewer-refresh-integration/request.schema.json');res=read(B/'viewer-refresh-integration/response.schema.json'); projection={'$defs':res['$defs'],'$ref':'#/$defs/Preview'}; err={'$defs':res['$defs'],'$ref':'#/$defs/Error'}
 c=copy.deepcopy(read(B/'viewer-refresh-integration/new-fixtures.json')[0]); c['id']='CIH-SEQ-001'; c['before']['sequence']='17';c['before']['projection']={'fresh_detached_fixture':True}
 out,after,calls=refresh.refresh(c,lambda x:schema.valid(req,x),lambda x:schema.valid(projection,x),lambda x:schema.valid(err,x));assert out['ok'] and after['sequence']=='1'
 old=copy.deepcopy(c);old['before']=after
 oldout,oldafter,oldcalls=refresh.refresh(old,lambda x:schema.valid(req,x),lambda x:schema.valid(projection,x),lambda x:schema.valid(err,x));assert oldout['error']['code']=='PreviewClosed';assert oldafter['content']==after['content']
 # No fabricated translation from refresh's provider to close's larger authority tuple.
 closecase={'before':copy.deepcopy(after),'request':{'preview_session':after['preview_session']},'provider':copy.deepcopy(c['provider'])}
 closeout=close.close(closecase,lambda x:True,lambda x:True)
 assert closeout['response']['error']=={'code':'DependencyNotReady','details':{'dependency':'M04_OWNER_INTEGRATION'}}
 witness={'id':'CIH-SEQ-001','status':'REPRODUCIBLE_COMPOSITION_GAP','premises':'Fresh trusted fixture explicitly supplies native identity, unique new UUID and immutable C1 projection. These are not returned by prior command bytes and not authentication proof. Modified detached prior sequence17 exercises reset.','fixture':c,'steps':[{'action':'design_viewer_refresh','response':out,'after':after,'calls':calls},{'action':'design_viewer_refresh with retired old handle','response':oldout,'after':oldafter,'calls':oldcalls},{'action':'design_viewer_close with unchanged refresh provider/state','result':closeout}],'output_boundary':'Only refresh response.value is wire output. after and provider are private fixture state. Passing output or provider across commands is not authority. Close request shape is known-valid; permissive callbacks deliberately isolate earlier provider-record failure, not schema validation.','conclusion':'Old handle retirement works in refresh reducer. Successful refresh cannot be composed with close without new trusted identity observation and state seam; no whole lifecycle PASS.'}
 put('new-sequence-witness.json',witness)
 gaps=[{'id':'CIH-G1','commands':['design_viewer_begin','design_viewer_intent','design_viewer_refresh','design_viewer_close'],'source_pointers':['preview-begin-correction/document_model.py::begin','viewer-action-typed-correction/document_model.py::provider_fault','viewer-refresh-integration/document_model.py::identity,refresh','viewer-close-integration/document_model.py::TUPLE,identity,close'],'counterexample':'CIH-SEQ-001: refresh succeeds and retires old UUID; close with the same provider observation refuses M04_OWNER_INTEGRATION. Refresh identity has consumer/window/document/session/generation/revision/closed; close requires consumer/window_instance/project_uuid/root_instance/runtime_epoch/document_uuid/session_uuid/generation/preview_session/native_live/revoked. No bijection derives project/root/runtime epoch from refresh output.','missing_conditions':['Owner-adopted native observation input port carrying full root/window/session tuple at capture and delivery.','One authoritative ephemeral registry mapping retired/new preview slots to same consumer and full root tuple.','Explicit conversion policy for stale/can_act/closed versus preview_active/identity state.','Atomic replacement/close race linearization, old intent/close result ordering and slot count invariants.','New independent sequence review after exact seam adoption.'],'status':'PROPOSED_PENDING_OWNER'}, {'id':'CIH-G2','commands':['design_binding_transfer','design_editor_select','design_viewer_begin'],'source_pointers':['binding-transfer-correction/module-spec.json','editor-select-integration/module-spec.json','preview-begin-correction/module-spec.json'],'missing_conditions':['Adopt exact revocation scope and provider tuple; execute transfer output receipt against select/begin with fresh trusted generation observations.','Do not infer native revocation or stale delivery suppression from separately constructed fixtures.'],'status':'PROPOSED_PENDING_OWNER'}, {'id':'CIH-G3','commands':['design_candidate_prepare','design_candidate_install','design_document_undo','design_document_save','design_binding_close'],'source_pointers':['candidate-install-correction/module-spec.json','undo-response-correction/module-spec.json','save-proof-correction/io-outcome-map.json','binding-close-integration/module-spec.json'],'missing_conditions':['One adopted candidate/request-key/live/history root-accounting model across install→undo→save→close.','Preserve FileCommit versus ACK versus retention/deferred outcomes; no ErrorUnchanged claim after unverified IO.','Single shared error-root vocabulary and revalidation of older command schemas against newer typed overlays.'],'status':'PROPOSED_PENDING_OWNER'}]
 put('composition-gaps.json',gaps)
 authority=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')['source_hashes'];matches=sum((ROOT/k).exists() and sha(ROOT/k)==v for k,v in authority.items());assert len(authority)==796 and matches==796
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 spec={'identity':{'module':'M03','task':'PD-P1-M03-PREP-01','slice':'command integration handoff','status':'PROPOSED_PENDING_OWNER','author':'/root/m03_command_coverage_handoff'},'scope':'NEW files in command-integration-handoff only; planning reconciliation, no Skeleton','architecture':{'hexagonal':'UI → Tauri input adapter → M03 facade → M04 owner/C1/M05 abstraction ports; native/IO adapters implement ports','dependency':'Domain remains inward; no IO or native authority from wire DTO','ownership':'M04 sole document/session authority; M03 detached ephemeral projections only','mutation':'No product mutation; proposed application use cases mediate authoritative mutation','transaction':'Preparation/read and capture-delivery revalidation precede publication; persistence receipt and ACK are distinct','approval':'Original H2 D1-D8 and C1 choices remain unadopted'},'command_count':13,'original_bdd_count':62,'category_count':12,'commands':'command-coverage.json','trace':'original-62-trace.json','categories':'bdd-categories.json','witness':'new-sequence-witness.json','gaps':'composition-gaps.json','health':'Yellow / REPLAN_REQUIRED; document coverage reconciliation PARTIAL, full module acceptance NOT RUN','head':head,'product_hashes':matches,'historical_authority_head':'31babe87a7ef1e40a0d4bedc523077e7a45d63ab','next_ready_action':'Independent document reviewer checks exact 13-command selection and CIH-SEQ-001 against hashed inputs; Owner then selects shared identity/registry/error policy for CIH-G1 before Skeleton or product RED.','forbidden':['No proposal union/adoption','No module PASS','No product/native/build/RED claim','No role/hooks/board/current-state mutations']}
 put('module-spec.json',spec);put('source-input-hashes.json',inputs)
 put('review-request.json',{'reviewer':'NEW independent document-only reviewer; must not be author','checks':['All13 exact original commands and selected correction predecessor chains','Review evidence claims remain scoped and unadopted','All62 original IDs and B1-B12 evaluated with no invented coverage','Reproduce refresh→retired-handle→close counterexample','Validate typed provider/root/IO drift and pending Owner decisions','Verify current796 product hashes and sealed input hashes'],'status':'REQUESTED_NOT_RUN','next_ready_action':spec['next_ready_action']})
 data=json.dumps(spec,ensure_ascii=False).replace('</','<\\/')
 table=''.join('<tr><td>'+html.escape(r['command'])+'</td><td>'+html.escape(r['effective_candidate'])+'</td><td>'+html.escape(r['independent_scoped_review'])+'</td><td>Pending Owner / document only</td></tr>' for r in rows)
 body='<!doctype html><html lang="en"><meta charset="utf-8"><title>M03 command integration handoff</title><style>body{font:16px system-ui;max-width:1200px;margin:32px auto;background:#101820;color:#e8edf2}a{color:#85ccff}td,th{padding:10px;border-bottom:1px solid #405060;text-align:left}pre{white-space:pre-wrap;background:#192736;padding:16px}h1,h2{color:#f5cf70}</style><h1>M03 · command integration handoff</h1><p>Yellow · PROPOSED_PENDING_OWNER · no Skeleton · no full module PASS</p><p>13 original commands, 62 original BDD scenarios, 12 coverage categories. Separate scoped document reviews do not establish one compatible module model.</p><h2>Architecture and boundaries</h2><pre>UI → Tauri → M03 facade → M04 sole owner / C1 / M05 ports\nNative and IO adapters implement ports; wire output is never native identity authority.\nEphemeral preview slot publication and close require captured and delivery-time authority.\nFileCommit receipt ≠ baseline ACK ≠ retention completion.</pre><h2>Command reconciliation</h2><table><tr><th>Exact command</th><th>Selected candidate</th><th>Independent scoped review</th><th>Adoption</th></tr>'+table+'<h2>Concrete new sequence and missing seam</h2><p>Fresh fixture refresh resets sequence17 to1 and retires old handle; old handle refresh is PreviewClosed. Feeding unchanged refresh provider/state into close returns DependencyNotReady(M04_OWNER_INTEGRATION). Full root/project/runtime identity cannot be recovered from output bytes.</p><pre>'+html.escape(json.dumps(gaps[0],ensure_ascii=False,indent=2))+'</pre><h2>Behavior, tests and tasks</h2><p><a href="original-62-trace.json">62 original BDD trace with exact ID mentions and unresolved gaps</a> · <a href="bdd-categories.json">B1–B12 applicability</a> · <a href="command-coverage.json">Full response roots, provider/IO maps, review claims and deviations</a></p><p><a href="new-sequence-witness.json">New ordered fixture and actual result bytes</a> · <a href="composition-gaps.json">Three bounded candidate seam handoffs</a></p><h2>Verification and acceptance</h2><p>Author document checks only. Native/product/build/valid RED/full module acceptance NOT RUN. Provider authenticity, global UUID uniqueness, atomicity and concurrency remain trusted fixture premises.</p><h2>Next action</h2><p>'+html.escape(spec['next_ready_action'])+'</p><script type="application/json" id="module-spec">'+data+'</script></html>'
 (P/'index.html').write_text(body,encoding='utf-8')
 put('verification.json',{'status':'PASS_AUTHOR_RECONCILIATION_CHECKS_ONLY','command_rows':13,'original_bdd_rows':62,'categories':12,'new_ordered_witnesses':1,'composition_gaps':3,'product_hashes_matched':matches,'head':head,'independent_review':'NOT RUN','product_native_build_RED':'NOT RUN','owner_adoption':'PENDING','full_module_complete':False,'input_hashes_checked':len(inputs),'input_hashes_match':all(sha(ROOT/k)==v for k,v in inputs.items())})
 manifest={f.name:sha(f) for f in P.iterdir() if f.is_file() and f.name not in ['artifact-hashes.json','seal.json']};put('artifact-hashes.json',manifest)
 put('seal.json',{'status':'SEALED_AUTHOR_DOCUMENT_HANDOFF_PENDING_INDEPENDENT_REVIEW','artifacts':len(manifest),'manifest_sha256':sha(P/'artifact-hashes.json'),'counts':{'commands':13,'original_bdd':62,'categories':12,'new_witnesses':1,'gaps':3},'next_ready_action':spec['next_ready_action'],'module_complete':False})
 print(json.dumps({'commands':13,'original_bdd':62,'categories':12,'product_hashes':matches,'input_hashes':len(inputs),'artifacts':len(manifest),'head':head}))
if __name__=='__main__': main()
