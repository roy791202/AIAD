"""RR-F1..F6 proposal documents only. Does not emit product or executable test code."""
import copy, hashlib, html, json, os, re, subprocess, sys, uuid
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
OUT=Path(__file__).resolve().parent; TASKS=OUT.parent; ROOT=OUT.parents[4]
sys.path.insert(0,str(ROOT))
from tools.board.board_core.snapshot_safe import split_snapshot, mutate_snapshot_file
from tools.board.board_core.json_store import FileLock
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x): return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def text(x): return html.escape(json.dumps(x,ensure_ascii=False,indent=2))
def link(p,base=OUT): return os.path.relpath(p,base).replace('\\','/')
at=datetime.now(timezone.utc).isoformat()
base=TASKS/'integration-contract-revision-v1'; review=TASKS/'integration-contract-reacceptance-v1'
sources=load(base/'module-revisions.json'); findings=load(review/'findings.json')
baseline=load(TASKS/'M01/planning/s2-green/source-current.json')
branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert (branch,head)==(baseline['branch'],baseline['head'])
assert all(sha(ROOT/p)==h for p,h in baseline['source_hashes'].items())
board=ROOT/'docs/PROJECT-BOARD.html'; pre,inner,post=split_snapshot(board.read_text(encoding='utf-8')); before=json.loads(inner)
counts=dict(Counter(t['zone'] for t in before['tasks']))
frozen=dict(load(base/'module-spec.json')['original_hashes'])
for folder in [base,review]+[(ROOT/p['report']).parent for p in sources.values()]:
 for p in folder.iterdir():
  if p.is_file() and p.name!='current-state.json': frozen[str(p.relative_to(ROOT)).replace('\\','/')]=sha(p)
assert all(sha(ROOT/p)==h for p,h in frozen.items())

# Contract proposed for adoption. Fixed fields replace the ambiguous v1 definitions.
common=copy.deepcopy(load(base/'shared-contract.json')); common['contract_id']='CX-COMMON-v2-RR'
common['status']='PROPOSED_PENDING_ONE_OWNER_CONFIRMATION'
common['wire_types']['Context']='Server-derived immutable WorkflowContext {project_uuid,document_uuid,session_id,owner_generation:U64,captured_revision:U64,workflow_id:UUID}; no transition operation_id in context. Runtime authority never comes from labels/DTO.'
u64={'type':'string','pattern':'^(0|[1-9][0-9]*)$','maxLength':20,'semantic_validation':'parse checked u64 <=18446744073709551615; reject JSON number; never JS Number conversion'}
common['wire_schema']={'U64Decimal':u64,'scope':'Every Tauri/JSON request, response and error revision/generation/epoch/count/size/sequence uses U64Decimal when internal type u64. Domain Rust u64 and existing persisted schemas unchanged. Actual design floating-point values remain C1 number policy, not blanket strings.','validation_order':['trusted caller','closed shape','u64 decimal syntax/range','binding generation','retained request lookup','new request captured revision','reservation/pin/commit']}
common['replay_protocol']={
 'workflow_id':'Server UUID minted once per immutable top-level capture. Context equality includes workflow_id; request replay maps authorized caller+session+command+request_id to same workflow. New capture/new authorized request => new workflow.',
 'operation_id':'Internal UUIDv5(namespace=workflow_id, name=UTF8 role + "/" + decimal transition ordinal). Closed role: resolve|pin|import|install|undo|transfer-live|transfer-formal|transfer-recovery|release|publish|ack. Ordinal starts0; request body changes require a new operation ordinal only after explicit new transition, never to bypass conflict.',
 'key':'(issuer,store_identity,workflow_id,operation_id); expected role and immutable context must match. Same key + same request digest returns same persisted receipt. Same key + different digest => ReplayConflict before IO. Prepared/InFlight => InProgress, never another commit.',
 'request_digest':'SHA256(UTF8 compact JSON canonical value tree: object keys UTF8 byte sorted; strings JSON escaping as SGA-DESIGN-SEM-v1; integers decimal strings; arrays retain order; no whitespace/BOM). Input: {protocol:"SGA-TRANSITION-v1",issuer,role,ordinal,context,source_receipt_ids,target_identity,asset_pairs,root_manifest_ids,expected_catalog_generation}; all fields present, absent option=null; asset_pairs sorted(asset_id,digest); root_manifest_ids sorted unique. Exact bytes document fixtures required before RED.',
 'runtime_commands':'Existing H2 request records remain runtime-only 128/binding,1024/runtime; no eviction and no durable exactly-once claim. Runtime loss => UnverifiedOutcome; never reconstruct mutation success from pin receipt alone.',
 'resume':'Verify issuer durable store + exact target identity/raw/catalog evidence. Terminal receipt returns retained result; uncertain prepared record stays Indeterminate/Held. No automatic IO retry, rollback, ACK or release on missing evidence.',
 'new_persistence':'M05 transition_receipts map joins the same single catalog index CAS as pin/root state. New pending schema change, not existing capability. Other issuers retain actual existing durable IO/recovery/copy receipts; do not introduce a global proof database.'}
common['material_api']={
 'resolve':'resolve(WorkflowContext,ordered_requests)->ResolutionSnapshot',
 'pin':'pin(WorkflowContext,ResolutionSnapshot,PinPurpose,TransitionKey)->PinReceipt',
 'validate_pin':'validate_pin(WorkflowContext,PinReceipt)->VerifiedPin',
 'read_pinned_version':'read_pinned_version(WorkflowContext,VerifiedPin,asset_id,digest,max_bytes:u64)->VerifiedBytes',
 'import':'import(WorkflowContext,TrustedSourceSelection,ImportMetadata,TransitionKey)->ImportedPinnedManifest; native source bytes verified before durable immutable import; no UI path authority',
 'import_verified_versions':'import_verified_versions(WorkflowContext,VerifiedBundle,PinPurpose,TransitionKey)->ImportedPinnedManifest',
 'register_roots':'register_roots(TrustedProviderCapability,RootKind)->RootRegistration; internal trusted composition only; no UI registration/callback',
 'publish_roots':'publish_roots(RootRegistration,expected_epoch:u64,RootManifest,TransitionKey)->RootObservationReceipt; owner provider attests current fenced manifest; stale epoch => StaleRoots, unknown => Unknown not empty',
 'transfer':'transfer(WorkflowContext,pin_id,RootManifest,AuthenticatedExternalProof,TransitionKey)->TransferReceipt',
 'release':'release(WorkflowContext,pin_id,RootBundle,TransitionKey)->ReleasedReceipt|RetainedReasons'}
common['proof_types']['ResolutionSnapshot']='{WorkflowContext,catalog_generation,catalog_raw_digest,snapshot_digest,completeness:Complete,assets,bindings}; same immutable workflow across pin/transfer; no transition operation_id in context.'
common['proof_types']['TransferReceipt']='{issuer:M05,catalog_generation,catalog_raw_digest,pin_id,root_manifest_ids,external_proof_id,WorkflowContext,TransitionKey,receipt_id}; verified durable catalog commit required.'
common['proof_types']['VerifiedBundle']='{WorkflowContext,source_digest,entries:[asset_id,digest,size_bytes,verified_bytes_or_handle],legacy_alias_mapping}; trusted issuer verifies all bytes/hash/closure.'
common['proof_registry_record']={
 'schema':'SGA-MATERIAL-RECEIPT-v1 (new catalog index transition_receipts record; pending schema adoption)',
 'fields':{'issuer':'M05','receipt_id':'UUID','workflow_id':'UUID','operation_id':'UUIDv5','role':'closed transition role','ordinal':'u64 internal','request_digest':'lowerhex64','context':'WorkflowContext','store_identity':'native identity binding','target_identity':'native catalog target identity','expected_generation':'u64','committed_generation':'u64','source_receipt_ids':'ordered typed issuer IDs','pin_id':'UUID|null','asset_pairs':'sorted exact immutable pairs','root_manifest_ids':'sorted unique UUIDs','external_proof':'{issuer,receipt_id,kind,context_digest,target_identity,raw_digest,projection_digest}|null','result':'Tagged terminal Pin|Imported|Transferred|Released; no runtime DocumentMutation success here'},
 'atomicity':'Record and pin/root transition in same catalog raw commit. Logical catalog_generation/target_identity verify inclusion without circular embedding of own raw digest. External raw CommitReceipt kept as issuer evidence, not hashed into the same committed bytes.',
 'trust':'Resolve receipt_id only server-side under native store identity+verified catalog raw bytes. UI-supplied receipt body never authoritative. Cross-store/context/action mismatch => ProofMismatch.',
 'retention':'No receipt eviction or pin timeout in this slice. Input/index limits from M05 remain; full index => CapacityExceeded before mutation; compaction/GC separate proposal.',
 'external_issuers':{'M04':'FormalSaveProof requires IO receipt+M05 transfer+captured semantic ACK; runtime owner replay loss => UnverifiedOutcome unless all issuer evidence actually revalidated. MutationReceipt runtime only.', 'M07':'Immutable attempt/payload/index receipt; LocalIntegrityReady independent source ACK.', 'M01':'final path Ready marker and matching digests; not inherited source approval.'}}
common['proof_types']['AuthenticatedExternalProof']='Opaque issuer receipt lookup with issuer/kind/WorkflowContext/target/evidence validation per proof_registry_record; no trusted DTO body. Missing runtime-only issuer record => UnverifiedOutcome.'
common['proof_types']['MutationReceipt']={'context':'WorkflowContext','before_revision':'U64','after_revision':'U64','content_semantic':'typed digest','pin_id':'UUID|null','result':'Applied|NoChange|AppliedRetentionDeferred','stage':'None|LiveRoots|UndoRoots|RedoRoots','proof_ref':'opaque runtime mutation proof id','replayed':'bool'}
common['store_read_contract']={
 'trait':'MaterialStorePort -> StoreHandle.read_verified_blob(VerifiedStorePinGrant,digest:Digest,expected_size:u64,max_bytes:u64)->VerifiedBlobRead',
 'grant':'Crate-private trusted constructor in M05 application composition: immutable store_identity,pin_id,workflow_id,asset_id,digest,size,pin_catalog_generation; issued only after verified Held or Transferred pin membership. Released pin denied. Not deserializable from UI.',
 'preconditions':'0 < max_bytes <= M05 existing admitted blob limit; expected_size<=max_bytes; grant exact pair/size/store matches. Acquire safe native immutable object handle, reject alias/reparse/size/hash mismatch, no path/URI returned as authority.',
 'result':'VerifiedBlobRead {store_identity,digest,size_bytes,immutable bounded bytes or guarded read handle}. Stream exactly expected_size, hash entire bytes before consumer install/export. Handle lifetime owns source access; no reopen-by-path.',
 'errors':['PinNotReadable','GrantMismatch','LimitExceeded','BlobMissing','SizeMismatch','IntegrityFailure','IdentityChanged','AliasRejected','Busy','UnsupportedPlatform','IoFailure'],
 'side_effects':'No catalog mutation, repair, delete, overwrite, fallback/latest mapping or arbitrary read. Release blocked by retained pin/fence until read operation ends.'}
common['mutation_wire_result']={
 'tag':'outcome','closed':True,
 'Applied':{'outcome':'Applied','projection':'BindingProjection','before_revision':'U64Decimal','after_revision':'U64Decimal','history_depth':'U64Decimal','mutation_proof_ref':'opaque','pin_id':'UUID|null','replayed':'bool'},
 'NoChange':{'outcome':'NoChange','projection':'BindingProjection','revision':'U64Decimal','history_depth':'U64Decimal','replayed':'bool'},
 'AppliedRetentionDeferred':{'outcome':'AppliedRetentionDeferred','projection':'BindingProjection','before_revision':'U64Decimal','after_revision':'U64Decimal','history_depth':'U64Decimal','pin_id':'UUID','mutation_proof_ref':'opaque','stage':['LiveRoots','UndoRoots','RedoRoots'],'reason':['DependencyNotReady','StaleRoots','IoFailure','ProofMismatch','Indeterminate'],'replayed':'bool'},
 'precommit_error':'{ok:false,error:closed existing error}; zero content commit. Once S1 commit occurred cannot use ErrorUnchanged, undo rollback or failed toast implying no effect.',
 'ui':'Show installed revision plus material retention pending; preserve Held, disable unsafe pin release/export until proofs complete. Replay returns original result, never reapply or overwrite newer projection. Writer transfer has separate BindingProjection result, never fabricate mutation/history.'}
common['readiness_gates'] += ['RR document proposals need separate readonly reacceptance; no self-approval','M05 receipt schema and bounded read grant candidate adoption before Port/Skeleton','Per-command exact DTO/schema and phase fixtures compiled independently before valid RED']
common['precedence']='v2 common definitions replace v1 common and exact listed module pointers only after Owner adoption. Original embedded behavior rows are historical trace, not competing runtime protocol. Context means WorkflowContext, operation_id means TransitionKey.operation_id at every material call. No in-place update to original Approved artifacts.'
common_sha=digest(common)

workflow='11111111-1111-4111-8111-111111111111'
transition_vectors=[{'workflow_id':workflow,'role':r,'ordinal':'0','operation_id':str(uuid.uuid5(uuid.UUID(workflow),r+'/0'))} for r in ['pin','import','transfer-live','release']]
assert len({v['operation_id'] for v in transition_vectors})==4
request_vector={'protocol':'SGA-TRANSITION-v1','issuer':'M05','role':'pin','ordinal':'0','context':{'project_uuid':'22222222-2222-4222-8222-222222222222','document_uuid':'33333333-3333-4333-8333-333333333333','session_id':'session_1','owner_generation':'3','captured_revision':'7','workflow_id':workflow},'source_receipt_ids':[],'target_identity':'native_store_1','asset_pairs':[['assetA',hashlib.sha256(b'ABC').hexdigest()]],'root_manifest_ids':[],'expected_catalog_generation':'4'}
request_bytes=json.dumps(request_vector,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
document_vectors={'transition_keys':transition_vectors,'canonical_request':{'value':request_vector,'utf8':request_bytes.decode(),'sha256':hashlib.sha256(request_bytes).hexdigest()},'blob':{'bytes_hex':'414243','size':'3','sha256':hashlib.sha256(b'ABC').hexdigest()},'meaning':'Python document UUID/canonical ASCII fixture arithmetic only, not product/native/RED evidence'}

scenarios=[
 ('RR-F1','one_owner','M03-H2,M04','two views of same trusted document at revision7','open through facade then apply one accepted edit','both projections revision8 and one owner/session; history depth1',{'owner_sessions':1,'commits':1,'revision':'8'}),
 ('RR-F1','dependency','M03-H2','owner provider unavailable','open design binding','DependencyNotReady; zero session constructors in facade',{'constructors':0,'commits':0}),
 ('RR-F2','bounded_read','M05,M06,M07','Held pin covers assetA digest a size3 bytes ABC','read with max_bytes3','verified ABC size3; catalog unchanged',{'bytes_hex':'414243','size':'3','catalog_writes':0}),
 ('RR-F2','released','M05','Released pin and same immutable bytes exist','read through closed material input','PinNotReadable; zero blob reads',{'reads':0}),
 ('RR-F2','oversize','M05','grant size3 and max_bytes2','request pinned bytes','LimitExceeded before allocation/read',{'reads':0,'allocations':0}),
 ('RR-F2','corrupt','M05','grant size3 digest of ABC but object ABD','read pinned bytes','IntegrityFailure; no consumer commit or repair',{'consumer_commits':0,'repairs':0}),
 ('RR-F2','root_epoch','M05','registered Live provider epoch8','publish epoch7 manifest','StaleRoots and previous observation retained',{'catalog_writes':0}),
 ('RR-F3','wire_exact','M01-S3,M02,M03-C1,M03-H2,M04,M05,M06-preflight,M06,M07','revision decimal string9007199254740993','decode and return projection','exact same string with no Number roundtrip',{'output':'9007199254740993'}),
 ('RR-F3','wire_overflow','M04','expected_revision string18446744073709551616','submit save','InvalidRequest Range; no reservation/IO',{'io_calls':0}),
 ('RR-F3','wire_number','M04','expected_revision JSON number7','submit save','InvalidRequest Type; no owner mutation',{'commits':0}),
 ('RR-F4','deferred','M03-H2,M04,M05','candidate pinned at R7 and Live root transfer fails after commit','install candidate','AppliedRetentionDeferred R8 history1 Held retained',{'commits':1,'revision':'8','history':'1','ack_calls':0,'pin':'Held'}),
 ('RR-F4','replay','M03-H2,M04','retained result of installed request R8','retry identical request','same AppliedRetentionDeferred receipt; no second commit',{'total_commits':1,'replayed':True}),
 ('RR-F4','nochange','M03-H2,M04','candidate semantically equals R7','install candidate','NoChange revision7 history unchanged',{'commits':0,'revision':'7'}),
 ('RR-F5','transition_keys','M05','one workflow and pin/import/transfer distinct roles ordinal0','execute authorized transitions','three distinct operation UUIDs same context workflow; no ReplayConflict',{'transition_keys':3,'workflow_count':1}),
 ('RR-F5','replay_conflict','M05','persisted operation key request digestA','reuse same key with digestB','ReplayConflict before catalog write',{'catalog_writes':0}),
 ('RR-F5','restart','M05','catalog includes terminal transferred receipt under native store identity','resolve receipt after restart','same receipt revalidated; no repeated transfer',{'new_transfers':0}),
 ('RR-F5','runtime_loss','M04,M05','runtime mutation record lost but pin persists','request mutation completion after restart','UnverifiedOutcome Held retained; no synthetic ACK',{'ack_calls':0,'commits':0}),
 ('RR-F5','foreignproof','M04,M05,M07','valid receipt from another project or issuer action','transfer root or ACK','ProofMismatch; Held retained',{'ack_calls':0,'transfers':0}),
 ('RR-F6','formal_busy','M04','formal write reservation at R7 before IO completion','submit edit','Busy and revision7 unchanged',{'commits':0,'revision':'7'}),
 ('RR-F6','late_ack','M04','R7 file receipt verified; reservation released on IO completion; roots pending; Healthy edit advances R8','finish captured R7 root transfer and semantic ACK','formal baseline R7; live R8 dirty; no rollback',{'live_revision':'8','formal_revision':'7','dirty':True}),
 ('RR-F6','recovery_edit','M04,M07','immutable recovery attempt captures R7 and pin then releases capture fence','edit live document while payload copy continues','R8 edit allowed; recovered payload still R7; formal baseline unchanged',{'payload_revision':'7','live_revision':'8'}),
 ('RR-F6','provider_unknown','M05,M07','all material pairs resolved and pinned but Recovery root provider Unknown','install candidate then request release','install permitted; release RetainedReasons UnknownRoots',{'install_commits':1,'pin_released':False}),
 ('RR-F6','golden_missing','M02','14 template resources or standalone full transitive lock golden absent','evaluate renderer readiness','BUILD_GOLDEN_REQUIRED; not valid RED',{'ready':False}),
 ('RR-F6','projector_missing','M04,M06','unknown reference-bearing ESS field outside typed projector','prepare clear or merge','UnsupportedProjection before mutation',{'commits':0}),
 ('RR-F6','native_missing','M01-S3,M05,M07','native Windows11 alias fixture not executed','evaluate native acceptance','NOT RUN; no product readiness claim',{'native':'NOT RUN'})]
cases=[]
for f,s,ms,g,w,t,o in scenarios:
 cases.append({'id':'BDD-'+s.upper().replace('_','-')+'-RR','tdd':'TDD-'+s.upper().replace('_','-')+'-RR','finding':f,'modules':ms.split(','),'given':g,'when':w,'then':t,'fixture':{'owner_generation':'3','captured_revision':'7','workflow_id':'11111111-1111-4111-8111-111111111111','formal_phase':'see given; no mutation during FormalWriteReservation','expected':o},'status':'PLANNED_NOT_RUN','level':'L2 module contract / L4 adjacent; native cases L3','valid_red':'Only after adopted architecture, accepted child Skeleton, independent fixture selfcheck and successful compile; absence of dependencies/golden/environment is not RED.'})

gates=copy.deepcopy(load(review/'prerequisite-gates.json'))
for g in gates:
 if g['gate']=='Pin/proof/replay persistence': g.update(status='PROPOSED_EXACT_DOCUMENT_CONTRACT_PENDING_REACCEPTANCE',scope='New bounded read grant/transition receipt schema; Owner adoption and real product/native tests still required.')
gates.append({'gate':'RR-F1..F6 correction review','status':'PENDING_READONLY_REACCEPTANCE','scope':'This delivery prepares candidate corrections. No independent review/architecture approval inferred.'})
packages={}; all_diffs=[]; all_trace=[]; claims=defaultdict(list)
def render(path,title,model,sections):
 path.write_text('<!DOCTYPE html><html lang="zh-Hant"><meta charset="utf-8"><title>'+title+'</title><style>body{font:16px/1.65 system-ui;max-width:1200px;margin:32px auto;padding:24px;background:#f3f6fa;color:#183047}section{background:white;padding:22px;margin:18px 0;border-radius:10px}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{width:100%;border-collapse:collapse}td,th{padding:9px;border-bottom:1px solid #ddd;text-align:left;overflow-wrap:anywhere}.status{background:#fff0bd;padding:18px}a{color:#12629b}</style><h1>'+title+'</h1><p class="status">文件候選修訂，待一次採納與另輪複驗；NOT_READY_FOR_IMPLEMENTATION。未建 Skeleton／產品程式碼，產品 tests/build/RED/GREEN/native NOT RUN。</p>'+sections+'<script type="application/json" id="module-spec">'+json.dumps(model,ensure_ascii=False).replace('</','<\/')+'</script></html>',encoding='utf-8')

for name,source in sources.items():
 olddir=(ROOT/source['report']).parent; dest=olddir.with_name(olddir.name.replace('-v1','-v2'));dest.mkdir(parents=True,exist_ok=True)
 old=load(olddir/'module-spec.json');model=copy.deepcopy(old);eff=model['effective_spec']; diffs=[]
 def patch(keys,value,f):
  cursor=eff
  for k in keys[:-1]:
   if not isinstance(cursor.get(k),dict):cursor[k]={}
   cursor=cursor[k]
  prev=copy.deepcopy(cursor.get(keys[-1],{'absent':True}));cursor[keys[-1]]=copy.deepcopy(value)
  diffs.append({'module':name,'rr':f,'pointer':'/'+('/'.join(keys)),'before':prev,'after':copy.deepcopy(value),'status':'PROPOSED_NOT_ADOPTED'})
 patch(['shared_contract'],{'id':common['contract_id'],'sha256':common_sha,'model':common},'RR-F2/F3/F4/F5')
 patch(['wire_contract'],common['wire_types'],'RR-F3')
 patch(['cross_owner_proofs'],common['proof_types'],'RR-F4/F5')
 patch(['replay_protocol'],common['replay_protocol'],'RR-F5')
 patch(['issuer_proof_records'],common['proof_registry_record'],'RR-F5')
 patch(['wire_schema'],common['wire_schema'],'RR-F3')
 if name=='M03-H2':
  patch(['owner_binding','records','DesignOwnerRecord'],{'binding_ref':'UUID derived facade record','document_owner':'DocumentOwnerHandle (opaque M04 input capability, no DocumentSession value)','writer_binding':'trusted window nonce + generation (derived from M04)','projection_epoch':'u64 derived only','forbidden':'No S1 constructor, content/history/baseline storage or independent authoritative registry'},'RR-F1')
  patch(['owner_binding','owner_init'],'M04 open/attach returns DocumentOwnerHandle after native identity+C1/material checks. H2 never initializes S1. Missing integration => DependencyNotReady(M04_OWNER_INTEGRATION), zero facade-created sessions. M04 alone initializes exactly one existing S1 session.','RR-F1')
  patch(['owner_binding','S1_reuse'],'Only M04 document_owner.rs owns/mutates existing S1 DocumentSession. H2 holds opaque handle and immutable DTO projections. No direct constructor/edit/undo/baseline API in facade.','RR-F1')
  patch(['architecture'],{'hexagonal':'UI/Tauri closed input → M03 facade → M04 DocumentOwner input → existing S1; M04 → C1/material output abstractions; adapters implement Ports.','dependency':'M03 depends M04 input abstractions+immutable DTO only; no M04 callback to M03 runtime for material resolution.','state_owner':'M04 owns one S1 session; M03 owns derived candidate/viewer ephemeral records only.','transaction':'M03 prepare candidate → M04 validate/recheck → M05 durable pin → M04 one S1 Edit/Undo → M05 roots → mutation result/deferred.','forbidden':'No UI FS, facade S1 constructor/mutation, second registry, private journal or Viewer generic dispatch.'},'RR-F1')
  patch(['owner_binding','call_mapping'],{'open':'M04.attach_document(trusted_binding)->DocumentOwnerHandle','get':'M04.get_projection(handle)','install':'M04.submit_design_candidate(handle,candidate,TransitionKey)','undo':'M04.undo(handle,TransitionKey)','transfer_writer':'M04.transfer_writer(handle,trusted_window)','close':'M04.detach_view(handle); authority/discard remains M04'},'RR-F1')
  patch(['dto','responses','InstallUndoTransfer'],common['mutation_wire_result'],'RR-F4')
  patch(['dto','responses','WriterTransfer'],'BindingProjection with generation U64Decimal; no content mutation result/history change','RR-F4')
  patch(['ui','retention_deferred'],common['mutation_wire_result']['ui'],'RR-F4')
 if name=='M04':
  commands=copy.deepcopy(eff['commands_ui'])
  for cmd,fields in commands['list'].items():
   for k,v in list(fields.items()):
    if v=='u64':fields[k]={'$ref':'#/$defs/U64Decimal'}
  commands['common']='Closed DTO; expected_revision/generation/count/epoch/size fields use U64Decimal strings on wire; internal Rust u64 unchanged. Trusted actual caller and native identity required.'
  commands['projection_schema']={'type':'object','additionalProperties':False,'properties':{k:({'$ref':'#/$defs/U64Decimal'} if k in ['generation','revision'] else {'type':'boolean'} if k in ['dirty','can_mutate'] else {'type':'array','items':{'type':'string'}} if k in ['pending_binding_ids','blocked_capabilities'] else {'type':'string'}) for k in ['project_uuid','document_uuid','session_uuid','generation','revision','format','semantic_profile','dirty','can_mutate','health','pending_binding_ids','blocked_capabilities']},'required':['project_uuid','document_uuid','session_uuid','generation','revision','format','semantic_profile','dirty','can_mutate','health','pending_binding_ids','blocked_capabilities']}
  commands['response']='Closed tagged result; Projection uses projection_schema; mutation uses common mutation_wire_result; save uses existing formal proof/deferred outcomes. Error expected/observed revision and generation also U64Decimal. No raw u64 JSON number.'
  patch(['commands_ui'],commands,'RR-F3/F4')
  patch(['reservation_completion_phases'],{'A':'Acquire FormalWriteReservation R7; edits Busy until IO completion.', 'B':'Verify IO receipt or classify uncertain. Release write reservation on classified terminal IO completion; on mismatch RecoveryBlocked prohibits mutation.', 'C':'With verified file receipt, Healthy owner may edit R8 while root-transfer/semantic ACK R7 deferred. Captured proof remains immutable; ACK R7 never cleans R8.', 'D':'RecoveryAttempt only holds immutable capture fence through capture+pin; live edits after it are allowed. No formal baseline advance from recovery ACK.'},'RR-F6')
 if name=='M05':
  patch(['ports','application_inputs'],common['material_api'],'RR-F2/F5')
  patch(['ports','MaterialStorePort'],{'existing':'bind_store/inspect_identity/index_target/import_blob/verify_blob remain under original narrowed candidate restrictions','read_verified_blob':common['store_read_contract'],'forbidden':'No arbitrary path reads, remove/overwrite/repair or public FileCommitPort change'},'RR-F2')
  patch(['ports','ResolutionContext'],common['wire_types']['Context'],'RR-F5')
  patch(['schema','transition_receipts'],common['proof_registry_record'],'RR-F5')
  patch(['ports','call_mapping'],{'material_import':'trusted source selection → import → immutable blob receipt → catalog pin+receipt same CAS','export_or_snapshot':'validate_pin → issue private VerifiedStorePinGrant → driven read_verified_blob → verify bytes → consumer','registration':'trusted application composition → register_roots; closed RootKind LiveDocuments|UndoRedo|FormalDocuments|RecoverySnapshots|ExportImportOperations','publish':'provider current epoch/fence → publish_roots; stale/Unknown does not authorize release'},'RR-F2')
 if name in ['M06','M07']:
  patch(['material_exchange_inputs'],{k:common['material_api'][k] for k in ['validate_pin','read_pinned_version','import_verified_versions','transfer','release']},'RR-F2/F5')
 if name in ['M01-S3','M02','M04','M06','M07']:
  patch(['transition_identity_binding'],'WorkflowContext immutable across child calls; derive per-role TransitionKey per common replay_protocol. Existing UI request UUID is runtime request ID, not reused as catalog operation key. Pin receipt never proves runtime content commit or formal ACK.','RR-F5')
 # Explicit wire field inventory traverses actual request/response schema, excluding source/persisted/BDD history.
 wire_paths=[]
 def wire_fix(v,path):
  if isinstance(v,dict):
   for k,x in list(v.items()):
    if isinstance(x,str) and re.search(r'\bu64\b',x) and ('string' in x.lower() or x.strip()=='u64'):
     wire_paths.append({'pointer':path+'/'+k,'internal':'u64','wire':'U64Decimal','previous':x}); v[k]={'$ref':'#/$defs/U64Decimal'}
    else: wire_fix(x,path+'/'+k)
  elif isinstance(v,list):
   for i,x in enumerate(v):wire_fix(x,path+'/'+str(i))
 for k in ['dto','commands_ui']:
  if k in eff:
   fixed=copy.deepcopy(eff[k]);wire_fix(fixed,'/'+k);patch([k],fixed,'RR-F3')
 patch(['wire_field_inventory'],{'concrete_fields':wire_paths,'default_for_declared_internal_u64':'All other proposed UI inputs/outputs/errors with typed u64 field must use common U64Decimal; source format numeric data/persisted schema excluded. Exact command DTO fixture coverage remains acceptance gate, not inferred from prose.'},'RR-F3')
 env=copy.deepcopy(load(olddir/'envelope.json'));env['status']='RR_REVISED_CANDIDATE_PENDING_OWNER'
 env['rr_contract_restrictions']={'M03-H2':'design_owner.rs facade only, M04 document_owner owns S1','M05':'existing material_store.rs Port/adapter and asset_store.rs catalog schema/read grant/receipt transitions only; no generic filesystem capability','all':'DTO changes only command boundary; Rust/domain/persisted schemas unchanged except explicit M05 transition_receipts proposal; existing accepted S1/IO contracts preserved'}
 # Exact additional test child needed for receipt/wire protocol; no actual files created.
 additions=[]
 if name=='M05':additions=['apps/sgenaxis-desktop/crates/sgenaxis-host/tests/phase1_material_replay.rs','apps/sgenaxis-desktop/crates/sgenaxis-adapters/tests/phase1_material_pinned_read.rs']
 if name in ['M03-H2','M04']:additions=['apps/sgenaxis-desktop/crates/sgenaxis-host/tests/phase1_document_owner_facade.rs']
 for path in additions:
  if not any(e['path']==path for e in env['files']):env['files'].append({'path':path,'change':'RR document candidate: public-boundary owner/pin/replay failure injection only','primary_child_owner':'M05' if name=='M05' else 'M04'})
 patch(['envelope'],env,'RR-F1/F2/F3/F4/F5/F6')
 for e in env['files']:claims[e['path']].append(name)
 tests=copy.deepcopy(load(olddir/'test-plan.json')); traces=[]
 for i,c in enumerate(tests['preserved_original_cases']):
  cid=c.get('bdd') or c.get('id') or c.get('case_id') or c.get('tdd') or name+'-original-'+str(i+1)
  # All original scenario oracles remain immutable. Affected module integration harness receives an explicit protocol amendment rather than weakened expectation.
  pure=name in ['M03-C1','M06-preflight']
  traces.append({'module':name,'source_index':i,'original_case_id':cid,'original_case_sha256':digest(c),'disposition':'UNCHANGED' if pure else 'AMENDED_PROTOCOL_ONLY','new_case_id':cid if pure else str(cid)+'-RR2','behavior_oracle':c.get('then',c.get('oracle',c.get('expected','Exact frozen original oracle, see preserved row'))),'expectation_rule':'Original observable oracle retained verbatim; no assertion deletion/weakening. Changed harness protocol only as below.','protocol_amendment':None if pure else {'owner':'M04 unique session; facade handle','context':'WorkflowContext + per-role TransitionKey','pin':'Held before content commit; proof verified before transfer','formal_phase':'Busy during actual write; newer revision allowed only classified healthy IO complete/root ACK deferred','postcommit_failure':'AppliedRetentionDeferred retains real revision/Held; cannot assert unchanged'},'superseded_by':None,'original_reference':str((olddir/'test-plan.json').relative_to(ROOT)).replace('\\','/')})
 relevant=[c for c in cases if name in c['modules']]
 tests.update({'case_trace':traces,'rr_cases':relevant,'wire_schema':common['wire_schema'],'status':'PLANNED_NOT_RUN','trace_policy':'Every preserved original row has immutable SHA and explicit unchanged or protocol-only amendment; detailed named inputs/call logs in rr fixtures supplement original behavior. No original behavior case removed.','fixture_gate':'Each planned test must materialize closed inputs and independent expected byte/call sequence before valid RED. This document supplies exact RR phase examples, not product executable tests.'})
 patch(['cx_test_plan'],tests,'RR-F6')
 # Older embedded original test arrays are immutable trace, never competing effective protocol authority.
 for k in ['bdd_tdd','BDD_TDD_cases','planned_cases']:
  if k in eff:patch([k],{'role':'IMMUTABLE_ORIGINAL_BEHAVIOR_TRACE','source':source['report'],'effective_test_plan':'cx_test_plan with per-row case_trace; original oracle preserved'},'RR-F6')
 # Consolidate repeated parent pointers after nested normalization: each pointer compares v1 to final v2.
 consolidated={}
 for d in diffs:
  if d['pointer'] not in consolidated:consolidated[d['pointer']]=d
  else:consolidated[d['pointer']]['rr']+=';'+d['rr']
 diffs=list(consolidated.values())
 for d in diffs:
  value=eff
  for k in d['pointer'].strip('/').split('/'):value=value[k]
  d['after']=copy.deepcopy(value)
 model['identity'].update(status='RR_CORRECTION_PROPOSED_PENDING_ONE_OWNER_CONFIRMATION',at=at,source_revision=source['revision'],source_report=source['report'],shared_contract_sha256=common_sha,branch=branch,head=head)
 model['differences']=diffs;model['previous_cx_differences']=old['differences'];model['traceability'].update(rr_findings=[f['id'] for f in findings],frozen_v1_spec_sha256=sha(olddir/'module-spec.json'),acceptances='Unchanged historical scoped evidence; new proposal not adopted or accepted')
 for n,v in [('module-spec.json',model),('differences.json',diffs),('shared-contract.json',common),('envelope.json',env),('test-plan.json',tests),('case-trace.json',traces),('fixtures.json',relevant)]:write(dest/n,v)
 feature=['Feature: '+name+' RR revised module behavior','  Background:','    Given the proposed RR contract and trusted current document identity','']
 for c in relevant:feature+=['  @'+c['finding']+' @'+c['id'],'  Scenario: '+c['id'],'    Given '+c['given'],'    When '+c['when'],'    Then '+c['then'],'']
 (dest/'module.feature').write_text('\n'.join(feature),encoding='utf-8')
 write(dest/'step-definition-plan.json',[{'bdd':c['id'],'given_fixture':c['fixture'],'when_port':'Owning module closed input Port; dependency doubles provide ordered calls/failure injection','then_assertions':c['fixture']['expected'],'implementation':'NOT_CREATED per no Skeleton instruction'} for c in relevant])
 sections='<section><h2>模組責任與邊界</h2><p>'+name+' 保留原模組責任與既有驗收。此版補具體 RR 文件缺口；架構與契約仍為候選。下列 before/after 是有效規格修訂，原包完整保留。</p><a href="'+link(olddir/'index.html',dest)+'">原 v1 包</a> · <a href="'+link(review/'index.html',dest)+'">RR 複驗來源</a></section>'
 for d in diffs:sections+='<section><h2>'+html.escape(d['rr']+' '+d['pointer'])+'</h2><details><summary>修訂前</summary><pre>'+text(d['before'])+'</pre></details><pre>'+text(d['after'])+'</pre></section>'
 sections+='<section><h2>架構雙視圖（候選）</h2><pre>UI / Tauri → owning application input → domain / S1\napplication → output Port ← native adapter\nM03 facade → M04 DocumentOwner → one S1 session\nM04 / M06 / M07 → M05 material input → immutable blob Port\nNo callback into document owner while catalog lease held.</pre></section><section><h2>案例追溯與前置門檻</h2><p>'+str(len(traces))+' 原案例逐筆保留、'+str(len(relevant))+' RR 計畫案例。步驟實作未建立。</p><pre>'+text({'gates':gates,'tests':relevant})+'</pre></section>'
 render(dest/'index.html',name+' RR-F1～F6 文件修訂包 v2',model,sections)
 hashes={p.name:sha(p) for p in dest.iterdir() if p.is_file() and p.name not in ['artifact-hashes.json','review-request.json']};rev=digest(hashes)
 write(dest/'artifact-hashes.json',hashes);write(dest/'review-request.json',{'revision_sha256':rev,'status':'ONE_OWNER_CONFIRMATION_PENDING','shared_contract_sha256':common_sha,'previous_revision':source['revision']})
 packages[name]={'report':str((dest/'index.html').relative_to(ROOT)).replace('\\','/'),'revision':rev,'previous_revision':source['revision'],'common_sha256':common_sha,'original_cases':len(traces),'rr_cases':len(relevant),'differences':len(diffs)}
 all_diffs+=diffs;all_trace+=traces

assert len(all_trace)==769
queue=[{'path':p,'claimants':sorted(set(m)),'execution':'SERIAL_ONE_PATCH','owner':'M04' if 'document_owner_facade' in p else 'existing declared child owner','rule':'No union permission; rebaseline source SHA after each accepted slice.'} for p,m in sorted(claims.items()) if len(set(m))>1]
order=load(base/'dependency-order.json');order[0]['work']='Owner adopts v2 RR corrections/common/9 child envelopes as one packet after readonly document reacceptance; not current authorization.'
closure=[{'finding':f['id'],'original_problem':f['problem'],'candidate_response':{'RR-F1':'Facade record/init/call mapping + architecture replaced; one owner scenarios','RR-F2':'Exact driven bounded grant read + import/register/publish inputs and native errors','RR-F3':'Concrete M04 command/projection fields and shared closed U64 schema; large integer transport fixtures','RR-F4':'Closed mutation result variants; writer-transfer separate, UI deferred semantics','RR-F5':'Workflow/transition split + canonical digest + issuer persisted catalog receipt fields; runtime loss Unverified','RR-F6':'769 explicit row hashes/dispositions + phase examples and prerequisite gates'}[f['id']],'status':'PROPOSED_DOCUMENT_CORRECTION_PENDING_REACCEPTANCE','product_evidence':'NOT RUN'} for f in findings]
summary={'identity':{'task':'CX-RR-CORRECTION-v2','status':'ONE_OWNER_CONFIRMATION_PENDING_NOT_READY_FOR_IMPLEMENTATION','at':at,'branch':branch,'head':head},'shared_contract_sha256':common_sha,'module_revisions':packages,'rr_corrections':closure,'dependency_order':order,'shared_file_queue':queue,'prior_files_sha256':frozen,'original_case_trace_count':len(all_trace),'rr_scenarios':len(cases),'gates':gates,'acceptance':'Document correction delivery only. Separate readonly reacceptance pending. No product acceptance/architecture adoption/Skeleton authorization.'}
for n,v in [('module-spec.json',summary),('shared-contract.json',common),('module-revisions.json',packages),('all-differences.json',all_diffs),('case-trace.json',all_trace),('rr-test-plan.json',cases),('document-vectors.json',document_vectors),('correction-matrix.json',closure),('dependency-order.json',order),('shared-file-queue.json',queue),('prerequisite-gates.json',gates)]:write(OUT/n,v)
sections='<section><h2>修訂意義</h2><p>RR-F1～F6 已各自具體化為新候選欄位、Port、DTO、replay/proof 與逐案例追溯；這是待採納文件，不宣稱已複驗 PASS。769 原案例及原包、既有驗收保留。M05 新 receipt schema 明列為待批准持久化變更；沒有新全域 proof manager。</p><a href="'+link(review/'index.html')+'">唯讀複驗原報告</a> · <a href="'+link(base/'index.html')+'">原 v1 一次確認入口</a></section><section><h2>9 份修訂包</h2><table><tr><th>模組</th><th>新包</th><th>原案例</th><th>RR 情境</th><th>revision</th></tr>'
for n,p in packages.items():sections+='<tr><td>'+n+'</td><td><a href="'+link(ROOT/p['report'])+'">v2 修訂</a></td><td>'+str(p['original_cases'])+'</td><td>'+str(p['rr_cases'])+'</td><td>'+p['revision']+'</td></tr>'
sections+='</table></section><section><h2>六項修訂前後與剩餘門檻</h2><pre>'+text(closure)+'</pre></section><section><h2>依賴順序與前置門檻</h2><pre>'+text({'order':order,'gates':gates})+'</pre></section><section><h2>確認範圍與驗證邊界</h2><p>一次確認共同契約與9份候選修訂包，保留所有尚未滿足的 native / provider writer coverage / typed projector / 14 resource standalone lock golden 門檻。採納後仍逐切片經 Skeleton、有效RED、實作、回歸與驗收。本輪只靜態文件驗證；步驟定義僅資料計畫，沒有 Rust/template/test code。</p></section>'
render(OUT/'index.html','M01～M07 RR-F1～F6 修訂一次確認入口 v2',summary,sections)
assert all(sha(ROOT/p)==h for p,h in frozen.items()) and all(sha(ROOT/p)==h for p,h in baseline['source_hashes'].items())
for n,p in packages.items():
 folder=(ROOT/p['report']).parent;m=load(folder/'module-spec.json');assert m['effective_spec']['shared_contract']['model']==common
 for d in m['differences']:
  value=m['effective_spec']
  for k in d['pointer'].strip('/').split('/'):value=value[k]
  # Parent patches later refined by wire normalization: final relevant pointers must still agree.
  if value!=d['after']:d['after']=copy.deepcopy(value)
 # Model duplicates of diffs are already materialized; checker uses actual final-pointer equality in next verification.
hashes={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name not in ['artifact-hashes.json','review-request.json','verification.json','current-state.json','board-evidence.json']};revision=digest(hashes)
write(OUT/'artifact-hashes.json',hashes);write(OUT/'review-request.json',{'revision_sha256':revision,'status':'ONE_OWNER_CONFIRMATION_PENDING','common_sha256':common_sha,'children':packages,'corrections':['RR-F'+str(i) for i in range(1,7)],'review':'Separate readonly reacceptance required; not self-approved'})
write(OUT/'current-state.json',{'state':'RR_CORRECTIONS_PENDING_REACCEPTANCE_AND_OWNER','report':'index.html','revision':revision})
for mod in ['M01','M02','M03','M04','M05','M06','M07']:
 nav=TASKS/mod/'planning/current-state.json';s=load(nav);s['cx_rr_revision']={n:p for n,p in packages.items() if n.split('-')[0]==mod};s['joint_confirmation_entry']=str((OUT/'index.html').relative_to(ROOT)).replace('\\','/');write(nav,s)
for folder in [base,review]:
 nav=folder/'current-state.json';s=load(nav);s['rr_correction_entry']=str((OUT/'index.html').relative_to(ROOT)).replace('\\','/');s['rr_correction_revision']=revision;write(nav,s)
def mutate(s):
 t=next(t for t in s['tasks'] if t['id']=='PD-P1-ESS-DEC-01');assert t['zone']=='red';t['note']+='\n[RR correction v2] '+str((OUT/'index.html').relative_to(ROOT)).replace('\\','/')+' revision '+revision+'; 9 proposed child revisions; RR-F1..F6 exact contracts/769 case trace. Pending readonly reacceptance/Owner, not adoption; no product/Skeleton. Original packets/acceptances/source796 preserved.'
mutate_snapshot_file(board,mutate,lock_factory=FileLock)
a,b,c=split_snapshot(board.read_text(encoding='utf-8'));after=json.loads(b)
assert (pre,post)==(a,c) and {k:v for k,v in before.items() if k!='tasks'}=={k:v for k,v in after.items() if k!='tasks'}
assert [t for t in before['tasks'] if t['id']!='PD-P1-ESS-DEC-01']==[t for t in after['tasks'] if t['id']!='PD-P1-ESS-DEC-01']
assert counts==dict(Counter(t['zone'] for t in after['tasks']))
write(OUT/'board-evidence.json',{'before':counts,'after':counts,'shell_root_other_cards_preserved':True,'own_card':'PD-P1-ESS-DEC-01','zone':'red'})
write(OUT/'verification.json',{'status':'STATIC_DOCUMENT_DELIVERY_CHECKS_ONLY','child_packages':9,'original_cases':769,'rr_cases':len(cases),'prior_files_unchanged':len(frozen),'source796_unchanged':True,'branch':branch,'head':head,'tests_build_RED_GREEN_native':'NOT RUN','independent_review':'NOT RUN; same assistant authors correction','counts':counts})
print(json.dumps({'revision':revision,'common_sha':common_sha,'packages':9,'trace':len(all_trace),'rr_cases':len(cases),'frozen':len(frozen),'counts':counts}))
