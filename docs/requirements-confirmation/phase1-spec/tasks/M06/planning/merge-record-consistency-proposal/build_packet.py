"""Generate only this bounded proposal. Execute with python -B."""
from pathlib import Path
import copy, hashlib, html, importlib.util, json, subprocess
P=Path(__file__).resolve().parent
S=P.parent/'merge-retention-handoff'
R=P.parents[6]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
c=read(S/'immutable-issuer-fixture.json')
write('retained-issuer-fixture.json',c)
mapping=[]
def schema(v,path=''):
    mapping.append({'pointer':'/'+path,'guard':'exact retained value and type; required object member; unknown members rejected','authority': 'merge-retention-handoff/immutable-issuer-fixture.json#/'+path,'status':'PROPOSED_PENDING_OWNER'})
    if isinstance(v,dict):return {'type':'object','additionalProperties':False,'required':list(v),'properties':{k:schema(a,path+'/'+k if path else k) for k,a in v.items()}}
    if isinstance(v,list):
        for i,a in enumerate(v):schema(a,path+'/'+str(i))
        return {'type':'array','minItems':len(v),'maxItems':len(v),'const':v,'items':{}}
    return {'type':'null' if v is None else 'boolean' if type(v)==bool else 'string','const':v}
write('record-domain.schema.json',schema(c))
spec=importlib.util.spec_from_file_location('proposal',P/'model.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
fixtures=read(S/'fixtures.json');base=copy.deepcopy(fixtures[0]['input']);base.update(commit_observation='Applied',root_observation='Verified',perform_undo=False)
results=[]
def setpath(o,path,v):
    for key in path[:-1]:o=o[key]
    o[path[-1]]=v
def run(name,x,cat=None,expected=None):
    got=m.evaluate(x,cat)
    results.append({'id':name,'request':x,'record_override':cat,'expected':expected,'actual':got,'passed':got['result']==expected if expected else True})
for f in fixtures:
    before=m.run_legacy(f['input'],c);run('original-'+f['id'],f['input'],expected=before['result'])
    results[-1]['exact_original_output_preserved']=results[-1]['actual']==before
old=read(P.parent/'merge-retention-review/new-fixtures-and-results.json')
diagnostics=[]
for f in old:
    if f['id'].startswith('defensive-'):
        cat=f['issuer_fixture_override'];run(f['id'],f['input'],cat,'RecordConsistencyRejected')
        diagnostics.append({'id':f['id'],'changed_path':f['changed_path'],'before':f['actual'],'after':results[-1]['actual'],'interpretation':'Expanded defensive trusted-record consistency domain; historical review remains valid under its stated premise.'})
def walk(v,path=()):
    yield path,v
    if isinstance(v,dict):
        for k,a in v.items():yield from walk(a,path+(k,))
    if isinstance(v,list):
        for i,a in enumerate(v):yield from walk(a,path+(i,))
for path,v in walk(c):
    if not path:continue
    pointer='/'.join(map(str,path))
    changed=copy.deepcopy(c);setpath(changed,path,{'invalid_type':True} if not isinstance(v,dict) else 'wrong-type')
    run('type-or-value:'+pointer,base,changed,'RecordConsistencyRejected')
    if isinstance(v,dict):
        changed=copy.deepcopy(c);target=changed
        for k in path:target=target[k]
        target['undeclared']=True;run('unknown:'+pointer,base,changed,'RecordConsistencyRejected')
        for key in v:
            changed=copy.deepcopy(c);target=changed
            for k in path:target=target[k]
            del target[key];run('missing:'+pointer+'/'+key,base,changed,'RecordConsistencyRejected')
    elif isinstance(v,str):
        changed=copy.deepcopy(c);setpath(changed,path,v+'-contradiction');run('contradiction:'+pointer,base,changed,'RecordConsistencyRejected')
for name,updates,expected in [('new-normal',{},'MergeApplied'),('new-undo',{'perform_undo':True,'undo_root_observation':'Verified'},'UndoApplied'),('proof-loss',{'root_observation':'Failure'},'MergeAppliedRetentionDeferred'),('unknown-commit',{'commit_observation':'Unknown'},'UnverifiedOutcome'),('unknown-undo',{'perform_undo':True,'undo_observation':'Unknown'},'UnverifiedOutcome')]:
    x=copy.deepcopy(base);x.update(updates);run(name,x,expected=expected)
varied=copy.deepcopy(c)
def offset(v):
    if isinstance(v,dict):
        for key,a in v.items():
            if key=='expected_catalog_generation' or key in ('expected_generation','committed_generation') and 'request_digest' in v:v[key]=str(int(a)+10)
            else:offset(a)
    elif isinstance(v,list):
        for a in v:offset(a)
offset(varied)
for record,req in zip([varied['import_record']]+varied['transfer_records'],[varied['import_request']]+varied['merge_transfer']+varied['undo_transfer']):record['request_digest']=m.legacy.digest(req)
x=copy.deepcopy(base)
for key in ['import_request','merge_publish','merge_transfer','undo_publish','undo_transfer']:x[key]=copy.deepcopy(varied[key])
run('coherent-CAS-plus-10',x,varied,'MergeApplied')
write('before-after-nine.json',diagnostics)
write('cases-and-results.json',results)
write('field-mapping.json',mapping)
owners=read(S/'owner-choices.json');write('owner-choices.json',owners)
inventory=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
source_drift=[n for n,h in inventory['source_hashes'].items() if not (R/n).is_file() or sha(R/n)!=h]
central=P.parent/'cx-exchange-revision-v3/shared-contract.json'
inputs=[S/'model.py',S/'immutable-issuer-fixture.json',S/'fixtures.json',S/'transition-request.schema.json',central,P.parent/'merge-retention-review/review.json',R/'docs/board.json',P.parent/'current-state.json',R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json']
write('source-pointers.json',{'inputs':{str(p.relative_to(R)):sha(p) for p in inputs},'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'inventory_head':inventory['head'],'authority':'M01/planning/s2-green/source-current.json, 796 tracked hashes, distinct from historical 31babe','source_count':len(inventory['source_hashes']),'source_drift':source_drift,'central_request_schema_parity':read(S/'transition-request.schema.json')==read(central)['request_hash_schema']})
board=read(R/'docs/board.json')
def find(v):
    if isinstance(v,dict):
        if v.get('id')=='PD-P1-M06-PREP-01':yield v
        for a in v.values():yield from find(a)
    elif isinstance(v,list):
        for a in v:yield from find(a)
write('board-readonly.json',list(find(board)))
specdoc={'module':'M06','task':'PD-P1-M06-PREP-01','state':'PROPOSED_PENDING_OWNER','scope':'one bounded DOCUMENT record-domain consistency validator; no Skeleton','intent':'Close MR-F1 defensive consistency coverage over all retained immutable fixture fields before documentary commit.','architecture':{'owner':'M04 exclusive document mutation; M05 owns pins/catalog','driving_adapter':'document fixture runner','input':'proposed document evaluate boundary','output':'state/call result projection only','ports':'No new Port','transaction':'record validation before modeled document commit; native atomicity remains premise'},'schema_parity':'Closed record-domain schema and oracle use the identical schema through legacy.valid; array values locked wholesale, nested pointers enumerated for traceability. Exact retained values intentionally reject otherwise plausible alternate records; not a general registry validator.','mapping':'field-mapping.json includes every represented field; request digest/context/target/issuer/receipt/source/purpose/assets/CAS/fence are frozen exact assertions. Unavailable native receipt issuance/raw digest provenance remains trusted premise.','precedence':['caller shape InvalidInput','closed record schema RecordConsistencyRejected','existing ProofMismatch','existing observation outcomes'],'guards':'All new guards, rejection vocabulary and error precedence PROPOSED_PENDING_OWNER','bdd':['RC-1 valid original behavior','RC-2 contradictory/missing/unknown/type record rejected before commit','RC-3 proof loss and unknown outcomes preserve existing semantics'],'tdd':'DOCUMENT executable diagnostics only. Product TDD planned; valid RED NOT RUN.','acceptance':['original 15 outputs exact','nine review perturbations rejected','every declared field enumerated with mutation evidence','no source/board/current-state writes','MH1..MH6 pending'],'not_run':['independent re-review','native','build','product tests','valid RED','full Draft'],'premises':c['premises'],'owner_choices':owners,'counts':{'original':len(fixtures),'review_diagnostics':len(diagnostics),'field_pointers':len(mapping),'cases':len(results),'passed':sum(r['passed'] for r in results)}}
write('module-spec.json',specdoc)
write('trace.json',{'bdd_to_tdd':[{'bdd':b,'planned_tdd':'TDD-'+b,'fixture':'cases-and-results.json','product_status':'NOT RUN'} for b in ['RC-1','RC-2','RC-3']],'field_mapping':'field-mapping.json','state_calls':'every case contains complete actual result/state/calls','skeleton':'NOT CREATED','pending_automation':['native issuer lookup','actual M04/M05 transaction','independent review','product BDD steps']})
(P/'module.feature').write_text('Feature: Bounded documentary issuer record consistency\n  Background:\n    Given the retained trusted fixture premise\n  Rule: Inconsistent records cannot authorize documentary mutation\n    Scenario: RC-1 Valid retained records preserve prior behavior\n      When the documented operation is evaluated\n      Then its original state and call output is preserved\n    Scenario: RC-2 Contradictory record is rejected\n      Given a missing unknown mistyped or contradictory retained record field\n      When the documented operation is evaluated\n      Then rejection occurs before document commit\n    Scenario: RC-3 Unknown observations remain unverified\n      When a commit observation is unknown\n      Then the outcome is unverified without retry or rollback\n',encoding='utf-8')
(P/'steps_pending.py').write_text('"""Planned product BDD stubs; no executable product verification claimed."""\ndef given_retained_fixture(context):\n    raise NotImplementedError("native fixture adapter pending Owner")\ndef when_evaluated(context):\n    raise NotImplementedError("product input boundary not adopted")\ndef then_precommit_reject(context):\n    raise NotImplementedError("independent product verification NOT RUN")\n',encoding='utf-8')
body='<h1>M06 record consistency proposal</h1><p>PROPOSED_PENDING_OWNER — documentary proof-domain extension only. No Skeleton, no product acceptance.</p><p>MR-F1 is a trusted fixture coverage limitation, not a caller exploit or native authenticity defect. The old handoff/review remain unchanged.</p><h2>System boundary</h2><pre>Fixture runner → document evaluator → closed record schema → retained legacy DOCUMENT oracle → state/call projection\nM04 exclusive mutation owner; M05 pins/catalog. No persistence or new Port.</pre><h2>Dependency and transaction</h2><pre>proposal → retained handoff model + CXv3 request schema\ncaller shape → record consistency → existing proof checks → modeled commit → publish/transfer\nUndo: separate workflow + Undo Held premise; no Import pin reuse</pre><h2>Scope and evidence</h2><p>Exact frozen fixture domain, not general catalog validation. All field mapping, individual mutations and complete states/calls are linked below. Native authenticity/atomicity remain premises. All proposed guard/error precedence and MH1–MH6 await Owner.</p>'
for name in ['module-spec.json','field-mapping.json','before-after-nine.json','cases-and-results.json','source-pointers.json','trace.json','owner-choices.json','module.feature','steps_pending.py']:body+='<p><a href="'+name+'">'+name+'</a></p>'
body+='<h2>Module specification and results</h2><pre>'+html.escape(json.dumps(specdoc,indent=2))+'</pre><script type="application/json" id="module-spec">'+json.dumps(specdoc).replace('<','\\u003c')+'</script>'
(P/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M06 documentary proposal</title><style>body{max-width:1100px;margin:40px auto;font:16px system-ui;background:#111827;color:#eee}a,h1,h2{color:#fbbf24}pre{white-space:pre-wrap}</style>'+body,encoding='utf-8')
assert len(diagnostics)==9 and all(r['passed'] for r in results)
assert all(r['exact_original_output_preserved'] for r in results[:len(fixtures)])
write('seal.json',{'scope':'bounded proposal only','counts':specdoc['counts'],'files':{p.name:sha(p) for p in P.iterdir() if p.is_file() and p.name!='seal.json'}})
print(json.dumps(specdoc['counts']))
