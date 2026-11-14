"""Independent documentary trace controls. No product behavior execution."""
import copy, hashlib, html, json, re, subprocess
from pathlib import Path
P=Path(__file__).resolve().parent
R=P.parents[5]
A=P.parent/'feature-trace-preparation'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,x): (P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def validate(x):
    errors=[]
    def ck(ok,name):
        if not ok: errors.append(name)
    rows=x['rows']; spec=x['spec']; v=x['verification']
    expected=[(['BDD-11'],'EXACT_ORIGINAL_SCENARIO'),(['BDD-12'],'EXACT_ORIGINAL_SCENARIO'),([],'PROSPECTIVE_AC_RECIPE_NOT_EXISTING_BDD'),(['BDD-12'],'PARTIAL_BDD_PLUS_AC_RECIPE'),([],'PROSPECTIVE_AC_RECIPE_NOT_EXISTING_BDD')]
    ck(len(rows)==5,'five recipes')
    for i,(bdd,relation) in enumerate(expected):
        z=rows[i]
        ck(z['requirement']=='REQ-09' and z['acceptance']=='AC07',f'{i}:original authority')
        ck(z['bdd']==bdd and z['mapping_kind']==relation,f'{i}:action equivalence')
        ck(z['status']=='PLANNED_NOT_RUN' and z['command']=='BLOCKED_PENDING_OWNER_ENVELOPE_SKELETON_RUNNER',f'{i}:pending behavior')
    ck(spec['original_packet']==x['original'],'original unchanged')
    ck(spec['traceability']==rows,'embedded trace parity')
    ck(spec['identity']['zone']=='gray','Gray retained')
    ck(spec['identity']['dependencies_unchanged']==x['original']['dependencies'],'dependencies retained')
    ck(set(spec['exact_scenario_equivalence'])=={'BDD-11','BDD-12'},'exact action set')
    ck(all(t in rows[1]['fixture_recipe'] for t in ['definition+ESS+UI','referenced']),'full project fixture')
    ck('one document/payload is not assumed' in rows[1]['gap'],'aggregate unresolved')
    ck('Before/after exact source file hashes equal' in rows[2]['oracle'],'source preservation')
    ck('No success UI/result on cancel' in rows[4]['oracle'],'cancel result')
    ck('not SGB1' in spec['proposals_preserved']['BIN_v1'] and 'none adopted here' in spec['proposals_preserved']['BIN_v1'],'format/adoption distinction')
    ck('not auto-approved ZIP' in spec['proposals_preserved']['BIN_v1'],'ZIP not adopted')
    ck('pending Owner' in spec['proposals_preserved']['BIN_v1'],'Owner pending')
    ck(v['feature_PASS'] is False and v['module_PASS'] is False and v['Done'] is False,'no completion escalation')
    ck(all(v[k]=='NOT RUN' for k in ['product_tests','build','native','valid_RED','full_Draft']),'unrun layers')
    ck(x['source_path']=='docs/requirements-confirmation/phase1-spec/phase1.feature','original BDD source')
    ck(x['source_hash']==sha(R/x['source_path']),'source hash binding')
    return errors

def main():
    original=read(R/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F07-DELIVERY-01.json')
    spec=read(A/'module-spec.json'); inputs=read(A/'inputs.json')
    baseline={'rows':read(A/'traceability.json'),'spec':spec,'verification':read(A/'verification.json'),'original':original,'source_path':'docs/requirements-confirmation/phase1-spec/phase1.feature','source_hash':inputs['docs/requirements-confirmation/phase1-spec/phase1.feature']}
    assert not validate(baseline),validate(baseline)
    mutants=[]
    def mutation(name,path,value):
        y=copy.deepcopy(baseline); z=y
        for key in path[:-1]: z=z[key]
        z[path[-1]]=value
        errors=validate(y)
        assert errors,name
        mutants.append({'id':name,'path':path,'mutation':value,'expected':'REJECT','actual':'REJECT','reasons':errors})
    for i in range(5):
        mutation(f'wrong-AC-{i}', ['rows',i,'acceptance'],'AC08')
        mutation(f'wrong-REQ-{i}', ['rows',i,'requirement'],'REQ-06')
        mutation(f'context-import-merge-BDD-{i}', ['rows',i,'bdd'],['BDD-09' if i!=4 else 'BDD-19'])
        mutation(f'current-behavior-pass-{i}', ['rows',i,'status'],'PASS')
    mutation('wrong-original-BDD-source',['source_path'],'tests/test_pd_scene_sgb_01.py')
    mutation('wrong-source-hash',['source_hash'],'0'*64)
    mutation('partial-as-exact',['rows',3,'mapping_kind'],'EXACT_ORIGINAL_SCENARIO')
    mutation('hash-as-BDD18',['rows',2,'bdd'],['BDD-18'])
    mutation('cancel-as-closeBDD08',['rows',4,'bdd'],['BDD-08'])
    mutation('single-document-scope',['rows',1,'fixture_recipe'],'One DocumentWithAssets only')
    mutation('aggregate-assumed',['rows',1,'gap'],'DocumentWithAssets fully satisfies project scope')
    mutation('hash-semantic-only',['rows',2,'oracle'],'Semantic state equal only')
    mutation('cancel-false-success',['rows',4,'oracle'],'Report success on cancel')
    mutation('SGB1-as-BINv1',['spec','proposals_preserved','BIN_v1'],'SGB1 is the approved BIN-v1')
    mutation('proposal-as-adopted',['spec','proposals_preserved','BIN_v1'],'BIN-v1 adopted; not SGB1')
    mutation('feature-PASS',['verification','feature_PASS'],True)
    mutation('module-PASS',['verification','module_PASS'],True)
    mutation('native-proof-escalation',['verification','native'],'PASS')
    mutation('dependency-removal',['spec','identity','dependencies_unchanged'],[])
    seal=read(A/'seal.json'); seal_errors=[n for n,h in seal['files'].items() if sha(A/n)!=h]
    assert len(seal['files'])==11 and not seal_errors
    authority_path=R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json'
    authority=read(authority_path); drift=[n for n,h in authority['source_hashes'].items() if sha(R/n)!=h]
    assert len(authority['source_hashes'])==796 and not drift
    pointers=read(A/'source-pointers.json')
    for z in pointers:
        assert sha(R/z['path'])==z['sha256']
        assert z['needle'] in (R/z['path']).read_text(encoding='utf-8-sig').splitlines()[z['line']-1]
    input_differences={n:{'author':h,'current':sha(R/n)} for n,h in inputs.items() if sha(R/n)!=h}
    assert all(n=='docs/board.json' for n in input_differences),input_differences
    embedded=re.search(r'<script id="module-spec" type="application/json">(.*?)</script>',(A/'index.html').read_text(encoding='utf-8'),re.S)
    assert read(A/'pending-test-recipes.json')['cases']==baseline['rows']
    assert json.loads(embedded[1])==spec
    feature=(R/baseline['source_path']).read_text(encoding='utf-8-sig')
    assert '@BDD-11 @M06 @REQ-09' in feature and '@BDD-12 @M06 @REQ-09' in feature
    assert '內容清單包含定義、ESS、UI及完整被引用素材' in feature
    merge=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M06/planning/merge-record-consistency-review/review.json')
    assert merge['total_direct_calls']==184 and merge['verdict']=='PASS_DOCUMENT_SCOPE_PENDING_OWNER'
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
    assert head=='5b709343a890503ebbe24a802e43cda5647df124'
    review={'reviewer':'/root/f07_feature_trace_review','author':'/root/f07_feature_trace_packet','verdict':'PASS_PREPARATION_DOCUMENT_SCOPE_ONLY','findings':[],'positive_semantic_baselines':1,'new_semantic_mutations_rejected':len(mutants),'author_seal_files':11,'source_pointers_verified':len(pointers),'product_inventory':796,'product_hash_drift':drift,'head':head,'historical_inventory_head':authority['head'],'input_hash_differences_separate':input_differences,'zone':'gray retained; no board write','skeleton_authority':False,'feature_PASS':False,'module_PASS':False,'new_BDD_approval':False,'not_run':['product tests','build','package','native UI','valid RED','full Draft'],'conclusions':['REQ-09/AC07: five prospective recipes; only BDD-11/12 exact original action equivalence. Content-list row partial BDD12 plus AC. Hash and cancel are prospective AC recipes, not BDD09/18/19/08 substitution.','Original full project definition+ESS+UI+referenced assets remains required. Proposed DocumentWithAssets scope mapping unresolved before Skeleton.','BIN-v1 SGABIN1 LF/SGA-BIN-v1 is proposed and distinct from legacy SGB1 three-entry source/fixture. Existing source/string tests and Python codec are static/historical, not format or current F07 proof.','M06 thresholds/adoption remain in unchanged hash-bound upstream files. Latest merge record review 184/184 is documentary and pending Owner; cannot prove export behavior.','No new BDD, ports, Skeleton, product implementation or state transitions approved.']}
    write('semantic-mutation-fixtures.json',mutants)
    write('review.json',review)
    write('source-hashes.json',{'authority':str(authority_path.relative_to(R)).replace('\\','/'),'authority_sha256':sha(authority_path),'author_seal_sha256':sha(A/'seal.json'),'review_inputs':{n:sha(R/n) for n in inputs},'author_outputs':{n:sha(A/n) for n in seal['files']}})
    body='<h1>F07 Independent Feature Trace Review</h1><p>PASS — preparation document scope only. Gray retained.</p>'+''.join('<p>'+html.escape(t)+'</p>' for t in review['conclusions'])+'<h2>New verification</h2><p>1 semantic baseline; '+str(len(mutants))+' new semantic counterexamples rejected; 11 author sealed files; 796 product hashes; 12 source pointers checked.</p><h2>Evidence limits</h2><p>Product tests, build, native UI, valid RED and full Draft NOT RUN. No Feature/module PASS, Skeleton authority, new BDD approval or board transition.</p><pre>'+html.escape(json.dumps(review,ensure_ascii=False,indent=2))+'</pre>'
    (P/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>F07 Independent Review</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto;line-height:1.6}pre{white-space:pre-wrap;background:#f2f4f7;padding:24px}</style>'+body+'<script type="application/json" id="review-spec">'+json.dumps(review,ensure_ascii=False).replace('</','<\\/')+'</script>',encoding='utf-8')
    print(json.dumps({'verdict':review['verdict'],'new_mutations':len(mutants),'inventory':796,'input_differences':list(input_differences)}))
if __name__=='__main__': main()
