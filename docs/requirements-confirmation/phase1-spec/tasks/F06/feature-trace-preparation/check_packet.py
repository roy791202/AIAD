import json,pathlib,hashlib,re
P=pathlib.Path(__file__).resolve().parent; R=P.parents[5]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((P/'module-spec.json').read_text(encoding='utf-8')); inputs=json.loads((P/'inputs.json').read_text(encoding='utf-8'))['sources']; checks=[]
def check(n,v):checks.append({'check':n,'pass':bool(v)})
for p,h in inputs.items():check('source unchanged '+p,sha(R/p)==h)
auth=json.loads((R/m['inventory_authority']).read_text(encoding='utf-8')); drift=[p for p,h in auth['source_hashes'].items() if not (R/p).is_file() or sha(R/p)!=h];check('796 authority source integrity',len(auth['source_hashes'])==796 and not drift)
check('current head distinct from inventory',m['head']=='5b709343a890503ebbe24a802e43cda5647df124' and m['inventory_head']=='31babe87a7ef1e40a0d4bedc523077e7a45d63ab')
check('original exact BDD retained',m['trace'][0]['bdd']=='BDD-31' and all(r['bdd'] is None for r in m['trace'][1:]))
h=(P/'index.html').read_text(encoding='utf-8'); embedded=json.loads(re.search(r'<script type="application/json" id="module-spec">(.*?)</script>',h,re.S).group(1));check('embedded spec exact',embedded==m)
for link in re.findall(r'href="([^"]+)"',h):check('link '+link,(P/link).is_file())
check('six bounded recipes',len(json.loads((P/'pending-test-recipes.json').read_text(encoding='utf-8')))==6)
check('Gray retained / no product completion',m['state']=='PLANNED_NOT_RUN' and m['board']=='Gray / Backlog retained')
out={'verdict':'PASS_STATIC_DOCUMENT_ONLY' if all(c['pass'] for c in checks) else 'FAIL','passed':sum(c['pass'] for c in checks),'total':len(checks),'checks':checks,'source_drift':drift,'not_run':m['not_run'],'feature_pass':False}
(P/'verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(out['verdict'],out['passed'],out['total']);raise SystemExit(0 if all(c['pass'] for c in checks) else 1)
