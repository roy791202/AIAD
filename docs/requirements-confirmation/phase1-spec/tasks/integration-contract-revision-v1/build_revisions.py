"""Materialize pending CX revisions as documents. Never generates product code."""
import json,copy,hashlib,html,re,subprocess,sys
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
OUT=Path(__file__).parent;TASKS=OUT.parent;ROOT=OUT.parents[4]
sys.path.insert(0,str(ROOT))
from tools.board.board_core.snapshot_safe import split_snapshot,mutate_snapshot_file
from tools.board.board_core.json_store import FileLock
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write_at(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write(n,v):write_at(OUT/n,v)
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
baseline=load(TASKS/'M01/planning/s2-green/source-current.json');head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
assert (branch,head)==(baseline['branch'],baseline['head']) and len(baseline['source_hashes'])==796 and all(sha(ROOT/p)==h for p,h in baseline['source_hashes'].items())
review=load(TASKS/'integration-contract-review/module-spec.json');originals=dict(review['original_hashes'])
for p in (TASKS/'integration-contract-review').glob('*'):
 if p.is_file() and p.name!='current-state.json':originals[str(p.relative_to(ROOT)).replace('\\','/')]=sha(p)
board=ROOT/'docs/PROJECT-BOARD.html';pre,inner,post=split_snapshot(board.read_text(encoding='utf-8'));before=json.loads(inner);counts=dict(Counter(t['zone'] for t in before['tasks']))
at=datetime.now(timezone.utc).isoformat()
common=copy.deepcopy(review['joint_contract_overlay'])
common.update({'contract_id':'CX-COMMON-v1','status':'PROPOSED_PENDING_ONE_OWNER_CONFIRMATION','precedence':'This common model and materialized module effective_spec replace only listed fields. Original packages are immutable historical baseline; accepted S1/IO behavior remains unchanged. No Owner adoption inferred from request to prepare revisions.',
 'wire_types':{'U64Decimal':'JSON STRING regex^(0|[1-9][0-9]*)$, checked0..18446744073709551615; no plus/leading-zero/exponent/space. Rust u64 internal. JS keeps string/BigInt; never Number roundtrip.','Digest':'{domain,profile?,lowerhex64}; sha256: prefix only existing M01/M02 S1 boundaries. No arbitrary cross-domain conversion.','OpaqueId':'ASCII[A-Za-z0-9_-]{1,128}; native/generated fixed-format IDs retain module constraint; actual context server-derived.','Context':'project_uuid/document_uuid/session_id/owner_generation/captured_revision/operation_id; UI strings decoded to existing typed IDs/u64; not label authority.'},
 'pin_enums':{'state':['Held','Transferred','Released'],'purpose':['Candidate','Save','Undo','Redo','Recovery','Import','Export']},
 'material_api':{'resolve':'resolve(context,ordered_requests)->ResolutionSnapshot','pin':'pin(context,snapshot,purpose,operation_id)->PinReceipt','validate_pin':'validate_pin(context,pin_receipt)->VerifiedPin','read_pinned_version':'read_pinned_version(context,VerifiedPin,asset_id,digest,max_bytes)->VerifiedBytes','import_verified_versions':'import_verified_versions(context,VerifiedBundle,purpose,operation_id)->ImportedPinnedManifest','transfer':'transfer(context,pin_id,RootManifest,AuthenticatedExternalProof,operation_id)->TransferReceipt','release':'release(context,pin_id,RootBundle,operation_id)->ReleasedReceipt|RetainedReasons'},
 'proof_types':{'ResolutionSnapshot':'{Context,catalog_generation,catalog_raw_digest,snapshot_digest,completeness:Complete,assets,bindings}; no root_proof_id; complete resolution is neither pin nor root completeness.','VerifiedBundle':'{context,source_digest,entries:[asset_id,digest,size_bytes,verified_bytes_or_handle],legacy_alias_mapping}; all raw bytes/hash/closure validated by trusted issuer.','AuthenticatedExternalProof':'Opaque issuer_receipt_id resolves server record {issuer,operation_kind,Context,target_identity,receipt/raw/projection evidence}; durable proof must be revalidated after restart; UI DTO never carries trusted receipt content.','TransferReceipt':'{issuer:M05,catalog_generation,catalog_raw_digest,pin_id,root_manifest_ids,external_proof_id,Context,receipt_id}; original Held transitions only after verified durable catalog commit.','MutationReceipt':'{Context,before_revision,after_revision,content_semantic,pin_id?,result:Applied|NoChange|AppliedRetentionDeferred}; after commit cannot be ErrorUnchanged.','VerifiedBytes':'{digest,size_bytes,immutable_bytes_or_guarded_handle,store_identity}; issued only native/hash validator, not URI/path trust.'},
 'quarantine_copy':{'marker':'.sgenaxis/copy-state.v1.json; {schema:SGA-PROJECT-COPY-v1,project_uuid,operation_id,state:Quarantined|Ready,definition_raw_digest?,document_raw_digest?,catalog_raw_digest?,manifest_digest?}. Strict duplicate/unknown/type/project validation; quarantine written durably before any public project manifest/definition/document/catalog.','sequence':'Exclusive create FINAL target directory (never rename it after any FileCommit operation) → create Quarantined marker via checked IO → initialize validated children/catalog/pins at FINAL paths → verify full copy proofs → CAS Ready marker with exact digests → authenticate M01 open/bind. Source approvals provenance only; new project+doc identities.','reader_gate':'All official M01 open/adopt/select and startup recovery check copy marker before S2 bind; Quarantined/invalid/uncertain journal refuses project readiness. Marker absent allows existing legacy policy only if no partial-copy evidence; empty/unmarked exclusive-copy crash residue is not adopted automatically. Existing accepted S2 public API unchanged; new application wrapper gate is proposed.','failure':'Before Ready no selectable completed project; retains quarantined diagnostic+pins. After Ready delivery loss returns ProjectCopyDeliveryDeferred; no rollback/delete. Never rewrite/move private journal to fix path binding.'},
 'source_reservation':{'application_trait':'SourceReadReservation: snapshot_id()->SourceSnapshotId; validate_held()->Result<SourceSnapshotId,SourceFenceError>; explicit release(self). Owns authenticated snapshot identity+held producer read capability; cannot be constructed from DTO. Drop releases handles only.','SourceSnapshotId':'{issuer:Definition|Design|Approval,project_uuid,owner_generation,revision_or_epoch,typed_digest}; exact equality, not timestamp.','native_trait':'CommittedReadPort.acquire_read(trusted_target_capability)->CommittedReadLease; lease.read_verified(max_bytes)->VerifiedCommittedBytes; lease owns OS shared lock compatible with existing FileCommit exclusive writer, normalized target+readonly journal validation. No create/repair/cleanup. Missing sidecar =>Unavailable.','producer_rules':'Definition/design owner read reservation blocks their mutation and exclusive file writer until generation terminal result; acquire definition→approval HOST epoch→design before active writer. Immutable SPEC Approved revisions remain pure; HOST epoch covers evidence validity changes, not a SPEC filesystem dependency. All producer mutation routes must honor reservation; incomplete coverage =>DependencyNotReady.','io_guard':'IO-owned crate-private CommittedReadGuard unforgeable outside adapter constructor. inspect_committed_locked(&CommittedReadGuard)->Result<CommittedReadInspection,CommitError>; validates guard-bound canonical target/terminal journal/current raw digest, no path argument replacement. Public FileCommitPort unchanged.','scope':'New committed_read.rs ports/adapter/native tests plus generation_sources.rs application provider adapters. Only proposed exact child files below; accepted IO implementation not re-approved automatically.'},
 'recovery_readiness':{'LocalIntegrityReady':'Native coherent recovery index+payload+ALL material copies and hashes/schema verified; independent from original catalog availability.','PublicationAcknowledged':'Original M05 root transfer receipt and original captured S1 Published/ACK verified.','restore':'LocalIntegrityReady permits explicit restore to authorized destination even SourceRetentionDeferred. Destination import+durable pin+M04 new-unsaved install mandatory; original Held/Unknown retained and no fake original Published/ACK. Missing/corrupt local blob always blocks.'},
 'reservation_kinds':{'FormalWriteReservation':'blocks same-owner content edits until matching IO completion; read diagnostics allowed.','RecoveryAttemptReservation':'one recovery attempt; after immutable capture+pin, live healthy owner may edit. Never reuse formal saving state for whole recovery copy pipeline.','CatalogLease':'short transition only, no callbacks into document owner while held.'},
 'readiness_gates':['No adoption or architecture PASS from document revision','M02 template14resources+standalone full transitive lock golden required before renderer Skeleton acceptance','ESS typed entity/parent/edge/binding projector with exact fixtures required before affected clear/merge/install','native Windows11 alias/8.3/reparse/durability separately measured; environment NOT RUN remains','No physical GC/repair/time-based pin release/no blanket union envelope']})
common_sha=digest(common);write('shared-contract.json',common)
delta_files=[
 ('apps/sgenaxis-desktop/crates/sgenaxis-ports/src/committed_read.rs','IO','opaque trusted-target read lease trait/types; no public FileCommit changes'),
 ('apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/committed_read.rs','IO','OS shared guard constructor and readonly inspector bridge'),
 ('apps/sgenaxis-desktop/crates/sgenaxis-adapters/tests/phase1_committed_read.rs','IO','reader/writer/terminal journal/native alias matrix'),
 ('apps/sgenaxis-desktop/crates/sgenaxis-ports/src/generation_sources.rs','M02','source snapshot reservation data/trait only'),
 ('apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/generation_sources.rs','M02','native definition source reservation using committed read; no business approval'),
 ('apps/sgenaxis-desktop/crates/sgenaxis-adapters/tests/phase1_generation_sources.rs','M02','source writer coverage/lock ordering native cases')]
targets={'M01-S3':'M01/planning/cx-revision-v1','M02':'M02/planning/cx-revision-v1','M03-C1':'M03/planning/cx-c1-revision-v1','M03-H2':'M03/planning/cx-h2-revision-v1','M04':'M04/planning/cx-revision-v1','M05':'M05/planning/cx-revision-v1','M06-preflight':'M06/planning/cx-preflight-revision-v1','M06':'M06/planning/cx-exchange-revision-v1','M07':'M07/planning/cx-revision-v1'}
applicability={'M01-S3':[3,9,11,15,16,17],'M02':[2,3,11,12,15,16,17],'M03-C1':[2,3,7,14,16,17],'M03-H2':[1,2,3,7,8,15,16,17],'M04':[1,2,3,4,6,7,8,9,11,13,14,15,16,17],'M05':[3,4,5,6,7,8,9,10,15,16,17],'M06-preflight':[3,7,14,15,16,17],'M06':[3,5,6,8,9,14,15,16,17],'M07':[2,3,6,7,8,9,10,13,15,16,17]}
vectors=[]
for text,ok in [('0',True),('1',True),('9007199254740993',True),('18446744073709551615',True),('18446744073709551616',False),('01',False),('+1',False),('1e0',False),('-1',False),(' 1',False),('',False)]:
 actual=bool(re.fullmatch(r'0|[1-9][0-9]*',text)) and int(text)<=18446744073709551615
 assert actual==ok;vectors.append({'input':text,'valid_wire_u64':ok,'expected':'parse exact integer internally' if ok else 'InvalidInput decimal_string'})
write('wire-fixtures.json',vectors)
shared_cases=[]
phase_oracles={
 1:['same DocumentOwner session/revision observed by facade','OwnerMismatch; zero content commits','old generation completion rejected; original receipt retained'],
 2:['same typed design profile/digest at all design consumers','ProfileMismatch; zero ACK','old-profile baseline not relabeled'],
 3:['18446744073709551615 preserved as exact decimal string','InvalidInput for 18446744073709551616 or JSON number','late DTO cannot overwrite newer exact revision'],
 4:['calls file_commit→transfer→ack exactly once','CommittedAckDeferred RetentionTransfer; fileCalls1 ackCalls0 Held retained','same proof replay fileCalls still1; no duplicate ACK'],
 5:['Export Held→Transferred with verified root proof','Released pin cannot grant bytes/mutation','duplicate Released transition returns same receipt; blobDeleteCalls0'],
 6:['exact context/asset set resolves then durable pin issued','extra/missing response reference rejected; commitCalls0','stale catalog snapshot requires explicit re-resolve; no silent mapping'],
 7:['Complete material pin permits install despite Unknown RecoverySnapshots roots','missing asset blocks install; Unknown roots blocks release','late root observation from old epoch rejected'],
 8:['one S1 commit yields Applied and one history entry','postcommit root failure yields AppliedRetentionDeferred at actual R8','replay same mutation keeps revisionR8/history count1'],
 9:['children/catalog written at FINAL canonical paths then Ready receipt','Quarantined copy denied by every official open path','restart never relocates/rewrites journal; marker uncertain stays blocked'],
 10:['LocalIntegrityReady restore allowed with destination pin','missing local asset blocks restore even if source proof claims success','source root transfer pending remains Unknown/Held; no original Published ACK'],
 11:['held source reservations precede active lease; release after receipt','producer write Busy while held; incomplete writer coverage unavailable','cancel after CAS start awaits actual result; old source not relabeled'],
 12:['shared guard protects terminal journal/read snapshot','forged guard/nonterminal/mismatch rejected; journalWriteCalls0','writer cannot expose transient active to reader'],
 13:['live edit permitted after stable recovery capture+pin','formal WriteInFlight rejects same-owner edit Busy','old recovery ACK leaves newer revision pending; formal baseline untouched'],
 14:['complete typed mapping updates all declared references once','unknown reference-bearing field hard-blocks; commitCalls0','stale preview mapping cannot apply to new target revision'],
 15:['issuer registry proof tag+context matches expected action','UI fabricated receipt/other proof tag denied; ackCalls0','restart missing issuer proof is Unverified, never fabricated completion'],
 16:['one serial patch owns shared path; candidate claims exact','outside adopted child envelope denied','new shared HEAD/SHA rebaselined before next accepted slice'],
 17:['golden/projector/native gate status shown accurately','missing fixture/provider is not valid RED or readiness','document regeneration never promotes product/parent card to green']}
for x in review['findings']:
 for vi,variant in enumerate(['normal','stale_or_failure','late_or_replay']):
  shared_cases.append({'id':'BDD-'+x['id']+'-'+variant,'tdd':'TDD-'+x['id']+'-'+variant,'cx':x['id'],'category':variant,'given':'Exact current/stale context and issuer-owned proof fixture for '+','.join(x['modules']),'when':'invoke corrected module input boundary with '+variant,'then':phase_oracles[int(x['id'][-2:])][vi],'contract':x['proposed_exact_amendment'],'oracle':{'context':{'project_uuid':'11111111-1111-4111-8111-111111111111','document_uuid':'22222222-2222-4222-8222-222222222222','session_id':'session_1','owner_generation':'3','captured_revision':'7','operation_id':'operation_1'},'digests':{'design_semantic':'a'*64,'file_raw':'b'*64,'catalog_raw':'c'*64,'recovery_fp':'d'*64},'result':phase_oracles[int(x['id'][-2:])][vi]},'status':'PLANNED_NOT_RUN','valid_red':'Accepted exact child Skeleton compiles, independent fixture oracle passes; missing setup/provider/native environment not RED.'})
write('integration-test-plan.json',shared_cases)
packages={};all_diffs=[];claim_map=defaultdict(list)
for name,source in review['packages'].items():
 folder=ROOT/Path(source['report']).parent;old=load(folder/'module-spec.json');effective=copy.deepcopy(old);diffs=[]
 def patch(keys,value,cx):
  cursor=effective
  for key in keys[:-1]:
   if key not in cursor or not isinstance(cursor[key],dict):cursor[key]={}
   cursor=cursor[key]
  before_value=copy.deepcopy(cursor.get(keys[-1],{'absent':True}));cursor[keys[-1]]=copy.deepcopy(value)
  diffs.append({'module':name,'cx':cx,'pointer':'/'+ '/'.join(keys),'before':before_value,'after':copy.deepcopy(value),'status':'MATERIALIZED_PROPOSAL_NOT_ADOPTED'})
 # Remove duplicate old-package history from effective view; source revision remains immutable.
 for historical in ['frozen_inputs','previous_exact_contract_embedded','preflight_frozen_contract_embedded','frozen_sources','source_hashes','verification','results','joint_amendments']:
  if historical in effective:effective.pop(historical)
 patch(['status'],'CX_REVISION_PENDING_ONE_OWNER_CONFIRMATION','CX-16')
 patch(['shared_contract'],{'id':'CX-COMMON-v1','sha256':common_sha,'model':common},'CX-01..CX-17')
 patch(['wire_contract'],common['wire_types'],'CX-03')
 patch(['cross_owner_proofs'],common['proof_types'],'CX-15')
 patch(['module_readiness'],'NOT_READY_FOR_IMPLEMENTATION; explicit golden/projector/native/provider gates remain; no Skeleton/product changes.','CX-17')
 if name=='M01-S3':
  patch(['copy_publication'],common['quarantine_copy'],'CX-09')
  patch(['generation_source_reservation'],common['source_reservation'],'CX-11')
  patch(['architecture','state_owner'],'Existing DispatchHost wizard owner retains project/definition authority; copy is child use case with final-path quarantine/Ready reader gate. No second owner, accepted S2 unchanged.','CX-09')
  patch(['contract_supplements'],{'reader_gate':'all official create/open/adopt/select honor copy-state before S2 binding; final path stable','proof':'ProjectCopyReady issuer-owned receipt required before selection/settings; deferred delivery never rollback'},'CX-09/CX-15')
 if name=='M02':
  patch(['source_contracts','stale_window'],common['source_reservation'],'CX-11')
  patch(['source_contracts','design_port'],'Capture saved M04 content/profile plus authenticated formal FileCommit +M05 root TransferReceipt +ACK provenance; dirty/deferred proof returns DesignSaveRequired, never save implicitly. Definition/approval/design source reservations held before active writer through receipt.','CX-04/CX-11')
  patch(['store_contract','private_IO_seam'],common['source_reservation']['io_guard'],'CX-12')
  patch(['store_contract','reader_consistency'],{'port':'CommittedReadPort shared lock +readonly journal terminal/hash verification','lifetime':'hold lease until active/manifest/allfiles copied and verified; no nested writer','failure':'Busy keeps prior verified snapshot tagged stale; no current proof'},'CX-12')
  patch(['source_contracts','prefix_boundary'],common['digest_domains'],'CX-02')
 if name=='M03-C1':
  patch(['semantic_interface'],{'profile':'SGA-DESIGN-SEM-v1','numeric':'exact coefficient/exponent tagged semantic projection after adopted C1 input guard','preserve':'C1 optional fields0/false/[]/absence and original resource overlay unchanged','projection_owner':'pure HOST document projector may reuse C1 guarded data; no dependency on runtime Viewer owner'},'CX-02/CX-07')
 if name=='M03-H2':
  owner=copy.deepcopy(effective['owner_binding']);owner['owner']='M04 document_owner.rs owns exactly one S1 DocumentSession per project/document; design_owner.rs facade only, no initializer/registry duplication.';owner['semantic_profile']='SGA-DESIGN-SEM-v1 exact common profile; payload preserves compatibility values; semantic omits exact approved paths only; no baseline relabeling.';owner['mutation']='Validate candidate→M05 Candidate pin→M04 one S1 Edit→complete live/history root transfer. Return MutationReceipt; AppliedRetentionDeferred reports real revision/Held, never ErrorUnchanged. Viewer selection/mock remains ephemeral.'
  patch(['owner_binding'],owner,'CX-01/CX-02/CX-08')
  patch(['architecture','ownership'],'M04 DocumentOwner authority; M03 facade/ephemeral projections; existing S1 unchanged.','CX-01')
  patch(['lifecycle','writer_transfer'],'Common owner transfer increments shared generation and invalidates all module plans bound to old generation; content/history/revision unchanged, pins/proofs retained.','CX-01')
 if name=='M04':
  patch(['architecture','ownership','M03'],'Facade only, M04 single DocumentOwner registry/session. All imported candidates/clear/merge/undo use common MutationReceipt.','CX-01/CX-08')
  patch(['output_serialization','semantic_design'],'SGA-DESIGN-SEM-v1 per common contract; never old untagged/mismatched profile; M07 ACK original semantic not recovery raw fingerprint.','CX-02')
  patch(['material_binding','interface'],common['material_api'],'CX-06')
  patch(['material_binding','response'],common['proof_types']['ResolutionSnapshot'],'CX-06')
  patch(['material_binding','freshness'],'ResolutionSnapshot generation/raw digest checked atomically by M05 pin under catalog lease; validate_pin before document commit, exact Context+versions. No validate(snapshot) root-proof shortcut. Missing root providers retain pins independently.','CX-06/CX-07')
  patch(['save_health_reopen','receipt'],'Capture→Save pin→verified file receipt→M05 formal-root TransferReceipt→ACK captured revision+semantic. Transfer failed after commit: CommittedAckDeferred stage RetentionTransfer, keep Held+file proof; no retry rewrite or snapshot ACK.','CX-04')
  patch(['save_health_reopen','reserve'],common['reservation_kinds'],'CX-13')
  patch(['clear_policy','confirm'],'Revalidate owner/generation/TTL/revision/semantic/proof; Candidate pin before one Clear commit; live/Undo/Redo transfer after. AppliedRetentionDeferred if transfer failed, actual revision retained; NoChange noUndo.','CX-08')
  patch(['typed_projector_gate'],'Lossless inspect is not trusted mutation. Pure HOST complete format-specific entity/parent/edge/binding/reference inventory required; exact fixtures before affected clear/merge Skeleton. Unknown fields block affected mutation, no heuristic ID rewrites.','CX-07/CX-14')
  patch(['source_read_reservation'],common['source_reservation'],'CX-11')
 if name=='M05':
  patch(['schema','pin_record','state'],'Held|Transferred|Released; Held only temporary authority; terminal transition receipt immutable.','CX-05')
  patch(['schema','pin_record','purpose'],'Candidate|Save|Undo|Redo|Recovery|Import|Export','CX-05')
  patch(['ports','application_inputs'],common['material_api'],'CX-06')
  patch(['ports','ResolutionSnapshot'],common['proof_types']['ResolutionSnapshot'],'CX-06')
  patch(['ports','resolution_independence'],'Complete asset/binding inventory resolution independent from all-five-root completeness. Pure HOST projector supplies identities; no call into M03 runtime. Missing M07/root provider remains Unknown, retains pins but does not prevent pinned valid installs.','CX-07')
  patch(['binding_save_integration','joint_amendments'],['Effective common MutationReceipt and formal transfer-before-ACK now materialized in this proposal; original package history preserved.'],'CX-04/CX-08')
  patch(['transactions','formal_save'],'Verified file receipt→authenticated FormalFile proof→M05 root transfer durable→M04 captured semantic ACK; failure CommittedAckDeferred with Held and exact proof.','CX-04')
  patch(['transactions','project_copy'],'Catalog/pins initialized at FINAL QuarantinedCopy path; never move journal-bearing directory. Ready marker after all native/catalog/definition/doc proofs; source namespace may not be adopted as destination.','CX-09')
  patch(['transactions','proof_authority'],common['proof_types'],'CX-15')
 if name=='M06-preflight':
  patch(['runtime_handoff'],'Original R1-R4/64oracles and exact failure precedence unchanged. Decoder creates report from immutable actual bytes; Allowed still not pin/commit authority. Context wire decimal strings only at UI transport.','CX-03/CX-15')
 if name=='M06':
  patch(['ports','ProjectCopyStoragePort'],'begin_project_copy(final trusted selection,new identity)->QuarantinedProjectCopy; initialize at stable final paths; publish_ready_checked(allproofs)->ProjectCopyReadyReceipt. NO directory rename after any FileCommit catalog/document operation. Official open gates copy-state+committed read proof.','CX-09')
  patch(['lifecycle','new_project_copy'],common['quarantine_copy'],'CX-09')
  patch(['ports','M05_port'],common['material_api'],'CX-05/CX-06')
  patch(['merge_undo','postcommit'],'Complete roots transfer after one M04 Merge commit; return common AppliedRetentionDeferred if needed, never unchanged failure. Same for Undo; source bytes/formal/recovery baselines unchanged.','CX-08')
  patch(['merge_undo','projector_readiness'],'PROJECTOR_FIXTURES_REQUIRED: exact typed field/ref mapping for allowed ESS/design constructs before merge Skeleton. Uncertain IDs/unknown reference fields hard-block; explicit FreshImportedIds map preview only.','CX-14')
  patch(['ports','M01_port'],'Existing M01 wizard owner invokes HOST project_copy child at final-path QuarantinedCopy→Ready, fresh project/doc UUID/provenance. Accepted S2 untouched; no independent owner.','CX-09')
 if name=='M07':
  patch(['ports','M05_extension_export'],common['material_api']['read_pinned_version'],'CX-06')
  patch(['ports','M05_extension_restore'],common['material_api']['import_verified_versions'],'CX-06')
  patch(['transactions_lifecycle','restart'],common['recovery_readiness'],'CX-10')
  patch(['transactions_lifecycle','restore_readiness'],'LocalIntegrityReady allows explicit authorized destination restore despite SourceRetentionDeferred. Destination import+pin+new-unsaved owner install mandatory. Keep original Held/Unknown; no fake original Published/ACK.','CX-10')
  patch(['ui','states'],'List LocalIntegrityReady separate PublicationAcknowledged, SourceRetentionDeferred, integrityBlocked, processed/history. Restore enabled only verified complete local bundle+authorized destination/providers. No original path authority.','CX-10')
  patch(['capture_fingerprint','baseline_mapping'],'M07 successful fingerprint=RECOVERY-FP-v1; M04 recovery ACK=captured revision+original content semantic profile/digest after original publication proofs. Formal baseline unchanged.','CX-02')
  patch(['capture_fingerprint','reservation'],common['reservation_kinds'],'CX-13')
 # Canonical envelope: one normalized path table, avoid retaining divergent old wildcard/port scopes.
 env_source=load(folder/'envelope.json') if (folder/'envelope.json').exists() else old.get('envelope',{})
 rawfiles=env_source.get('files',env_source.get('allowed_files',[]));envfiles=[]
 if not rawfiles:
  rawfiles=sum((env_source.get(k,[]) for k in ['existing','new','test'] if isinstance(env_source.get(k,[]),list)),[])
 for e in rawfiles:
  v=copy.deepcopy(e) if isinstance(e,dict) else {'path':e,'change':'Original exact candidate restriction remains unless listed CX delta.'}
  if v.get('path','').startswith('apps/'):envfiles.append(v)
 if name=='M03-C1' and not envfiles:
  envfiles=[{'path':'apps/sgenaxis-desktop/crates/sgenaxis-host/src/uidesign_doc.rs','change':'original C1 codec only'}, {'path':'apps/sgenaxis-desktop/crates/sgenaxis-host/tests/phase1_design_roundtrip.rs','change':'original C1 exact codec regression'}]
 if name=='M06-preflight':
  assert {e['path'] for e in envfiles}=={'apps/sgenaxis-desktop/crates/sgenaxis-work/src/lib.rs','apps/sgenaxis-desktop/crates/sgenaxis-work/src/merge_plan.rs','apps/sgenaxis-desktop/crates/sgenaxis-work/tests/phase1_import_preflight.rs'}
 if name in ['M01-S3','M02','M04']:
  for path,owner,why in delta_files:
   if owner=='IO' or name=='M02':envfiles.append({'path':path,'change':why,'primary_child_owner':owner,'cx':'CX-11/CX-12'})
  envfiles.append({'path':'apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/file_commit.rs','change':'IO-owned crate-private guard-bound readonly inspector only; no public trait/journal behavior changes','primary_child_owner':'IO','cx':'CX-12'})
  for p in ['apps/sgenaxis-desktop/crates/sgenaxis-ports/src/lib.rs','apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/lib.rs']:
   envfiles.append({'path':p,'change':'Only new committed_read/generation_sources module declarations/exports for approved child; no unrelated public API refactor','primary_child_owner':'IO','cx':'CX-11/CX-12'})
 if name in ['M01-S3','M06']:
  for path in ['apps/sgenaxis-desktop/crates/sgenaxis-host/src/project_copy.rs','apps/sgenaxis-desktop/crates/sgenaxis-host/tests/phase1_project_copy.rs']:
   envfiles.append({'path':path,'change':'M01-owned final-path quarantine/Ready child and official reader gate tests; never move journal','cx':'CX-09'})
 unique={}
 for e in envfiles:
  if e['path'] in unique:unique[e['path']]['cx_restriction']=e.get('change')
  else:unique[e['path']]=e
 env={'status':'CX_REVISED_CANDIDATE_PENDING_OWNER','primary_module':name.split('-')[0],'files':list(unique.values()),'shared_rules':'Same path is one serial integration patch under explicit child owner; claiming path not blanket permission to implement another module. Rebaseline SHA before Skeleton. Existing accepted WORK/IO interfaces/tests unchanged.','protected':'All current product code during this planning task; all original packages/acceptances; accepted S1 behavior; all manifests/lockfiles except already declared old candidate narrow edge. No GC/repair/automatic release.','readiness':common['readiness_gates']}
 patch(['envelope'],env,'CX-09/CX-11/CX-12/CX-16')
 for e in env['files']:claim_map[e['path']].append(name)
 original_cases=[]
 for k in ['bdd_tdd','BDD_TDD_cases','planned_cases','original_cases','cases','additional_output','additional_resource']:
  val=old.get(k)
  if isinstance(val,dict) and isinstance(val.get('cases'),list):original_cases+=val['cases']
  elif isinstance(val,list):original_cases+=val
 if not original_cases and (folder/'test-plan.json').exists():
  x=load(folder/'test-plan.json');original_cases=x if isinstance(x,list) else x.get('cases',[])
 if name=='M06-preflight':assert len(original_cases)==64
 if name=='M03-C1':assert len(original_cases)==36
 relevant=[c for c in shared_cases if int(c['cx'][-2:]) in applicability[name]]
 tests={'status':'PLANNED_NOT_RUN','preserved_original_cases':original_cases,'preservation':'Original cases remain traced to frozen source revision. Affected expected protocol must use after-value in differences and shared contract; old conflicting contract text is superseded only as proposed, never silently approved.','cx_cases':relevant,'wire_fixtures':vectors,'coverage':'Original module B1-B12 plus normal/stale-or-failure/late-or-replay for each applicable CX. No product RED/GREEN claimed.','commands':'Original exact module future test commands retained in effective spec; new committed-read/source-fence native suites require accepted child envelope/Skeleton first.','valid_red':'Compiles and independent fixture validates intended behavior; missing golden/projector/native/provider remains readiness gap.'}
 # Replace affected authoritative behavior/test view; preserve original test rows explicitly as trace, not competing expected oracle.
 patch(['cx_test_plan'],tests,'CX-01..CX-17')
 dest=TASKS/targets[name];dest.mkdir(parents=True,exist_ok=True)
 model={'identity':{'module':name,'status':'PROPOSED_CX_REVISION_PENDING_ONE_OWNER_CONFIRMATION','at':at,'source_revision':source['revision'],'source_report':source['report'],'shared_contract_sha256':common_sha,'branch':branch,'head':head},'effective_spec':effective,'differences':diffs,'applicable_cx':['CX-'+str(i).zfill(2) for i in applicability[name]],'traceability':{'original_file_sha256':sha(folder/'module-spec.json'),'acceptances':'All previous scoped acceptances retained; no product authorization expansion.','readiness':'NOT_READY_FOR_IMPLEMENTATION; exact fixture/golden/provider/native gates preserved.'}}
 write_at(dest/'module-spec.json',model);write_at(dest/'differences.json',diffs);write_at(dest/'envelope.json',env);write_at(dest/'test-plan.json',tests);write_at(dest/'shared-contract.json',common)
 lines=['Feature: '+name+' CX revised module contract','  Background:','    Given the frozen original module revision and proposed common contract','']
 for c in relevant:lines+=['  @'+c['id'],'  Scenario: '+c['id'],'    Given '+c['given'],'    When '+c['when'],'    Then '+c['then'],'']
 (dest/'module.feature').write_text('\n'.join(lines),encoding='utf-8')
 # Human-facing differences first; raw technical model remains machine-readable and expandable.
 cards=''.join('<article><h3>'+html.escape(d['cx']+' '+d['pointer'])+'</h3><details><summary>修訂前（原包保留）</summary><pre>'+html.escape(json.dumps(d['before'],ensure_ascii=False,indent=2))+'</pre></details><p><b>修訂後候選：</b></p><pre>'+html.escape(json.dumps(d['after'],ensure_ascii=False,indent=2))+'</pre></article>' for d in diffs)
 (dest/'index.html').write_text('<!DOCTYPE html><html lang="zh-Hant"><meta charset="utf-8"><title>'+name+' CX修訂包</title><style>body{font:16px system-ui;max-width:1150px;margin:30px auto;padding:24px;background:#f2f6fa;color:#172b40}article,section{background:white;padding:20px;margin:16px 0;border-radius:10px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 Consolas,monospace}.status{background:#fff0bd;padding:16px}</style><h1>'+name+' CX修訂一次確認包</h1><p class="status">待Owner整包採納；非實作批准。共用契約 '+common_sha+'；原revision '+source['revision']+' 保留。</p><p>以下欄位已直接套入新effective_spec；原檔不改。既有驗收不重開；未建Skeleton、未修改產品，tests/build/RED/native NOT RUN。</p>'+cards+'<section><h2>完整新規格（技術展開）</h2><details><summary>effective module contract</summary><pre>'+html.escape(json.dumps(effective,ensure_ascii=False,indent=2))+'</pre></details></section><script type="application/json" id="module-spec">'+json.dumps(model,ensure_ascii=False).replace('</','<\/')+'</script></html>',encoding='utf-8')
 hashes={p.name:sha(p) for p in dest.iterdir() if p.is_file() and p.name not in ['artifact-hashes.json','review-request.json','verification.json']};revision=digest(hashes);write_at(dest/'artifact-hashes.json',hashes);write_at(dest/'review-request.json',{'revision_sha256':revision,'status':'ONE_OWNER_CONFIRMATION_PENDING','common_contract_sha256':common_sha,'original_revision':source['revision'],'cx':model['applicable_cx']})
 packages[name]={'report':str((dest/'index.html').relative_to(ROOT)).replace('\\','/'),'revision':revision,'original_revision':source['revision'],'diff_fields':len(diffs),'cx_cases':len(relevant),'candidate_files':len(env['files']),'shared_contract_sha256':common_sha};all_diffs+=diffs
write('module-revisions.json',packages);write('all-differences.json',all_diffs)
order=copy.deepcopy(review['dependency_order']);order[0]['work']='Owner confirms materialized CX module revisions/common/envelopes as one pending bundle; then stage-specific readiness/Skeleton gates (this document request is not adoption).'
write('dependency-order.json',order)
shared={p:sorted(set(ms)) for p,ms in claim_map.items() if len(set(ms))>1};queue=[]
for path,owners in sorted(shared.items()):queue.append({'path':path,'claimants':owners,'execution':'SERIAL_ONE_INTEGRATION_PATCH','primary_child':'IO' if '/committed_read' in path or path.endswith('/file_commit.rs') else ('M01' if '/project_copy' in path else 'declared owning module'),'rule':'Do not union approvals or duplicate implementation; rebaseline shared file SHA after each accepted patch.'})
write('shared-file-queue.json',queue)
summary={'identity':{'task':'M01-M07-CX-MATERIALIZED-REVISION','status':'ONE_OWNER_CONFIRMATION_PENDING_NOT_READY_FOR_IMPLEMENTATION','at':at,'branch':branch,'head':head},'shared_contract_sha256':common_sha,'module_revisions':packages,'differences':len(all_diffs),'cx_coverage':{x['id']:[m for m,ids in applicability.items() if int(x['id'][-2:]) in ids] for x in review['findings']},'dependency_order':order,'shared_file_queue':queue,'integration_cases':len(shared_cases),'wire_document_oracles':{'count':len(vectors),'passed':len(vectors),'meaning':'Python document grammar/u64 arithmetic only, not product DTO tests'},'scope':'Only new document revision folders +existing current-state pointers +own governance card note. All source packets/prior acceptances/product remain immutable.','readiness':'Materialized proposals are internally linked but not approved architecture or acceptance. Golden/projector/source-writer/native evidence still explicit gates; no product work.','original_hashes':originals}
write('module-spec.json',summary)
links=''.join('<tr><td>'+m+'</td><td><a href="../../../../../'+p['report']+'">修訂包</a></td><td>'+str(p['diff_fields'])+'</td><td>'+str(p['cx_cases'])+'</td><td>'+p['revision']+'</td></tr>' for m,p in packages.items())
# Relative URL computed from central directory, not workspace guessing.
import os
links=''.join('<tr><td>'+m+'</td><td><a href="'+os.path.relpath(ROOT/p['report'],OUT).replace('\\','/')+'">修訂包</a></td><td>'+str(p['diff_fields'])+'</td><td>'+str(p['cx_cases'])+'</td><td>'+p['revision']+'</td></tr>' for m,p in packages.items())
human=''.join('<li><b>Wave '+str(x['wave'])+'</b> '+html.escape(x['work'])+'</li>' for x in order)
(OUT/'index.html').write_text('<!DOCTYPE html><html lang="zh-Hant"><meta charset="utf-8"><title>M01–M07 CX修訂一次確認入口</title><style>body{font:16px system-ui;max-width:1250px;margin:30px auto;padding:24px;background:#f2f6fa;color:#172b40}section{background:white;padding:24px;margin:18px 0;border-radius:12px}table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left;overflow-wrap:anywhere}td:last-child{font:12px Consolas;max-width:240px}.status{background:#fff0bd;padding:18px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>M01～M07 CX01～CX17 修訂一次確認入口</h1><p class="status">9份新修訂包 · '+str(len(all_diffs))+'欄位前後差異 · 17項CX完整映射 · 共用契約同SHA · 全部仍待一次採納，非Skeleton／產品批准。</p><p>新effective_spec直接呈現修訂後契約、Port、envelope與行為測試；原包與既有驗收不修改。M01 copy改最終路徑Quarantined→Ready，IO journal不搬。共用pin/receipt/wire/source reservation已統一；未完成golden、typed projector與Windows11證據仍留gate。</p><section><h2>各模組新revision</h2><table><tr><th>模組</th><th>入口</th><th>差異欄位</th><th>CX計畫情境</th><th>revision SHA256</th></tr>'+links+'</table></section><section><h2>依賴與驗收順序</h2><ol>'+human+'</ol></section><section><h2>確認範圍</h2><p>一次確認此整包的共用契約、各模組修訂後規格與列明的候選envelope；不是將原包所有文字無條件合併，也不是授權修改產品。採納後仍逐切片確認前置資料完整、Skeleton與有效RED驗收。待確認/缺證據不轉綠，不以靜態文件通過稱產品完成。</p></section><section><h2>完整追溯與共用檔案隊列</h2><details><summary>技術資料</summary><pre>'+html.escape(json.dumps({k:v for k,v in summary.items() if k!='original_hashes'},ensure_ascii=False,indent=2))+'</pre></details></section><script type="application/json" id="module-spec">'+json.dumps(summary,ensure_ascii=False).replace('</','<\/')+'</script></html>',encoding='utf-8')
assert len(packages)==9 and all(summary['cx_coverage'].values()) and all(sha(ROOT/p)==h for p,h in originals.items()) and all(sha(ROOT/p)==h for p,h in baseline['source_hashes'].items())
hashes={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name not in ['artifact-hashes.json','review-request.json','verification.json','board-evidence.json','current-state.json']};revision=digest(hashes);write('artifact-hashes.json',hashes);write('review-request.json',{'revision_sha256':revision,'status':'ONE_OWNER_CONFIRMATION_PENDING','shared_contract_sha256':common_sha,'module_revisions':packages,'cx':['CX-'+str(i).zfill(2) for i in range(1,18)],'hash_rule':'SHA256 UTF8 sorted compact JSON filename→SHA256 map; module-revisions binds all nine child revisions; evidence/request/current-state excluded','confirmation':'一次確認9份CX修訂包及共同契約/候選envelope；未採納，不建Skeleton。原包與驗收保留；缺golden/projector/native/provider仍不得越門檻。'})
write('current-state.json',{'state':'MATERIALIZED_CX_REVISIONS_PENDING_OWNER','report':'index.html','revision':revision,'next':'Owner one confirmation; then exact child readiness and accepted Skeleton/RED gates; no product work now.'})
# Update navigation only, preserve original report files and acceptance stage/history.
for module in ['M01','M02','M03','M04','M05','M06','M07']:
 p=TASKS/module/'planning/current-state.json';state=load(p);state.setdefault('history',[]).append({'at':at,'previous_report':state.get('report'),'change':'CX proposal revision navigation only; no adoption/acceptance change'});children={m:v for m,v in packages.items() if m.split('-')[0]==module};state['cx_revision']=children;state['joint_confirmation_entry']=str((OUT/'index.html').relative_to(ROOT)).replace('\\','/');state['state']='CX_REVISION_PENDING_OWNER';state['module_complete']=False;write_at(p,state)
oldnav=TASKS/'integration-contract-review/current-state.json';state=load(oldnav);state['latest_revision_entry']=str((OUT/'index.html').relative_to(ROOT)).replace('\\','/');state['latest_revision']=revision;state['revision_preparation_authorized_not_adopted']=True;write_at(oldnav,state)
def mutate(s):
 t=next(t for t in s['tasks'] if t['id']=='PD-P1-ESS-DEC-01');assert t['zone']=='red';t['note']+='\n[CX materialized revision proposals] docs/requirements-confirmation/phase1-spec/tasks/integration-contract-revision-v1/index.html revision '+revision+';9 module revisions/common SHA/'+str(len(all_diffs))+' field diffs, CX01-CX17 covered; ONE_OWNER_CONFIRMATION_PENDING. Original packets/acceptances/product796 unchanged; no Skeleton/product tests. Governance remains red.'
mutate_snapshot_file(board,mutate,lock_factory=FileLock);a,p,c=split_snapshot(board.read_text(encoding='utf-8'));after=json.loads(p);aftercounts=dict(Counter(t['zone'] for t in after['tasks']))
assert (pre,post)==(a,c) and counts==aftercounts and {k:v for k,v in before.items() if k!='tasks'}=={k:v for k,v in after.items() if k!='tasks'}
assert [t for t in before['tasks'] if t['id']!='PD-P1-ESS-DEC-01']==[t for t in after['tasks'] if t['id']!='PD-P1-ESS-DEC-01']
write('board-evidence.json',{'before':counts,'after':aftercounts,'own_task':'PD-P1-ESS-DEC-01','zone':'red','shell_root_other_cards_preserved':True});write('verification.json',{'status':'STATIC_REVISION_CHECKS_ONLY','branch':branch,'head':head,'original_files_unchanged':len(originals),'product_796_unchanged':True,'child_packages':9,'diff_fields':len(all_diffs),'cx_coverage':17,'integration_scenarios':len(shared_cases),'wire_document_oracles':len(vectors),'shared_paths':len(queue),'adoption_architecture_acceptance':'NOT RUN; proposal only','product_tests_build_RED_GREEN_native':'NOT RUN','reviewer':'same assistant; no delegated reviewer','counts':aftercounts})
print(json.dumps({'revision':revision,'common_sha':common_sha,'modules':len(packages),'diff_fields':len(all_diffs),'integration_cases':len(shared_cases),'shared_paths':len(queue),'counts':aftercounts},ensure_ascii=True))
