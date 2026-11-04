"""Independent F02 semantic trace review. No product runner is invoked."""
import copy, hashlib, json, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
PREP = HERE.parent / 'feature-trace-preparation'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
trace = read(PREP/'trace.json')
legacy = read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F02-DELIVERY-01.json')
clauses = ['修改模板副本不影響來源','更新必先看差異','不增加無需求模組']
test_source = 'apps/sgenaxis-desktop/crates/sgenaxis-work/tests/phase1_generation_plan.rs'
test_lines = (ROOT/test_source).read_text(encoding='utf-8').splitlines()
expected_tests = [(t['name'],t['line']) for t in trace['tests']]

def validate(t):
    errors=[]
    def require(ok, label):
        if not ok: errors.append(label)
    require(t['original_acceptance']==legacy['acceptance'], 'original AC preservation')
    require([r['criterion'] for r in t['trace']]==clauses,'exact three AC02 clauses')
    for row in t['trace']:
        require(row['original_acceptance']==legacy['acceptance'][0], 'row original AC')
        require(row['original_bdd']==['BDD-03','BDD-04'], 'shared BDD IDs')
        require(row['bdd_relationship']=='shared M02 generation regression only; neither directly specifies this template-copy/update/select AC', 'regression not direct feature proof')
        require(row['verdict']=='GAP_NOT_FEATURE_PROVEN','unsupported feature PASS')
    require(len(t['tests'])==6,'six pointers')
    for i,item in enumerate(t['tests']):
        require((item['name'],item['line'])==expected_tests[i], 'test identity')
        require(item['source']==test_source,'test path')
        require(test_lines[item['line']-1].startswith('fn '+item['name']+'('),'test source location')
        require(item['executed_this_run'] is False,'current test claim')
    for path,digest in t['sources'].items():
        require((ROOT/path).exists() and sha(ROOT/path)==digest, 'input hash:'+path)
    require(t['gates']['native']=='NOT RUN','native claim')
    require(t['gates']['build_golden14']=='MISSING','golden claim')
    require(t['gates']['product_tests_this_run']=='NOT RUN','product current claim')
    require(t['board_zone']=='gray' and t['state']=='PLANNING_ONLY','authority escalation')
    require(len(t['recipes'])==3,'three recipes')
    for i,recipe in enumerate(t['recipes']):
        require(recipe['when']==clauses[i] and recipe['status']=='PLANNED_NOT_RUN','recipe derivation')
        require('Owner-approved' in recipe['valid_red'] and 'compile exit 0' in recipe['valid_red'] and 'invalid RED' in recipe['valid_red'],'valid RED gates')
        require(recipe['runner'].startswith('BLOCKED_PENDING_APPROVED'), 'no invented runner')
    return errors

mutations=[]
def mutation(name, action):
    changed=copy.deepcopy(trace); action(changed)
    errors=[e for e in validate(changed) if e not in validate(trace)]
    mutations.append({'id':name,'rejected':bool(errors),'errors':errors})
mutation('wrong-AC',lambda t:t['trace'][0].update(criterion='來源可被修改'))
mutation('wrong-BDD',lambda t:t['trace'][0].update(original_bdd=['BDD-09']))
mutation('direct-feature-proof',lambda t:t['trace'][0].update(bdd_relationship='direct F02 proof'))
mutation('wrong-test',lambda t:t['tests'][0].update(name='m02_t07_same_binding_is_valid'))
mutation('wrong-path',lambda t:t['tests'][0].update(source='missing.rs'))
mutation('wrong-hash',lambda t:t['sources'].update({test_source:'0'*64}))
mutation('unsupported-feature-PASS',lambda t:t['trace'][1].update(verdict='PASS'))
mutation('native-PASS',lambda t:t['gates'].update(native='PASS'))
mutation('golden-PASS',lambda t:t['gates'].update(build_golden14='PASS'))
mutation('current-test-claim',lambda t:t['tests'][0].update(executed_this_run=True))
mutation('current-product-claim',lambda t:t['gates'].update(product_tests_this_run='PASS'))
mutation('skip-Owner-RED',lambda t:t['recipes'][0].update(valid_red='static checker passes'))
baseline_all=validate(trace)
baseline=[e for e in baseline_all if e!='input hash:docs/board.json']
inventory_path=ROOT/trace['inventory_authority']
inventory=read(inventory_path)['source_hashes']
drift=[p for p,h in inventory.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
seal=read(PREP/'seal.json')
seal_drift=[p for p,h in seal['files'].items() if sha(PREP/p)!=h]
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
results={'status':'PASS_PREPARATION_ONLY' if not baseline and not drift and not seal_drift and all(m['rejected'] for m in mutations) else 'FAIL', 'reviewer':'/root/f02_feature_trace_review','author':'/root/f02_feature_trace_packet','baseline_errors':baseline,'mutation_count':len(mutations),'mutations':mutations,'head':head,'inventory_count':len(inventory),'product_drift':drift,'preparation_seal_drift':seal_drift,'board_management_diff_separate': [e for e in baseline_all if 'docs/board.json' in e], 'counts':{'features':1,'original_BDD_shared':2,'AC02_clauses':3,'test_pointers':6,'planned_recipes':3},'product_tests':'NOT RUN','build':'NOT RUN','native':'NOT RUN','valid_RED':'NOT RUN','full_Draft':'NOT RUN','feature_PASS':False,'module_PASS':False,'Skeleton_authority':False,'Gray_retained':True}
(HERE/'checker-result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
