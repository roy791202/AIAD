import pathlib,json,hashlib,re,copy,subprocess,datetime,html
R=pathlib.Path('D:/AIAD'); B=R/'docs/requirements-confirmation/phase1-spec/tasks'; C=B/'M02/planning/golden14-lock-inventory-20261103'; O=B/'M02/planning/golden14-lock-review-20261103'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
c=read(C/'candidate.json'); f=read(C/'fixtures.json'); p=read(C/'pending.json'); h=(C/'index.html').read_text(encoding='utf-8'); feature=(C/'module.feature').read_text(); steps=(C/'steps.py').read_text()
pre={x.name:sha(x) for x in C.iterdir() if x.is_file()}; board_before=sha(R/'docs/board.json')
base=read(B/'M02/planning/exact-design/module-spec.json')['first_template']['product_paths']; inv=read(B/'M01/planning/remaining-action-dispatch-20261103/template14-source-inventory.json')
# All cited sources read, digested, with JSON pointers resolved independently.
bindings=[]
def pointer(obj,ptr):
 if ptr in ('/','whole-file'):return obj
 for key in ptr.strip('/').split('/'):
  key=key.replace('~1','/').replace('~0','~');obj=obj[int(key)] if isinstance(obj,list) else obj[key]
 return obj
for ref in c['source_refs']:
 path=R/ref['path']; actual=sha(path); ptr=ref['pointer']; value=pointer(read(path),ptr) if ptr!='whole-file' else path.read_text(encoding='utf-8-sig')
 bindings.append(dict(ref,actual_sha256=actual,status='MATCH' if actual==ref['sha256'] else 'MANAGEMENT_SOURCE_DRIFT' if ref['path']=='docs/board.json' else 'FAIL',pointer_resolved=True))
rowbindings=[]
for i,row in enumerate(c['rows']):
 for ref in row['source_refs']:
  value=pointer(read(R/ref['path']),ref['pointer']); expected=base[i] if '/first_template/' in ref['pointer'] else inv['rows'][i]
  rowbindings.append({'slot':row['slot'],'ref':ref,'hash_match':sha(R/ref['path'])==ref['sha256'],'pointer_value_match':value==expected})
ss=read(B/'M01/planning/s2-green/source-current.json'); drift=[k for k,v in ss['source_hashes'].items() if not (R/k).is_file() or sha(R/k)!=v]
embedded=re.search(r'<script[^>]*id="module-spec"[^>]*>(.*?)</script>',h,re.S)
# Review-only semantic oracle. It does not render products or execute the candidate stubs.
def semantic(x):
 assert x['primary_module']=='M02' and x['state']=='BOUNDED_PLANNING_PACKET_ONLY'
 assert x['authority']=='Original planning scope only; no implementation authorization or decision adoption.'
 assert x['baseline']['product_paths']==base
 assert len(x['rows'])==14 and len({r['declared_product_path'] for r in x['rows']})==14
 assert [r['declared_product_path'] for r in x['rows']]==base
 assert 'not a claim of repository-wide nonexistence' in x['missing_interpretation']
 assert x['standalone_lock_oracle_candidate']['status']=='PROPOSED_NOT_ACCEPTED'
 assert x['standalone_lock_oracle_candidate']['workspace_lock_reuse']=='NOT ACCEPTABLE as standalone proof'
 for i,r in enumerate(x['rows']):
  assert r['proof_status']=='MISSING_ADMITTED_EVIDENCE' and r['expectation_status']=='CANDIDATE_REVIEW_OBLIGATION_NOT_NEW_CONTRACT'
  assert r['oracle']['status']=='PROPOSED_NOT_EXECUTED'
  for key in ('submitted_resource','golden','lock_provider_evidence'):
   assert r[key]['status']=='MISSING' and r[key]['provider']
  assert r['submitted_resource']['bytes'] is None and r['submitted_resource']['sha256'] is None
  assert all(r['golden'][k] is None for k in ('input_definition_revision','input_design_revision','expected_rendered_bytes','output_sha256'))
  assert all(r['lock_provider_evidence'][k] is None for k in ('manifest_digest','lock_digest','resolver_provenance'))
  assert len(r['source_refs'])==2
  for ref in r['source_refs']:
   assert sha(R/ref['path'])==ref['sha256']
   val=pointer(read(R/ref['path']),ref['pointer'])
   assert val==(base[i] if '/first_template/' in ref['pointer'] else inv['rows'][i])
 assert 'product tests' in x['not_run'] and 'native provider identity/atomicity' in x['not_run']
 return True
checks=[]
def ck(n,ok):checks.append({'id':n,'pass':bool(ok)})
ck('positive_candidate_semantics',semantic(c));ck('exact_six_files',set(pre)=={'candidate.json','fixtures.json','pending.json','index.html','module.feature','steps.py'})
ck('13_top_bindings_no_nonmanagement_drift',len(bindings)==13 and all(x['status']!='FAIL' for x in bindings));ck('28_row_hash_pointer_bindings',len(rowbindings)==28 and all(x['hash_match'] and x['pointer_value_match'] for x in rowbindings));ck('796_authority_no_product_drift',len(ss['source_hashes'])==796 and not drift)
ck('html_embedded_json_matches',embedded is not None and json.loads(embedded.group(1))==c)
ids=set(re.findall(r'Scenario: (M02-G14-\d+)',feature));ck('feature_fixture_stub_ids',len(ids)==4 and ids<={x['id'] for x in f['cases']} and all(x in steps for x in ids));ck('pending_stubs_explicit',steps.count('raise NotImplementedError')==4 and 'not executable product proof' in steps)
ck('fixture_no_invented_bytes',all(f['future_golden_fixture_composition'][k] is None for k in ('input_definition','input_design','canonical_resource_bytes','rendered_output_bytes')))
ck('pending_questions_and_scope',len(p['open_questions'])==3 and len(p['scope']['allowed_files'])==6 and all(x['state']=='PENDING' for x in p['automation']))
probes=[]
mutations=[('same_count_substituted_path',lambda x:x['rows'][0].update(declared_product_path='program/Cargo.toml')),('duplicate_path',lambda x:x['rows'][1].update(declared_product_path=base[0])),('source_hash_forgery',lambda x:x['rows'][0]['source_refs'][0].update(sha256='0'*64)),('source_pointer_substitution',lambda x:x['rows'][0]['source_refs'][0].update(pointer='/first_template/product_paths/1')),('resource_missing_with_fake_bytes',lambda x:x['rows'][0]['submitted_resource'].update(bytes='fabricated')),('golden_missing_with_fake_digest',lambda x:x['rows'][2]['golden'].update(output_sha256='f'*64)),('full_lock_false_provenance',lambda x:x['rows'][12]['lock_provider_evidence'].update(resolver_provenance='workspace copy')),('provider_omitted',lambda x:x['rows'][3]['golden'].update(provider='')),('oracle_promoted_executed',lambda x:x['rows'][1]['oracle'].update(status='PASS')),('candidate_promoted_adopted',lambda x:x['standalone_lock_oracle_candidate'].update(status='ADOPTED')),('whole_repo_absence_claim',lambda x:x.update(missing_interpretation='No resources exist anywhere in repository')),('implementation_authority_escalation',lambda x:x.update(authority='Implementation approved')),('native_notrun_removed',lambda x:x['not_run'].remove('native provider identity/atomicity'))]
for name,mut in mutations:
 x=copy.deepcopy(c);mut(x)
 try:semantic(x); rejected=False
 except (AssertionError,KeyError,IndexError,ValueError):rejected=True
 probes.append({'id':name,'expected':'REJECT','observed':'REJECT' if rejected else 'ACCEPT','pass':rejected,'layer':'FRESH_REVIEW_DOCUMENT_SEMANTIC_ORACLE_ONLY'})
commands=[]
for flag in ('--packet','--deliverables'):
 argv=['python','-B',str(B/'M01/planning/remaining-action-oracle-correction-20261103/check.py'),flag,'M02'];run=subprocess.run(argv,cwd=R,capture_output=True,text=True);commands.append({'argv':argv,'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr});ck(flag,run.returncode==0)
ck('candidate_unchanged',pre=={x.name:sha(x) for x in C.iterdir() if x.is_file()});ck('board_unchanged_by_review',board_before==sha(R/'docs/board.json'))
write('probes.json',probes)
result={'author':c['author'],'reviewer':'/root/m02_template_candidate_review','status':'PASS_DOCUMENT_PREPARATION_ONLY' if all(x['pass'] for x in checks+probes) else 'CHANGES_REQUIRED','timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate_creation_instruction_timestamp':c['owner_instruction_timestamp'],'candidate_created_at':c['created_at'],'review_owner_instruction_timestamp':'2026-11-03T14:47:07.332Z','head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'historical_inventory_head':ss['head'],'checks':checks,'commands':commands,'bindings':bindings,'row_bindings':rowbindings,'source_inventory':{'authority':'M01/planning/s2-green/source-current.json','count':len(ss['source_hashes']),'drift':drift},'candidate_hashes':pre,'board_before_review':board_before,'board_after_review':sha(R/'docs/board.json'),'fresh_semantic_probe_count':len(probes),'not_run':['product/native tests','valid product RED/GREEN','real resource/golden rendering','standalone lock resolution','build/package/install/DCC','Owner adoption','full-module acceptance']}
write('results.json',result)
findings={'status':result['status'],'blocking_findings':[],'limits':['MISSING is accepted as bounded absence of admitted proof in cited inputs, not repository-wide absence.','13 source bindings include board management drift. Prior board bytes were not retained here; no full-board reconstruction or exclusive append-only diff is asserted. Parent reports only M02 note/item/root updatedAt append. Review took live board snapshot and made no writes.','first_template DX1-DX7 adoption retained; pending activation body/representation/error proposals remain unadopted.','73 focused S1 GREEN is historical and not rerun/native/golden/module completion.','Reviewer semantic probes validate document claims only; stubs/fixtures/oracles remain pending/proposed, not product TDD GREEN.','Native publication/provider, standalone full transitive lock/root identity/toolchain tuple and actual resource/output bytes remain MISSING admitted evidence.'],'scope':'Only new sibling review directory written. Candidate, product/tests/spec/hooks/roles/board unchanged by reviewer; no commit.'}
write('findings.json',findings)
(O/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>M02 independent document review</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto}pre{white-space:pre-wrap}</style><h1>M02 Golden14 / full-lock 獨立文件審查</h1><p>'+result['status']+'</p><p>作者 '+html.escape(c['author'])+'；審查者 /root/m02_template_candidate_review。14 exact paths、13 source bindings、28 row pointer/hash bindings、796 product inventory 及 fresh semantic negative probes。PASS 僅文件準備，非產品/native/Owner 採納。</p><h2>結果</h2><pre>'+html.escape(json.dumps({'checks':checks,'probe_count':len(probes),'commands':commands},ensure_ascii=False,indent=2))+'</pre><h2>限制與風險</h2><pre>'+html.escape(json.dumps(findings,ensure_ascii=False,indent=2))+'</pre><h2>時間</h2><p>Creation instruction '+c['owner_instruction_timestamp']+'；created '+c['created_at']+'；review instruction 2026-11-03T14:47:07.332Z。</p><p><a href="results.json">Results/bindings</a> · <a href="probes.json">Fresh probes</a> · <a href="findings.json">Findings</a> · <a href="seal.json">Seal</a></p></html>',encoding='utf-8')
write('seal.json',{'reviewer':'/root/m02_template_candidate_review','sealed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'payload':{x.name:sha(x) for x in O.iterdir() if x.is_file() and x.name!='seal.json'},'candidate_payload':pre,'status':result['status'],'rule':'Stop writing after seal; seal excludes itself.'})
print(json.dumps({'status':result['status'],'failed_checks':[x for x in checks if not x['pass']],'failed_probes':[x for x in probes if not x['pass']],'source_drift':[x['path'] for x in bindings if x['status']!='MATCH']},indent=2))
