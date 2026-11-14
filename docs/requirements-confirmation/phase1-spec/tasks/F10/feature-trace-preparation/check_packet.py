from pathlib import Path
import hashlib,json,re
O=Path(__file__).resolve().parent
R=O.parents[5]
def load(n): return json.loads((O/n).read_text(encoding='utf-8-sig'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
t=load('trace.json'); a=load('original-authority.json'); s=load('sources.json')
checks={
 'original_acceptance_exact':t['original_acceptance']==a['task']['acceptance'],
 'gray':t['zone']=='gray',
 'eight_trace_rows':len(t['trace'])==8,
 'all_planned':all(x['status']=='PLANNED_NOT_RUN' for x in t['trace']),
 'eight_pending_recipes':len(load('pending-recipes.json'))==8,
 'exact_only_20_21':[x['bdd'] for x in t['trace'] if x['mapping']=='exact scenario equivalence']==['BDD-20','BDD-21'],
 'source_integrity':all(digest(R/x['path'])==x['sha256'] for x in s),
 'authority_796':load('source-integrity.json')['entries']==796,
 'no_product_drift':not load('source-integrity.json')['drift'],
 'embedded_trace':json.loads(re.search(r'id="module-spec">(.*?)</script>',(O/'index.html').read_text(encoding='utf-8'),re.S).group(1))==t,
}
if (O/'seal.json').exists():
 seal=load('seal.json')
 checks['seal_hashes']=all(digest(O/n)==h for n,h in seal['files'].items())
 checks['seal_file_set']=set(seal['files'])=={p.name for p in O.iterdir() if p.is_file() and p.name!='seal.json'}
print(json.dumps({'status':'PASS_STATIC_ONLY' if all(checks.values()) else 'FAIL','checks':checks,'feature_status':'PLANNED_NOT_RUN'},indent=2))
raise SystemExit(0 if all(checks.values()) else 1)

