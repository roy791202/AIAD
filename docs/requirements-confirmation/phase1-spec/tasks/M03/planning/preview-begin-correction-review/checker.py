"""Independent document review; never executes author checker or writes its evidence."""
import copy, hashlib, html, importlib.util, json, pathlib, subprocess, sys
sys.dont_write_bytecode=True
P=pathlib.Path(__file__).resolve().parent
R=P.parents[6]
C=P.parent/'preview-begin-correction'
O=P.parent/'preview-begin-integration'
def load(p): return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mod(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=mod('document_model',C/'document_model.py');sys.modules['document_model']=m
v=mod('bounded_schema',C/'checker.py')
o=mod('original_model',O/'document_model.py')
req=load(C/'request.schema.json');res=load(C/'response.schema.json')
base=load(C/'fixtures.json')[0]
checks=[];fixtures=[]
def check(name,ok,detail=None):checks.append({'id':name,'passed':bool(ok),'detail':detail})
def case(name,current,observed='MISSING',code='StaleRevision',updates=None,details=None):
 c=copy.deepcopy(base);c['id']=name;c['before']['revision']=current;c['request']['expected_revision']=current;c['provider_projection']['source_revision']=current;c['premises']['delivery_change']='revision'
 if observed!='MISSING':c['premises']['delivery_observed_revision']=observed
 if updates:
  for section,values in updates.items():c[section].update(values)
 response,after,calls=m.begin(c,lambda x:v.valid(req,x))
 expected={'ok':False,'error':{'code':code,'details':details if details is not None else ({'expected':current,'observed':observed} if code=='StaleRevision' else {'dependency':'M01_NATIVE_IDENTITY'})},'replayed':False}
 check(name,response==expected and after==c['before'] and 'preview.publish' not in calls and v.valid(res,response),{'response':response,'calls':calls,'state_unchanged':after==c['before']})
 fixtures.append({'input':c,'expected':expected,'response':response,'calls':calls,'state_unchanged':after==c['before']})
MAX='18446744073709551615'
# Independent cross product exercises numeric boundaries, strict native observation typing and contradictions.
for current in ['0','1',MAX]:
 for observed in ['0','1','2',MAX]:
  case('CR-boundary-'+current+'-'+observed,current,observed,'DependencyNotReady' if current==observed else 'StaleRevision')
 for label,bad in [('missing','MISSING'),('null',None),('bool-true',True),('bool-false',False),('number-zero',0),('number-one',1),('number-max',18446744073709551615),('float',1.0),('LF','1\n'),('CRLF','1\r\n'),('leading-zero','01'),('empty',''),('signed','+1'),('negative','-1'),('overflow','18446744073709551616'),('unicode','１'),('array',[]),('object',{})]:
  case('CR-type-'+current+'-'+label,current,bad,'DependencyNotReady')
# Earlier failures must win even with max revision plus missing or malformed delivery observation.
for label,updates,code,details in [
 ('unauthorized',{'premises':{'trusted_local':False}},'UnauthorizedCaller',{}),
 ('missing-binding',{'premises':{'binding_present':False}},'MissingBinding',{}),
 ('generation',{'request':{'expected_generation':'0'}},'StaleOwner',{}),
 ('revision',{'request':{'expected_revision':'0'}},'StaleRevision',{'expected':'0','observed':MAX}),
 ('capacity',{'before':{'preview_count':4}},'ResourceLimit',{'field':'/preview_sessions','limit':'preview_sessions_per_binding'}),
 ('provider',{'premises':{'provider_ready':False}},'DependencyNotReady',{'dependency':'M04_OWNER_INTEGRATION'}),
 ('request-bool',{'request':{'expected_revision':True}},'InvalidRequest',{'field':'/expected_revision','reason':'Type'}),
 ('request-leading-zero',{'request':{'expected_revision':'01'}},'InvalidRequest',{'field':'/expected_revision','reason':'InvalidNumber'}),
 ('request-LF',{'request':{'expected_revision':'1\n'}},'InvalidRequest',{'field':'/expected_revision','reason':'InvalidNumber'})]:
 for observed in ['MISSING',True,MAX]:case('CR-precedence-'+label+'-'+str(observed),MAX,observed,code,updates,details)
# Original PB-IR-F1 remains reproducible, with zero mutation, then corrected missing observation rejects safely.
c=copy.deepcopy(base);c['before']['revision']=MAX;c['request']['expected_revision']=MAX;c['premises']['delivery_change']='revision'
a,after,calls=o.begin(c,lambda x:v.valid(req,x))
check('CR-original-PB-IR-F1',a['error']['details']['observed']=='18446744073709551616' and not v.valid(res,a) and after==c['before'],a)
for name in ['request.schema.json','response.schema.json']:
 check('CR-bytewise-'+name,(C/name).read_bytes()==(O/name).read_bytes(),{'original':sha(O/name),'corrected':sha(C/name)})
# Full response schema closure and typed branches: independent paths from every stored response.
def walk(x,path=()):
 if type(x)is dict:
  yield path,x
  for k,z in x.items():yield from walk(z,path+(k,))
 elif type(x)is list:
  for i,z in enumerate(x):yield from walk(z,path+(i,))
for fixture in load(C/'fixtures.json'):
 response,after,calls=m.begin(fixture,lambda x:v.valid(req,x))
 check('CR-stored-'+fixture['id'],response==fixture['expected'] and v.valid(res,response) and calls==fixture['expected_calls'] and (after==fixture['before'] if not response['ok'] else after['preview_count']==fixture['before']['preview_count']+1))
 for path,node in walk(response):
  for key in node:
   bad=copy.deepcopy(response);target=bad
   for k in path:target=target[k]
   target[key]=None if node[key] is not None else True
   check('CR-response-type-'+fixture['id']+'-'+str(path)+'-'+key,not v.valid(res,bad))
# Verify immutable frozen packet/review and authoritative product inventory directly.
for path,h in load(C/'preserved-inputs.json').items():check('CR-frozen-'+path,sha(R/path)==h)
for path,h in load(C/'artifact-hashes.json').items():check('CR-author-seal-'+path,sha(C/path)==h)
authority=load(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
matched=sum(sha(R/path)==h for path,h in authority['source_hashes'].items())
check('CR-product-796',matched==len(authority['source_hashes'])==796)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
check('CR-head',head=='5b709343a890503ebbe24a802e43cda5647df124' and authority['head']=='31babe87a7ef1e40a0d4bedc523077e7a45d63ab')
spec=load(C/'module-spec.json');check('CR-pending-policy',spec['correction']['policy_status']=='PROPOSED_PENDING_OWNER' and spec['product_readiness']=='NOT_READY_FOR_IMPLEMENTATION')
board=load(R/'docs/board.json')
# Current board is management evidence, not a product-file authority member.
management={'current_board_sha256':sha(R/'docs/board.json'),'frozen_drift_record':load(C/'input-drift.json'),'classification':'Management note changes separate from product hashes; frozen historical inputs preserved','current_state':load(P.parent/'current-state.json')['state']}
failed=[x for x in checks if not x['passed']]
result={'verdict':'PASS_DOCUMENT_CORRECTION_ONLY_PENDING_OWNER' if not failed else 'CHANGES_REQUIRED_DOCUMENT_MODEL_ONLY','author':'/root/m03_viewer_begin_correction','reviewer':'/root/m03_viewer_begin_correction_review','head':head,'historical_authority_head':authority['head'],'checks':len(checks),'passed':len(checks)-len(failed),'failed':failed,'independent_new_cases':len(fixtures),'authority_count':len(authority['source_hashes']),'authority_matched':matched,'schema_engine':'Author bounded keyword evaluator used for wire schema checks; independent explicit response/state/precedence oracle; not full Draft2020 validator','PB-IR-F1':'Closed only for corrected document-model bounded actual-observation proposal; original frozen counterexample retained','pending':'Owner adoption remains pending; C1 CP1-CP3 and H2 decisions unchanged','trusted_premises':'Native/provider observations are trusted premises; authenticity, reachability and temporal correctness unproven; lower distinct revision does not assert native monotonic reachability','product_tests':'NOT RUN','native':'NOT RUN','build':'NOT RUN','valid_RED':'NOT RUN','module_acceptance':'NOT RUN','management':management}
for name,data in [('fixtures.json',fixtures),('results.json',result),('checks.json',checks)]: (P/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
inputs={str(p.relative_to(R)).replace('\\','/'):sha(p) for folder in [C,O,P.parent/'preview-begin-review'] for p in folder.iterdir() if p.is_file()}
inputs['docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json']=sha(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
(P/'source-hashes.json').write_text(json.dumps(inputs,indent=2)+'\n',encoding='utf8')
text='<html><meta charset="utf-8"><title>M03 independent correction review</title><style>body{font:16px system-ui;max-width:1100px;margin:35px auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}h1{color:#705400}</style><h1>M03 Viewer begin — independent document correction review</h1><p>'+html.escape(result['verdict'])+'</p><p>PB-IR-F1: original overflow reproduced; corrected bounded observation rejects missing, malformed and equal contradictory values with unchanged state and no publication. Actual max to 0/1 observations are represented without arithmetic fabrication.</p><p>Schema bytes unchanged. New boundary/type/precedence probes supplement stored author fixtures. Native observations and validated C1 projections remain trusted premises. All policy choices remain proposed pending Owner. No product, module, native, build or valid RED acceptance.</p><h2>Review summary</h2><pre>'+html.escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre><h2>Checks</h2><pre>'+html.escape(json.dumps(checks,ensure_ascii=False,indent=2))+'</pre><script type="application/json" id="review-spec">'+json.dumps({'review':result,'fixtures':fixtures,'checks':checks,'source_hashes':inputs},ensure_ascii=False).replace('</','<\/')+'</script></html>'
(P/'index.html').write_text(text,encoding='utf8')
print(json.dumps({'verdict':result['verdict'],'checks':len(checks),'failed':failed,'new_cases':len(fixtures),'source_matched':matched}))

