"""Document candidate generator only; no product/test/Skeleton output."""
import json,copy,hashlib,html,re,subprocess,sys
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
O=Path(__file__).resolve().parent; T=O.parent; R=O.parents[4]; B=T/'integration-contract-revision-v2'; V=T/'integration-contract-reacceptance-v2'
sys.path.insert(0,str(R))
from tools.board.board_core.snapshot_safe import split_snapshot,mutate_snapshot_file
from tools.board.board_core.json_store import FileLock
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def put(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def dig(x):return hashlib.sha256(canon(x)).hexdigest()
def obj(p):return {'type':'object','properties':p,'required':list(p),'additionalProperties':False}
def ref(n):return {'$ref':'#/$defs/'+n}
def arr(s):return {'type':'array','items':s}
def enum(*v):return {'enum':list(v)}
S={'type':'string'}; BOOL={'type':'boolean'}; NIL={'type':'null'}
U={'type':'string','pattern':'^(0|[1-9][0-9]*)$','maxLength':20,'description':'Checked runtime u64 <=18446744073709551615; no JSON number or JS Number'}
D={'type':'string','pattern':'^[0-9a-f]{64}$'}
ID={'type':'string','minLength':1}
base=read(T/'M01/planning/s2-green/source-current.json')
branch=subprocess.check_output(['git','branch','--show-current'],cwd=R,text=True).strip();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
assert (branch,head)==(base['branch'],base['head']);assert all(sha(R/p)==h for p,h in base['source_hashes'].items())
sources=read(B/'module-revisions.json');frozen=dict(read(B/'module-spec.json')['prior_files_sha256'])
for folder in [B,V]+[(R/p['report']).parent for p in sources.values()]:
 for p in folder.iterdir():
  if p.is_file() and p.name!='current-state.json':frozen[p.relative_to(R).as_posix()]=sha(p)
board=R/'docs/PROJECT-BOARD.html';a,b,c=split_snapshot(board.read_text(encoding='utf-8'));before=json.loads(b);counts=dict(Counter(t['zone'] for t in before['tasks']))
at=datetime.now(timezone.utc).isoformat()
common=copy.deepcopy(read(B/'shared-contract.json'));common['contract_id']='CX-COMMON-v3-V2-F1-F3';common['status']='PROPOSED_PENDING_OWNER_AND_READONLY_REACCEPTANCE'
defs={'U64Decimal':U,'Digest':D,'Identifier':ID,'WorkflowContext':obj({k:ref('U64Decimal') if k in ['owner_generation','captured_revision'] else ID for k in ['project_uuid','document_uuid','session_id','owner_generation','captured_revision','workflow_id']}),'NativeIdentity':obj({'volume_id':S,'file_id':S,'canonical_target':S}),'ReceiptRef':obj({'issuer':S,'receipt_id':ID,'kind':S,'context_digest':D,'evidence_digest':D}),'Asset':obj({'asset_id':ID,'digest':D,'size_bytes':ref('U64Decimal')}),'RootManifest':obj({'manifest_id':ID,'provider_id':ID,'kind':S,'epoch':ref('U64Decimal'),'completeness':enum('Complete','Unknown'),'assets':arr(ref('Asset'))}),'ImportMetadata':obj({'asset_id':ID,'name':S,'media_type':S,'original_filename':S,'legacy_aliases':arr(S)}),'Resolution':obj({'snapshot_digest':D,'catalog_raw_digest':D,'catalog_generation':ref('U64Decimal'),'completeness':enum('Complete'),'assets':arr(ref('Asset'))}),'SourceSelection':obj({'selection_id':ID,'native_identity':ref('NativeIdentity'),'raw_digest':D,'size_bytes':ref('U64Decimal')}),'Bundle':obj({'issuer_proof':ref('ReceiptRef'),'source_digest':D,'entries':arr(obj({'asset':ref('Asset'),'metadata':ref('ImportMetadata')})),'legacy_alias_mapping':arr(obj({'alias':S,'asset_id':ID,'digest':D}))})}
# Each role's full admitted body is closed and recursively hashed. No field whitelist projection.
roles={
'resolve':obj({'ordered_requests':arr(obj({'asset_id':ID,'requested_digest':{'anyOf':[D,NIL]}})),'catalog_identity':ref('NativeIdentity'),'expected_catalog_generation':ref('U64Decimal')}),
'pin':obj({'resolution':ref('Resolution'),'purpose':enum(*common['pin_enums']['purpose']),'store_identity':ref('NativeIdentity'),'expected_catalog_generation':ref('U64Decimal')}),
'import':{'oneOf':[obj({'mode':enum('Selection'),'source':ref('SourceSelection'),'metadata':ref('ImportMetadata'),'purpose':enum(*common['pin_enums']['purpose']),'store_identity':ref('NativeIdentity'),'expected_catalog_generation':ref('U64Decimal')}),obj({'mode':enum('VerifiedBundle'),'bundle':ref('Bundle'),'purpose':enum(*common['pin_enums']['purpose']),'store_identity':ref('NativeIdentity'),'expected_catalog_generation':ref('U64Decimal')})]},
'install':obj({'owner_handle':ID,'binding_ref':ID,'candidate_ref':ID,'candidate_semantic_digest':D,'candidate_raw_digest':D,'expected_revision':ref('U64Decimal'),'expected_generation':ref('U64Decimal'),'pin_receipt':ref('ReceiptRef')}),
'undo':obj({'owner_handle':ID,'binding_ref':ID,'history_entry_id':ID,'history_content_digest':D,'expected_revision':ref('U64Decimal'),'expected_generation':ref('U64Decimal'),'pin_receipt':ref('ReceiptRef')}),
'release':obj({'pin_id':ID,'store_identity':ref('NativeIdentity'),'root_bundle':arr(ref('RootManifest')),'provider_fences':arr(ref('ReceiptRef')),'expected_catalog_generation':ref('U64Decimal')}),
'publish':obj({'registration_id':ID,'provider_capability_id':ID,'expected_epoch':ref('U64Decimal'),'manifest':ref('RootManifest'),'expected_catalog_generation':ref('U64Decimal')}),
'ack':obj({'owner_handle':ID,'captured_revision':ref('U64Decimal'),'captured_semantic_digest':D,'formal_target_identity':ref('NativeIdentity'),'file_receipt':ref('ReceiptRef'),'transfer_receipt':ref('ReceiptRef')})}
for role in ['transfer-live','transfer-formal','transfer-recovery']:
 roles[role]=obj({'pin_id':ID,'store_identity':ref('NativeIdentity'),'root_manifest':ref('RootManifest'),'external_proof':ref('ReceiptRef'),'expected_catalog_generation':ref('U64Decimal')})
request_schema={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:sga:cx-v3:transition-request','$defs':defs,'oneOf':[]}
for role,body in roles.items():request_schema['oneOf'].append(obj({'protocol':enum('SGA-TRANSITION-v2'),'issuer':ID,'role':enum(role),'ordinal':ref('U64Decimal'),'context':ref('WorkflowContext'),'body':body}))
protocol=common['replay_protocol'];protocol['request_digest']={'schema_root':'transition-request.schema.json','algorithm':'SHA256 of canonical UTF8 of ENTIRE validated request value, including body recursively. No field projection, ignored fields, defaults or post-hash enrichment. Authentication resolves every opaque handle before frozen body assembly. Server resolved identity/content/evidence fields shown in schema are mandatory.','canonicalization':['Reject duplicates before object construction; unknown/missing/null outside declared union reject before replay lookup and IO.','Object names sorted by UTF8 bytes. All scalar text valid Unicode scalar values; no normalization.','Strings: quote and backslash escaped, backspace/tab/newline/formfeed/carriage-return as \\b/\\t/\\n/\\f/\\r; remaining U+0000..001F as lowercase \\u00xx; other scalars literal UTF8; no slash escaping/BOM/whitespace.','All integers U64Decimal strings checked in range. No numeric JSON tokens in transition hash schema.','Arrays preserve admitted order, including resolve requests, entries, aliases, roots, evidence and assets. Order changes conflict; do not sort/deduplicate after hashing.','Same key and valid changed body => ReplayConflict before IO; exact same bytes replay retained receipt. Invalid body => InvalidRequest before key lookup. SHA collision resistance assumed, not proved by vectors.'],'per_role_closed_bodies':roles,'excluded':'Transport correlation, UI display strings outside declared operation, transient read handles and secrets are not request inputs. Any new behavior-affecting input requires schema/replan; cannot silently exclude.','generated_outputs':'Pin id created by pin/import is OUTPUT, never caller input. Existing pin_id mandatory for transfer/release. Selection handles freeze full native identity/raw digest/metadata before hash; bundle entries include all admitted metadata and alias mapping.','read_only_calls':'validate_pin/read_pinned_version/register_roots do not use transition receipt key; authorization and bounds still apply. Provider registration lifecycle unchanged.'}
common['request_hash_schema']=request_schema
common['proof_registry_record']['fields']['request_digest']='SHA256 of full validated SGA-TRANSITION-v2 request; no v1 projected digest accepted as v2 proof'
common['proof_registry_record']['fields']['request_protocol']='SGA-TRANSITION-v2; new candidate field, existing pending schema proposal only'
# Closed public H2 failures and explicit stage-sensitive mappings.
h2=read((R/sources['M03-H2']['report']).with_name('module-spec.json'))['effective_spec'];errors=copy.deepcopy(h2['dto']['errors'])
errors.update({'UnverifiedOutcome':{'request_id':S,'reason':enum('RuntimeRecordLost','IssuerEvidenceMissing','CommitOutcomeUnknown'),'retry_allowed':{'const':False}},'ReplayConflict':{'request_id':S},'InProgress':{'request_id':S},'MaterialReadRejected':{'reason':enum('PinNotReadable','GrantMismatch','LimitExceeded','BlobMissing','SizeMismatch','IntegrityFailure','IdentityChanged','AliasRejected','UnsupportedPlatform')},'ProofMismatch':{},'CapacityExceeded':{},'IoFailure':{},'Indeterminate':{}})
errors['DependencyNotReady']={'dependency':enum('M04_S2','C1_CODEC','M04_OWNER_INTEGRATION','M05_MATERIAL','M01_NATIVE_IDENTITY','ESS_PROJECTOR','ROOT_PROVIDER')}
mapping=[]
def mp(src,pre,post):mapping.append({'source':src,'before_content_commit':pre,'after_verified_content_commit':post,'unknown_commit':'UnverifiedOutcome(reason=CommitOutcomeUnknown); retain Held, block resubmission; never ErrorUnchanged'})
mp('ReplayConflict','ReplayConflict; zero IO','Return retained committed result for original digest; changed digest ReplayConflict with no second commit')
mp('InProgress','InProgress; no second IO','InProgress for still-running original delivery; query retained result only')
mp('RuntimeRecordLost|IssuerEvidenceMissing','UnverifiedOutcome; no mutation retry','UnverifiedOutcome; cannot manufacture MutationReceipt from material receipt')
for e in common['store_read_contract']['errors']:
 pre='Busy' if e=='Busy' else 'IoFailure' if e=='IoFailure' else 'MaterialReadRejected(reason='+e+')'
 post='AppliedRetentionDeferred(reason='+('IoFailure' if e=='IoFailure' else 'DependencyNotReady' if e in ['Busy','UnsupportedPlatform'] else 'ProofMismatch')+'); actual revision/proof/pin preserved'
 mp(e,pre,post)
for e in ['ProofMismatch','CapacityExceeded','DependencyNotReady','StaleRoots','Indeterminate','IoFailure']:
 mp(e,('DependencyNotReady(dependency=ROOT_PROVIDER)' if e=='StaleRoots' else e), 'AppliedRetentionDeferred(reason='+('DependencyNotReady' if e in ['CapacityExceeded','DependencyNotReady'] else e)+'); retain Held and committed revision')
life=[{'event':'same authorized request, binding current, identical body','result':'Retained exact outcome; replayed=true; do not reapply, downgrade newer UI projection or revalidate new revision in place of captured revision.'},{'event':'same key, different valid body','result':'ReplayConflict before any dependency IO; no new ordinal to evade conflict.'},{'event':'old binding closed, writer transferred or window instance replaced','result':'Validate caller/instance/binding first: UnauthorizedCaller or MissingBinding or StaleOwner; old runtime result is not disclosed to new authority. No resubmit on fresh binding.'},{'event':'inflight binding/window loss','result':'Owner finishes already admitted operation under captured authority only; keep evidence/Held. No delivery to stale window. New binding cannot claim same runtime request.'},{'event':'process restart or runtime record missing','result':'UnverifiedOutcome if admitted request cannot be authenticated in current runtime; old binding normally MissingBinding first. No automatic mutation retry or recreation. Durable issuer lookup is internal authenticated reconciliation only, not new H2 command.'},{'event':'authenticated durable material lookup succeeds after restart','result':'May establish material transition only; cannot establish runtime install/Undo success or ACK. Fresh owner open and explicit new intent required; prior uncertainty remains recorded.'},{'event':'known content commit, roots fail','result':'AppliedRetentionDeferred with original revisions, pin and mutation proof; never rollback, unchanged failure, automatic release or fabricated success.'}]
common['h2_error_lifecycle']={'closed_errors':errors,'mapping':mapping,'lifecycle':life,'precedence':['caller+instance','closed DTO/range','binding+generation','retained request full body','new request revision','candidate/pin/dependency preflight','content commit','retention delivery'],'postcommit_stage':'LiveRoots for install; UndoRoots for Undo outgoing retention; RedoRoots for retained redo root, according to actual failed root target. Multi-root failure reports first failed stage in declared order LiveRoots,UndoRoots,RedoRoots; retain all unresolved pins.','uncertainty':'UnverifiedOutcome does not assert zero changes. UI shows outcome unknown and requires reconciliation, preserves draft and disables blind retry. Other precommit failures assert zero content commit only when commit is positively known not attempted.'}
common['precedence']='Only after Owner adoption: v3 exact schema roots/full request bodies/error lifecycle override corresponding v2 definitions and historical descriptors. Original packages immutable. No adoption, product readiness or executable evidence implied.'
common_sha=dig(common)
# Explicit schemas, each file is a JSON Schema root with local defs. Schema descriptors are not scraped at runtime.
wire_defs={'U64Decimal':U,'Identifier':ID,'Digest':D}
wire_defs['Unsupported']=obj({'node_id':S,'type':S,'reason':S})
wire_defs['BindingProjection']=obj({'binding_ref':ID,'document_uuid':ID,'session_uuid':ID,'owner_generation':ref('U64Decimal'),'revision':ref('U64Decimal'),'design_json':S,'dirty':BOOL,'can_edit':BOOL,'unsupported':arr(ref('Unsupported')),'selection':{'type':['string','null']},'persistence_ready':BOOL})
wire_defs['Candidate']=obj({'candidate_ref':ID,'request_id':ID,'captured_revision':ref('U64Decimal'),'unsupported':arr(ref('Unsupported')),'installable':BOOL})
wire_defs['Select']=obj({'node_id':{'type':['string','null']},'content_changed':{'const':False},'revision':ref('U64Decimal')})
wire_defs['MockValue']={'oneOf':[obj({'kind':enum('Action')}),obj({'kind':enum('Toggle'),'checked':BOOL}),obj({'kind':enum('Text'),'text':S}),obj({'kind':enum('Number'),'number_text':S}),obj({'kind':enum('Selection'),'item_id':S})]}
wire_defs['Preview']=obj({'preview_session':ID,'source_revision':ref('U64Decimal'),'expected_sequence':ref('U64Decimal'),'stale':BOOL,'mock_state':arr(obj({'node_id':ID,'value':ref('MockValue')})),'capabilities':arr(obj({'node_id':ID,'allowed_actions':arr(enum('Activate','SetToggle','SetText','SetNumber','SelectItem'))}))})
wire_defs['Intent']=obj({'consumed_sequence':ref('U64Decimal'),'next_sequence':ref('U64Decimal'),'mock_delta':ref('MockValue'),'content_changed':{'const':False}})
wire_defs['Close']=obj({'closed':{'const':True},'content_changed':{'const':False}})
variants=[]
for name in ['Applied','NoChange','AppliedRetentionDeferred']:
 p={'outcome':enum(name),'projection':ref('BindingProjection'),'replayed':BOOL}
 if name=='NoChange':p.update(revision=ref('U64Decimal'),history_depth=ref('U64Decimal'))
 else:p.update(before_revision=ref('U64Decimal'),after_revision=ref('U64Decimal'),history_depth=ref('U64Decimal'),mutation_proof_ref=ID,pin_id=ID if name.endswith('Deferred') else {'type':['string','null']})
 if name.endswith('Deferred'):p.update(stage=enum('LiveRoots','UndoRoots','RedoRoots'),reason=enum('DependencyNotReady','StaleRoots','IoFailure','ProofMismatch','Indeterminate'))
 variants.append(obj(p))
wire_defs['MutationResult']={'oneOf':variants}
def field_schema(v):
 if isinstance(v,dict):
  if '$ref' in v or any(k in v for k in ['type','enum','const','oneOf','anyOf']):return copy.deepcopy(v)
  return obj({k:field_schema(x) for k,x in v.items()})
 if v=='bool':return BOOL
 if isinstance(v,str) and 'u64' in v.lower():return ref('U64Decimal')
 return S
error_variants=[]
for code,fields in errors.items():error_variants.append(obj({'code':enum(code),'details':obj({k:field_schema(v) for k,v in fields.items()})}))
wire_defs['Error']={'oneOf':error_variants}
response_names={'design_binding_open':'BindingProjection','design_binding_get':'BindingProjection','design_binding_transfer':'BindingProjection','design_candidate_prepare':'Candidate','design_candidate_install':'MutationResult','design_document_undo':'MutationResult','design_document_save':'BindingProjection','design_editor_select':'Select','design_viewer_begin':'Preview','design_viewer_intent':'Intent','design_viewer_refresh':'Preview','design_viewer_close':'Close','design_binding_close':'Close'}
# H2 save stays dependency-gated in this slice; no fabricated formal-save response. Integrated save result requires M04 adoption.
schemas={'transition-request.schema.json':request_schema}
for cmd,request in h2['dto']['requests'].items():
 schemas['h2-'+cmd+'-request.schema.json']={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:sga:cx-v3:'+cmd+':request','$defs':copy.deepcopy(wire_defs),**copy.deepcopy(request)}
 success=obj({'ok':{'const':True},'value':ref(response_names[cmd]),'replayed':BOOL})
 failure=obj({'ok':{'const':False},'error':ref('Error'),'replayed':BOOL})
 schemas['h2-'+cmd+'-response.schema.json']={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:sga:cx-v3:'+cmd+':response','$defs':copy.deepcopy(wire_defs),'oneOf':[failure] if cmd=='design_document_save' else [success,failure]}
m04=read((R/sources['M04']['report']).with_name('module-spec.json'))['effective_spec']['commands_ui']
for cmd,fields in m04['list'].items():
 props={k:(v if isinstance(v,dict) else enum('EssXmlV1','DesignJsonV1') if k=='source_format' else enum('close','switch_project','exit') if k=='action' else enum('save','discard','cancel') if k=='choice' else S) for k,v in fields.items()}
 sch=obj(props)
 if 'save_as_selection_id' in props:sch['required'].remove('save_as_selection_id')
 schemas['m04-'+cmd+'-request.schema.json']={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:sga:cx-v3:'+cmd+':request','$defs':copy.deepcopy(wire_defs),**sch}
schemas['m04-projection.schema.json']={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:sga:cx-v3:m04:projection','$defs':{'U64Decimal':U},**m04['projection_schema']}
# Full public request/response roots for H2 and actual M04 u64 command/projection roots; remaining M04 result precision remains original planned gate.
for n,s in schemas.items():put(O/n,s)
# Review-local document vectors. Never executable product tests or valid RED.
def sample(s):
 if '$ref' in s:return sample(defs[s['$ref'].split('/')[-1]])
 if 'oneOf' in s:return sample(s['oneOf'][0])
 if 'anyOf' in s:return sample(s['anyOf'][0])
 if 'enum' in s:return s['enum'][0]
 if s.get('type')=='object':return {k:sample(v) for k,v in s['properties'].items()}
 if s.get('type')=='array':return [sample(s['items'])]
 if s==U:return '7'
 if s==D:return 'a'*64
 return 'id_A'
def leaves(x,p=()):
 if isinstance(x,dict):
  for k,v in x.items():yield from leaves(v,p+(k,))
 elif isinstance(x,list):
  for i,v in enumerate(x):yield from leaves(v,p+(i,))
 else:yield p,x
def change(x,path,v):
 out=copy.deepcopy(x);at=out
 for k in path[:-1]:at=at[k]
 at[path[-1]]=v;return out
vectors=[]
for role,body in roles.items():
 options=body.get('oneOf',[body])
 for variant,opt in enumerate(options):
  req={'protocol':'SGA-TRANSITION-v2','issuer':'M05' if role in ['pin','import','publish','release','resolve'] or role.startswith('transfer') else 'M04','role':role,'ordinal':'0','context':sample(defs['WorkflowContext']),'body':sample(opt)}
  for path,val in leaves(req['body']):
   # enum fields with one admitted value are rejection vectors; mutable body fields produce distinct canonical digests.
   if path[-1] in ['completeness','mode']:continue
   replacement='8' if val=='7' else 'b'*64 if val=='a'*64 else 'Undo' if val=='Candidate' else val+'_B'
   other=change(req,('body',)+path,replacement)
   vectors.append({'id':'V3-HASH-'+str(len(vectors)+1),'role':role,'variant':variant,'changed_pointer':'/body/'+ '/'.join(map(str,path)),'same_transition_key':True,'a':req,'b':other,'a_utf8_hex':canon(req).hex(),'b_utf8_hex':canon(other).hex(),'a_sha256':dig(req),'b_sha256':dig(other),'expected':'ReplayConflict before IO for both admitted bodies; if changed enum is outside admitted domain InvalidRequest before replay. No second commit.','document_check':'distinct full canonical bytes and SHA only; role semantic validation/product behavior NOT RUN'})
  for fault in ['unknown','missing','null']:
   bad=copy.deepcopy(req)
   if fault=='unknown':bad['body']['unrecognized']='x'
   elif fault=='missing':del bad['body'][next(iter(bad['body']))]
   else:bad['body'][next(iter(bad['body']))]=None
   vectors.append({'id':'V3-HASH-'+str(len(vectors)+1),'role':role,'fault':fault,'value':bad,'expected':'InvalidRequest before hashing/replay/IO'})
assert all(v['a_sha256']!=v['b_sha256'] for v in vectors if 'a' in v)
# Deterministic reference-resolution only: every local pointer is traversed from its declared FILE root.
ref_checks=[]
def check_refs(v,root,path=''):
 if isinstance(v,dict):
  if '$ref' in v:
   q=v['$ref'];assert q.startswith('#/'),q;t=root
   for key in q[2:].split('/'):t=t[key.replace('~1','/').replace('~0','~')]
   ref_checks.append(path)
  for k,x in v.items():check_refs(x,root,path+'/'+k)
 elif isinstance(v,list):
  for i,x in enumerate(v):check_refs(x,root,path+'/'+str(i))
for n,s in schemas.items():check_refs(s,s,n)
# Real document examples for corrected u64 boundaries (no runtime claim).
u64_vectors=[{'value':v,'admitted':isinstance(v,str) and bool(re.fullmatch(r'0|[1-9][0-9]*',v)) and int(v)<=2**64-1} for v in ['0','9007199254740993','18446744073709551615','18446744073709551616','01','-1',1,None]]
put(O/'request-hash-vectors.json',vectors);put(O/'u64-vectors.json',u64_vectors)
put(O/'shared-contract.json',common);put(O/'h2-error-lifecycle.json',common['h2_error_lifecycle'])
gates=read(B/'prerequisite-gates.json')
new_gates=['Separate readonly semantic reacceptance of v3; author static checks are not reacceptance','Owner adopts full v3 request protocol and candidate DTO root shapes, including named Preview/Intent mock value encoding; no implicit architecture approval','Full JSON Schema draft2020-12 validator and generated Rust/JS DTO parity fixtures before Skeleton/valid RED; local pointer traversal only performed here','Every producer assembles frozen complete body BEFORE key lookup; canonical Unicode/control and metadata/root/identity one-field negative fixtures required in actual implementation','H2 request replay remains runtime-only; no public restart resume API or durable mutation exactly-once claim']
all_gates={'inherited':gates,'v3':new_gates}
cases=[]
for f,title,g,w,t in [('V2-F1','Full operation body','same transition key with changed pin_id, purpose, root content or metadata','submit the changed request','reject conflict before IO and preserve original receipt'),('V2-F1','Unknown body field','an otherwise valid closed role request with an unknown property','submit the request','reject InvalidRequest before hash or IO'),('V2-F2','Resolvable schema root','one designated schema file and its local definitions','resolve every local reference','every reference resolves within that file'),('V2-F2','Large wire integer','revision 9007199254740993 represented as decimal text','transport the revision','preserve exact decimal digits without Number conversion'),('V2-F3','Unknown mutation outcome','runtime request evidence was lost','request the previous result','report UnverifiedOutcome without automatic retry or inferred success'),('V2-F3','Committed retention failure','one verified content commit and failed root transfer','return the mutation result','report AppliedRetentionDeferred and retain actual revision and Held pin'),('V2-F3','Revoked binding','an old binding after writer transfer or restart','query using the old binding','reject binding authority before replay disclosure')]:
 cases.append({'id':'V3-BDD-'+str(len(cases)+1),'finding':f,'title':title,'given':g,'when':w,'then':t,'status':'PLANNED_NOT_RUN'})
feature=['Feature: Complete cross-module request identity and public result boundaries','  Background:','    Given the proposed v3 contracts are the review target','']
for x in cases:feature+=['  @'+x['finding'],'  Scenario: '+x['title'],'    Given '+x['given'],'    When '+x['when'],'    Then '+x['then'],'']
(O/'module.feature').write_text('\n'.join(feature),encoding='utf-8')
put(O/'bdd-tdd-plan.json',{'cases':cases,'fixture_files':['request-hash-vectors.json','u64-vectors.json','h2-error-lifecycle.json'],'step_definition_stubs':'NOT_CREATED per explicit no Skeleton instruction; declarative step plans only','pending_automation':new_gates,'assumptions':['No existing approved contract adopted by this document','All original 769 cases and v2 RR25 scenarios retained; new exact wire forms are proposed, not current product behavior'],'acceptance':['Per-role full-body hashing exact and closed','All designated local schema refs resolve','Every material/read/proof/replay error maps at known precommit, verified commit and uncertain commit phases','Original packages, acceptance and source796 remain byte-identical']})
def render(path,title,model,body):
 path.write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>'+html.escape(title)+'</title><style>body{max-width:1200px;margin:40px auto;font:16px system-ui;line-height:1.6}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f7;padding:16px}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #ccc}</style><h1>'+html.escape(title)+'</h1><p>候選文件交付；待另輪唯讀複驗與 Owner 一次採納。未建立 Skeleton、未改產品。tests/build/RED/GREEN/native NOT RUN。</p>'+body+'<script type="application/json" id="module-spec">'+json.dumps(model,ensure_ascii=False).replace('</','<\/')+'</script></html>',encoding='utf-8')
def pre(x):return '<pre>'+html.escape(json.dumps(x,ensure_ascii=False,indent=2))+'</pre>'
packages={};all_diffs=[];traces=[]
for name,src in sources.items():
 old=(R/src['report']).parent;dest=old.with_name(old.name.replace('-v2','-v3'));dest.mkdir(exist_ok=True)
 model=copy.deepcopy(read(old/'module-spec.json'));eff=model['effective_spec'];diffs=[]
 def patch(k,v):
  diffs.append({'module':name,'pointer':'/'+k,'before':copy.deepcopy(eff.get(k)),'after':copy.deepcopy(v)});eff[k]=copy.deepcopy(v)
 patch('shared_contract',{'model':common,'sha256':common_sha})
 patch('replay_protocol',protocol);patch('v3_schema_roots',{'central_directory':O.relative_to(R).as_posix(),'files':list(schemas),'interpretation':'Each named FILE is schema root, never DTO prose subtree or ModuleSpec. Local refs resolve within file. No network resolution.'})
 patch('wire_schema',{'U64Decimal':U,'authoritative_roots':list(schemas),'legacy_descriptors':'Historical prose only; old blanket-converted Candidate/Select/Preview/Intent/common scalar descriptors superseded by exact named roots. No silent inferred schema.'})
 if name=='M03-H2':
  dto=copy.deepcopy(eff['dto']);dto['errors']=errors;dto['schema_roots']={cmd:{'request':'h2-'+cmd+'-request.schema.json','response':'h2-'+cmd+'-response.schema.json'} for cmd in response_names};dto['responses']={n:copy.deepcopy(wire_defs[n]) for n in ['BindingProjection','Candidate','Select','Preview','Intent','Close','MutationResult']};dto['responses']['WriterTransfer']=ref('BindingProjection');dto['$defs']=copy.deepcopy(wire_defs);dto['validation_order']=common['h2_error_lifecycle']['precedence'];patch('dto',dto);patch('v3_error_lifecycle',common['h2_error_lifecycle'])
 if name=='M04':
  commands=copy.deepcopy(eff['commands_ui']);commands['$defs']={'U64Decimal':U};commands['common']={'meaning':'per-command closed request FILE roots + projection FILE root; old scalar u64 descriptor superseded'};commands['schema_roots']=[n for n in schemas if n.startswith('m04-')];patch('commands_ui',commands)
 if name=='M05':patch('issuer_proof_records',common['proof_registry_record'])
 model['identity'].update(status='V3_CANDIDATE_PENDING_REACCEPTANCE_AND_OWNER',at=at,source_revision=src['revision'],shared_contract_sha256=common_sha)
 model['previous_cx_differences']=model['differences'];model['differences']=diffs
 env=read(old/'envelope.json');tests=read(old/'test-plan.json');trace=read(old/'case-trace.json');traces+=trace
 tests['v3_cases']=cases;tests['v3_fixture_source']=O.relative_to(R).as_posix();tests['status']='PLANNED_NOT_RUN';eff['cx_test_plan']=tests
 for fn,value in [('module-spec.json',model),('shared-contract.json',common),('differences.json',diffs),('envelope.json',env),('test-plan.json',tests),('case-trace.json',trace)]:put(dest/fn,value)
 render(dest/'index.html',name+' V2-F1～F3 新候選 v3',model,'<p>主要模組責任、原範圍與架構圖沿用有效規格；候選 envelope 原樣保留，並非 union 授權。</p><a href="../'+old.name+'/index.html">原 v2 包</a><h2>候選架構與 ownership</h2><pre>UI → Tauri → M03 facade → M04 DocumentOwner → S1\nApplication → declared Ports ← native adapters\nM05 owns catalog transition receipts; no second document owner\nOne content commit; root delivery failure retains Held, never fake rollback.</pre><h2>精確差異</h2>'+pre(diffs)+'<h2>前置門檻／驗證邊界</h2>'+pre(all_gates))
 hashes={p.name:sha(p) for p in dest.iterdir() if p.is_file() and p.name not in ['artifact-hashes.json','review-request.json']};revision=dig(hashes);put(dest/'artifact-hashes.json',hashes);put(dest/'review-request.json',{'revision_sha256':revision,'previous_revision':src['revision'],'common_sha256':common_sha,'status':'PENDING_REACCEPTANCE_AND_OWNER'})
 packages[name]={'report':(dest/'index.html').relative_to(R).as_posix(),'revision':revision,'previous_revision':src['revision'],'common_sha256':common_sha,'original_cases':len(trace)};all_diffs+=diffs
assert len(traces)==769
put(O/'case-trace.json',traces);put(O/'all-differences.json',all_diffs);put(O/'module-revisions.json',packages);put(O/'prerequisite-gates.json',all_gates)
summary={'identity':{'task':'CX-V2-F1-F3-CORRECTION-v3','status':'ONE_OWNER_CONFIRMATION_PENDING_NOT_READY_FOR_IMPLEMENTATION','at':at,'branch':branch,'head':head},'common_sha256':common_sha,'children':packages,'findings':read(V/'findings.json'),'candidate_corrections':{'V2-F1':'11 closed roles, import two variants; full recursive body hash and per-field negative vectors','V2-F2':'Self-contained local-def schema FILE roots; concrete H2 responses replace historical scalar conversion descriptors','V2-F3':'Closed H2 errors + all11 read errors + phase/lifecycle mapping; no restart mutation resume'},'original_cases':769,'hash_vectors':len(vectors),'schemas':len(schemas),'gates':all_gates,'prior_files_sha256':frozen,'review':'Author static document checks only, no independent/delegated review or adoption'}
put(O/'module-spec.json',summary)
links='<table><tr><th>模組</th><th>候選包</th><th>原案例</th></tr>'
import os
for n,p in packages.items():links+='<tr><td>'+n+'</td><td><a href="'+os.path.relpath(R/p['report'],O).replace('\\','/')+'">v3</a></td><td>'+str(p['original_cases'])+'</td></tr>'
links+='</table>'
render(O/'index.html','CX V2-F1～F3 修訂一次確認入口 v3',summary,'<h2>交付與決策</h2><p>補完整 request body、可解析 schema roots、H2 closed error／lifecycle。原包與既有驗收保留。v3 為新候選，並非三缺口已驗收。一次確認範圍包括 protocol v2 bytes、M05 候選 receipt protocol 欄位及 H2 明確 response shapes；採納後仍按原各切片 gate 推進。</p>'+links+'<h2>行為、案例與差異</h2><p>769 原案例逐 row 保留；7 新 BDD 計畫、'+str(len(vectors))+' 文件負例／hash vectors。非產品測試。</p>'+pre(summary['candidate_corrections'])+'<h2>機器可讀入口</h2><p><a href="transition-request.schema.json">完整 per-role request schema</a> · <a href="request-hash-vectors.json">完整 bytes/hash 負例</a> · <a href="h2-error-lifecycle.json">closed errors 與 lifecycle</a> · <a href="all-differences.json">逐欄位差異</a> · <a href="bdd-tdd-plan.json">BDD/TDD 與待自動化</a></p><h2>前置門檻</h2>'+pre(all_gates))
assert all(sha(R/p)==h for p,h in frozen.items());assert all(sha(R/p)==h for p,h in base['source_hashes'].items())
put(O/'verification.json',{'status':'AUTHOR_STATIC_DOCUMENT_CHECKS_ONLY','local_ref_resolution_count':len(ref_checks),'schema_roots':len(schemas),'schema_validator':'NOT RUN: jsonschema dependency unavailable; deterministic local-ref traversal only, no install/manifests changed','hash_vectors':len(vectors),'distinct_full_hash_vectors':sum('a' in v for v in vectors),'u64_document_vectors':u64_vectors,'frozen_files':len(frozen),'source_files':796,'source_unchanged':True,'tests_build_RED_GREEN_native':'NOT RUN','reacceptance':'NOT RUN','counts':counts})
hashes={p.name:sha(p) for p in O.iterdir() if p.is_file() and p.name not in ['artifact-hashes.json','review-request.json','current-state.json','board-evidence.json']};revision=dig(hashes)
put(O/'artifact-hashes.json',hashes);put(O/'review-request.json',{'revision_sha256':revision,'common_sha256':common_sha,'children':packages,'status':'ONE_OWNER_CONFIRMATION_PENDING','review':'Separate readonly reacceptance required; no self-approval'})
put(O/'current-state.json',{'state':'V3_CANDIDATE_PENDING_REACCEPTANCE_AND_OWNER','revision':revision,'report':'index.html'})
for mod in ['M01','M02','M03','M04','M05','M06','M07']:
 p=T/mod/'planning/current-state.json';nav=read(p);nav['cx_v3_revision']={n:v for n,v in packages.items() if n.split('-')[0]==mod};nav['joint_confirmation_entry']=(O/'index.html').relative_to(R).as_posix();put(p,nav)
p=B/'current-state.json';nav=read(p);nav['v3_correction_entry']=(O/'index.html').relative_to(R).as_posix();nav['v3_correction_revision']=revision;put(p,nav)
def mutate(s):
 card=next(x for x in s['tasks'] if x['id']=='PD-P1-ESS-DEC-01');assert card['zone']=='red';card['note']+='\n[V3 candidate V2-F1..F3] '+(O/'index.html').relative_to(R).as_posix()+' revision '+revision+'; full role hash bodies/vectors, local schema roots, H2 error/lifecycle. Pending readonly reacceptance and Owner; no Skeleton/product changes. Original796 preserved.'
mutate_snapshot_file(board,mutate,lock_factory=FileLock)
aa,bb,cc=split_snapshot(board.read_text(encoding='utf-8'));after=json.loads(bb)
assert (a,c)==(aa,cc);assert {k:v for k,v in before.items() if k!='tasks'}=={k:v for k,v in after.items() if k!='tasks'}
assert [x for x in before['tasks'] if x['id']!='PD-P1-ESS-DEC-01']==[x for x in after['tasks'] if x['id']!='PD-P1-ESS-DEC-01'];assert counts==dict(Counter(x['zone'] for x in after['tasks']))
put(O/'board-evidence.json',{'before':counts,'after':counts,'shell_root_other_cards_preserved':True,'own_card':'PD-P1-ESS-DEC-01','zone':'red'})
print(json.dumps({'revision':revision,'common':common_sha,'children':9,'vectors':len(vectors),'schemas':len(schemas),'frozen':len(frozen),'counts':counts}))
