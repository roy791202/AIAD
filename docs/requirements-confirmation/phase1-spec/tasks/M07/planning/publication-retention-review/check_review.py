"""Independent bounded documentary review. Run python -B; never runs author main."""
from pathlib import Path
import json, hashlib, uuid, copy, importlib.util, subprocess, html
P=Path(__file__).resolve().parent
R=P.parents[6]
A=P.parent/'publication-retention-handoff'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dig(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def write(n,v): (P/n).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
spec=importlib.util.spec_from_file_location('bounded_author_oracle',A/'check_documents.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
c=read(A/'immutable-issuer.json'); x=read(A/'fixtures.json')[0]['input']; traces=[]
def check(name,condition,detail=None):
 assert condition,name
 traces.append(dict(id=name,passed=True,detail=detail))
sealed=read(A/'seal.json')['hashes']
check('sealed-author-inputs',all(sha(A/n)==v for n,v in sealed.items()),sealed)
check('independent-roles','/root/m07_publication_handoff_review'!='/root/m07_publication_handoff_packet')
q=c['frozen_request']; e=c['index_proof']['evidence']; proof=c['index_proof']['proof']; rec=c['transfer_receipt']; ctx=q['context']
check('exact-central-schema',sha(A/'request.schema.json')==sha(R/'docs/requirements-confirmation/phase1-spec/tasks/integration-contract-revision-v3/transition-request.schema.json'))
check('closed-body-valid-used-subset',m.valid(q,read(A/'request.schema.json'),read(A/'request.schema.json')))
check('full-request-digest',dig(q)==rec['request_digest'],dict(actual=dig(q),recorded=rec['request_digest']))
check('workflow-role-ordinal-uuid',str(uuid.uuid5(uuid.UUID(ctx['workflow_id']),q['role']+'/'+q['ordinal']))==rec['operation_id'])
check('context-evidence-binding',dig(ctx)==proof['context_digest'] and dig(e)==proof['evidence_digest'])
check('snapshot-not-document',e['snapshot_id']!=ctx['document_uuid'] and e['attempt_id']!=e['snapshot_id'])
check('fingerprint-not-raw',len({e['recovery_fingerprint']['lowerhex64'],e['payload_raw_digest'],e['index_expected_prior_raw_digest'],e['index_committed_raw_digest'],e['materials'][0]['digest']})==5)
check('receipt-index-not-payload',rec['external_proof']['raw_digest']==e['index_committed_raw_digest'] and rec['external_proof']['projection_digest']==dig(e))
check('asset-closure',c['held']['assets']==e['materials']==q['body']['root_manifest']['assets'] and rec['asset_pairs']==[{k:a[k] for k in ('asset_id','digest')} for a in e['materials']])
check('source-lineage',rec['source_receipt_ids']==[dict(issuer='M05',receipt_id=c['held']['receipt_id']),dict(issuer='M07',receipt_id=proof['receipt_id'])])

# NEW combined event witnesses, not an 8+5 rerun. Inputs and full outputs retained.
events=[('unknown-index-and-replaced-owner',dict(index_outcome='Unknown',owner_generation='3',live_revision='12'),'UncertainPublication',False,0,0),
 ('failed-index-newer-live',dict(index_outcome='Failed',live_revision='13'),'NotReady',False,0,0),
 ('unknown-root-newer-live',dict(root_outcome='Unknown',live_revision='14'),'SourceRetentionDeferred',True,1,0),
 ('deferred-root-replaced-owner',dict(root_outcome='Deferred',owner_generation='4',live_revision='15'),'SourceRetentionDeferred',True,1,0),
 ('transferred-replaced-owner-newer-live',dict(owner_generation='4',live_revision='16'),'CommittedAckDeferred',True,1,0),
 ('captured-ack-newer-live',dict(live_revision='17'),'PublicationAcknowledged',True,1,1),
 ('restart-proof-loss-after-transferred',dict(issuer_record_available=False,root_outcome='Transferred',live_revision='18'),'UnverifiedOutcome',False,0,0),
 ('ack-not-requested-newer-live',dict(captured_ack_requested=False,live_revision='19'),'CommittedAckDeferred',True,1,0)]
fixtures=[]
for name,changes,status,ready,t,a in events:
 z=copy.deepcopy(x);z.update(changes);out=m.evaluate(z,c)
 check(name,out['status']==status and out['local_integrity_ready']==ready and out['calls']==dict(transfer=t,ack=a,retry=0,release=0) and out['formal_baseline_revision']=='6' and out['live_revision']==z['live_revision'] and out['recovery_baseline_revision']==('10' if a else '5'),dict(input=z,result=out))
 fixtures.append(dict(id=name,input=z,expected=out))

# Full-field defensive catalog perturbations: assertions signal inconsistent trusted
# fixture premises, NOT production rejection of an attacker-controlled issuer.
paths=[('transfer_receipt','request_digest'),('transfer_receipt','operation_id'),('transfer_receipt','context','session_id'),('transfer_receipt','role'),('transfer_receipt','ordinal'),('transfer_receipt','external_proof','raw_digest'),('transfer_receipt','source_receipt_ids',0,'receipt_id'),('transfer_receipt','asset_pairs',0,'digest'),('transfer_receipt','root_manifest_ids',0),('index_proof','evidence','snapshot_id'),('index_proof','evidence','recovery_fingerprint','lowerhex64'),('index_proof','evidence','payload_raw_digest'),('index_proof','evidence','index_expected_prior_raw_digest'),('index_proof','evidence','index_committed_raw_digest')]
for path in paths:
 altered=copy.deepcopy(c);at=altered
 for k in path[:-1]:at=at[k]
 at[path[-1]]='f'*64
 try: result=m.evaluate(x,altered); observed=result['status']
 except AssertionError: result=None;observed='TrustedFixtureConsistencyAssertion'
 check('mutate-'+'.'.join(map(str,path)),observed in ('ProofMismatch','TrustedFixtureConsistencyAssertion'),dict(changed_path=path,altered_issuer=altered,result=result,observed=observed,interpretation='defensive premise consistency only'))

# Every request leaf contributes to the full recursive digest; no purpose enrichment.
def leaves(v,p=()):
 if isinstance(v,dict):
  for k,w in v.items():yield from leaves(w,p+(k,))
 elif isinstance(v,list):
  for k,w in enumerate(v):yield from leaves(w,p+(k,))
 else:yield p
for path in leaves(q):
 altered=copy.deepcopy(q);at=altered
 for k in path[:-1]:at=at[k]
 at[path[-1]]=str(at[path[-1]])+'changed'
 check('hash-leaf-'+'.'.join(map(str,path)),dig(altered)!=rec['request_digest'])
z=copy.deepcopy(x);z['request']['body']['purpose']='Recovery'
check('no-purpose-enrichment',m.evaluate(z,c)['status']=='InvalidInput')
z=copy.deepcopy(x);z['payload_verified']='true'
check('boolean-is-not-string',m.evaluate(z,c)['status']=='InvalidInput')
central=read(A/'request.schema.json')
ack=next(v for v in central['oneOf'] if v['properties']['role'].get('enum')==['ack'])
required=ack['properties']['body']['required']
check('PH-G1-formal-only-ack-shape',all(k in required for k in ('formal_target_identity','file_receipt','captured_semantic_digest')),required)
recovery_ack=copy.deepcopy(q);recovery_ack['role']='ack';recovery_ack['body']=dict(attempt_id=e['attempt_id'],snapshot_id=e['snapshot_id'],recovery_fingerprint=e['recovery_fingerprint'],index_proof=proof,transfer_receipt=rec)
check('PH-G1-recovery-ack-not-representable',not m.valid(recovery_ack,central,central),dict(request=recovery_ack,result='Invalid closed formal ACK shape; Owner approval required'))

inventory=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
hashes=inventory['source_hashes'];drift=[n for n,v in hashes.items() if not (R/n).is_file() or sha(R/n)!=v]
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
check('authority-796',len(hashes)==796 and not drift,dict(count=len(hashes),drift=drift))
check('head-distinct-inventory',head=='5b709343a890503ebbe24a802e43cda5647df124' and inventory['head']=='31babe87a7ef1e40a0d4bedc523077e7a45d63ab')
sources=read(A/'source-pointers.json');sourcechecks=[dict(path=s['path'],recorded=s['sha256'],actual=sha(R/s['path']),matches=sha(R/s['path'])==s['sha256']) for s in sources]
check('non-board-inputs-unchanged',all(s['matches'] for s in sourcechecks if s['path']!='docs/board.json'),sourcechecks)
board=read(R/'docs/board.json')
write('fixtures.json',fixtures);write('trace.json',traces)
review=dict(reviewer='/root/m07_publication_handoff_review',author='/root/m07_publication_handoff_packet',verdict='PASS_DOCUMENT_ONLY_PENDING_OWNER',passed=len(traces),total=len(traces),head=head,inventory_head=inventory['head'],inventory_files=len(hashes),source_hashes_unchanged=not drift,board_management_hash=dict(recorded=next(s['recorded'] for s in sourcechecks if s['path']=='docs/board.json'),actual=sha(R/'docs/board.json'),classification='management evidence separate from 796 product authority; review performs no board mutation'),findings=[],owner_gaps=read(A/'module-spec.json')['owner_gaps'],premises=['Trusted immutable issuer fixture; bool inputs represent assumed verification outcomes, not native authentication.','Closed request checked with bounded used-keyword subset; fixture context/state strings do not establish full issuer input admission.','Defensive issuer mutations produce assertions, not runtime fail-closed authentication evidence.','No label classifier is counted as behavior proof.','PH-G1 formal-only ACK cannot encode recovery ACK with exact captured source; contextual capture mismatch is unresolved Owner design, not an approved specification conflict.','PH-G2 index provider, PH-G3 M05 receipt adoption, PH-G4 restart proof remain Owner pending. Actual providers/durability/atomicity unproved.'],not_run=['native','build','product tests','valid RED/GREEN','full Draft2020-12','module acceptance'],module_pass=False,next_action='Owner resolves PH-G1..4 and confirms architecture/contract/BDD/Skeleton; preserve Yellow, no automatic retry/release or implementation authorization.')
write('review.json',review)
inputs={str(p.relative_to(R)).replace('\\','/'):sha(p) for p in A.iterdir() if p.is_file()}
for s in sources: inputs[s['path']]=sha(R/s['path'])
write('input-hashes.json',inputs)
body='<h1>M07 publication / retention independent review</h1><p>PASS_DOCUMENT_ONLY_PENDING_OWNER. Yellow preserved. Not module PASS.</p><p>Author: /root/m07_publication_handoff_packet. Reviewer: /root/m07_publication_handoff_review.</p><p>Fresh combined state witnesses, full-field binding and hash mutations. Trusted fixture assumptions remain explicit; no native provider, durability or atomicity proof.</p>'
body+='<h2>Review / Owner decisions</h2><pre>'+html.escape(json.dumps(review,indent=2))+'</pre><h2>Complete trace</h2><pre>'+html.escape(json.dumps(traces,indent=2))+'</pre>'
(P/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M07 independent documentary review</title><style>body{font:16px system-ui;max-width:1150px;margin:40px auto;background:#10151e;color:#e0e7ef}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#1b2533;padding:20px}h1,h2{color:#f2cf6b}</style>'+body+'<script type="application/json" id="module-review">'+json.dumps(review).replace('<','\\u003c')+'</script>',encoding='utf-8')
seal={p.name:sha(p) for p in P.iterdir() if p.is_file() and p.name!='seal.json'}
write('seal.json',dict(status='SEALED_BOUNDED_DOCUMENT_REVIEW',count=len(traces),hashes=seal))
print(json.dumps(dict(verdict=review['verdict'],passed=len(traces),files=len(seal),source_count=len(hashes),drift=len(drift))))
