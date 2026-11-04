from pathlib import Path
import json,hashlib,re,subprocess
O=Path(__file__).resolve().parent; R=O.parents[5]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def run():
 checks=[]
 def ck(name,value):checks.append({'name':name,'pass':bool(value)})
 t=load(O/'feature-trace.json'); task=load(R/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F03-DELIVERY-01.json')
 ck('original acceptance exact',t['original_acceptance']==task['acceptance']);ck('original BDD exact',t['original_bdd']==task['bdd']);ck('original contract exact',t['original_contract']==task['contract'])
 ck('one bounded feature',t['feature']=='F03' and t['primary_module']=='M02');ck('four AC03 recipes',len(t['trace'])==4)
 for x in t['trace']:ck(x['id']+' planned and oracle',x['status']=='PLANNED_NOT_RUN' and all(x[k] for k in ['fixture_recipe','oracle_recipe','valid_red','gap']))
 h=(O/'index.html').read_text(encoding='utf-8'); embedded=json.loads(re.search(r'<script id="feature-trace" type="application/json">(.*?)</script>',h,re.S)[1]);ck('embedded trace exact',embedded==t)
 for p,digest in load(O/'source-bindings.json').items():ck('source '+p,sha(R/p)==digest)
 authority=load(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
 ck('796 authority count',len(authority['source_hashes'])==796)
 for p,digest in authority['source_hashes'].items():ck('product integrity '+p,(R/p).is_file() and sha(R/p)==digest)
 ck('current head separate historical authority',subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()=='5b709343a890503ebbe24a802e43cda5647df124' and authority['head']=='31babe87a7ef1e40a0d4bedc523077e7a45d63ab')
 for target in re.findall(r'href="([^"]+)"',h): ck('local link '+target,(O/target).exists())
 result={'status':'PASS_STATIC_ONLY' if all(x['pass'] for x in checks) else 'FAIL','checks':len(checks),'passed':sum(x['pass'] for x in checks),'failed':[x for x in checks if not x['pass']],'product_tests':'NOT RUN','valid_RED':'NOT RUN','independent_review':'NOT RUN','feature_acceptance':'NOT RUN','health':'GRAY_RETAINED'}
 (O/'check-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result));return result
if __name__=='__main__':run()

