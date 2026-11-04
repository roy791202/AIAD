"""Closed DOCUMENT candidate checks only; never runs product/native/historical tests."""
import copy, hashlib, json, pathlib
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[6]
def load(n): return json.loads((OUT/n).read_text(encoding='utf-8'))
def validate(p,f,g,y):
    assert p['layer']=='DOCUMENT_ONLY' and p['module_complete'] is False
    assert p['reviewer'] is None and p['approval'] is None
    for key in ['owner_selection','format','sdk','thresholds']: assert p[key] is None
    assert p['product_native_decode_render_build']=='NOT RUN'
    assert len(f['recipes'])==8 and {r['dimension'] for r in f['recipes']}=={f'MM{i:02}' for i in range(1,9)}
    for r in f['recipes']:
        for key in ['format','sdk','thresholds','selection']: assert r[key] is None
        assert {c['category'] for c in r['cases']}=={'normal','invalid','empty','boundary','permission','timeout','dimension-specific'}
        for c in r['cases']:
            assert c['recipe'] and c['observable_oracle_candidate']
            assert c['execution']=='NOT RUN' and c['fixture_bytes'] is None and c['fixture_sha256'] is None and c['owner_outcome'] is None
            assert c['applicability'] in ['Applicable','Deferred','Not Applicable']
            if c['applicability']!='Applicable': assert c['deferred_reason']
    assert len(g)==14 and len({r['path'] for r in g})==14
    for r in g:
        assert r['authority']['pointer'].startswith('/rows/')
        assert r['missing_resource_bytes']['bytes'] is None
        assert r['missing_input_revision_output_bytes_hash']['expected_rendered_bytes'] is None
        assert r['toolchain']['exact_version'] is None and len(r['provider_list'])==3
    assert len(y)==8 and all(r['completion'] is False and r['selection'] is None for r in y)
    assert sum(r['action_this_round']=='DELIVER_M03_FIXTURE_PROVENANCE_CANDIDATE' for r in y)==1
    return True
def main():
    p,f,g,y=load('packet.json'),load('fixtures.json'),load('golden14-handoff.json'),load('yellow-actions.json')
    validate(p,f,g,y)
    assert len(f['provenance']['required_fields'])>=20 and len(f['provenance']['sampling_rules'])==7
    upstream=json.loads((ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M03/planning/preview-media-candidate-20261103/candidate.json').read_text(encoding='utf-8-sig'))
    golden=json.loads((ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M02/planning/golden14-lock-inventory-20261103/candidate.json').read_text(encoding='utf-8-sig'))
    for i,r in enumerate(f['recipes']):
        assert r['source']['pointer']=='/rows/'+str(i) and r['family']==upstream['rows'][i]['family']
    for i,r in enumerate(g):
        assert r['path']==golden['rows'][i]['declared_product_path']
        assert r['missing_resource_bytes']==golden['rows'][i]['submitted_resource']
        assert r['missing_input_revision_output_bytes_hash']==golden['rows'][i]['golden']
        assert r['missing_manifest_lock_resolver']==golden['rows'][i]['lock_provider_evidence']
    probes=[]
    mutations=[('owner auto-adopt',lambda a,b,c,d:a.update(owner_selection='adopted')),('decoder false success',lambda a,b,c,d:b['recipes'][0]['cases'][0].update(execution='PASS')),('missing dimension',lambda a,b,c,d:b['recipes'].pop()),('missing deferred reason',lambda a,b,c,d:b['recipes'][0]['cases'][3].update(deferred_reason=None)),('fabricated bytes',lambda a,b,c,d:b['recipes'][0]['cases'][0].update(fixture_bytes='fake')),('missing provenance oracle',lambda a,b,c,d:b['recipes'][1]['cases'][0].update(observable_oracle_candidate='')),('duplicate golden path',lambda a,b,c,d:c[1].update(path=c[0]['path'])),('missing golden provider',lambda a,b,c,d:c[0].update(provider_list=[])),('false module completion',lambda a,b,c,d:d[0].update(completion=True)),('unselected SDK populated',lambda a,b,c,d:b['recipes'][2].update(sdk='unapproved'))]
    for name,change in mutations:
        args=copy.deepcopy((p,f,g,y));change(*args)
        try: validate(*args)
        except AssertionError: probes.append({'probe':name,'rejected':True})
        else: raise AssertionError('Mutation admitted: '+name)
    drift=[]
    for s in load('source-hashes.json'):
        actual=hashlib.sha256((ROOT/s['path']).read_bytes()).hexdigest()
        if actual!=s['sha256']:drift.append({'path':s['path'],'expected':s['sha256'],'actual':actual})
    product=json.loads((ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf-8-sig'))['source_hashes']
    product_drift=[p for p,h in product.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    result={'author':'/root/yellow_scope_execution','layer':'AUTHOR_DOCUMENT_CHECK_ONLY','new_negative_probes':probes,'source_drift':drift,'product_authority_count':len(product),'product_drift':product_drift,'historical_suites':'NOT RERUN','product_native':'NOT RUN','independent_review':'PENDING','valid_red':'N/A_DOCUMENT_ONLY'}
    print(json.dumps(result,indent=2)); assert not product_drift
    (OUT/'checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
