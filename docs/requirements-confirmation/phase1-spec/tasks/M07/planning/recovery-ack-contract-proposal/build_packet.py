"""Generate PH-G1 planning artifacts only. Run with python -B."""
from pathlib import Path
import copy, hashlib, html, json, uuid

P = Path(__file__).resolve().parent
ROOT = P.parents[6]
TASKS = P.parents[2]
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(v): return hashlib.sha256(json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
def write(n,v): (P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
issuer = read(P.parent/'publication-retention-handoff/immutable-issuer.json')
e = issuer['index_proof']['evidence']
ctx = e['context']
request = dict(protocol='SGA-RECOVERY-ACK-PROPOSAL-v1',issuer='M04',role='ack-recovery',ordinal='0',context=ctx,body=dict(
    source_owner_handle='opaque-document-owner-2',capture_handle='opaque-capture-10',
    attempt_id=e['attempt_id'],snapshot_id=e['snapshot_id'],captured_recovery_fingerprint=e['recovery_fingerprint'],
    material_versions=e['materials'],payload_raw_digest=e['payload_raw_digest'],index_target_identity=e['target_identity'],
    index_expected_prior_raw_digest=e['index_expected_prior_raw_digest'],index_committed_raw_digest=e['index_committed_raw_digest'],
    index_transaction_id=e['index_transaction_id'],index_receipt=issuer['index_proof']['proof'],
    transfer_receipt=dict(issuer='M05',receipt_id=issuer['transfer_receipt']['receipt_id'],kind='RecoveryTransfer',
                         context_digest=digest(ctx),evidence_digest=digest(issuer['transfer_receipt']))))
op = str(uuid.uuid5(uuid.UUID(ctx['workflow_id']),'ack-recovery/0'))
state = dict(project_uuid=ctx['project_uuid'],document_uuid=ctx['document_uuid'],session_id=ctx['session_id'],owner_generation='2',
             live_revision='10',formal_baseline='formal-unchanged',recovery_baseline=None)
capture = dict(source_owner_handle=request['body']['source_owner_handle'],capture_handle=request['body']['capture_handle'],context=ctx,
               attempt_id=e['attempt_id'],snapshot_id=e['snapshot_id'],fingerprint=e['recovery_fingerprint'],materials=e['materials'])
fixture = dict(premise='Immutable trusted DOCUMENT fixture only; not a new registry, production provider or authentication proof',
               capture=capture,index=issuer['index_proof'],transfer_request=issuer['frozen_request'],transfer=issuer['transfer_receipt'],
               held=issuer['held'],owner_state=state)
write('immutable-proof.json',fixture)
write('request-example.json',request)

def shape(v,key=''):
    if isinstance(v,dict): return dict(type='object',properties={k:shape(x,k) for k,x in v.items()},required=list(v),additionalProperties=False)
    if isinstance(v,list): return dict(type='array',items=shape(v[0]),maxItems=4096)
    if v is None: return dict(type='null')
    if type(v)==bool:return dict(type='boolean')
    if key in ('protocol','issuer','role','kind','profile'): return dict(type='string',const=v)
    if key in ('ordinal','owner_generation','captured_revision','size_bytes','live_revision'):
        return dict(type='string',pattern='^(0|[1-9][0-9]{0,19})$',description='Checked runtime u64 decimal <=18446744073709551615')
    if len(v)==64 and all(c in '0123456789abcdef' for c in v):return dict(type='string',pattern='^[0-9a-f]{64}$')
    if len(v)==36 and v.count('-')==4:return dict(type='string',pattern='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    return dict(type='string',minLength=1,maxLength=4096)
schema=shape(request);schema['$schema']='https://json-schema.org/draft/2020-12/schema'
schema['$id']='urn:sgenaxis:proposal:recovery-ack:v1:request'
write('request.schema.json',schema)
response_ok=dict(protocol=request['protocol'],operation_id=op,request_digest=digest(request),result='CapturedRecoveryAcknowledged',
    capture_context=ctx,attempt_id=e['attempt_id'],snapshot_id=e['snapshot_id'],acknowledged_fingerprint=e['recovery_fingerprint'],
    baseline_effect='CapturedRecoveryOnly',formal_baseline_changed=False,live_revision='10')
ok=shape(response_ok)
for k in ('result','baseline_effect'):ok['properties'][k]={'const':response_ok[k],'type':'string'}
ok['properties']['formal_baseline_changed']={'const':False,'type':'boolean'}
fail=dict(protocol=request['protocol'],operation_id=op,request_digest=digest(request),result='Rejected',reason='ProofMismatch',
          baseline_effect='None',retry_allowed=False,release_allowed=False)
fs=shape(fail)
fs['properties']['result']={'enum':['Rejected','Deferred','UnverifiedOutcome','Superseded','ReplayConflict','InProgress'],'type':'string'}
fs['properties']['reason']={'enum':['InvalidRequest','ProofMismatch','WrongOwner','RootDeferred','MissingIssuerProof','OlderThanBaseline','ChangedRequest','PendingRecord'],'type':'string'}
fs['properties']['baseline_effect']={'const':'None','type':'string'}
for k in ('retry_allowed','release_allowed'):fs['properties'][k]={'const':False,'type':'boolean'}
write('response.schema.json',{'$schema':schema['$schema'],'oneOf':[ok,fs]})
write('response-example.json',response_ok)

cases=[]
def case(name,change,expected):
    x=dict(id='M07-RA-'+str(len(cases)+1).zfill(3),behavior=name,request=copy.deepcopy(request),state=copy.deepcopy(state),
           root_state='Transferred',proof_available=True,expected=expected)
    change(x);cases.append(x)
case('valid captured recovery ACK',lambda x:None,'CapturedRecoveryAcknowledged')
case('newer live revision remains dirty',lambda x:x['state'].update(live_revision='11'),'CapturedRecoveryAcknowledged')
case('late older ACK cannot regress recovery baseline',lambda x:x['state'].update(recovery_baseline=dict(revision='11',fingerprint={'profile':'SGA-RECOVERY-FP-v1','lowerhex64':'f'*64})),'Superseded')
case('formal baseline never changes',lambda x:x['state'].update(formal_baseline='formal-saved-12'),'CapturedRecoveryAcknowledged')
case('payload raw is not recovery fingerprint',lambda x:x['request']['body']['captured_recovery_fingerprint'].update(lowerhex64=e['payload_raw_digest']),'Rejected')
case('index raw is not recovery fingerprint',lambda x:x['request']['body']['captured_recovery_fingerprint'].update(lowerhex64=e['index_committed_raw_digest']),'Rejected')
case('wrong transfer issuer',lambda x:x['request']['body']['transfer_receipt'].update(issuer='M07'),'Rejected')
case('wrong project context',lambda x:x['request']['context'].update(project_uuid='00000000-0000-4000-8000-000000000099'),'Rejected')
case('wrong session',lambda x:x['state'].update(session_id='00000000-0000-4000-8000-000000000099'),'Rejected')
case('stale generation',lambda x:x['state'].update(owner_generation='3'),'Rejected')
case('root deferred retains local integrity without ACK',lambda x:x.update(root_state='Deferred'),'Deferred')
case('unknown root no ACK no retry',lambda x:x.update(root_state='Unknown'),'UnverifiedOutcome')
case('restart lost issuer proof no ACK retry or release',lambda x:x.update(proof_available=False),'UnverifiedOutcome')
case('wrong material version',lambda x:x['request']['body']['material_versions'][0].update(digest='f'*64),'Rejected')
case('wrong attempt',lambda x:x['request']['body'].update(attempt_id='00000000-0000-4000-8000-000000000099'),'Rejected')
case('wrong owner handle',lambda x:x['request']['body'].update(source_owner_handle='other-owner'),'Rejected')
case('unknown request key rejected before lookup',lambda x:x['request']['body'].update(formal_target_identity='forbidden'),'Rejected')
case('wrong index transaction',lambda x:x['request']['body'].update(index_transaction_id='00000000-0000-4000-8000-000000000099'),'Rejected')
case('wrong snapshot',lambda x:x['request']['body'].update(snapshot_id='00000000-0000-4000-8000-000000000099'),'Rejected')
case('wrong index evidence hash',lambda x:x['request']['body']['index_receipt'].update(evidence_digest='f'*64),'Rejected')
write('fixtures.json',cases)

sources={
 'effective_formal_ack':('M07/planning/cx-revision-v3/shared-contract.json','/replay_protocol/request_digest/per_role_closed_bodies/ack'),
 'effective_role':('M07/planning/cx-revision-v3/shared-contract.json','/replay_protocol/operation_id'),
 'hash_contract':('M07/planning/cx-revision-v3/shared-contract.json','/replay_protocol/request_digest'),
 'original_capture':('M07/planning/snapshot-exact-design/module-spec.json','/capture_fingerprint'),
 'original_ownership':('M07/planning/snapshot-exact-design/module-spec.json','/architecture/ownership'),
 's1':('M07/s1/green/verification.json',''),
 's1_policy':('../../../../apps/sgenaxis-desktop/crates/sgenaxis-work/src/recovery_state.rs',''),
 'handoff':('M07/planning/publication-retention-handoff/module-spec.json','/contracts'),
 'gap':('M07/planning/publication-retention-review/review.json','/owner_gaps/0'),
 'issuer':('M07/planning/publication-retention-handoff/immutable-issuer.json',''),
 'current_state':('M07/planning/current-state.json',''),
 'inventory':('M01/planning/s2-green/source-current.json','/source_hashes')}
pointers=[]
for name,(p,ptr) in sources.items():
    path=TASKS/p
    path=path.resolve()
    pointers.append(dict(name=name,path=str(path.relative_to(ROOT)).replace('\\','/'),pointer=ptr,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
write('source-pointers.json',pointers)
write('before-after.json',[
 dict(source='effective_formal_ack',before='ack body requires owner_handle,captured_revision,captured_semantic_digest,formal_target_identity,file_receipt,transfer_receipt; closed additionalProperties=false',after='UNCHANGED. Separate proposed SGA-RECOVERY-ACK-PROPOSAL-v1/ack-recovery candidate; no legal effective invocation before Owner adoption'),
 dict(source='effective_role',before='Closed CXv3 roles include ack, not ack-recovery',after='UNCHANGED. Owner option A: adopt distinct protocol/role. Option B: explicitly revise effective union/role/hash with discriminator; not approved here'),
 dict(source='original_ownership',before='M04 only DocumentOwner; M07 captures immutable attempt observations',after='UNCHANGED. M04 proposes exact captured recovery baseline ACK; no M07 setter, content registry or new domain API'),
 dict(source='handoff',before='LocalIntegrityReady follows durable payload/index/material, Published also requires M05 recovery root and exact captured source ACK',after='UNCHANGED. Deferred root/proof unavailable cannot ACK; retained material remains Held/Unknown; never automatic retry/release')])
spec=dict(module='M07',task='PD-P1-M07-PREP-01',seam='PH-G1 only',state='PROPOSED_PENDING_OWNER',author='/root/m07_recovery_ack_packet',
 authority=dict(head='5b709343a890503ebbe24a802e43cda5647df124',inventory_head='31babe87a7ef1e40a0d4bedc523077e7a45d63ab',inventory_files=796),
 intent='Close candidate recovery capture ACK request/response and issuer-proof mapping without changing effective formal ACK.',
 architecture=dict(hexagonal='Trusted M07 observation → proposed M04 captured-recovery ACK input boundary → sole DocumentOwner → existing trusted proof lookup abstractions ← M07 index/M05 transfer issuer adapters',
 dependency='M07 observer → M04 owner boundary; M04 depends on proof abstractions; no UI/native/domain bypass. No new API approval.',
 ownership='M04 owns document/live state and formal/recovery baselines. M07 owns immutable attempt/index observations. M05 owns materials/pins/roots.',
 mutation='Only M04 matching owner generation/session may ACK exact immutable capture. Baseline update is conditional monotonic by captured revision, never live content overwrite.',
 transaction='Resolve handles/proofs outside index/catalog leases, recheck owner fence at M04 baseline commit. Owner baseline + replay terminal response must be atomic in future design; native atomicity unproved.'),
 boundary=dict(caller='Only trusted orchestration with pre-resolved M04 capture capability; UI supplies no trusted body/proof/state. No unauthenticated caller data admitted.',
 lookup='Fixture stands for existing issuer-owned lookup: exact (issuer, receipt_id) for M07 index and M05 root transfer; compare full context, capture and body. ReceiptRef hashes are commitments, not authorization. Never accept caller boolean verified labels.',
 no_registry='immutable-proof.json is a documentary fixture, never a proposed document registry; proof/provider integration PH-G2..4 remains separate pending adoption.'),
 s1_limit='Accepted S1 recovery_state.rs consumes HOST-supplied Published; it has no timer, filesystem, codec, fingerprint computation, pinning, capture/provider authentication or M04 ACK integration. This proposal changes none of those facts.',
 hash=dict(status='NEW_VARIANT_PROPOSED_PENDING_OWNER',protocol=request['protocol'],role='ack-recovery',issuer='M04',operation_id='UUIDv5(workflow_id, UTF8 ack-recovery/0)',
 digest='SHA256 canonical UTF8 entire admitted request recursively, including protocol/issuer/role/ordinal/context/body. Same canonical rules as CXv3; distinct protocol prevents cross-purpose replay.',
 key='Proposed M04 owner replay store identity + workflow_id + operation_id + authenticated issuer/owner binding; physical durable store/provider pending Owner.',
 replay='Exact retained terminal digest returns exact response, not another mutation. Changed valid body same key ReplayConflict. InFlight InProgress. Lost durable proof UnverifiedOutcome; no automatic retry/release/ACK.',
 details='Request body commits capture owner/capability, attempt/snapshot/context, fingerprint profile+hash, immutable ordered material versions, payload raw, index prior/new raw+transaction+target, index/transfer refs. Resolve before freeze; no enrichment after hash.'),
 mapping=dict(fingerprint='Reuse original SGA-RECOVERY-FP-v1 definition includes format/semantic/material versions/bindings. Do not replace by payload/index raw or formal semantic hash.',
 index='index_receipt.evidence_digest hashes FULL immutable index evidence; context_digest hashes full WorkflowContext. Match target/prior/new raw/transaction/payload/materials/attempt/snapshot/fingerprint exactly.',
 transfer='transfer_receipt.evidence_digest hashes FULL M05 immutable transfer record; request_digest must hash entire frozen transfer-recovery request. Match issuer, role, workflow, operation, context, pin, source receipt IDs, materials, roots, expected+committed generation and native store/target identity.',
 distinction='M05 external_proof.raw_digest=index committed raw; projection_digest=index FULL evidence hash; recovery fingerprint remains independent. source_receipt_ids bind Held and index refs.'),
 contracts=['Never reuse formal-only ack body/role implicitly','Only M04 mutates recovery baseline; no formal baseline change','Captured R ACK may succeed with live R+1 while live remains dirty','Late R after acknowledged R+1 returns Superseded; no backward baseline','M05 root Deferred retains LocalIntegrityReady, not Published; no ACK/release','Missing or Unknown issuer evidence => UnverifiedOutcome, no automatic retry','No catalog/index lease held during M04 callback'],
 owner_options=[dict(id='RA-O1',status='PROPOSED_PENDING_OWNER',option='Adopt distinct protocol and ack-recovery role/body/receipt mapping, replay lifecycle and atomic owner mutation'),dict(id='RA-O2',status='PROPOSED_PENDING_OWNER',option='Instead explicitly version effective transition schema with formal/recovery discriminated union, role/hash migration and full compatibility analysis; not performed')],
 tasks=[dict(id='M07-RA-PLAN',primary_module='M07',status='PLANNING',allowed='this new directory only',protected='all originals/product/board/current-state/hooks/roles',acceptance='20 bounded DOCUMENT witnesses and source/hash/seal checks; not implementation acceptance')],
 bdd_tdd=[dict(id=x['id'],behavior=x['behavior'],contract='Exact captured ACK binding and baseline isolation',test='DOCUMENT:'+x['id'],native='NOT RUN') for x in cases],
 assumptions=['Immutable fixture authenticity assumed only','Native durable index provider unavailable/unproved','Native M05 material/root atomic inclusion unproved','Native M04 replay+baseline transaction and restart provider unproved','SHA256 collision resistance assumed','No native interface or skeleton created'],
 remaining_gates=['Owner selects protocol/role/hash option and confirms architecture/contracts/BDD','PH-G2 index issuer/provider adoption','PH-G3 material/root transition receipt adoption','PH-G4 restart proof lookup/lifecycle','Approved Skeleton and intended valid RED','Independent documentary review then separate native implementation acceptance'],
 not_run=['independent review','native','build','product tests','valid RED/GREEN','full Draft2020-12','module acceptance'],module_complete=False)
write('module-spec.json',spec)
feature=['Feature: Captured recovery acknowledgment','  Background:','    Given a captured document version and immutable publication evidence','  Rule: Only the document owner acknowledges an exact retained recovery capture']
for x in cases:
    feature += ['','    @'+x['id'],'    Scenario: '+x['behavior'],'      Given the recovery evidence and owner state for '+x['id'],'      When recovery acknowledgment is requested','      Then the observable outcome is '+x['expected'],'      And the formal baseline and live content are preserved']
(P/'module.feature').write_text('\n'.join(feature)+'\n',encoding='utf-8')
(P/'steps_pending.py').write_text('"""Native automation stubs only; not executable acceptance."""\n'+ '\n'.join('def planned_'+x['id'].replace('-','_')+'():\n    raise NotImplementedError("Pending approved native owner/proof seams")\n' for x in cases),encoding='utf-8')
write('test-plan.json',dict(document='python -B check_documents.py',seal='python -B verify_seal.py',native_pending=[x['id'] for x in cases],
 valid_red='Future native tests must build and fail for missing approved captured ACK behavior; document checks are not RED',
 layers=dict(L0='canonical hash and closed types',L1='M04 owner captured ACK boundary',L2='M07 publication contract with output-port doubles',L3='real issuer adapters',L4='formal save/recovery separation',L5='full desktop recovery'),
 category_evaluation={k:'Applicable; native NOT RUN' for k in ['success','input boundary','invalid input','dependency failure','partial failure','state consistency','transaction','lifecycle','rollback/recovery','cross-module','compatibility','regression']}))
page='<html><meta charset="utf-8"><title>M07 recovery ACK PH-G1 proposal</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;line-height:1.5}pre{white-space:pre-wrap;background:#f2f4f8;padding:18px}h1{color:#273d73}</style><h1>M07 · PH-G1 recovery ACK</h1><p>PROPOSED_PENDING_OWNER · Yellow preserved · document-only · no implementation authorization</p><p>One ACK seam. M04 remains sole DocumentOwner. Formal ACK schema unchanged.</p>'
for k,v in spec.items():page+='<h2>'+html.escape(k.replace('_',' '))+'</h2><pre>'+html.escape(json.dumps(v,ensure_ascii=False,indent=2))+'</pre>'
page+='<h2>Dependency view</h2><pre>M07 observation → M04 input boundary → DocumentOwner baseline\nM04 → abstract proof lookup ← M07 index / M05 transfer issuers\nNo UI setter; no second document registry; no callback under catalog/index lease.</pre><script type="application/json" id="module-spec">'+json.dumps(spec,ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
(P/'index.html').write_text(page,encoding='utf-8')
print('Generated 20 planning witnesses; NOT_RUN layers preserved')
