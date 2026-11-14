import json, hashlib, pathlib, subprocess, datetime, html
ROOT=pathlib.Path('D:/AIAD')
BASE='docs/requirements-confirmation/phase1-spec/tasks/'
OUT=ROOT/(BASE+'M01/planning/exact-disposition-register-20261103')
def read(p): return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def digest(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def ref(p, pointer=''):
    value=read(p)
    if pointer:
        for token in pointer.split('/')[1:]:
            token=token.replace('~1','/').replace('~0','~')
            value=value[int(token)] if isinstance(value,list) else value[token]
    return {'path':p,'sha256':digest(p),'pointer':pointer}
def save(n,v): (OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
oldpath=BASE+'M01/planning/remaining-action-correction-20261103/31-card-actions.json'
old=read(oldpath)['cards']; board=read('docs/board.json'); cards=[]
prohibited=['product implementation','schema/Port/Skeleton change','valid RED authorization','board completion','commit/push/release']
for ix,c in enumerate(old):
    bi=next(i for i,x in enumerate(board['items']) if x['id']==c['id'])
    item=board['items'][bi]
    row={'id':c['id'],'light':item['light'],'board':ref('docs/board.json',f'/items/{bi}'),'prior_action':ref(oldpath,f'/cards/{ix}'),'action':c.get('action',c['original_action']),'missing_conditions':c['missing'],'provider':c['provider'],'selected':None,'cannot_authorize':prohibited}
    row['action']=c.get('action','Request exact pending disposition/provider evidence described in missing_conditions; preserve historical PASS without rerun.')
    if c['light']=='Yellow' and '-M0' in c['id']:
        m=c['id'].split('-')[2]
        row['adopted_current_status']=ref(BASE+m+'/planning/current-state.json')
        candidate=next((p for p in c['refs'][3:] if p.endswith('module-spec.json')),None)
        row['pending_candidate']=ref(candidate) if candidate else None
        row['decision']={'question':c['missing'].split('; exact adopted')[0],'options':['adopt exact hash and explicitly named fields','return with exact changed fields','defer with reason'],'selected':None,'effect':'Record a bounded design disposition only; separately revalidate affected contracts/BDD and approve Skeleton/valid RED before production.'}
        row['existing_adoption_records']=[ref(str(p.relative_to(ROOT)).replace('\\','/')) for p in (ROOT/(BASE+m)).glob('**/adoption.json')]
    if c['id']=='PD-P1-IO-PREREQ-IMPL-01':
        row['action']='Supply Windows11 x64 isolated environment plus native reparse and 8.3 fixtures, then assign different verifier only remaining native matrix.'
        row['owner_adoption_required']=False
    cards.append(row)
mc=BASE+'M03/planning/preview-media-candidate-20261103/candidate.json'; gc=BASE+'M02/planning/golden14-lock-inventory-20261103/candidate.json'
media=read(mc); golden=read(gc)
decisions=[{'id':r['id'],'dimension':r['family'],'source':ref(mc,f'/rows/{i}'),'question':r['owner_question'],'options':r['candidate_dispositions'],'selected':None,'fixture_input_required':r['required_fixture_set'],'approval_effect':'Only exact support subset and explicit policy disposition; no decoding/runtime evidence or renderer authorization.','provider':'Owner for exact support disposition; media fixture/renderer provider for bytes, provenance, decoder/version/limits and native evidence'} for i,r in enumerate(media['rows'])]
resources=[{'slot':r['slot'],'path':r['declared_product_path'],'source':ref(gc,f'/rows/{i}'),'provider':'M02 template author + standalone manifest/lock/toolchain provider; independent fixture reviewer','action':'Submit actual candidate resource bytes and SHA256, definition/design revisions, expected rendered bytes/output digest and provenance; submit independent standalone manifest/lock/resolver/toolchain tuple.','state':'MISSING_ADMITTED_EVIDENCE','selected':None} for i,r in enumerate(golden['rows'])]
for c in cards:
    if c['id']=='PD-P1-M03-PREP-01':
        c['action']='Owner can disposition MM01..MM08 individually below; fixture providers may prepare candidate bytes/provenance now within original planning scope.'
        c['media_decisions']=decisions;c['new_review']=ref(BASE+'M03/planning/preview-media-review-20261103/findings.json')
    if c['id']=='PD-P1-M02-PREP-01':
        c['action']='Provider prepares actual golden14 resource-byte candidates and standalone manifest/lock proof inputs now; inventory/document PASS does not supply these bytes.'
        c['golden14_provider_inputs']=resources;c['new_review']=ref(BASE+'M02/planning/golden14-lock-review-20261103/results.json')
    if '-G0' in c['id']:
        g=c['id'].split('-')[2]; c['pending_candidate']=ref(BASE+'decisions/'+g+'/decision-request.json');c['review']=ref(BASE+'decisions/'+g+'-review/results.json');c['provider']='Owner exact field/revision disposition; named native/fixture providers for subsequent evidence'
    if c['id']=='PD-P1-M08-VERIFY-01': c['review']=ref(BASE+'M08/verification/input-admission-correction-review-20261103/results.json');c['provider']='Feature delivery providers + versioned portable artifact provider + independent native harness provider; Owner only for M08-PD1..PD3 design choice'
    if '-F' in c['id']:
        f=c['id'].split('-')[2]; paths=list((ROOT/BASE).glob('M0*/'+f+'/feature-trace-review/*.json')); c['trace_review']=[ref(str(p.relative_to(ROOT)).replace('\\','/')) for p in paths if p.name in ['results.json','review.json']]
authority=read(BASE+'M01/planning/s2-green/source-current.json'); drift=[p for p,h in authority['source_hashes'].items() if digest(p)!=h]
packet={'id':'M02-GOLDEN14-PROVIDER-INPUT-NEXT','primary_module':'M02','state':'ORIGINAL_SCOPE_CANDIDATE_PREPARATION_AVAILABLE_NOW','input':ref(gc,'/rows'),'provider':'M02 template author and standalone manifest/lock/toolchain provider','permitted_action':'Prepare reviewable resource bytes and immutable provenance/digests for exactly the fourteen declared paths, without adopting resources or altering product. Package standalone manifest/lock resolver evidence; do not borrow workspace-root lock.','output_scope_proposal':'New M02 planning candidate-only package; coordinator must assign an exact new writable path before dispatch. This register writes no M02 files.','acceptance':['14 exact paths each once','bytes/digest/provenance and definition/design input revisions','rendered expected bytes/output hashes','independent standalone manifest/lock/toolchain tuple','explicit unknowns and pending independent review'],'blocked_portion':'Actual build/native proof requires appropriate toolchain and later authorized executable scope; not claimed here.','no_new_owner_adoption_needed_for_candidate_preparation':True,'cannot_authorize':prohibited}
data={'author':'/root/exact_disposition_register','heartbeat':'2026-11-03T15:07:08.441Z','layer':'DOCUMENT_COORDINATION_ONLY','head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'historical_head':authority['head'],'authority_count':len(authority['source_hashes']),'authority_drift':drift,'authority':ref(BASE+'M01/planning/s2-green/source-current.json'),'management_snapshot':'Board hash is current read-time management snapshot; previous candidate board digests retained in their originals.','counts':{v:sum(c['light']==v for c in cards) for v in ['Yellow','Gray','Red']},'cards':cards,'remaining_original_scope':'Actionable candidate preparation remains: actual golden14 provider input package and media fixture/provenance candidate preparation. No claim that all preparation is Owner-blocked. External evidence/adoption gates apply only to their named portions.','next_packet':packet,'product_tests_build_native_package':'NOT RUN','independent_acceptance':'NOT RUN','historical_PASS':'NOT RERUN','selected':None}
save('register.json',data)
bindings=[]
def scan(x):
    if isinstance(x,dict):
        if {'path','sha256','pointer'}<=x.keys():
            checked=ref(x['path'],x['pointer']);assert checked==x;bindings.append(x)
        for y in x.values():scan(y)
    elif isinstance(x,list):
        for y in x:scan(y)
scan(data)
assert data['counts']=={'Yellow':8,'Gray':18,'Red':5} and not drift
assert all(c['action'] and c['provider'] and c['selected'] is None for c in cards)
save('checks.json',{'status':'PASS_AUTHOR_STATIC_COORDINATION_CHECK_ONLY','resolvable_bindings':len(bindings),'cards':31,'null_selections':True,'authority_count':796,'authority_drift':drift,'limits':'No historical PASS rerun; no product test or acceptance.'})
save('source-hashes.json',{'bindings':bindings})
body=''.join('<article><h2>'+html.escape(c['id'])+' · '+c['light']+'</h2><p>'+html.escape(c['action'])+'</p><p>Provider: '+html.escape(c['provider'])+'</p><p>Missing: '+html.escape(c['missing_conditions'])+'</p></article>' for c in cards)
detail=html.escape(json.dumps({'M03_exact_decisions':decisions,'M02_golden14_inputs':resources,'next_packet':packet},ensure_ascii=False,indent=2))
(OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Exact disposition register</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;background:#101a26;color:#e2e8f0}article{padding:18px;border:1px solid #45566a;margin:14px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}h1,h2{color:#f6cd75}</style><h1>31-card exact disposition / provider register</h1><p>8 Yellow · 18 Gray · 5 Red. All selections remain null. Document coordination only; no product/Skeleton/RED authorization. Candidate preparation remains available within original scope.</p><h2>Priority: M03 eight decisions, M02 actual golden14 inputs</h2><pre>'+detail+'</pre>'+body+'<p>Exact hashes and JSON pointers: register.json. All bindings resolved by author static check; independent acceptance NOT RUN.</p><script type="application/json" id="module-spec">'+json.dumps(data,ensure_ascii=False).replace('</','<\\/')+'</script>',encoding='utf-8')
save('seal.json',{'sealed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'author':'/root/exact_disposition_register','payload':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='seal.json'},'instruction':'Sealed; author stops writes. Independent review pending.'})
print(json.dumps({'counts':data['counts'],'bindings':len(bindings),'authority_drift':drift,'output':str(OUT)}))
