"""Independent F09 document semantics review. Does not execute product code."""
import copy
import hashlib
import json
import pathlib
import re
import subprocess

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[5]
PREP = OUT.parent / 'feature-trace-preparation'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate(trace, evidence, bindings):
    errors = []
    original = read(ROOT / 'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F09-DELIVERY-01.json')
    feature = (ROOT / 'docs/requirements-confirmation/phase1-spec/phase1.feature').read_text(encoding='utf-8-sig')
    rows = trace['exact_and_shared_trace']
    expected = [('BDD-15','REQ-12'),('BDD-16','REQ-11'),('BDD-17','REQ-14'),('BDD-18','REQ-14'),('BDD-19','REQ-11'),('BDD-21','REQ-15')]
    if len(rows) != 6:
        errors.append('row-count')
    for row, (bdd, req) in zip(rows, expected):
        if (row['bdd'],row['requirement']) != (bdd,req):
            errors.append('bdd-requirement')
        match = re.search(r'  @'+bdd+r'\b.*?(?=\n  @|\Z)',feature,re.S)
        if not match or row['original_scenario'] != match.group(0).strip():
            errors.append('original-bdd-content')
        if row['acceptance'] != ('AC09; AC10 shared' if bdd == 'BDD-21' else 'AC09'):
            errors.append('acceptance-binding')
        if row['relationship'] != ('shared cross-module exact scenario' if bdd == 'BDD-21' else 'exact original scenario'):
            errors.append('relationship')
        if row['status'] != 'PLANNED_NOT_RUN':
            errors.append('false-current-feature-evidence')
        if 'After Owner/envelope/Skeleton approval' not in row['valid_RED'] or 'Compile/fixture/environment/unknown test target is invalid RED' not in row['valid_RED']:
            errors.append('red-gate')
    if trace['original_packet'] != original or trace['original_thresholds'] != original['acceptance']:
        errors.append('original-ac-packet')
    if trace['zone'] != 'gray' or trace['status'] != original['status']:
        errors.append('unauthorized-state')
    if len(trace['prospective_AC_recipes']) != 5 or any(x['status'] != 'PLANNED_NOT_RUN' or not x['equivalence_limit'] for x in trace['prospective_AC_recipes']):
        errors.append('prospective-separation')
    if trace['context_only'].get('BDD-09/10') != 'F08 ESS independent copy/name collision, not exact F09 merge':
        errors.append('import-context-equivalence')
    rollback = rows[4]['fixture_recipe']['then']
    if rollback != 'complete semantic target state restored; no Undo; source unchanged':
        errors.append('rollback-narrowing')
    conflict = evidence['transaction_conflict']
    if 'Owner/G02 must reconcile' not in conflict or 'do not silently reinterpret original BDD' not in conflict or 'before production' not in conflict:
        errors.append('failure-taxonomy-unapproved')
    for item in bindings:
        if not (ROOT/item['path']).is_file() or digest(ROOT/item['path']) != item['sha256']:
            errors.append('source-binding:'+item['path'])
    return sorted(set(errors))

def main():
    trace,evidence,bindings = [read(PREP/name) for name in ('trace.json','evidence-and-gaps.json','inputs.json')]
    source_changes = [{'path':x['path'],'author':x['sha256'],'current':digest(ROOT/x['path'])} for x in bindings if digest(ROOT/x['path']) != x['sha256']]
    # Board is management state, explicitly separated from product/spec integrity.
    live_bindings = [x for x in bindings if x['path'] != 'docs/board.json']
    baseline = validate(trace,evidence,live_bindings)
    cases=[]
    def probe(name, mutate, expected):
        t,e,b=copy.deepcopy(trace),copy.deepcopy(evidence),copy.deepcopy(live_bindings)
        mutate(t,e,b)
        actual=validate(t,e,b)
        cases.append({'id':name,'expected_error':expected,'observed':actual,'detected':expected in actual})
    probe('wrong-ac',lambda t,e,b:t['exact_and_shared_trace'][0].update(acceptance='AC08'),'acceptance-binding')
    probe('wrong-bdd',lambda t,e,b:t['exact_and_shared_trace'][0].update(bdd='BDD-09'),'bdd-requirement')
    probe('wrong-source-hash',lambda t,e,b:b[0].update(sha256='0'*64),'source-binding:'+live_bindings[0]['path'])
    probe('wrong-relation',lambda t,e,b:t['exact_and_shared_trace'][0].update(relationship='prospective recipe'),'relationship')
    probe('shared-as-owned',lambda t,e,b:t['exact_and_shared_trace'][5].update(relationship='exact original scenario'),'relationship')
    probe('rollback-narrowing',lambda t,e,b:t['exact_and_shared_trace'][4]['fixture_recipe'].update(then='precommit only; retain committed state'),'rollback-narrowing')
    probe('deferred-as-approved',lambda t,e,b:e.update(transaction_conflict='Owner/G02 approved postcommit retention as complete rollback'),'failure-taxonomy-unapproved')
    probe('current-feature-pass',lambda t,e,b:t['exact_and_shared_trace'][4].update(status='PASS'),'false-current-feature-evidence')
    probe('copy-context-as-equivalent',lambda t,e,b:t['context_only'].update({'BDD-09/10':'exact successful F09 merge'}),'import-context-equivalence')
    probe('prospective-as-green',lambda t,e,b:t['prospective_AC_recipes'][0].update(status='GREEN'),'prospective-separation')
    probe('red-before-approval',lambda t,e,b:t['exact_and_shared_trace'][0].update(valid_RED='Any failing test permits production'),'red-gate')
    inventory=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
    product_drift=[p for p,h in inventory['source_hashes'].items() if not (ROOT/p).is_file() or digest(ROOT/p)!=h]
    seal=read(PREP/'seal.json')
    seal_drift=[p for p,h in seal['files'].items() if digest(PREP/p)!=h]
    report={'reviewer':'/root/f09_feature_trace_review','author':'/root/f09_feature_trace_packet','verdict':'PASS_PREPARATION_DOCUMENT_SCOPE_ONLY' if not baseline and not product_drift and not seal_drift and all(x['detected'] for x in cases) else 'FAIL', 'baseline_errors':baseline,'semantic_probes':len(cases),'detected':sum(x['detected'] for x in cases),'findings':[], 'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'inventory_historical_head':inventory['head'],'inventory_count':len(inventory['source_hashes']),'product_drift':product_drift,'author_source_bindings':len(bindings),'author_sealed_files':len(seal['files']),'author_seal_drift':seal_drift,'management_input_changes_separate':source_changes,'gray_retained':True,'feature_module_pass':False,'skeleton_authority':False,'NOT_RUN':['product tests','build','native UI','actual archive merge','valid RED','full Draft','independent feature acceptance'], 'interpretation':'Original BDD-19 full recovery at any commit failure remains unchanged. Postcommit MergeAppliedRetentionDeferred proposal requires Owner/G02 failure-taxonomy reconciliation; no approved SPEC_CONFLICT or silent weakening. S1 historical source/log, 64 preflight document oracles and 184 document calls are contextual only.'}
    (OUT/'fixtures.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (OUT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,ensure_ascii=False))

if __name__ == '__main__':
    main()
