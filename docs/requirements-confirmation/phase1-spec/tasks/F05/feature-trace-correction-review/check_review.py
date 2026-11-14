import json,hashlib,copy,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[6]
HERE=Path(__file__).resolve().parent
F=HERE.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def check(m,old):
 e=[]; rows={r['test_id']:r for r in m['trace']}; prior={r['test_id']:r for r in old['trace']}
 if set(rows)!=set(prior) or len(rows)!=7:e.append('seven recipe identities')
 for k,r in rows.items():
  for field,value in prior[k].items():
   if field!='bdd' and r.get(field)!=value:e.append(k+':preserved:'+field)
  if k in ['F05-P01','F05-P04','F05-P05']:
   expected={'F05-P01':'F05-CAND-REOPEN-01','F05-P04':'F05-CAND-ISOLATION-01','F05-P05':'F05-CAND-ACK-01'}
   if (r.get('relation_type'),r.get('contextual_bdd'),r.get('exact_scenario'),r.get('candidate_scenario'),r.get('candidate_status'))!=('PROSPECTIVE_AC_DERIVED',['BDD-07'],[],expected[k],'PROPOSED_PENDING_OWNER'):e.append(k+':context-is-not-exact')
  elif (r.get('relation_type'),r.get('exact_scenario'),r.get('contextual_bdd'),r.get('candidate_scenario'))!=('EXISTING_BDD_OBLIGATION',prior[k]['bdd'],[],None):e.append(k+':existing-obligation')
 for field in ['original_packet','original_feature','original_scenarios','original_requirement_traceability','gates','identity','evidence']:
  if m[field]!=old[field]:e.append('protected:'+field)
 if m['correction']['approval']!='NOT_GRANTED' or m['correction']['status']!='PROPOSED_PENDING_OWNER':e.append('approval escalation')
 return e

def run():
 m=read(F/'feature-trace-correction/module-spec.json');old=read(F/'feature-trace-preparation/module-spec.json');errors=check(m,old)
 inputs=[]
 for directory in ['feature-trace-preparation','feature-trace-review','feature-trace-correction']:
  for p in sorted((F/directory).glob('*')):
   if p.is_file():inputs.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)})
 authority=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
 drift=[p for p,h in authority['source_hashes'].items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 if drift or len(authority['source_hashes'])!=796 or head!='5b709343a890503ebbe24a802e43cda5647df124':errors.append('authority')
 for item in read(F/'feature-trace-correction/seal.json')['files']:
  if sha(F/'feature-trace-correction'/item['path'])!=item['sha256']:errors.append('candidate seal:'+item['path'])
 for item in read(F/'feature-trace-correction/source-inputs.json')['sources']:
  if sha(ROOT/item['path'])!=item['sha256']:errors.append('candidate input:'+item['path'])
 html=(F/'feature-trace-correction/index.html').read_text(encoding='utf-8')
 embedded=re.search(r'<script id="module-spec" type="application/json">(.*?)</script>',html,re.S)
 if not embedded or json.loads(embedded.group(1))!=m:errors.append('candidate HTML')
 mutations=[]
 def probe(name,fn):
  mutant=copy.deepcopy(m);fn(mutant);diagnostics=check(mutant,old);mutations.append({'id':name,'detected':bool(diagnostics),'diagnostics':diagnostics})
 for i in [0,3,4]:
  probe('wrong-relation-'+str(i),lambda x,i=i:x['trace'][i].__setitem__('relation_type','EXISTING_BDD_OBLIGATION'))
  probe('context-counted-exact-'+str(i),lambda x,i=i:x['trace'][i].__setitem__('exact_scenario',['BDD-07']))
  probe('candidate-adopted-'+str(i),lambda x,i=i:x['trace'][i].__setitem__('candidate_status','ADOPTED'))
 for name,fn in [('AC-weaken',lambda x:x['original_feature'].__setitem__('acceptance','success only')),('test-evidence-upgrade',lambda x:x['trace'][0].__setitem__('status','GREEN')),('oracle-loss',lambda x:x['trace'][4].__setitem__('fixture_and_oracle_recipe','ack now')),('failure-BDD-rewrite',lambda x:x['original_scenarios'][0].__setitem__(6,'switch succeeds')),('gate-bypass',lambda x:x.__setitem__('gates',[])),('Feature-PASS',lambda x:x['identity'].__setitem__('feature_verdict','PASS')),('source-pointer-rebind',lambda x:x['original_packet'].__setitem__('source','elsewhere')),('source-hash-forge',lambda x:x['original_packet'].__setitem__('source_sha256','0'*64))]:probe(name,fn)
 if not all(x['detected'] for x in mutations):errors.append('surviving mutation')
 return m,inputs,mutations,{'errors':errors,'head':head,'historical_head':authority['head'],'authority_count':len(authority['source_hashes']),'authority_drift':drift,'board_management_sha256':sha(ROOT/'docs/board.json')}
if __name__=='__main__':
 m,inputs,mutations,checks=run()
 report={'reviewer':'/root/f05_trace_correction_review','author':m['correction']['author'],'verdict':'PASS_CORRECTION_PREPARATION_ONLY' if not checks['errors'] else 'FAIL','finding_closures':[{'id':'F05-TRACE-01:'+k,'result':'CLOSED_TRACE_ONLY','meaning':'BDD-07 remains context; prospective AC-derived candidate is PROPOSED_PENDING_OWNER, exact scenario absent.'} for k in ['F05-P01','F05-P04','F05-P05']],'counts':{'rows':7,'feature_plans':5,'adjacent_regressions':2,'new_independent_mutations':len(mutations),'detected':sum(x['detected'] for x in mutations)},'checks':checks,'observations':['All original recipe fields, outputs/oracles, valid RED requirements, target pending gates, AC05, existing BDD-07/08/20/21 and seven-row scope compared field-for-field to original preparation.','BDD-07 is failed save while switching and preserves old file, edits and project; it cannot be the exact success roundtrip, fencing or semantic ACK scenario.','S1 history and IO220 are historical bounded evidence; current source inspection is static only; retention704 is document/model-only pending Owner G1-G4.','Gray original state retained; Yellow dependencies unchanged; board management hash separate from 796-file historical content authority. No new BDD or Skeleton approved.'],'not_run':['product tests','build/package/install','native/UI/IPC','valid RED/GREEN','full Draft 2020-12 conformance'],'authority':'No Feature/module PASS, implementation/Skeleton authority, acceptance promotion, dispatch, board change, commit or release.'}
 for name,value in [('review.json',report),('source-inputs.json',{'sources':inputs}),('mutation-fixtures.json',mutations),('results.json',checks)]: (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 body=json.dumps(report,ensure_ascii=False,indent=2)
 (HERE/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>F05 correction independent review</title><h1>F05 trace correction review</h1><p>'+report['verdict']+'</p><p>Gray retained. Preparation trace only. Product/native/valid RED NOT RUN.</p><pre>'+body.replace('&','&amp;').replace('<','&lt;')+'</pre><script id="review-spec" type="application/json">'+body+'</script></html>',encoding='utf-8')
 (HERE/'seal.json').write_text(json.dumps({'counts':report['counts'],'files':[{'path':p.name,'sha256':sha(p)} for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='seal.json']},indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(bool(checks['errors']))
