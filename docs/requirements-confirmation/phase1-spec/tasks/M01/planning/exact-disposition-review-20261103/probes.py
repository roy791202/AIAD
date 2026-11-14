import pathlib, json, hashlib, subprocess, copy, datetime, html
ROOT=pathlib.Path('D:/AIAD')
BASE=ROOT/'docs/requirements-confirmation/phase1-spec/tasks'
OUT=pathlib.Path(__file__).parent
CAND=BASE/'M01/planning/exact-disposition-register-20261103'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v): (OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pointer(p,s):
    x=read(ROOT/p)
    for t in s.split('/')[1:]:
        t=t.replace('~1','/').replace('~0','~')
        x=x[int(t)] if isinstance(x,list) else x[t]
    return x
def refs(x):
    if isinstance(x,dict):
        if {'path','sha256','pointer'} <= x.keys(): yield x
        for v in x.values(): yield from refs(v)
    elif isinstance(x,list):
        for v in x: yield from refs(v)
def semantic(d):
    assert len(d['cards'])==31 and len({c['id'] for c in d['cards']})==31
    assert {l:sum(c['light']==l for c in d['cards']) for l in ['Yellow','Gray','Red']}=={'Yellow':8,'Gray':18,'Red':5}
    assert all(c['action'] and c['provider'] and c['selected'] is None for c in d['cards'])
    io=d['cards'][0]; assert io['owner_adoption_required'] is False
    m3=next(c for c in d['cards'] if c['id']=='PD-P1-M03-PREP-01')
    assert len(m3['media_decisions'])==8 and all(x['selected'] is None and x['options'] for x in m3['media_decisions'])
    m2=next(c for c in d['cards'] if c['id']=='PD-P1-M02-PREP-01')
    assert len(m2['golden14_provider_inputs'])==14 and len({r['path'] for r in m2['golden14_provider_inputs']})==14
    assert d['next_packet']['no_new_owner_adoption_needed_for_candidate_preparation'] is True
    assert d['product_tests_build_native_package']=='NOT RUN' and d['historical_PASS']=='NOT RERUN'
    for r in refs(d):
        assert sha(ROOT/r['path'])==r['sha256'] or r['path']=='docs/board.json'
        pointer(r['path'],r['pointer'])
def main():
    r=read(CAND/'register.json'); board_before=sha(ROOT/'docs/board.json'); candidate_before={p.name:sha(p) for p in CAND.iterdir() if p.is_file()}
    bindings=[]
    for v in refs(r):
        pointer(v['path'],v['pointer'])
        bindings.append({**v,'actual_sha256':sha(ROOT/v['path']),'status':'MATCH' if sha(ROOT/v['path'])==v['sha256'] else 'MANAGEMENT_SNAPSHOT_DRIFT' if v['path']=='docs/board.json' else 'FAIL'})
    semantic(r)
    auth=read(BASE/'M01/planning/s2-green/source-current.json')
    drift=[p for p,h in auth['source_hashes'].items() if sha(ROOT/p)!=h]
    board=read(ROOT/'docs/board.json')
    card_results=[]
    for c in r['cards']:
        actual=next(i for i in board['items'] if i['id']==c['id'])
        original=read(BASE/(c['id']+'.json')) if (BASE/(c['id']+'.json')).exists() else None
        card_results.append({'id':c['id'],'light':actual['light'],'light_matches':actual['light']==c['light'],'action':c['action'],'provider':c['provider'],'original_scope_read':original is not None,'selection':c['selected'],'verdict':'BOUNDED_ROUTING_PRESENT_EXACTNESS_LIMITED' if c['light']=='Yellow' and '-M0' in c['id'] else 'BOUNDED_ROUTING_PRESENT'})
    media=read(BASE/'M03/planning/preview-media-candidate-20261103/candidate.json')
    m3=next(c for c in r['cards'] if c['id']=='PD-P1-M03-PREP-01')
    assert all(x['options']==y['candidate_dispositions'] and x['question']==y['owner_question'] for x,y in zip(m3['media_decisions'],media['rows']))
    golden=read(BASE/'M02/planning/golden14-lock-inventory-20261103/candidate.json')
    assert all(x['submitted_resource']['bytes'] is None and x['golden']['expected_rendered_bytes'] is None for x in golden['rows'])
    prior_reviews={}
    for path in ['M02/planning/golden14-lock-review-20261103/results.json','M03/planning/preview-media-review-20261103/findings.json','M08/verification/input-admission-correction-review-20261103/results.json']+['decisions/G0%d-review/results.json'%i for i in range(1,5)]:
        q=read(BASE/path); prior_reviews[path]={'sha256':sha(BASE/path),'verdict':q.get('verdict',q.get('status')),'use':'read bounded prior document verdict only; not rerun'}
    negatives=[]
    mutations=[('selection',lambda d:d['cards'][1].update(selected='adopt')),('IO adoption gate',lambda d:d['cards'][0].update(owner_adoption_required=True)),('M03 dimension missing',lambda d:next(c for c in d['cards'] if c['id']=='PD-P1-M03-PREP-01')['media_decisions'].pop()),('M02 duplicate path',lambda d:next(c for c in d['cards'] if c['id']=='PD-P1-M02-PREP-01')['golden14_provider_inputs'][0].update(path='program/src-tauri/build.rs')),('extra Owner candidate gate',lambda d:d['next_packet'].update(no_new_owner_adoption_needed_for_candidate_preparation=False)),('false runtime PASS',lambda d:d.update(product_tests_build_native_package='PASS')),('source hash tamper',lambda d:d['authority'].update(sha256='0'*64)),('unresolvable pointer',lambda d:d['authority'].update(pointer='/missing-review-probe'))]
    for name,f in mutations:
        d=copy.deepcopy(r); f(d)
        try: semantic(d); rejected=False
        except (AssertionError,KeyError,IndexError,ValueError): rejected=True
        negatives.append({'probe':name,'rejected':rejected,'method':'in-memory mutation; no candidate writes'})
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    gitdiff=subprocess.check_output(['git','diff','--name-only',auth['head'],head],cwd=ROOT,text=True).splitlines()
    seal=read(CAND/'seal.json'); seal_ok=all(sha(CAND/n)==h for n,h in seal['payload'].items())
    findings=[{'id':'F01','priority':'P2','status':'OPEN','location':'register.json /cards/1..7/decision and index.html','problem':'Exact-disposition deliverable remains document-level routing: adopted_current_status and pending_candidate point to whole documents; generic adopt/return/defer options do not enumerate exact adopted field sets/revisions versus pending selectable field values. HTML shows generic action/provider/missing text and does not expose adoption record contents. M03 MM01-MM08 is the stronger explicit exception.','evidence':'M01 existing adoption names M01-S2-D1..D7 and review_revision_sha256; register does not project those values. Seven module Yellow entries have pointer empty for adopted_current_status/pending_candidate and a generic three-option decision.','required_correction':'Project exact already-adopted revision/fields with source JSON pointers; separately enumerate each pending decision field/value/option and its effect. Preserve selected=null. Do not seek readoption of existing S1/S2 slices.'},{'id':'F02','priority':'P2','status':'OPEN','location':'register.json /next_packet/output_scope_proposal and /next_packet/acceptance','problem':'New deliverable is legitimate actual golden14 resource bytes/goldens/standalone lock evidence beyond completed inventory, but this is a proposal rather than an executable dispatch packet: exact writable path is deferred to coordinator and acceptance entries have no runnable command/fixture/check definition.','evidence':'output_scope_proposal literally requires coordinator to assign an exact new writable path before dispatch; acceptance is five prose strings. Prior inventory rows still have bytes and expected_rendered_bytes null.','required_correction':'Before dispatch assign a new exact candidate-only M02 path, name files/deliverables and offline deterministic byte/hash/provenance checks and pending external resolver evidence. Candidate preparation requires no extra Owner adoption. Do not recreate inventory as the claimed new deliverable.'}]
    results={'reviewer':'/root/exact_disposition_review','author':r['author'],'verdict':'CHANGES_REQUESTED_BOUNDED_DOCUMENT_COMPLETENESS','checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate_heartbeat':r['heartbeat'],'current_review_instruction_heartbeat':'2026-11-03T15:17:08.858Z','head':head,'historical_head':auth['head'],'head_diff_paths':gitdiff,'authority':{'path':'M01/planning/s2-green/source-current.json','count':len(auth['source_hashes']),'drift':drift},'counts':r['counts'],'binding_occurrences':len(bindings),'nonmanagement_binding_failures':[b for b in bindings if b['status']=='FAIL'],'seal_payload_intact':seal_ok,'semantic_negative_probes':negatives,'candidate_unchanged':candidate_before=={p.name:sha(p) for p in CAND.iterdir() if p.is_file()},'board_unchanged_by_review':board_before==sha(ROOT/'docs/board.json'),'management_snapshot':{'candidate_hash':r['cards'][0]['board']['sha256'],'current_hash':board_before,'limit':'No candidate-time old board bytes available; do not reconstruct. Parent reports subsequent own M01 append note/item/root timestamp update; classify observed management snapshot drift separately from 796 authority and board-only HEAD commit. Whole-board exclusive diff cannot be proved from hashes alone.'},'prior_reviews_read':prior_reviews,'cards':card_results,'not_run':['historical PASS suites','product/native/runtime tests','valid RED/GREEN','build/package/install/DCC','Owner adoption','module completion'],'findings':findings}
    assert len(bindings)==115 and len(auth['source_hashes'])==796 and not drift and seal_ok and all(n['rejected'] for n in negatives)
    save('source-bindings.json',bindings); save('findings.json',{'verdict':results['verdict'],'findings':findings}); save('results.json',results)
    (OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Exact disposition independent review</title><h1>CHANGES REQUESTED — document completeness only</h1><p>31 cards / 115 source bindings / 796 authority files checked. No product or historical suites rerun.</p><pre>'+html.escape(json.dumps({'findings':findings,'results':results},ensure_ascii=False,indent=2))+'</pre>',encoding='utf-8')
    save('seal.json',{'reviewer':'/root/exact_disposition_review','sealed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'payload':{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='seal.json'},'instruction':'Review sealed; stop all writes. No candidate/board/product changes.'})
    print(json.dumps({'verdict':results['verdict'],'bindings':len(bindings),'authority':len(auth['source_hashes']),'negative_probes':len(negatives),'findings':len(findings),'board_drift':results['management_snapshot']},ensure_ascii=False))
if __name__=='__main__': main()
