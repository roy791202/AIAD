import json,hashlib,subprocess,copy,html
from pathlib import Path
P=Path(__file__).resolve().parent
R=Path.cwd()
C=R/'docs/requirements-confirmation/phase1-spec/tasks/M07/planning/provider-source-map-20261104'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
checks=[]
def ck(n,v):checks.append({'name':n,'pass':bool(v)})
seal=read(C/'seal.json');before={f:sha(C/f) for f in seal['files']}
for f,h in seal['files'].items():ck('sealed:'+f,sha(C/f)==h)
spans=read(C/'source-spans.json')
for x in spans:
 ls=(R/x['path']).read_text(encoding='utf-8').splitlines()
 ck(x['id']+':hash',sha(R/x['path'])==x['sha256'])
 ck(x['id']+':range_nonempty',1<=x['start']<=x['end']<=len(ls) and bool(x['text'].strip()))
 ck(x['id']+':literal','\n'.join(ls[x['start']-1:x['end']])==x['text'])
ck('RS05:Published_claim_supported','CompletionOutcome::Published' in next(x['text'] for x in spans if x['id']=='RS05'))
a=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')['source_hashes'];ck('authority796',len(a)==796 and all((R/k).exists() and sha(R/k)==v for k,v in a.items()))
d=read(C/'module-spec.json');ck('four_pending_bridges',len(d['bridges'])==4 and all(x['selected'] is None for x in d['bridges']));ck('six_earlier_attempts',len(d['earlier_yellow_attempts'])==6);ck('no_product_pass',d['product_pass'] is False and d['selected'] is None)
q=d['scoped_search'];r=subprocess.run(q['command'],capture_output=True,text=True,encoding='utf-8');ck('scoped_search',r.returncode==q['exit'] and r.stdout==q['stdout'])
probes=[]
def valid(x):
 ls=(R/x['path']).read_text(encoding='utf-8').splitlines()
 return 1<=x['start']<=x['end']<=len(ls) and bool(x['text'].strip()) and '\n'.join(ls[x['start']-1:x['end']])==x['text'] and sha(R/x['path'])==x['sha256']
for name,mut in [('empty',lambda x:x.update(text='')),('out_of_range',lambda x:x.update(start=999,end=1000)),('reversed',lambda x:x.update(start=4,end=2)),('zero',lambda x:x.update(start=0)),('hash',lambda x:x.update(sha256='0'*64)),('literal',lambda x:x.update(text=x['text']+' altered'))]:
 x=copy.deepcopy(spans[0]);mut(x);probes.append({'name':name,'rejected':not valid(x)})
ck('candidate_unchanged',before=={f:sha(C/f) for f in seal['files']})
findings=[{'id':'M07-PM-R1','severity':'P2','issue':'RS06 is empty/out of range: recovery_state.rs has216 lines, claimed236–240. Replace with actual validate_capture lines212–216 and reject empty/out-of-range spans.'},{'id':'M07-PM-R2','severity':'P2','issue':'RS05 lines171–192 omit Published fingerprint advancement claimed by meaning. Bind complete completion branch lines157–173; consider RS04 claims60000 while excerpt omits actual threshold, include threshold or narrow wording.'}]
result={'reviewer':'/root/m07_provider_review','author':d['author'],'status':'CHANGES_REQUESTED_BOUNDED_DOCUMENT_SOURCE_BINDINGS','checks':checks,'probes':probes,'findings':findings,'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'limits':['Static source review only','No historical PASS rerun','Product/native/build/regression NOT RUN']}
(P/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M07 independent review</title><h1>CHANGES_REQUESTED</h1><p>Author and reviewer independent. Source boundary claims need precise bindings; no product/native proof.</p><pre>'+html.escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre>',encoding='utf-8')
(P/'seal.json').write_text(json.dumps({'reviewer':result['reviewer'],'status':'SEALED','files':{f.name:sha(f) for f in P.iterdir() if f.is_file() and f.name!='seal.json'}},indent=2),encoding='utf-8')
print(result['status'],len(checks),len(probes),sum(not x['pass'] for x in checks))
