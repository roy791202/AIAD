"""Author document self-check only. No product acceptance."""
import copy,json,pathlib,hashlib,subprocess,sys,html,difflib
from document_model import *
P=pathlib.Path(__file__).resolve().parent
S=P.with_name('binding-transfer-integration')
def save(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run([sys.executable,str(P/'checker.py')],check=True,stdout=subprocess.DEVNULL)
rows=[]
BAD=[None,False,True,0,1,1.0,'','ready','timeout','COMMIT',{},[]]
def run(label,slot,key,value,expected,missing=False):
 s=fresh();r=dict(binding_ref=UUID,expected_generation='7',expected_revision='9',target_window='ui-editor');o=observation(s)
 c=('main','source-1','tauri://localhost',True);args=dict(provider=True,outcome='commit')
 if slot=='args':
  if missing:del args[key]
  else:args[key]=value
 elif slot=='observation':
  if missing:del o[key]
  else:o[key]=value
 elif slot=='state':s[key]=value
 elif slot=='state-root':s=value
 elif slot=='observation-root':o=value
 elif slot=='request':r=value
 elif slot=='request-field':r[key]=value
 elif slot=='caller':c=value
 a=Authority();token=a.mint(o);before=copy.deepcopy(s);reads=[]
 original_read=a.read
 def counted_read(token):reads.append('authority.read');return original_read(token)
 a.read=counted_read
 result=transfer(s,r,c,a,token,**args)
 assert result==expected,(label,result,expected)
 if label.startswith(('provider-','outcome-malformed','outcome-missing','exact-provider')):assert not reads,label
 if label.startswith('enum-positive-'):assert len(reads)==1,label
 committed=expected in ('Transferred','TransferredAckDeferred')
 calls=s['transfers']-before['transfers'] if type(s)is dict and type(s.get('transfers')) is int and type(before.get('transfers')) is int else 0
 assert calls==int(committed),label
 if not committed:assert s==before,label
 if type(s)is dict and 'document'in s:assert s['document']==before['document'] and s['forbidden_calls']==before['forbidden_calls']
 decision_observed=label.startswith('enum-positive-')
 rows.append(dict(id=label,result=result,before=before,after=s,commit_calls=calls,authority_read_calls=len(reads),transaction_outcome_observed=int(decision_observed),native_transaction_calls='NOT RUN; no native provider implemented',authorizing_receipt=False,model_nochange=not committed,native_unchanged_claim=False))
for outcome,result in [('commit','Transferred'),('ack-lost','TransferredAckDeferred'),('rollback','IoFailure'),('unknown','Indeterminate')]:run('enum-positive-'+outcome,'args','outcome',outcome,result)
for key in ('provider','outcome'):
 for i,v in enumerate(BAD):
  if key=='provider' and type(v)is bool:continue
  run(key+'-malformed-'+str(i),'args',key,v,'DependencyNotReady' if key=='provider' else 'Indeterminate')
 run(key+'-missing','args',key,None,'DependencyNotReady' if key=='provider' else 'Indeterminate',True)
run('exact-provider-false','args','provider',False,'DependencyNotReady')
for key,original in observation(fresh()).items():
 for i,v in enumerate(BAD):
  if type(v)is type(original):continue
  run('authority-'+key+'-'+str(i),'observation',key,v,'ProofMismatch')
 run('authority-missing-'+key,'observation',key,None,'ProofMismatch',True)
bool_results=dict(source_live='StaleOwner',target_live='MissingBinding',target_ready='DependencyNotReady',target_consent='DependencyNotReady',target_revoked='MissingBinding',target_dirty='Busy',discard_confirmed='Transferred',unique_owner='IdentityConflict',target_unique='DependencyNotReady')
for key,result in bool_results.items():run('real-bool-'+key,'observation',key,not observation(fresh())[key],result)
for i,v in enumerate(BAD):
 if type(v)is not dict:
  run('state-root-'+str(i),'state-root',None,v,'ProofMismatch')
  run('observation-root-'+str(i),'observation-root',None,v,'ProofMismatch')
 if type(v)is not dict:run('request-root-'+str(i),'request',None,v,'InvalidRequest')
 if type(v)is not str:
  for key in ('binding_ref','expected_generation','expected_revision','target_window'):run('request-field-'+key+'-'+str(i),'request-field',key,v,'InvalidRequest')
for key in ('identity','generation','revision','writer','captured_target','source_active','target_active','capacity','transfers'):
 for i,v in enumerate(BAD):
  if type(v)is type(fresh()[key]):continue
  run('state-'+key+'-'+str(i),'state',key,v,'ProofMismatch')
for i,v in enumerate(BAD):
 if type(v)is not bool:run('caller-live-'+str(i),'caller',None,('main','source-1','tauri://localhost',v),'UnauthorizedCaller')
protected=['request.schema.json','response.schema.json','schema_subset.py','owner-choices.json','before-after.json','module-spec.json','module.feature','fixtures.json','traceability.json','steps.py','step-definition-stubs.json']
preserved={n:dict(original=sha(S/n),correction=sha(P/n),equal=sha(S/n)==sha(P/n))for n in protected}
assert all(v['equal']for v in preserved.values())
save('preserved-bytes.json',preserved);save('new-mutation-probes.json',rows)
diff=''.join(difflib.unified_diff((S/'document_model.py').read_text().splitlines(True),(P/'document_model.py').read_text().splitlines(True),fromfile='original/document_model.py',tofile='proposed/document_model.py'))
(P/'model.diff').write_text(diff,encoding='utf-8')
spec=dict(module='M03',task='PD-P1-M03-PREP-01',state='PROPOSED_PENDING_OWNER',author='/root/m03_transfer_typed_correction',finding='TR-R1',scope='document model exact guards only; no runtime skeleton',guard_choices=[dict(id='TR-COR-P1',status='PROPOSED',choice='Exact bool provider false/missing/malformed => DependencyNotReady before observation/commit'),dict(id='TR-COR-P2',status='PROPOSED',choice='Explicit exact enum only; missing/malformed => Indeterminate zero model commit, no authorizing receipt, no native unchanged claim; unknown unchanged existing semantics'),dict(id='TR-COR-P3',status='PROPOSED',choice='Malformed request => existing generic InvalidRequest; malformed trusted metadata => ProofMismatch; no rootType DTO adoption')],preserved='TR-P1..8, receiptOwnerchoice, schemas/error shapes and lexical guards byte identical',architecture='M04 sole authoritative owner; M03 projection only; existing original diagram retained',transaction='Only explicit commit/ack-lost reaches existing atomic model transition; no retry',pitfall_audit=['bool 0 versus False exact guard','target consent/discard/revoked/readiness typed','source native authority live bool typed','root/generation/revision/instance scalar metadata typed before equality','nonobject request uses existing closed schema subset','seven typed DomainRejected variants and U64 lexical checker reused unchanged'],native_uncertainty='zero model mutation is not native unchanged proof',acceptance='Author model checks only; independent acceptance and Owner pending')
save('correction-module-spec.json',spec)
save('correction-fixtures.json',dict(values=BAD,tests=[dict(id=x['id'],expected=x['result'])for x in rows],trusted_premise='Authority.mint only; not IPC or production observations'))
save('correction-traceability.json',[dict(requirement='TR-R1',bdd='TR-COR-1' if x['id'].startswith(('provider','outcome','enum','exact-provider')) else 'TR-COR-2',tdd=x['id'],result='PASS',evidence='new-mutation-probes.json#'+x['id'])for x in rows])
(P/'correction.feature').write_text('''Feature: Typed transfer observation seams (PROPOSED)
  Background:
    Given a valid source writer and trusted target consent
  Rule: Undeclared seam values cannot authorize transfer
    Scenario: TR-COR-1 Malformed provider or undeclared outcome
      Given a missing or incorrectly typed transfer observation
      When transfer is requested
      Then no transfer is committed by the document model
      And no authorizing receipt is issued
  Rule: Authority metadata must retain exact types
    Scenario: TR-COR-2 Malformed root or scalar authority metadata
      Given malformed source or target metadata
      When transfer is requested
      Then a typed diagnostic is returned
      And the document model remains unchanged
''',encoding='utf-8')
save('correction-step-stubs.json',dict(status='PENDING_AUTOMATION_NOT_NATIVE_PROOF',steps=['Given valid native source and consent: native provider adapter fixture pending','Given malformed seam: correction-fixtures.json','When transfer requested: document_model.transfer only','Then zero model commit: new-mutation-probes commit_calls','Then native outcome: NOT RUN'],unknown_semantics='Explicit unknown is a valid observed transaction outcome; Indeterminate with no native unchanged assertion. It is distinct from invalid timeout/missing guard (zero authority reads).'))
save('source-current-observation.json',dict(authority='M01/planning/s2-green/source-current.json',current_796='all hash comparisons in source-comparison.json',current_HEAD=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),current_branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),historical_HEAD='5b709343a890503ebbe24a802e43cda5647df124',historical_evidence='original transfer/review records; not current source proof'))
ver=dict(status='AUTHOR_DOCUMENT_CORRECTION_CHECKS_PASS_PENDING_INDEPENDENT_REVIEW',author=spec['author'],new_model_cases=len(rows),baseline='original full model/schema/lexical/796 source checks pass',FullDraft='NOT RUN',product_native_RED='NOT RUN',product_tests='NOT RUN',build='NOT RUN',Owner='NOT RUN',independent_acceptance='NOT RUN',module_complete=False)
save('correction-verification.json',ver)
save('correction-lessons-pending.json',dict(lesson='Truthiness and fallthrough enums at trusted fixture seams can authorize commits despite schema-correct IPC; enumerate typed seam mutations beyond literal counterexamples.',pending=['Independent document reviewer','Owner exact guard/error choice adoption','Native provider contract and valid product RED','Full Draft validation; build/package/runtime acceptance']))
page=(P/'index.html').read_text(encoding='utf-8')
marker='<!--CORRECTION-->'
if marker in page:page=page[:page.index(marker)]
page+=marker+'<section><h1>TR-R1 correction candidate — PROPOSED</h1><p>Author self-check only. Original transfer policy and diagrams below/above are preserved; no product or Owner acceptance. Use correction_checker.py for this candidate; inherited build_packet.py is historical source only.</p><pre>'+html.escape(json.dumps(spec,ensure_ascii=False,indent=2))+'</pre><pre>'+html.escape(json.dumps(ver,indent=2))+'</pre><p>Current source authority: M01 s2-green 796 paths rehashed by checker. HEAD 5b70934 in original evidence is historical, not source proof.</p><ul>'+''.join('<li><a href="'+n+'">'+n+'</a></li>'for n in ['correction-module-spec.json','new-mutation-probes.json','preserved-bytes.json','model.diff','correction-verification.json','correction-lessons-pending.json','correction_checker.py','correction.feature','correction-fixtures.json','correction-step-stubs.json','correction-traceability.json','source-current-observation.json'])+'</ul></section><script type="application/json" id="correction-module-spec">'+json.dumps(spec,ensure_ascii=False).replace('</','<\\/')+'</script>'
(P/'index.html').write_text(page,encoding='utf-8')
save('artifact-hashes.json',{f.name:sha(f)for f in P.iterdir()if f.is_file()and f.name!='artifact-hashes.json'})
print(json.dumps(ver))
