"""Independent bounded DOCUMENT review. Run python -B; writes this directory only."""
import copy, hashlib, importlib.util, json, pathlib, subprocess
from types import MappingProxyType
P=pathlib.Path(__file__).resolve().parent
C=P.parent/'copy-ready-correction'
ROOT=P.parents[6]
def read(p): return json.loads(p.read_text(encoding='utf8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v): (P/n).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
s=importlib.util.spec_from_file_location('reviewed_oracle',C/'oracle.py'); o=importlib.util.module_from_spec(s);s.loader.exec_module(o)
# Frozen independently in this review directory BEFORE probe mutation. These are
# documented issuer premises, never newly issued authority or native evidence.
frozen=read(P/'frozen-issuer-premises.json')
assert frozen==read(C/'authority-fixtures.json')
o.AUTHORITY=MappingProxyType({k:json.dumps(v,sort_keys=True) for k,v in frozen.items()})
base=read(C/'fixtures.json')[0]['fixture']; probes=[]
def add(name,f,expected): probes.append(dict(id='NEW-%03d'%(len(probes)+1),name=name,fixture=f,expected=expected))
def reseal(f):
 f['request_digest']=o.digest(f['request'])
 f['issuer_records']['ready-1']['request_digest']=f['request_digest']
# Each actual body field is consumed against issuer-owned data, not merely hash.
for field,value in base['request']['body'].items():
 f=copy.deepcopy(base); f['request']['body'][field]=dict(value, file_id='different-file') if isinstance(value,dict) else value+'-different'
 if field=='new_project_uuid':f['request']['context']['project_uuid']=f['request']['body'][field]
 if field=='new_document_uuid':f['request']['context']['document_uuid']=f['request']['body'][field]
 reseal(f); add('semantic body binding '+field,f,'ProofMismatch')
# Whole-root guard probes, plus every schema object is audited below.
for field in base:
 f=copy.deepcopy(base);del f[field];add('missing root '+field,f,'RejectedBeforeMutation')
 f=copy.deepcopy(base);f[field]=None;add('wrong root type '+field,f,'RejectedBeforeMutation')
objects=[]; enums=[]
def walk(schema,path):
 if schema['type']=='object':
  assert schema['additionalProperties'] is False
  assert set(schema['required'])==set(schema['properties'])
  objects.append(path)
  for k,v in schema['properties'].items():walk(v,path+[k])
 if 'enum' in schema:enums.append(path)
schema=read(C/'candidate.schema.json');walk(schema,[])
def at(f,path):
 for k in path:f=f[k]
 return f
for path in objects:
 f=copy.deepcopy(base);at(f,path)['unexpected']=True;add('closed object '+'.'.join(path),f,'RejectedBeforeMutation')
 # One missing child at each object exercises validation BEFORE indexing.
 if at(f,path):
  f=copy.deepcopy(base);del at(f,path)[next(iter(at(f,path)))];add('missing nested '+'.'.join(path),f,'RejectedBeforeMutation')
for path in enums:
 f=copy.deepcopy(base);at(f,path[:-1])[path[-1]]='UNDECLARED';add('enum '+'.'.join(path),f,'RejectedBeforeMutation')
for field in base['request']['context']:
 f=copy.deepcopy(base);f['request']['context'][field]+='-other';reseal(f);add('context '+field,f,'RejectedBeforeMutation' if field in ['workflow_id','project_uuid','document_uuid'] else 'ProofMismatch')
for key in ['provider-1','catalog-1','copy-1','ready-1']:
 f=copy.deepcopy(base);f['issuer_records'][key]['context']['session_id']+='-echo';add('proof context '+key,f,'ProofMismatch')
# Coherent alternative uses existing separate frozen authority. No mapping is
# modified or issuer record minted to make an expected result pass.
alts=read(C/'targeted-fixtures.json')
for aid in ['coherent-B','unknown-CAS']:
 f=next(copy.deepcopy(x['fixture']) for x in alts+read(C/'fixtures.json') if x['fixture'].get('authority_fixture_id')==aid and not o.shape_errors(x['fixture'],schema))
 # choose the matching baseline by comparing complete issuer records
 candidates=[x['fixture'] for x in alts+read(C/'fixtures.json') if x['fixture'].get('authority_fixture_id')==aid and x['fixture']['issuer_records']==frozen[aid]['issuer_records']]
 f=copy.deepcopy(next(x for x in candidates if x['request_digest']==o.digest(x['request'])))
 add('independently frozen alternate '+aid,f,'VerifiedPublished' if aid=='coherent-B' else 'UncertainPublication')
for k,expected in [('owner_current','DeliveryDeferred'),('source_ack','CommittedAckDeferred')]:
 f=copy.deepcopy(base);f[k]=False;add(k,f,expected)
f=copy.deepcopy(base);f['authority_fixture_id']='absent-issuer';add('unavailable authority',f,'ProofMismatch')
save('new-fixtures.json',probes)
results=[]
groups=[('reused-original-eight',read(C/'fixtures.json')),('reused-exact-18',read(C/'closure-fixtures.json')),('new-independent',probes)]
old_review=read(P.parent/'copy-ready-review'/'review.json')
assert {x['id'] for x in groups[1][1]}=={x['id'] for x in old_review['counterexamples']}
assert len(groups[1][1])==18
legacy=read(P.parent/'copy-ready-handoff'/'fixtures.json')
assert [(x['id'],x['expected']) for x in groups[0][1]]==[(x['id'],x['expected']) for x in legacy]
migration=read(C/'representation-migration.json')
assert [(x['id'],x['expected_before'],x['expected_after']) for x in migration['cases']]==[(x['id'],x['expected'],x['expected']) for x in legacy]
save('schema-review.json',{'object_paths':objects,'enum_paths':enums,'all_objects_closed':True,'all_properties_required':True,'guard_before_access':'oracle.observe invokes shape_errors before any request/context/proof indexing','types':'exact Python types; bool is not accepted as string or vice versa; closed string enums','closure_ids_equal_original_counterexamples':True,'original_eight_expected_outputs_equal_legacy':True,'migration_before_after_outputs_equal':True,'migration_status':'PROPOSED_PENDING_OWNER; UTF8 text + issuer bindings changes are not current wire admission'})
for group,cases in groups:
 for case in cases:
  before=copy.deepcopy(case['fixture'])
  try: result=o.observe(case['fixture'])
  except Exception as e: result={'result':'EXCEPTION','exception':repr(e)}
  good=result['result']==case['expected'] and before==case['fixture'] and all(result.get('state_calls',{}).get(k)==0 for k in ['CAS','native_IO','model_mutation','retry','cleanup'])
  results.append(dict(group=group,id=case['id'],name=case['name'],expected=case['expected'],observed=result,input_unchanged=before==case['fixture'],pass_=good))
save('trace.json',results)
seal=read(C/'seal.json');source=read(C/'source-bindings.json');inventory=read(ROOT/source['authority_inventory'])
checks={}
checks['candidate_seal']={'count':len(seal['artifacts']),'mismatches':[n for n,h in seal['artifacts'].items() if sha(C/n)!=h]}
checks['source_bindings']={'count':len(source['source_hashes']),'mismatches':[n for n,h in source['source_hashes'].items() if sha(ROOT/n)!=h]}
checks['product_inventory']={'count':len(inventory['source_hashes']),'mismatches':[n for n,h in inventory['source_hashes'].items() if sha(ROOT/n)!=h]}
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
save('input-hashes.json',{str(p.relative_to(ROOT)):sha(p) for p in list(C.iterdir()) if p.is_file()})
report=dict(reviewer='/root/m01_copy_correction_review',author='/root/m01_copy_ready_correction',task='PD-P1-M01-PREP-01',verdict='PASS_DOCUMENT_REVIEW_PENDING_OWNER' if all(x['pass_'] for x in results) else 'FINDINGS_DOCUMENT_REVIEW_ONLY',head=head,required_head=source['head_required'],historical_inventory_head=source['historical_inventory_head'],checks=checks,counts={g:len(c) for g,c in groups},new_schema_objects_audited=len(objects),new_enum_probes=len(enums),failed=[x for x in results if not x['pass_']],owner_pending=['CR-D1','CR-D2','CR-D3'],schema_error_policy='PROPOSED_PENDING_OWNER',original_closed_publish='UNCHANGED; candidate not admitted',module_pass=False,ready_transitions_implemented=0,verification={k:'NOT RUN' for k in ['native','build','product','valid_RED','full_Draft']},limits=['Observational classification only: every probe CAS/native IO/model mutation/retry/cleanup is zero.','Frozen issuer premises independently snapshotted, not native authenticity, lease or durability proof.','Reused 8 outputs and exact 18 closure cases counted separately from new probes. Author 399 suite NOT rerun.','Coherent-B is a separate existing issuer fixture; no runtime or arbitrary issuer generality claim.'],next_action='Owner decides CR-D1..D3 and exact schema/error/representation migration; separately approve Skeleton and valid RED. Keep Yellow; no implementation dispatch.')
save('review.json',report)
save('management-diff.json',dict(board_binding=checks['source_bindings'],current_board_sha256=sha(ROOT/'docs/board.json'),candidate_board_sha256=source['source_hashes']['docs/board.json'],classification='Management evidence separate from 796 protected product inventory; no board writes by reviewer.',diff=subprocess.check_output(['git','diff','--','docs/board.json'],cwd=ROOT,text=True,encoding='utf8')))
html='<!doctype html><meta charset="utf-8"><title>M01 Independent Copy Ready Correction Review</title><style>body{font:16px system-ui;max-width:1050px;margin:40px auto;background:#111827;color:#e5e7eb}pre{white-space:pre-wrap}h1{color:#fbbf24}</style><h1>M01 — Independent document review</h1><p>One final-path QuarantinedCopy → Ready proposal. Yellow; pending Owner. No module PASS or transition implementation.</p><pre>'+json.dumps(report,indent=2,ensure_ascii=False).replace('&','&amp;').replace('<','&lt;')+'</pre><p><a href="trace.json">Full calls/results trace</a> · <a href="new-fixtures.json">New independent probes</a> · <a href="check.py">Reproducible checker</a></p><script type="application/json" id="module-spec">'+json.dumps(report,ensure_ascii=False).replace('</','<\/')+'</script>'
(P/'index.html').write_text(html,encoding='utf8')
save('seal.json',{'reviewer':report['reviewer'],'artifact_count':len([p for p in P.iterdir() if p.is_file() and p.name!='seal.json']),'artifacts':{p.name:sha(p) for p in sorted(P.iterdir()) if p.is_file() and p.name!='seal.json'},'seal_excludes_self':True})
print(json.dumps({k:report[k] for k in ['verdict','counts','failed','checks']},indent=2))

