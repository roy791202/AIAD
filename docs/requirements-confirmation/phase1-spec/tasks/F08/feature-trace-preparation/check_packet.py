"""Static documentation checks; no production execution."""
import hashlib,json,pathlib,re
O=pathlib.Path(__file__).resolve().parent
R=O.parents[5]
def load(n):return json.loads((O/n).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=load('feature-trace.json')
page=(O/'index.html').read_text(encoding='utf-8')
embedded=json.loads(re.search(r'<script type="application/json" id="module-spec">(.*?)</script>',page,re.S)[1].replace('<\\/','</'))
checks={'embedded_equals_json':embedded==spec,'ten_rows':len(spec['trace'])==10,'four_exact':sum(r['equivalence']=='EXACT_ORIGINAL_SCENARIO' for r in spec['trace'])==4,'all_planned':all(r['status']=='PLANNED_NOT_RUN' for r in spec['trace']),'no_product_claims':not spec['feature_pass'] and not spec['module_pass'] and not spec['done'],'all_verification_not_run':set(spec['verification'].values())=={'NOT RUN'},'bindings_current':all(sha(R/p)==h for p,h in load('source-bindings.json').items()),'links_resolve':all((O/p).is_file() for p in re.findall(r'href="([^"]+)"',page)),'inventory_796_unchanged':load('source-integrity.json')['count']==796 and not load('source-integrity.json')['mismatches'],'current_head_bound':load('source-integrity.json')['current_head']=='5b709343a890503ebbe24a802e43cda5647df124'}
result={'status':'PASS' if all(checks.values()) else 'FAIL','layer':'STATIC_DOCUMENT_ONLY_NOT_FEATURE_PASS','checks':checks,'counts':{'rows':10,'exact_original':4,'contextual':2,'prospective_AC':4,'source_bindings':len(load('source-bindings.json')),'product_inventory':796},'unrun':['independent review','product tests','build','native','valid RED','full Draft'],'gray_retained':True}
(O/'static-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
seal={p.name:sha(p) for p in sorted(O.iterdir()) if p.is_file() and p.name!='seal.json'}
(O/'seal.json').write_text(json.dumps({'algorithm':'SHA256','files':seal,'count':len(seal),'excludes':'seal.json self only; static seal not acceptance'},indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
raise SystemExit(0 if all(checks.values()) else 1)
