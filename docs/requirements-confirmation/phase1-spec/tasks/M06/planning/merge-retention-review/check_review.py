"""Independent bounded DOCUMENT probes. Run python -B; never mutates sealed inputs."""
from pathlib import Path
import json, copy, hashlib, importlib.util, subprocess, html
P=Path(__file__).resolve().parent
S=P.parent/'merge-retention-handoff'
R=P.parents[6]
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(n,v): (P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('reviewed_m06_oracle',S/'model.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original_read=m.read
catalog=read(S/'immutable-issuer-fixture.json')
base=copy.deepcopy(read(S/'fixtures.json')[0]['input'])
base.update(commit_observation='Applied',root_observation='Verified',perform_undo=False)
probes=[]
def run(name,x,expected,cat=None,path=None):
    m.read=lambda n: copy.deepcopy(cat) if cat is not None and n=='immutable-issuer-fixture.json' else original_read(n)
    got=m.evaluate(copy.deepcopy(x));m.read=original_read
    checks={'no_retry_release_rollback_formal':all(got['calls'][k]==0 for k in ['retry','release','rollback','formal_save','formal_ack']),'one_merge_max':got['calls']['merge_commit']<=1,'preserved_on_rejection':got['before']==got['after'] if got['result'] in ['ProofMismatch','InvalidInput','RejectedBeforeMutation'] else True,'original_import_held':got['pin']==catalog['held_pin'],'separate_undo_held':got['undo_pin']==catalog['undo_held_pin'],'other_document_preserved':got['other_document']==catalog['other_document']}
    probes.append({'id':name,'changed_path':path,'input':x,'issuer_fixture_override':cat,'expected':expected,'actual':got,'state_call_checks':checks,'passed':got['result']==expected and all(checks.values())})
run('new-merge-success',base,'MergeApplied')
x=copy.deepcopy(base);x['root_observation']='Failure';run('new-merge-deferred',x,'MergeAppliedRetentionDeferred')
x=copy.deepcopy(base);x['perform_undo']=True;x['undo_root_observation']='Failure';run('new-undo-new-context-deferred',x,'UndoAppliedRetentionDeferred')
x=copy.deepcopy(base);x['commit_observation']='Unknown';run('new-unknown-commit',x,'UnverifiedOutcome')
x=copy.deepcopy(base);x['commit_observation']='KnownNotAttempted';run('new-precommit-preserves',x,'RejectedBeforeMutation')
def setpath(o,path,value):
    for k in path[:-1]: o=o[k]
    o[path[-1]]=value
changes=[('import-generation',['import_request','body','expected_catalog_generation'],'99'),('ordinal',['merge_transfer',1,'ordinal'],'9'),('context-owner',['undo_request','context','owner_generation'],'99'),('mapping-child',['mutation','mapping',1,'target_id'],'existing'),('candidate',['mutation','candidate_digest'],'e'*64),('import-target',['import_request','body','store_identity','file_id'],'wrong-file'),('formal-proof',['merge_transfer',1,'body','external_proof','kind'],'FormalFile'),('proof-issuer',['merge_transfer',1,'body','external_proof','issuer'],'IO'),('stale-provider',['undo_publish',1,'body','expected_epoch'],'1'),('wrong-type',['import_request','body','bundle','entries'],{}),('unknown-field',['merge_publish',0,'body','unknown'],True),('reuse-import-pin',['undo_mutation','pin_id'],catalog['held_pin']['pin_id']),('reuse-import-context',['undo_request','context'],catalog['held_pin']['context'])]
for name,path,value in changes:
    x=copy.deepcopy(base);setpath(x,path,value);run('new-'+name,x,'ProofMismatch',path=path)
x=copy.deepcopy(base);del x['merge_transfer'][0]['body']['pin_id'];run('new-missing-pin',x,'ProofMismatch')
x=copy.deepcopy(base);del x['undo_mutation'];run('new-missing-top',x,'InvalidInput')
# Defensive consistency probes of trusted fixture premise, not caller forgery claims.
for name,path,value in [('import-record-target',['import_record','target_identity'],{'wrong':'target'}),('import-record-kind',['import_record','result'],'Released'),('import-record-source',['import_record','source_receipt_ids'],[]),('import-record-generation',['import_record','committed_generation'],'0'),('transfer-record-issuer',['transfer_records',0,'issuer'],'UI'),('transfer-record-proof-target',['transfer_records',0,'external_proof','target_identity'],{'wrong':'target'}),('transfer-record-proof-issuer',['transfer_records',0,'external_proof','issuer'],'IO'),('transfer-record-receipt',['transfer_records',0,'receipt_id'],'not-a-receipt'),('transfer-record-generation',['transfer_records',0,'committed_generation'],'0')]:
    c=copy.deepcopy(catalog);setpath(c,path,value);run('defensive-'+name,base,'ProofMismatch',cat=c,path=path)
write('new-fixtures-and-results.json',probes)
seal=read(S/'seal.json'); sealed={n:sha(S/n)==h for n,h in seal['files'].items()}
inputs=read(S/'inputs.json'); input_results={n:{'expected':h,'actual':sha(R/n),'match':sha(R/n)==h} for n,h in inputs.items()}
inventory=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
source_drift=[n for n,h in inventory['source_hashes'].items() if not (R/n).is_file() or sha(R/n)!=h]
central=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M06/planning/cx-exchange-revision-v3/shared-contract.json')
roles=[v['properties']['role']['enum'][0] for v in central['request_hash_schema']['oneOf']]
checks={'sealed_handoff':all(sealed.values()),'schema_exact':read(S/'transition-request.schema.json')==central['request_hash_schema'],'no_merge_role':not any('merge' in v.lower() for v in roles),'inventory_796':len(inventory['source_hashes'])==796,'source_unchanged':not source_drift,'owner_choices_pending':all(v['status']=='PROPOSED_PENDING_OWNER' for v in read(S/'owner-choices.json'))}
write('trace.json',{'sealed':sealed,'inputs':input_results,'source_inventory_head':inventory['head'],'actual_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'source_count':len(inventory['source_hashes']),'source_drift':source_drift,'central_roles':roles,'checks':checks,'management_diff':subprocess.check_output(['git','diff','--numstat','--','docs/board.json','docs/requirements-confirmation/phase1-spec/tasks/M06/planning/current-state.json'],cwd=R,text=True),'historical_runs':'15+416 and preflight64 NOT RERUN'})
board=read(R/'docs/board.json');stack=[board];cards=[]
while stack:
    v=stack.pop()
    if isinstance(v,dict):
        if v.get('id')=='PD-P1-M06-PREP-01': cards.append(v)
        stack.extend(v.values())
    elif isinstance(v,list): stack.extend(v)
write('board-readonly.json',{'current_cards':cards,'sealed_input_hash':inputs['docs/board.json'],'current_hash':sha(R/'docs/board.json'),'interpretation':'Board input hash changed since handoff capture. Management-only context separately recorded, not source inventory drift or product evidence. No board writes by reviewer.'})
findings=[{'id':'MR-F1','severity':'DOCUMENTARY_COVERAGE_LIMITATION','scope':'Trusted issuer fixture internal consistency; not a caller-controlled exploit and not a demonstrated violation of its trusted fixture premise','contract_pointers':['merge-retention-handoff/index.html:17 exact full request/context/issuer/target/digest lineage','merge-retention-handoff/precise-mapping.json issuer_record_fields says represented, not all dynamically validated','merge-retention-handoff/model.py evaluate import-record matched predicate and transfer-record predicate','merge-retention-handoff/immutable-issuer-fixture.json premises trusted immutable issuer lookup'], 'description':'The actual DOCUMENT oracle does not consume all central proof registry fields. Mutated import record target/result/source_receipt_ids/committed_generation and transfer record issuer/receipt_id/committed_generation/external_proof issuer/target remain admitted as MergeApplied. Frozen request equality is strong caller input closure but does not establish full issuer-record consistency.','counterexamples':[v['id'] for v in probes if not v['passed']],'required_action':'Keep full-field public request validation distinct from assumed trusted-record validity. If stronger defensive record consistency is required, authorize a correction packet, add these checks, reseal and independently re-review. No production change or architecture approval implied.'}]
review={'reviewer':'/root/m06_merge_retention_review','author':'/root/m06_merge_retention_handoff','verdict':'FINDINGS_DOCUMENT_ORACLE_PENDING_OWNER','passed':sum(v['passed'] for v in probes),'total':len(probes),'static_checks':checks,'findings':findings,'boundaries':'One handoff review only; no module PASS, no Owner approval, no native capability proof. MH1..MH6 including separate Undo Held producer stay pending. Trusted issuer lookup and atomic M04 commit/catalog CAS are premises.','not_run':['native','build','product tests','valid RED','full Draft','historical preflight64','author 15+416'],'next_action':'Resolve MR-F1 within a separately authorized correction packet; then independent re-review and Owner MH1..MH6 decision before implementation.'}
write('review.json',review)
body='<h1>M06 Merge / Retention independent document review</h1><p>FINDINGS — document oracle only; pending Owner. No module PASS.</p><p>Developer /root/m06_merge_retention_handoff; independent reviewer /root/m06_merge_retention_review.</p><p>New probes: '+str(review['passed'])+'/'+str(review['total'])+' met expected guard behavior. Nine defensive trusted-record consistency counterexamples remain accepted.</p><h2>Finding MR-F1</h2><p>'+html.escape(findings[0]['description'])+'</p><h2>Verified behavior</h2><p>One Merge commit; deferred roots keep actual revision/history without rollback. Unknown commit makes no unchanged claim, retry or release. Precommit failure preserves full state. Undo uses a separate workflow and Undo Held premise; Import Held is not implicitly reused. Fresh ID map, candidate digest, context, target and caller proof mutations reject before mutation.</p><h2>Authority and limits</h2><p>796 source inventory authority is M01 s2-green/source-current.json at historical 31babe; actual HEAD 5b709343a890503ebbe24a802e43cda5647df124. Input hashes and board management drift are recorded separately. Historical 64 and author 15+416 were not rerun. Closed central roles contain no Merge role. MH1..MH6 pending; trusted issuer and atomicity are fixture premises. Native/build/product/valid RED/full Draft NOT RUN.</p><h2>Next action</h2><p>'+html.escape(review['next_action'])+'</p><script type="application/json" id="review">'+json.dumps(review).replace('<','\\u003c')+'</script><h2>Review data</h2><pre>'+html.escape(json.dumps(review,indent=2))+'</pre>'
(P/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M06 independent review</title><style>body{max-width:1100px;margin:40px auto;font:16px system-ui;background:#111827;color:#e5e7eb}pre{white-space:pre-wrap}h1,h2{color:#fbbf24}</style>'+body,encoding='utf-8')
write('seal.json',{'scope':'new bounded independent document review','files':{p.name:sha(p) for p in P.iterdir() if p.is_file() and p.name!='seal.json'}})
print(json.dumps({'passed':review['passed'],'total':review['total'],'checks':checks,'counterexamples':findings[0]['counterexamples']}))
