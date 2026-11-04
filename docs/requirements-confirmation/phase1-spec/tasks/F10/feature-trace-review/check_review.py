from pathlib import Path
import copy, hashlib, html, json, re, subprocess

O = Path(__file__).resolve().parent
R = O.parents[5]
P = O.parent / 'feature-trace-preparation'
def read(p): return p.read_text(encoding='utf-8-sig')
def load(p): return json.loads(read(p))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n, v): (O/n).write_text(json.dumps(v, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def validate(t, recipes, sources, original):
    errors = []
    def check(v, name):
        if not v: errors.append(name)
    check(t['original_acceptance'] == original['task']['acceptance'], 'original AC10 exact')
    check(t['state']=='PLANNED_NOT_RUN' and t['zone']=='gray', 'current Feature remains Gray NOT RUN')
    check(len(t['trace'])==8 and len(recipes)==8, 'eight rows and recipes')
    expected = [('REQ-15','BDD-20','exact scenario equivalence'), ('REQ-15/16','BDD-21','exact scenario equivalence'), ('REQ-15','BDD-19','shared regression, not BDD-20 equivalence'), ('REQ-16','BDD-31','shared roots regression, not clear scenario'), ('REQ-07','BDD-07/08','contextual lifecycle regression only'), ('REQ-20','BDD-26','cross-module regression only'), ('REQ-15','none','prospective AC10 recipe; no invented BDD ID'), ('REQ-15','none','prospective original-feature/UI recipe; no invented BDD ID')]
    for i, (row, recipe, exp) in enumerate(zip(t['trace'],recipes,expected),1):
        check(row['id']==recipe['id']==f'F10-T{i:02}', 'row recipe identity')
        check((row['requirement'],row['bdd'],row['mapping'])==exp, f'T{i} exact provenance/classification')
        check(row['acceptance']=='AC10' and row['status']==recipe['status']=='PLANNED_NOT_RUN', f'T{i} pending AC10')
        check(recipe['action']==row['oracle'] and recipe['oracle'].startswith(row['oracle']), f'T{i} recipe oracle parity')
        check(all(x in recipe['fixture'] for x in ['Form root/children','architecture hierarchy/relations','pending bindings','document B','read-only source BIN','earlier history entry H0']), f'T{i} whole document fixture')
        check(all(x in recipe['oracle'] for x in ['whole canonical payload','linked-state projections','source/shared hashes','unaffected B']), f'T{i} whole restoration scope')
        check('PENDING_OWNER_ENVELOPE_AND_APPROVED_SKELETON' in recipe['next_command'], f'T{i} no self-approved execution')
        check(all(x in recipe['valid_red'] for x in ['runner builds','intended missing F10 behavior','not valid RED','not new F10 RED']), f'T{i} valid RED gate')
    check('one Undo' in t['trace'][0]['oracle'] and 'one Undo' in t['trace'][1]['oracle'], 'one compound Undo each')
    check('source/shared materials preserved' in t['trace'][1]['oracle'], 'source shared preservation')
    check('any merge commit stage failure' in t['trace'][2]['oracle'] and 'zero new Undo' in t['trace'][2]['oracle'], 'all stage rollback no history')
    check('confirm or cancel' in t['trace'][7]['oracle'] and 'restore Form and linked state' in t['trace'][7]['oracle'], 'confirmation Form linkage')
    check(all(x in t['authority_boundary'] for x in ['No new Redo/Undo/provider semantics','D11 proposal is not blanket approval']), 'proposed remains unadopted')
    check(all(x in t['next_action'] for x in ['Owner/exact envelope','approved Skeleton','compile-valid RED','no module/feature PASS']), 'future approval gates')
    check(len(sources)==20 and all(sha(R/x['path'])==x['sha256'] for x in sources if x['path']!='docs/board.json'), '20 source bindings; 19 non-board current hashes')
    return errors

def main():
    t, recipes, sources, a = [load(P/n) for n in ['trace.json','pending-recipes.json','sources.json','original-authority.json']]
    original_html=read(R/'docs/requirements-confirmation/phase1-spec/index.html')
    raw=json.loads(re.search(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',original_html,re.S).group(1))
    task=load(R/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F10-DELIVERY-01.json')
    original_checks={'feature_exact':a['feature']==next(x for x in raw['features'] if x['id']=='F10'), 'task_exact':a['task']==task}
    feature_text=read(R/'docs/requirements-confirmation/phase1-spec/phase1.feature')
    original_checks['seven_scenarios_exact']=all(v==re.search(r'  @'+k+r'\b.*?(?=\n  @BDD-|\Z)',feature_text,re.S).group(0).rstrip() for k,v in a['scenarios'].items())
    original_checks['requirements_exact']=a['requirements']==[x for x in raw['requirement_traceability'] if 'F10' in x['feature']]
    seal=load(P/'seal.json')
    original_checks['author_seal']=len(seal['files'])==9 and all(sha(P/n)==h for n,h in seal['files'].items())
    authority=load(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
    drift=[p for p,h in authority['source_hashes'].items() if not (R/p).exists() or sha(R/p)!=h]
    original_checks['796_current_bytes']=len(authority['source_hashes'])==796 and not drift
    original_checks['embedded_trace']=json.loads(re.search(r'id="module-spec">(.*?)</script>',read(P/'index.html'),re.S).group(1))==t
    baseline=validate(t,recipes,sources,a)
    cases=[]
    mutations=[('wrong AC', 'trace', lambda x:x['trace'][0].update(acceptance='AC09')),
      ('wrong exact BDD', 'trace', lambda x:x['trace'][0].update(bdd='BDD-08')),
      ('shared misrepresented as owned exact', 'trace', lambda x:x['trace'][2].update(mapping='exact scenario equivalence')),
      ('whole becomes design only', 'recipe', lambda x:x[0].update(oracle=x[0]['oracle'].replace('whole canonical payload','design only'))),
      ('compound becomes multiple Undo', 'trace', lambda x:x['trace'][0].update(oracle=x['trace'][0]['oracle'].replace('one Undo','multiple Undo'))),
      ('proposed becomes adopted', 'trace', lambda x:x.update(authority_boundary='D11 adopted; new Redo/provider semantics approved')),
      ('current feature PASS', 'trace', lambda x:x.update(state='PASS')),
      ('source hash substitution', 'sources', lambda x:x[19].update(sha256='0'*64)),
      ('snapshot invented BDD', 'trace', lambda x:x['trace'][6].update(bdd='BDD-20')),
      ('confirmation removed', 'trace', lambda x:x['trace'][7].update(oracle='clear immediately; design only')),
      ('self approved command', 'recipe', lambda x:x[0].update(next_command='cargo test now approved')),
      ('fixture failure as RED', 'recipe', lambda x:x[1].update(valid_red='compile failure is valid RED'))]
    fixtures=[]
    for name,kind,mutate in mutations:
        tt,rr,ss=copy.deepcopy(t),copy.deepcopy(recipes),copy.deepcopy(sources)
        target={'trace':tt,'recipe':rr,'sources':ss}[kind]; mutate(target)
        detected=validate(tt,rr,ss,a)
        cases.append({'name':name,'detected':bool(detected),'reasons':detected})
        fixtures.append({'name':name,'kind':kind,'mutated_input':target})
    write('new-semantic-fixtures.json',fixtures)
    write('new-semantic-results.json',{'positive_pass':not baseline,'negative_controls':cases,'passed':sum(x['detected'] for x in cases),'total':len(cases)})
    write('source-review.json',{'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'inventory_head':authority['head'],'authority_entries':len(authority['source_hashes']),'drift':drift,'source_bindings':sources,'original_checks':original_checks,'author_seal':seal,'input_hash_differences':{x['path']:{'bound':x['sha256'],'current':sha(R/x['path'])} for x in sources if sha(R/x['path'])!=x['sha256']}})
    report={'reviewer':'/root/f10_feature_trace_review','author':'/root/f10_feature_trace_packet','verdict':'PASS_PREPARATION_ONLY' if not baseline and all(original_checks.values()) and all(x['detected'] for x in cases) else 'FAIL','findings':baseline+[k for k,v in original_checks.items() if not v], 'trace_rows':8,'pending_recipes':8,'new_semantic_controls':len(cases),'not_run':['product tests','build','valid RED','native UI','full Draft','full module regression'],'interpretation':'Exact equivalence is the intended BDD obligation, not executed evidence. Only BDD-20/21 are exact. BDD-19/31 are shared, BDD-07/08 contextual, BDD-26 cross-module, T07/T08 prospective AC10/UI recipes. All remain pending. Gray retained; no Feature/module PASS or Skeleton authority.','limits':['Pure S1 historical 24/73 and historical 222/model are not full ESS/native behavior proof.','Current local UI design recovery shows preview/confirm/Undo/Redo only for designDoc. Form-linked whole document restoration and source/shared material integrity still need approved integration evidence.','M06 MR-F1 document correction closes historical finding only; MH1-MH6 pending Owner. M03 correction and retention observation do not adopt providers, retained-history or new Redo choices.']}
    write('review.json',report)
    extra={'source_test_log_pointers': ['apps/sgenaxis-desktop/ui/app.js:11831-11907 local designDoc preview/confirm/Undo/Redo; no full ESS assertion','apps/sgenaxis-desktop/crates/sgenaxis-work/tests/phase1_document_history.rs:111,125 pure clear/Undo fixture assertions; not executed now','tasks/M04/planning/exact-design/s1-green/verification.json historical focused 24/work 73, red_provenance and NOT RUN native limitations','tasks/M04/planning/exact-design/independent-review/review.json historical S1 independent acceptance and log/test provenance','tasks/M06/planning/merge-record-consistency-review/review.json MR-F1 documentary closure only','tasks/M03/planning/undo-correction-review/review.json document checker/trusted premises only'], 'command':'python -B docs/requirements-confirmation/phase1-spec/tasks/F10/feature-trace-review/check_review.py'}
    log_paths=['s1-green/green.stdout.txt','s1-green/work-regression.stdout.txt','independent-review/work.stdout.txt','independent-review/probe.stdout.txt']
    log_root=R/'docs/requirements-confirmation/phase1-spec/tasks/M04/planning/exact-design'
    extra['historical_logs']=[{'path':(log_root/n).relative_to(R).as_posix(),'sha256':sha(log_root/n),'result_lines':[{'line':i,'text':line} for i,line in enumerate(read(log_root/n).splitlines(),1) if 'test result:' in line]} for n in log_paths]
    extra['log_interpretation']='Original focused green stdout is the earlier 21-test snapshot. Later work-regression and independent work logs contain 24-test history suite and total 73 across suites. Independent probe is 7. All historical files read only; no execution now; no whole ESS/native proof.'
    rendered={'review':report,'verification':load(O/'new-semantic-results.json'),'provenance':extra,'source_checks':original_checks}
    (O/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>F10 independent preparation review</title><style>body{font:16px/1.6 system-ui;max-width:1100px;margin:30px auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>F10 independent review — preparation only</h1><p>Gray retained. No product acceptance.</p><pre>'+html.escape(json.dumps(rendered,ensure_ascii=False,indent=2))+'</pre><script type="application/json" id="review-spec">'+json.dumps(rendered,ensure_ascii=False).replace('</','<\\/')+'</script>',encoding='utf-8')
    files={p.name:sha(p) for p in O.iterdir() if p.is_file() and p.name!='seal.json'}
    write('seal.json',{'scope':'independent F10 preparation document review only','file_count':len(files),'trace_rows':8,'recipes':8,'source_bindings':20,'semantic_negative_controls':len(cases),'files':files})
    print(json.dumps({'verdict':report['verdict'],'original_checks':original_checks,'baseline_errors':baseline,'negative_controls_detected':sum(x['detected'] for x in cases),'negative_controls_total':len(cases),'sealed_files':len(files)},indent=2))
    return 0 if report['verdict']=='PASS_PREPARATION_ONLY' else 1

if __name__=='__main__': raise SystemExit(main())
