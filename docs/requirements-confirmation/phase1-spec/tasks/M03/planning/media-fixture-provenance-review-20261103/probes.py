import json,pathlib,hashlib,copy,importlib.util,re,subprocess,html,datetime
ROOT=pathlib.Path(__file__).resolve().parents[7]
OUT=pathlib.Path(__file__).resolve().parent
C=OUT.parent/'media-fixture-provenance-20261103'
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():return {str(p.relative_to(C)):sha(p) for p in C.rglob('*') if p.is_file()}
def write(n,v):(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
before=snapshot(); p,f,g,y=[load(C/n) for n in ['packet.json','fixtures.json','golden14-handoff.json','yellow-actions.json']]
base=ROOT/'docs/requirements-confirmation/phase1-spec/tasks'
u=load(base/'M03/planning/preview-media-candidate-20261103/candidate.json'); gold=load(base/'M02/planning/golden14-lock-inventory-20261103/candidate.json'); reg=load(base/'M01/planning/exact-disposition-correction-20261103/register.json')
spec=importlib.util.spec_from_file_location('candidate_validator',C/'validate.py'); v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
assert v.validate(p,f,g,y)
checks=[]
def check(name,ok,detail=None):
 checks.append({'name':name,'pass':bool(ok),'detail':detail});assert ok,name
# Independent semantic source oracle, not candidate main and not its ten mutations.
def semantic(f,g,y):
 assert len(f['recipes'])==8
 for i,r in enumerate(f['recipes']):
  s=u['rows'][i];assert r['dimension']==s['id'] and r['family']==s['family']
  assert r['source']['pointer']=='/rows/'+str(i) and sha(ROOT/r['source']['path'])==r['source']['sha256']
  special=next(c for c in r['cases'] if c['category']=='dimension-specific')
  assert special['recipe'].startswith(s['required_fixture_set']+';') and s['risk_dimensions'] in special['observable_oracle_candidate']
  assert len(r['cases'])==7 and len({c['id'] for c in r['cases']})==7
  assert all(c['id']==r['dimension']+'-'+c['category'] for c in r['cases'])
  for c in r['cases']:
   if c['category'] in ['permission','timeout']:
    assert c['applicability']==('Not Applicable' if i>=6 else 'Deferred')
   if c['category']=='boundary' and i<5:assert c['applicability']=='Deferred'
 fields=f['provenance']['required_fields'];assert len(fields)==len(set(fields)) and {'sha256','byte_length','provider_identity','source_revision','owner_disposition_revision','expected_outcome_revision','reviewer_identity'}.issubset(fields)
 assert len(f['provenance']['sampling_rules'])==7 and f['provenance']['status']=='PROPOSED_NOT_ADOPTED'
 assert len(g)==14
 for i,r in enumerate(g):
  s=gold['rows'][i];assert r['path']==s['declared_product_path'] and r['slot']==s['slot']
  assert r['authority']['pointer']=='/rows/'+str(i) and sha(ROOT/r['authority']['path'])==r['authority']['sha256']
  for k,sk in [('missing_resource_bytes','submitted_resource'),('missing_input_revision_output_bytes_hash','golden'),('missing_manifest_lock_resolver','lock_provider_evidence')]:assert r[k]==s[sk]
  assert r['not_repository_absence_claim'] is True
  assert all(r['toolchain'][k] is None for k in ['exact_version','target','resolver_command_environment'])
  assert r['provider_list']==['M02 template author','M02 independent fixture reviewer','M02 standalone manifest/lock provider']
 yellow=[(i,r) for i,r in enumerate(reg['cards']) if r['light']=='Yellow'];assert len(y)==len(yellow)==8
 for a,(i,s) in zip(y,yellow):
  assert a['id']==s['id'] and a['source']['pointer']=='/cards/'+str(i)
  assert a['remaining_conditions']==s['missing_conditions'] and a['provider']==s['provider']
  task=load(base/('IO-PREREQ/implementation/module-spec.json' if a['id']=='PD-P1-IO-PREREQ-IMPL-01' else a['id']+'.json'))
  assert a['original_allowed_files']==task.get('allowed_files') and a['original_dependencies']==task.get('dependencies')
  state=s.get('adopted_current_status');assert a['current_state']==(load(ROOT/state['path']) if state else None)
 return True
check('independent exact source/row/scope oracle',semantic(f,g,y))
probes=[]
mutations=[('dimension ID reordering',lambda f,g,y:f['recipes'][0].update(dimension='MM02')),('dimension-specific source risk substitution',lambda f,g,y:f['recipes'][3]['cases'][6].update(observable_oracle_candidate='arbitrary outcome')),('wrong source pointer',lambda f,g,y:f['recipes'][1]['source'].update(pointer='/rows/6')),('duplicate scenario identity',lambda f,g,y:f['recipes'][0]['cases'][1].update(id='MM01-normal')),('permission deferred upgraded to Applicable',lambda f,g,y:f['recipes'][0]['cases'][4].update(applicability='Applicable')),('provenance origin field deletion',lambda f,g,y:f['provenance']['required_fields'].remove('source_revision')),('golden input revision invented',lambda f,g,y:g[2]['missing_input_revision_output_bytes_hash'].update(input_design_revision='invented')),('golden resolver provenance invented',lambda f,g,y:g[4]['missing_manifest_lock_resolver'].update(resolver_provenance='workspace lock')),('golden repository absence overclaim',lambda f,g,y:g[5].update(not_repository_absence_claim=False)),('yellow dependencies erased',lambda f,g,y:y[2].update(original_dependencies=['invented'])),('IO adoption blocker substituted',lambda f,g,y:y[0].update(remaining_conditions='Owner must adopt IO first')),('MM08 decoder timeout made applicable',lambda f,g,y:f['recipes'][7]['cases'][5].update(applicability='Applicable'))]
for name,mutate in mutations:
 args=copy.deepcopy((f,g,y));mutate(*args)
 try:semantic(*args)
 except AssertionError:probes.append({'name':name,'rejected':True,'oracle':'independent source/semantic oracle'})
 else:raise AssertionError(name)
check('12 independent semantic/source negative probes',all(x['rejected'] for x in probes),len(probes))
text=(C/'index.html').read_text(encoding='utf-8');embedded=json.loads(re.search(r'<script type="application/json" id="module-spec">(.*?)</script>',text,re.S).group(1))
check('HTML embedded exact JSON parity',embedded=={'packet':p,'fixtures':f,'yellow8':y,'golden14':g})
check('HTML visible exact JSON parity',all(html.escape(json.dumps(obj,ensure_ascii=False,indent=2)) in text for obj in [p,f,y,g]))
feature=(C/'module.feature').read_text();steps=(C/'steps.py').read_text();pending=load(C/'pending.json')
check('8 supplier scenarios and pending stubs consistent',feature.count('  Scenario: ')==8 and all(r['dimension']+' fixture provenance remains reviewable' in feature for r in f['recipes']) and steps.count('raise NotImplementedError')==2 and pending['automation']=='PENDING_NOT_IMPLEMENTED')
bindings=[]
for b in load(C/'source-hashes.json'):bindings.append({**b,'actual':sha(ROOT/b['path']),'matches':sha(ROOT/b['path'])==b['sha256']})
check('candidate read-time source hashes current',all(b['matches'] for b in bindings),len(bindings))
auth=load(base/'M01/planning/s2-green/source-current.json')['source_hashes'];drift=[path for path,h in auth.items() if sha(ROOT/path)!=h]
check('796 current product authority hashes',len(auth)==796 and not drift,{'count':len(auth),'drift':drift})
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();check('live HEAD differs only by declared historical baseline',head==p['head'] and p['historical_head']=='31babe87a7ef1e40a0d4bedc523077e7a45d63ab',head)
check('candidate files unchanged',snapshot()==before)
write('probes.json',probes);write('source-bindings.json',bindings)
findings=[{'id':'STAT-01','severity':'INFORMATION','finding':'Actual provenance schema has 24 unique fields and 7 sampling rules; parent author summary of 26 fields is a count correction only. Candidate does not claim 26 and no invented two-field gate is imposed.','disposition':'No candidate change required.'}]
write('findings.json',findings)
results={'reviewer':'/root/media_fixture_provenance_review','author':p['author'],'verdict':'PASS_BOUNDED_DOCUMENT_PREPARATION_ONLY','scope':'independent document review; no implementation, Owner adoption, native or module acceptance','checks':checks,'dimension_count':8,'recipe_count':56,'provenance_field_count':len(f['provenance']['required_fields']),'sampling_rule_count':7,'golden_rows':14,'yellow_actions':8,'new_negative_probes':len(probes),'HEAD':head,'historical_HEAD':p['historical_head'],'product_authority_count':len(auth),'product_drift':drift,'candidate_hashes_before':before,'candidate_hashes_after':snapshot(),'historical_PASS':'NOT RERUN','native_product_build_package_install_DCC':'NOT RUN','module_complete':False,'owner_approval':None,'remaining_gates':['Owner exact format/subset/SDK/limits and disposition revision','Supplier immutable bytes/provenance; no supplied fixture bytes in this preparation','Approved Skeleton, valid behavioral RED, independent decoder/render/native evidence','All 14 golden rows lack submitted bytes/hash, Definition/Design revisions, expected rendered bytes/hash, standalone manifest/lock digests and resolver provenance; exact toolchain/target/environment provider evidence is still missing','Other seven yellow actions remain handoffs, not delivered implementations; IO needs native Windows11/reparse/8.3 evidence, no new Owner adoption']}
write('results.json',results)
(OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M03 independent fixture provenance review</title><h1>PASS — bounded document preparation only</h1><p>8 dimensions × 7 categories = 56 candidate recipes; 24 provenance fields; 7 sampling rules. 14 golden source rows and 8 Yellow handoffs match current authority. No native/product acceptance or Owner adoption.</p><p>Author '+html.escape(p['author'])+'; reviewer /root/media_fixture_provenance_review. Historical PASS suites NOT RERUN. Product/native/build/package/install/DCC NOT RUN.</p><h2>Remaining gates</h2><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in results['remaining_gates'])+'</ul><h2>Independent checks</h2><pre>'+html.escape(json.dumps(checks,ensure_ascii=False,indent=2))+'</pre><h2>Findings</h2><pre>'+html.escape(json.dumps(findings,ensure_ascii=False,indent=2))+'</pre><script type="application/json" id="review-results">'+json.dumps(results,ensure_ascii=False).replace('<','\\u003c')+'</script>',encoding='utf-8')
assert snapshot()==before
seal={'state':'SEALED_STOP_WRITING','reviewer':results['reviewer'],'candidate_unchanged':True,'files':{x.name:sha(x) for x in OUT.iterdir() if x.is_file() and x.name!='seal.json'},'candidate':before}
write('seal.json',seal)
print(json.dumps({'verdict':results['verdict'],'checks':len(checks),'probes':len(probes),'source_bindings':len(bindings),'candidate_unchanged':True}))
