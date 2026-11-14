"""Independent bounded document review; python -B; writes only this review directory."""
from pathlib import Path
import copy, hashlib, html, importlib.util, json, subprocess
P=Path(__file__).resolve().parent
R=next(p for p in P.parents if (p/'AGENTS.md').exists())
C=P.parent/'save-response-handoff'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v): (P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
spec=importlib.util.spec_from_file_location('candidate',C/'model.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
base=read(C/'fixtures.json')[0]; rows=[]
def probe(name,changes,outcome,ack,root):
 f=copy.deepcopy(base);f.update(changes);r=mod.evaluate(f)
 assert (r['outcome'],r['ack_calls'],r['root_calls'])==(outcome,ack,root),(name,r)
 assert r['snapshot']==f['snapshot'] and r['live_revision']==f['live_revision'] and r['retained'] and not r['unchanged_claim']
 if outcome!='Saved': assert (r['formal_revision'],r['formal_semantic'])==(f['formal_revision'],f['formal_semantic'])
 else: assert r['formal_semantic']==f['semantic'] and r['formal_semantic']!=f['raw']
 rows.append({'id':name,'changes':changes,'expected':outcome,'observed':r,'status':'PASS_DOCUMENT_PROPOSITION'})
# Independent combinations, not the author's eleven-row rerun.
for field in ['receipt_target','receipt_previous','receipt_raw']:
 for root_state in ['verified','deferred']:
  probe(field+'-'+root_state,{field:'KNOWN-MISMATCH','root':root_state},'UnverifiedOutcome',0,0)
probe('missing-transaction-plus-replaced-owner',{'transaction':'','owner_current':False},'UnverifiedOutcome',0,0)
for state in ['deferred','failed','uncertain']:
 probe('root-'+state+'-newer-formal',{'root':state,'formal_revision':12,'formal_semantic':'sem12'},'CommittedAckDeferred:RootTransfer',0,1)
probe('root-capture-mismatch-newer-live',{'root_capture':'other','live_revision':20},'CommittedAckDeferred:RootTransfer',0,1)
probe('owner-replaced-root-deferred',{'owner_current':False,'root':'deferred'},'CommittedAckDeferred:OwnerChanged',0,0)
probe('equal-formal-revision-conflicting-semantic',{'formal_revision':10,'formal_semantic':'other'},'CommittedAckDeferred:SemanticAck',1,1)
probe('equal-formal-idempotent-semantic',{'formal_revision':10,'formal_semantic':'sem10'},'Saved',1,1)
probe('live-newer-same-semantic',{'live_revision':15,'live_semantic':'sem10'},'Saved',1,1)
assert rows[-1]['observed']['dirty'] is False
probe('late-ack-many-revisions',{'formal_revision':25,'formal_semantic':'sem25','live_revision':30},'CommittedAckDeferred:SemanticAck',1,1)
for err in ['Busy','Conflict','InvalidPath','Storage:PrepareNew','Storage:Publish','Storage:Restore','RecoveryRequired']:
 probe('io-'+err,{'io_error':err,'root':'deferred'},'SaveRejected' if err=='Busy' else 'UnverifiedOutcome',0,0)
# Probe trust boundary explicitly: the oracle is not a typed input validator.
trust=[]
for name,changes in [('truthy-transaction',{'transaction':7}),('truthy-owner',{'owner_current':'false'}),('invalid-root-enum',{'root':'invalid-enum'}),('falsey-io-error',{'io_error':False})]:
 f=copy.deepcopy(base);f.update(changes);trust.append({'id':name,'changes':changes,'observed':mod.evaluate(f),'classification':'OUTSIDE_TRUSTED_SYMBOLIC_FIXTURE_DOMAIN; no typed validation claim'})
authority=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
drift=[n for n,h in authority['source_hashes'].items() if digest(R/n)!=h];assert len(authority['source_hashes'])==796 and not drift
input_drift=[x['path'] for x in read(C/'inputs.json') if digest(R/x['path'])!=x['sha256']]
candidate_drift=[n for n,h in read(C/'artifact-hashes.json').items() if digest(C/n)!=h]
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
assert head=='5b709343a890503ebbe24a802e43cda5647df124' and not input_drift and not candidate_drift
cx=read(P.parent/'cx-revision-v3/module-spec.json');ptr='/effective_spec/architecture/transaction';cur=cx
for k in ptr.strip('/').split('/'): cur=cur[k]
assert 'Save: capture' in cur
review={'id':'M04-SAVE-RESPONSE-INDEPENDENT-REVIEW','verdict':'PASS_DOCUMENT_ONLY_PENDING_OWNER','author':'/root/m04_save_response_gap_packet','reviewer':'/root/m04_save_handoff_review','parent':'PD-P1-M04-PREP-01 remains Yellow; G1-G4 pending','new_independent_probes':len(rows),'trust_boundary_probes':len(trust),'original_11_plus_1_rerun':False,'findings':[],
 'source_context':{'exact_pointer':'cx-revision-v3/module-spec.json#'+ptr,'value':cur,'interpretation':'Receipt→ACK shorthand omits exact save-response/root-result mapping; read with existing common material-retention rules. This is a new pending precision proposal, not proof approved architecture orders unsafe ACK or an approved SPEC_CONFLICT.','receipt_source':'apps/sgenaxis-desktop/crates/sgenaxis-ports/src/file_commit.rs:22-27; four exact fields','ack_source':'apps/sgenaxis-desktop/crates/sgenaxis-work/src/document_edit.rs:282 and :354; semantic ACK distinct from raw digest'},
 'limits':['Capture and root_capture are trusted symbolic propositions, not full issuer-bound tuple verification. M03 17-field capture mapping remains G1/G2 pending.','retained=true is a model proposition. Existing Held evidence must survive root failure; model has no Held input/state and pin_state=Unverified is verification status, not authority to demote an existing Held root. Native Held preservation remains pending.','Unknown/deferred root cannot ACK. Known receipt mismatch cannot call root or ACK and must not claim unchanged bytes.','Owner replacement suppresses delivery in symbolic model; IO errors never ACK. Exact original IO fields and public response envelope require G1/G3; model collapses errors conservatively, not an exhaustive typed wire encoder.','Truthy malformed transaction/owner and falsey IO values pass some model branches; invalid root conservatively defers. Inputs are declared trusted fixtures; no parser/schema/type security is proved. Do not promote model to runtime validator.','S1 also rejects future revision, equal-live conflicting semantic, invalid digest and noneditable state. Oracle does not implement all S1 validation; trusted capture premise and future native tests remain required.','M04 sole DocumentOwner; M03 facade; no second registry/private journal/new native provider or Port adoption.'],
 'checkout':{'head':head,'authority_head':authority['head'],'authority_count':796,'product_drift':drift,'input_drift':input_drift,'candidate_manifest_drift':candidate_drift,'management_drift':'board changes are separate from 796-file source authority; no source baseline rewritten'},
 'not_run':['product/native UI/IPC','build/package/install','valid RED/GREEN','full Draft 2020-12 validation','runtime issuer authenticity/Held isolation'],
 'next_action':'Owners G1-G4 decide exact capture/response/root/ACK mappings, retain original common rules, then approve Skeleton and obtain valid RED; no product implementation authorized.'}
write('fixtures.json',{'independent_probes':rows,'trust_boundary_observations':trust})
write('review.json',review)
trace=[{'probe':r['id'],'contract':'four-field receipt → root result → captured semantic ACK; no baseline rollback','result':r['status']} for r in rows]
write('trace.json',trace)
body='<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>M04 independent save response review</title><style>body{max-width:1100px;margin:32px auto;font:16px system-ui;background:#101923;color:#eee}pre{white-space:pre-wrap;background:#203040;padding:16px}h1,h2{color:#ffdc81}</style><h1>M04 保存回應：獨立文件審查</h1><p>PASS_DOCUMENT_ONLY_PENDING_OWNER · Yellow · G1-G4 pending · NOT_READY_FOR_IMPLEMENTATION</p>'
for title,data in [('Review and boundaries',review),('New independent witnesses',rows),('Trust premise probes',trust),('Traceability',trace)]: body+='<h2>'+title+'</h2><pre>'+html.escape(json.dumps(data,ensure_ascii=False,indent=2))+'</pre>'
body+='<script type="application/json" id="module-spec">'+json.dumps(review,ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
(P/'index.html').write_text(body,encoding='utf-8')
write('verification.json',{'status':'PASS_BOUNDED_DOCUMENT_REVIEW','new_probes':len(rows),'trust_probes':len(trust),'source_count':796,'source_drift':drift,'input_drift':input_drift,'candidate_drift':candidate_drift,'command':'python -B '+str(P.relative_to(R)/'check_review.py')})
write('seal.json',{'scope':'Only new save-response-review artifacts; excludes seal self','files':{p.name:digest(p) for p in sorted(P.iterdir()) if p.is_file() and p.name!='seal.json'},'next':review['next_action']})
print(json.dumps({'verdict':review['verdict'],'new_probes':len(rows),'trust_probes':len(trust),'source_count':796,'source_drift':len(drift),'input_drift':len(input_drift),'candidate_drift':len(candidate_drift)}))
