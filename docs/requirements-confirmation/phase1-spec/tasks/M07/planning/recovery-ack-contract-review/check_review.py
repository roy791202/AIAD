"""Independent bounded DOCUMENT probes. Never invoke proposal main or edit its files."""
from pathlib import Path
import copy, hashlib, html, importlib.util, json, subprocess, sys, uuid
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
ROOT=P.parents[6]
S=P.parent/'recovery-ack-contract-proposal'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def main():
 spec=importlib.util.spec_from_file_location('reviewed_oracle',S/'check_documents.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 inputs={str(p.relative_to(ROOT)).replace('\\','/'):h(p) for p in S.iterdir() if p.is_file()}
 seal=read(S/'seal.json');assert all(h(S/n)==v for n,v in seal['sha256'].items())
 inventory_path=ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json'
 inv=read(inventory_path);assert len(inv['source_hashes'])==796
 assert all(h(ROOT/n)==v for n,v in inv['source_hashes'].items())
 pointers=read(S/'source-pointers.json');resolved=[]
 for p in pointers:
  path=ROOT/p['path'];assert h(path)==p['sha256'];v=read(path) if p['pointer'] else None
  for k in p['pointer'].strip('/').split('/') if p['pointer'] else []:v=v[int(k)] if isinstance(v,list) else v[k.replace('~1','/').replace('~0','~')]
  resolved.append(dict(**p,resolved_value=v));inputs[p['path']]=h(path)
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();assert head=='5b709343a890503ebbe24a802e43cda5647df124';assert inv['head']=='31babe87a7ef1e40a0d4bedc523077e7a45d63ab'
 board=ROOT/'docs/board.json';board_hash=h(board);board_review=read(P.parent/'publication-retention-review/review.json')
 f=read(S/'immutable-proof.json');q=read(S/'request-example.json');response=read(S/'response-example.json')
 base=dict(request=q,state=f['owner_state'],proof_available=True,root_state='Transferred')
 rows=[];fixtures=[]
 def probe(name,x,proof,expected):
  before=copy.deepcopy(x);out=None;error=None
  try:out=m.evaluate(copy.deepcopy(x),copy.deepcopy(proof))
  except Exception as e:error=type(e).__name__+': '+str(e)
  observed=out['result'] if out else 'EXCEPTION'
  safe=out is None or (out['state']['formal_baseline']==x['state']['formal_baseline'] and out['state']['live_revision']==x['state']['live_revision'] and out['calls']['retry']==out['calls']['release']==0)
  if out and observed!='CapturedRecoveryAcknowledged':safe=safe and out['state']==x['state'] and out['calls']['ack']==0
  rows.append(dict(id=name,expected=expected,observed=observed,pass_document=observed==expected and safe,error=error,input_unchanged=x==before,full_result=out))
  fixtures.append(dict(id=name,input=x,issuer_fixture=proof,expected=expected))
  return out
 probe('IR-BASE-FULL',copy.deepcopy(base),f,'CapturedRecoveryAcknowledged')
 # Independently enumerated admission mutations, not author 20/6/2 execution.
 for k in q:
  x=copy.deepcopy(base);del x['request'][k];probe('IR-MISSING-'+k,x,f,'Rejected')
 for k,value in [('protocol','unknown'),('issuer','M07'),('role','ack'),('ordinal','1'),('body',None),('context',None)]:
  x=copy.deepcopy(base);x['request'][k]=value;probe('IR-MALFORMED-'+k,x,f,'Rejected')
 x=copy.deepcopy(base);x['request']['unexpected']=True;probe('IR-UNKNOWN-KEY',x,f,'Rejected')
 for k in q['context']:
  x=copy.deepcopy(base);x['request']['context'][k]='11' if k in ('owner_generation','captured_revision') else '00000000-0000-4000-8000-000000000099';probe('IR-CONTEXT-'+k,x,f,'Rejected')
 for k in q['body']:
  x=copy.deepcopy(base);v=x['request']['body'][k]
  if isinstance(v,str):x['request']['body'][k]='f'*64 if 'digest' in k else ('00000000-0000-4000-8000-000000000099' if k.endswith('_id') else 'other-handle')
  elif isinstance(v,list):v[0]['size_bytes']='8'
  elif k=='captured_recovery_fingerprint':v['lowerhex64']='f'*64
  elif k=='index_target_identity':v['file_id']='other-index'
  else:v['receipt_id']='00000000-0000-4000-8000-000000000099'
  probe('IR-BODY-'+k,x,f,'Rejected')
 for k in ('project_uuid','document_uuid','session_id','owner_generation'):
  x=copy.deepcopy(base);x['state'][k]='other';probe('IR-OWNER-'+k,x,f,'Rejected')
 for root,expected in [('Deferred','Deferred'),('Unknown','UnverifiedOutcome')]:
  x=copy.deepcopy(base);x['root_state']=root;probe('IR-ROOT-'+root,x,f,expected)
 x=copy.deepcopy(base);x['proof_available']=False;probe('IR-RESTART-PROOF-LOSS',x,f,'UnverifiedOutcome')
 x=copy.deepcopy(base);x['state']['live_revision']='11';probe('IR-LIVE-NEWER',x,f,'CapturedRecoveryAcknowledged')
 x=copy.deepcopy(base);x['state']['recovery_baseline']={'revision':'11','fingerprint':{'profile':'SGA-RECOVERY-FP-v1','lowerhex64':'f'*64}};probe('IR-OLDER-LATE',x,f,'Superseded')
 # Mutate full issuer records while preserving references where needed: commitment is not authenticity.
 for section,keys in [('transfer',['issuer','role','workflow_id','operation_id','ordinal','request_digest','context','pin_id','source_receipt_ids','asset_pairs','root_manifest_ids','expected_generation','committed_generation','store_identity','target_identity','external_proof']),('held',['issuer','purpose','state','context','assets','pin_id']),('index',['proof','evidence']),('capture',['context','fingerprint','materials','capture_handle'])]:
  for k in keys:
   mutant=copy.deepcopy(f);v=mutant[section][k]
   if isinstance(v,str):mutant[section][k]='999' if 'generation' in k else 'invalid'
   elif isinstance(v,list):mutant[section][k]=[]
   else:mutant[section][k]={}
   probe('IR-ISSUER-'+section+'-'+k,copy.deepcopy(base),mutant,'Rejected')
 # Schema conformance is deliberately separated from request/response relational truth.
 relation=[]
 assert digest(q)==response['request_digest'];assert str(uuid.uuid5(uuid.UUID(q['context']['workflow_id']),'ack-recovery/0'))==response['operation_id']
 for k in ('operation_id','request_digest','capture_context','attempt_id','snapshot_id','acknowledged_fingerprint','live_revision'):
  r=copy.deepcopy(response)
  if k=='capture_context':r[k]['workflow_id']='00000000-0000-4000-8000-000000000099'
  elif k=='acknowledged_fingerprint':r[k]['lowerhex64']='f'*64
  elif k=='request_digest':r[k]='f'*64
  elif k=='live_revision':r[k]='999'
  else:r[k]='00000000-0000-4000-8000-000000000099'
  relation.append(dict(field=k,request=q,response=r,accepted_by_actual_response_schema=m.valid(r,read(S/'response.schema.json')),relationally_wrong=True))
 assert all(r['accepted_by_actual_response_schema'] for r in relation)
 # Sequential calls expose absence of retained replay state; no invented wrapper is counted as target evidence.
 first=m.evaluate(copy.deepcopy(base),copy.deepcopy(f));again=copy.deepcopy(base);again['state']=first['state'];second=m.evaluate(again,copy.deepcopy(f))
 changed=copy.deepcopy(again);changed['request']['body']['snapshot_id']='00000000-0000-4000-8000-000000000099';changed_result=m.evaluate(changed,copy.deepcopy(f))
 replay=dict(first_input=base,first_result=first,second_input=again,second_result=second,changed_input=changed,changed_result=changed_result,retained_store_parameter=False)
 findings=[dict(id='RA-R1',priority='P2',title='Admission accesses body/context before validation',counterexamples=['IR-MISSING-context','IR-MISSING-body'],impact='Missing body/context raises KeyError rather than deterministic Rejected. Move admission validation before field access in a future corrected packet; current originals remain sealed.')]
 limits=[dict(id='RA-L1',title='Ordinal/hash specification consistency needs clarification',counterexample='IR-MALFORMED-ordinal: ordinal 1 is admitted and ACKs',source='/hash/operation_id in module-spec.json specifies UUIDv5(workflow_id, UTF8 ack-recovery/0), while request.schema.json admits any u64 ordinal.',classification='Potential ambiguity, not proven behavior defect: fixed operation0 could intentionally coexist with admitted ordinal1; Owner/author must state intended relation. No reviewer architecture decision.'),dict(id='RA-L2',title='Response and replay evidence are narrower than proposed lifecycle',counterexample='7 relationally wrong responses pass shape schema; evaluate repeated request ACKs again and changed body returns Rejected.',classification='Proof limit, not native implementation defect: response schema is shape-only; replay dictionary proves hash difference and retained-value equality, no stateful replay transition. Retained store/provider remain pending Owner.'),dict(id='RA-L3',title='Malformed issuer record outside trusted fixture premise',counterexample='IR-ISSUER-index-evidence: replacing evidence with {} raises KeyError.',classification='Robustness limit only, not admitted caller request defect. Authentic immutable issuer structure is assumed, never authenticated by this fixture.')]

 assert first['calls']['ack']==second['calls']['ack']==1 and changed_result['result']=='Rejected'
 assert all(h(ROOT/n)==v for n,v in inputs.items());assert h(board)==board_hash
 review=dict(reviewer='/root/m07_recovery_ack_review',author='/root/m07_recovery_ack_packet',verdict='FINDINGS_DOCUMENT_ORACLE_COVERAGE',head=head,inventory_head=inv['head'],inventory_files=796,source_pointer_checks=len(resolved),proposal_seal_entries=len(seal['sha256']),document_probes=len(rows),passed=sum(r['pass_document'] for r in rows),failed=sum(not r['pass_document'] for r in rows),response_relation_counterexamples=len(relation),replay_sequences=1,findings=findings,proof_limits=limits,board_management=dict(actual=board_hash,prior_review_actual=board_review['board_management_hash']['actual'],classification='management diff separate from 796 source authority; no mutation'),premises=['Full equality and body hashes are consumed for capture/index/transfer records; this is not label-only classification.','Issuer tuple is compared against a single trusted immutable fixture, not authenticated provider lookup. Authenticity remains premise; forged self-consistent fixture is not runtime authorization.','protocol/role/schema/hash Owner options remain proposed; effective formal ACK and accepted S1 untouched.','PH-G2..4 remain open; PH-G1 candidate not adopted.'],not_run=['native','build','product tests','valid RED/GREEN','full Draft2020-12','module acceptance'],module_pass=False,next_action='Author creates a new correction packet for RA-R1 and clarifies RA-L1..3 evidence limits; independent review of corrected evidence, then Owner selects protocol/role/hash and confirms contracts. Preserve Yellow; no API/Skeleton implementation approval.')
 write('fixtures.json',fixtures);write('trace.json',rows);write('response-binding.json',relation);write('replay.json',replay);write('source-pointers-resolved.json',resolved);write('input-hashes.json',inputs);write('review.json',review)
 page='<!doctype html><html lang="en"><meta charset="utf-8"><title>M07 recovery ACK independent document review</title><style>body{max-width:1100px;margin:40px auto;font:16px system-ui;background:#101820;color:#edf3f8}pre{white-space:pre-wrap;background:#192832;padding:20px}a{color:#8cd9ff}</style><h1>M07 recovery ACK: independent document review</h1><p>1 P2 admission finding; 3 bounded proof/specification limits. No module PASS. Owner decisions remain pending.</p><p>Review only; full state, calls and results below. No product, original packet, board or current-state edits.</p>'
 for title,data in [('Review and limits',review),('Full probe state and calls',rows),('Response relation counterexamples',relation),('Replay sequence',replay),('Resolved original source pointers',resolved)]:page+='<h2>'+title+'</h2><pre>'+html.escape(json.dumps(data,ensure_ascii=False,indent=2))+'</pre>'
 page+='<script type="application/json" id="module-spec">'+json.dumps(review,ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
 (P/'index.html').write_text(page,encoding='utf-8')
 files={p.name:h(p) for p in P.iterdir() if p.is_file() and p.name!='seal.json'}
 write('seal.json',dict(status='SEALED_BOUNDED_INDEPENDENT_DOCUMENT_REVIEW_FINDINGS',files=len(files),sha256=files,counts={k:review[k] for k in ('document_probes','passed','failed','response_relation_counterexamples','replay_sequences','source_pointer_checks','inventory_files')},next_action=review['next_action'],module_pass=False))
 print(json.dumps({k:v for k,v in review.items() if k not in ('findings','premises')},ensure_ascii=False))
if __name__=='__main__':main()
