import copy, hashlib, html, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[6]
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'feature-trace-preparation'
REVIEW=HERE.parent/'feature-trace-review'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def expected():
    original=read(BASE/'module-spec.json'); out=copy.deepcopy(original)
    out['correction']={'finding':'F05-TRACE-01','scope':'Three false exact BDD mappings plus explicit relation schema only','status':'PROPOSED_PENDING_OWNER','approval':'NOT_GRANTED','author':'/root/f05_trace_correction_packet'}
    candidates={'F05-P01':'F05-CAND-REOPEN-01','F05-P04':'F05-CAND-ISOLATION-01','F05-P05':'F05-CAND-ACK-01'}
    for row in out['trace']:
        old=row.pop('bdd'); candidate=candidates.get(row['test_id'])
        row.update(relation_type='PROSPECTIVE_AC_DERIVED' if candidate else 'EXISTING_BDD_OBLIGATION',contextual_bdd=old if candidate else [],exact_scenario=[] if candidate else old,candidate_scenario=candidate,candidate_status='PROPOSED_PENDING_OWNER' if candidate else 'NOT_APPLICABLE')
        row['relation_note']='Existing BDD-07 failure behavior is context only; AC-derived recipe requires exact future Given/When/Then and Owner approval before tests.' if candidate else 'Existing scenario obligation retained; broader recipe clauses are not thereby adopted BDD or executed evidence.'
    out['not_run']=list(dict.fromkeys(out['not_run']+['independent review of trace correction']))
    return out

def validate(model, sources=None):
    errors=[]
    reference=expected()
    if model!=reference: errors.append('Canonical trace/contract/status/adoption mapping mismatch')
    if len(model.get('trace',[]))!=7: errors.append('Seven rows required')
    if sources is not None:
        for s in sources:
            p=ROOT/s['path']
            if not p.exists() or sha(p)!=s['sha256']: errors.append('Source hash mismatch:'+s['path'])
    return errors

def build():
    model=expected(); write(HERE/'module-spec.json',model)
    diff=[]
    old=read(BASE/'module-spec.json')
    for a,b in zip(old['trace'],model['trace']):
        diff.append({'test_id':a['test_id'],'old_bdd':a['bdd'],'new_relation_type':b['relation_type'],'contextual_bdd':b['contextual_bdd'],'exact_scenario':b['exact_scenario'],'candidate_scenario':b['candidate_scenario'],'candidate_status':b['candidate_status'],'recipe_unchanged':a['fixture_and_oracle_recipe']==b['fixture_and_oracle_recipe']})
    write(HERE/'old-new-diff.json',diff)
    inputs=[BASE/'module-spec.json',BASE/'seal.json',REVIEW/'review.json',REVIEW/'seal.json',ROOT/'docs/requirements-confirmation/phase1-spec/phase1.feature',ROOT/'docs/requirements-confirmation/phase1-spec/index.html',ROOT/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F05-DELIVERY-01.json',ROOT/model['authority']['authority_file']]
    inputs+=sorted(p for p in BASE.iterdir() if p.is_file())+sorted(p for p in REVIEW.iterdir() if p.is_file())
    sources=[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in dict.fromkeys(inputs)]
    write(HERE/'source-inputs.json',{'sources':sources,'pointers':{'original_ac':'index.html embedded PD-P1-F05-DELIVERY-01 / AC05','existing_bdd':'phase1.feature BDD-07/08/20/21; module-spec original_scenarios exact text','finding':'feature-trace-review/review.json findings[F05-TRACE-01]'},'board':'Management state excluded; no mutation or promotion'})
    mutations=[]
    for idx in [0,3,4]: mutations.append({'id':'old-false-equivalence-'+model['trace'][idx]['test_id'],'row':idx,'field':'exact_scenario','value':['BDD-07']})
    mutations += [{'id':'context-counted-exact','row':0,'field':'relation_type','value':'EXISTING_BDD_OBLIGATION'},{'id':'candidate-adopted','row':3,'field':'candidate_status','value':'APPROVED'},{'id':'planned-promoted','row':4,'field':'status','value':'GREEN'},{'id':'wrong-scenario','row':1,'field':'exact_scenario','value':['BDD-08']},{'id':'wrong-candidate','row':0,'field':'candidate_scenario','value':'F05-CAND-ACK-01'},{'id':'lost-context','row':4,'field':'contextual_bdd','value':[]}]
    write(HERE/'mutation-fixtures.json',{'mutations':mutations,'additional':['source-hash-mismatch','original-failure-scenario-change','gray-promotion','gate-removal']})
    embedded=json.dumps(model,ensure_ascii=False).replace('<','\\u003c')
    rows=''.join('<tr>'+''.join('<td>'+html.escape(str(d[k]))+'</td>' for k in ['test_id','old_bdd','new_relation_type','exact_scenario','contextual_bdd','candidate_scenario','candidate_status'])+'</tr>' for d in diff)
    (HERE/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>F05 trace correction</title><style>body{font:16px system-ui;margin:32px;background:#f6f7fa}td,th{border:1px solid #aaa;padding:8px}table{border-collapse:collapse}pre{white-space:pre-wrap}</style><h1>F05 — trace correction / Gray</h1><p>F05-TRACE-01 P2: P01 reopen, P04 isolation, P05 semantic ACK derive from AC05; BDD-07 is contextual failure evidence only. Candidates remain PROPOSED_PENDING_OWNER. No BDD adoption, product evidence, Skeleton authority or Feature/module PASS.</p><p>7 rows: 5 feature plans + 2 adjacent regressions. All PLANNED_NOT_RUN. Original recipes, acceptance, contracts and gates preserved.</p><table><tr><th>Plan</th><th>Old BDD</th><th>Relation</th><th>Exact existing scenario</th><th>Context only</th><th>Candidate</th><th>Candidate status</th></tr>'+rows+'</table><h2>Existing failure behavior unchanged</h2><pre>'+html.escape(json.dumps(model['original_scenarios'],ensure_ascii=False,indent=2))+'</pre><h2>Full trace, recipes and gates</h2><pre>'+html.escape(json.dumps(model,ensure_ascii=False,indent=2))+'</pre><script id="module-spec" type="application/json">'+embedded+'</script>',encoding='utf-8')
if __name__=='__main__': build()
