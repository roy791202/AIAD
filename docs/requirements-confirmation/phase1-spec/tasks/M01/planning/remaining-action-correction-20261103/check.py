"""Static document envelope checks only; never a production behavior test."""
import argparse, copy, json, pathlib, sys
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[6]
def read(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'))
def validate(p):
    m=p['primary_module']
    assert m in ['M02','M03'] and p['allowed_modules']==[m], 'mixed primary module'
    assert p.get('allowed_files') and len(p['allowed_files'])==6, 'missing allowed files'
    prefix='docs/requirements-confirmation/phase1-spec/tasks/'+m+'/planning/'
    assert all(x.startswith(prefix) and '*' not in x and '..' not in x for x in p['allowed_files']), 'outside original module planning scope'
    assert {pathlib.Path(x).name for x in p['allowed_files']}=={'candidate.json','module.feature','steps.py','fixtures.json','pending.json','index.html'}
    assert len({str(pathlib.Path(x).parent) for x in p['allowed_files']})==1
    assert p.get('commands') and all('check.py --' in x for x in p['commands']), 'missing executable commands'
    assert p.get('protected') and p.get('source_refs') and p.get('acceptance')
    assert p.get('bdd_requirements') and p.get('fixture_requirements')
    assert p['valid_red'].startswith('N/A')
    for x in p['source_refs']: assert (ROOT/x).is_file(), 'source missing: '+x
def io_validate(row):
    assert 'Windows11' in row['provider'] and 'fixture provider' in row['provider'] and 'No new Owner adoption required' in row['provider'], 'provider regression'
    assert 'Owner exact candidate disposition' not in row['provider']
def deliverables(p):
    for x in p['allowed_files']: assert (ROOT/x).is_file(), 'missing deliverable: '+x
    paths={pathlib.Path(x).name:ROOT/x for x in p['allowed_files']}
    for name,keys in p['deliverable_schema'].items():
        obj=read(paths[name]); assert all(k in obj for k in keys)
        assert obj['primary_module']==p['primary_module']
    feature=paths['module.feature'].read_text(encoding='utf-8')
    for token in ['Feature:','Background:','Rule:','Scenario:','Given ','When ','Then ']: assert token in feature
    assert paths['steps.py'].stat().st_size>0 and paths['index.html'].stat().st_size>0
    c=read(paths['candidate.json'])
    assert len(c['rows'])==(8 if p['primary_module']=='M03' else 14)
    assert c['not_run'] and all(r.get('source_refs') and r.get('oracle') for r in c['rows'])
    if p['primary_module']=='M03':
        assert all(r.get('decoder_sdk') is None and r.get('limits') is None and r.get('support')=='UNSELECTED_NOT_APPROVED' for r in c['rows'])
    else:
        inventory=read(HERE.parent/'remaining-action-dispatch-20261103/template14-source-inventory.json')
        assert {r['declared_product_path'] for r in c['rows']}==set(inventory['baseline']['product_paths'])
        assert all(r.get('proof_status') in ['MISSING_ADMITTED_EVIDENCE','PROPOSED_NOT_ACCEPTED'] for r in c['rows'])
def rejected(fn,obj):
    try: fn(obj)
    except (AssertionError,KeyError): return True
    return False
def selftest(ps,cards):
    cases=[]
    mutations=[('mixed_primary',lambda p:p.update(allowed_modules=['M03','M02'])),('missing_allowed_files',lambda p:p.pop('allowed_files')),('missing_commands',lambda p:p.pop('commands'))]
    for name,mutate in mutations:
        p=copy.deepcopy(ps[0]); mutate(p); cases.append({'id':name,'expected':'REJECT','pass':rejected(validate,p)})
    row=copy.deepcopy(cards['cards'][0]); row['provider']='Owner exact candidate disposition'; cases.append({'id':'provider_regression','expected':'REJECT','pass':rejected(io_validate,row)})
    fixture=read(HERE/'fixtures.json')
    assert {x['id'] for x in cases}=={x['id'] for x in fixture['cases']}
    assert all(x['pass'] for x in cases)
    return cases
if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--packet'); parser.add_argument('--deliverables'); args=parser.parse_args()
    ps=read(HERE/'task-packets.json'); cards=read(HERE/'31-card-actions.json')
    for p in ps:
        if not args.packet or p['primary_module']==args.packet: validate(p)
        if args.deliverables==p['primary_module']: deliverables(p)
    io_validate(cards['cards'][0]); assert len(cards['cards'])==31
    original=read(HERE.parent/'remaining-action-dispatch-20261103/31-card-actions.json')
    for i,(before,after) in enumerate(zip(original['cards'],cards['cards'])):
        expected=copy.deepcopy(before)
        if i==0: expected['provider']=after['provider']
        assert expected==after, 'unexpected per-card drift'
    print(json.dumps({'status':'PASS','layer':'AUTHOR_STATIC_DOCUMENT_CHECK_ONLY','negative_fixtures':selftest(ps,cards),'product':'NOT RUN','valid_red':'N/A'},indent=2))
