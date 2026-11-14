"""Compact reconstructible inputs, correct explicit normal Undo observation, check and seal."""
from pathlib import Path
import copy, hashlib, html, importlib.util, json
P=Path(__file__).resolve().parent
def read(n):return json.loads((P/n).read_text(encoding='utf-8'))
def write(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
spec=importlib.util.spec_from_file_location('proposal_final',P/'model.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
c=read('retained-issuer-fixture.json');rows=read('cases-and-results.json');base=copy.deepcopy(rows[0]['request']);base.update(commit_observation='Applied',root_observation='Verified',perform_undo=False)
write('base-request.json',base)
def diff(a,b,path=()):
    if type(a)!=type(b):return [{'path':list(path),'op':'replace','value':b}]
    if isinstance(a,dict):
        out=[]
        for k in a.keys()-b.keys():out.append({'path':list(path+(k,)),'op':'remove'})
        for k in b.keys()-a.keys():out.append({'path':list(path+(k,)),'op':'add','value':b[k]})
        for k in a.keys()&b.keys():out.extend(diff(a[k],b[k],path+(k,)))
        return out
    if isinstance(a,list) and len(a)==len(b):return [d for i,(x,y) in enumerate(zip(a,b)) for d in diff(x,y,path+(i,))]
    return [] if a==b else [{'path':list(path),'op':'replace','value':b}]
for r in rows:
    if r['id']=='new-undo':
        r['request']['undo_root_observation']='Verified';r['actual']=m.evaluate(r['request']);r['passed']=r['actual']['result']==r['expected']
    r['request_patch']=diff(base,r.pop('request'))
    override=r.pop('record_override')
    r['record_patch']=diff(c,override) if override is not None else []
    r['request_base']='base-request.json';r['record_base']='retained-issuer-fixture.json'
assert all(r['passed'] for r in rows)
assert all(r['exact_original_output_preserved'] for r in rows[:15])
assert all(r['actual']['before']==r['actual']['after'] and not any(r['actual']['calls'].values()) for r in rows if r['expected']=='RecordConsistencyRejected')
write('cases-and-results.json',rows)
doc=read('module-spec.json');doc['counts']['passed']=len(rows)
doc['schema_parity']='Closed schema exact frozen fixture values after relational CAS normalization. normalize_catalog_generations permits a coherent nonnegative u64 CAS offset and recomputes full request digests; IDs/raw evidence remain frozen trusted premises. Not a generic registry.'
doc['mapping']='field-mapping.json enumerates each represented field. All CAS expected/committed generations are mapped relationally with expected+1 preserved; coherent +10 normal case passes. Context/target/issuer/receipt/source/purpose/assets/fence and unavailable native evidence IDs remain exact retained fixture assertions.'
doc['diagnostic_correction']='New normal Undo fixture explicitly uses Verified undo-root observation; inherited Failure observation originally returned the correct deferred result. No product/test expectation weakened.'
write('module-spec.json',doc)
page=(P/'index.html').read_text(encoding='utf-8');start=page.index('<h2>Module specification and results</h2>');page=page[:start]+'<h2>Module specification and results</h2><pre>'+html.escape(json.dumps(doc,indent=2))+'</pre><script type="application/json" id="module-spec">'+json.dumps(doc).replace('<','\\u003c')+'</script>'
(P/'index.html').write_text(page,encoding='utf-8')
write('seal.json',{'scope':'bounded proposal only; no independent acceptance','counts':doc['counts'],'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in P.iterdir() if p.is_file() and p.name!='seal.json'}})
print(json.dumps(doc['counts']))
