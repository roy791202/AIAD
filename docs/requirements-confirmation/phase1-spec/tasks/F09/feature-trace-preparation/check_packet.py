import hashlib,json,pathlib,re
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[5]
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def j(p):return json.loads(p.read_text(encoding='utf-8-sig'))
inputs=j(OUT/'inputs.json')
assert all(h(ROOT/x['path'])==x['sha256'] for x in inputs),'source input drift'
t=j(OUT/'trace.json')
assert len(t['exact_and_shared_trace'])==6
assert {x['bdd'] for x in t['exact_and_shared_trace']}=={'BDD-15','BDD-16','BDD-17','BDD-18','BDD-19','BDD-21'}
assert all(x['status']=='PLANNED_NOT_RUN' for x in t['exact_and_shared_trace']+t['prospective_AC_recipes'])
assert t['zone']=='gray' and len(t['prospective_AC_recipes'])==5
embedded=json.loads(re.search(r'id="module-spec">(.*?)</script>',(OUT/'index.html').read_text(encoding='utf8'),re.S).group(1))
assert embedded==t
inventory=j(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')['source_hashes']
assert len(inventory)==796
drift=[p for p,d in inventory.items() if not (ROOT/p).exists() or h(ROOT/p)!=d]
assert not drift,drift
seal=OUT/'seal.json'
if seal.exists():
 s=j(seal)
 assert all(h(OUT/p)==d for p,d in s['files'].items()),'packet seal drift'
print(json.dumps({'verdict':'PASS_STATIC_DOCUMENT_SCOPE_ONLY','trace_rows':6,'prospective_AC_recipes':5,'source_inputs':len(inputs),'product_inventory':796,'product_drift':0,'product_tests':'NOT RUN','valid_RED':'NOT RUN','module_feature_PASS':False}))
