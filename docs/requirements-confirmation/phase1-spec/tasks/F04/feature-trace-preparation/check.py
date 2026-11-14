from pathlib import Path
import json,hashlib,re,subprocess
O=Path(__file__).resolve().parent; R=O.parents[5]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def run():
 checks=[]
 def ck(name,value):checks.append({'name':name,'pass':bool(value)})
 t=load(O/'feature-trace.json'); task=load(R/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F04-DELIVERY-01.json')
 ck('original acceptance exact',t['original_acceptance']==task['acceptance']);ck('original BDD exact',t['original_bdd']==task['bdd']);ck('original contract exact',t['original_contract']==task['contract'])
 ck('one bounded feature',t['feature']=='F04' and t['primary_module']=='M03');ck('seven original clause recipes',len(t['trace'])==7)
 for x in t['trace']:ck(x['id']+' planned and oracle',x['status']=='PLANNED_NOT_RUN' and all(x[k] for k in ['fixture_recipe','oracle_recipe','valid_red','gap']))
 ck('two confirmed original BDD rows',[(x['bdd'],x['authority']) for x in t['trace'][:2]]==[('BDD-05','CONFIRMED_REQ05'),('BDD-06','CONFIRMED_REQ05')])
 ck('remaining proposals not adopted',all(x['authority']=='PROPOSAL_PENDING_OWNER' for x in t['trace'][2:]))
 ck('all execution layers unrun',all(t['execution'][x]=='NOT RUN' for x in ['new_product_tests','valid_RED','build','native_UI','independent_acceptance','full_Draft','feature_acceptance']))
 ck('no new Skeleton or completion',t['execution']['new_Skeleton'] is False and t['execution']['feature_complete'] is False and t['execution']['module_complete'] is False)
 ck('unchanged dependencies',task['dependencies']==['PD-P1-M03-PREP-01','PD-P1-G01-DEC-01','PD-P1-G04-DEC-01'])
 ck('bounded unique trace IDs',len(set(x['id'] for x in t['trace']))==7 and all(x['requirement']=='REQ-05' for x in t['trace']))
 for name,digest in load(O/'seal.json')['payload_sha256'].items():ck('sealed artifact '+name,sha(O/name)==digest)
 h=(O/'index.html').read_text(encoding='utf-8'); embedded=json.loads(re.search(r'<script id="feature-trace" type="application/json">(.*?)</script>',h,re.S)[1]);ck('embedded trace exact',embedded==t)
 for p,digest in load(O/'source-bindings.json').items():ck('source '+p,sha(R/p)==digest)
 authority=load(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
 ck('796 authority count',len(authority['source_hashes'])==796)
 for p,digest in authority['source_hashes'].items():ck('product integrity '+p,(R/p).is_file() and sha(R/p)==digest)
 ck('current head separate historical authority',subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()=='5b709343a890503ebbe24a802e43cda5647df124' and authority['head']=='31babe87a7ef1e40a0d4bedc523077e7a45d63ab')
 for target in re.findall(r'href="([^"]+)"',h): ck('local link '+target,(O/target).exists())
 result={'status':'PASS_STATIC_ONLY' if all(x['pass'] for x in checks) else 'FAIL','checks':len(checks),'passed':sum(x['pass'] for x in checks),'failed':[x for x in checks if not x['pass']],'product_tests':'NOT RUN','valid_RED':'NOT RUN','independent_review':'NOT RUN','feature_acceptance':'NOT RUN','health':'GRAY_RETAINED'}
 (O/'check-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result));return result
if __name__=='__main__':
 import sys
 sys.exit(0 if run()['status']=='PASS_STATIC_ONLY' else 1)

