"""Generic schema and pure document oracle checks. Not production or native proof."""
import copy, json, pathlib, re, subprocess, sys
sys.dont_write_bytecode=True
P=pathlib.Path(__file__).resolve().parent
def read(n):return json.loads((P/n).read_text(encoding='utf8'))
def write(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def walk(x,p=''):
 if isinstance(x,dict):
  yield p,x
  for k,v in x.items():yield from walk(v,p+'/'+k)
 elif isinstance(x,list):
  for i,v in enumerate(x):yield from walk(v,p+'/'+str(i))
def resolve(root,ref):
 x=root
 for k in ref[2:].split('/'):x=x[k]
 return x
def sample(s):
 if 'const'in s:return copy.deepcopy(s['const'])
 if 'enum'in s:return s['enum'][0]
 if 'pattern'in s:
  if '[0-9a-f]{8}'in s['pattern']:return 'abcdef01-abcd-4abc-8abc-abcdef012345'
  if '{64}'in s['pattern']:return 'abcdef01'*8
  return '7'
 t=s.get('type');t=t[0] if isinstance(t,list) else t
 return {'string':'x','boolean':False,'array':[],'null':None}.get(t)
def witness(root,s,branches):
 if '$ref'in s:return witness(root,resolve(root,s['$ref']),branches)
 if 'oneOf'in s:return witness(root,s['oneOf'][branches.pop(0) if branches else 0],branches)
 if s.get('type')=='object':return {k:witness(root,v,branches) for k,v in s.get('properties',{}).items() if k in s.get('required',[])}
 return sample(s)
def routes(root,s,sp='',ip=(),branches=(),refs=()):
 if '$ref'in s:
  assert s['$ref']not in refs
  yield from routes(root,resolve(root,s['$ref']),s['$ref'][1:],ip,branches,refs+(s['$ref'],));return
 if 'pattern'in s:yield {'schema_pointer':sp+'/pattern','instance_path':list(ip),'branches':list(branches),'ref_chain':list(refs)}
 for i,z in enumerate(s.get('oneOf',[])):yield from routes(root,z,sp+'/oneOf/'+str(i),ip,branches+(i,),refs)
 for k,z in s.get('properties',{}).items():yield from routes(root,z,sp+'/properties/'+k,ip+(k,),branches,refs)
 if 'items'in s:yield from routes(root,s['items'],sp+'/items',ip+('*',),branches,refs)
def values(s):
 v=sample(s);kind='uuid' if '[0-9a-f]{8}'in s['pattern'] else 'digest' if '{64}'in s['pattern'] else 'u64'
 a=[('canonical',v,True),('empty','',False),('number',7,False),('prefix','x'+v,False),('suffix',v+'x',False)]
 a.extend((repr(t),v+t,False) for t in ['\n','\r','\r\n','\0','\t','\x85','\u2028','\u2029'])
 if kind=='u64':a.extend((v,v,ok) for v,ok in [('0',True),('9007199254740993',True),('18446744073709551615',True),('18446744073709551616',False),('01',False),('-1',False),('1e0',False),('1.0',False)])
 else:a.extend([('uppercase',v.upper(),False),('short',v[:-1],False),('long',v+'0',False)])
 return a
def run():
 from schema_subset import Draft202012Validator
 from document_model import fixtures, reduce, deliver, delivery_fixtures
 roots={n:read(n) for n in read('module-spec.json')['roots']};audit=[];trace=[];cases=[];physical=[]
 for n,root in roots.items():
  Draft202012Validator.check_schema(root)
  rr=list(routes(root,root))
  for p,s in walk(root):
   if '$ref'in s:assert s['$ref'].startswith('#/');resolve(root,s['$ref'])
   if 'pattern'not in s:continue
   matching=[r for r in rr if r['schema_pointer']==p+'/pattern']
   audit.append({'schema':n,'pointer':p+'/pattern','pattern':s['pattern'],'reachability':'ROOT_REACHABLE' if matching else 'UNREACHABLE_SHARED_DEF','routes':len(matching),'policy':'strict lexical end from prepare correction; no field-name hook'})
   for label,v,expected in values(s):
    if not isinstance(v,str):continue
    physical.append({'schema':n,'pointer':p+'/pattern','pattern':s['pattern'],'value':v,'expected':expected,'id':n+p+label})
  for r in rr:
   assert '*'not in r['instance_path'];trace.append(dict(r,schema=n))
   s=resolve(root,'#'+r['schema_pointer'][:-8]);base=witness(root,root,r['branches'].copy())
   for label,value,expected in values(s):
    x=copy.deepcopy(base);t=x
    for k in r['instance_path'][:-1]:t=t[k]
    t[r['instance_path'][-1]]=value
    cases.append({'id':n+str(len(cases))+label,'schema':n,'instance':x,'expected_accept':expected})
  # Closed complete root counterexamples are independent of lexical fields.
  base=witness(root,root,[])
  cases.append({'id':n+':base','schema':n,'instance':base,'expected_accept':True})
  extra=copy.deepcopy(base);extra['unapproved']=True
  cases.append({'id':n+':unknown','schema':n,'instance':extra,'expected_accept':False})
  for k in base:
   missing=copy.deepcopy(base);del missing[k]
   cases.append({'id':n+':missing:'+k,'schema':n,'instance':missing,'expected_accept':False})
 # Seven exact domain variant objects remain schema-checked even when not emitted by open/get.
 for n,root in roots.items():
  if '-response.'not in n:continue
  domains=[s for s in root['$defs']['Error']['oneOf'] if s['properties']['code'].get('enum')==['DomainRejected'] or s['properties']['code'].get('const')=='DomainRejected'];assert len(domains)==7
  for domain in domains:
   branch=domain['properties']['details']
   d=witness(root,branch,[]);x={'ok':False,'error':{'code':'DomainRejected','details':d},'replayed':False}
   cases.append({'id':n+':domain:'+d['code'],'schema':n,'instance':x,'expected_accept':True})
   y=copy.deepcopy(x);y['error']['details']['fields']='Debug string forbidden'
   cases.append({'id':n+':domain-string:'+d['code'],'schema':n,'instance':y,'expected_accept':False})
 results=[]
 for c in cases:
  try:Draft202012Validator(roots[c['schema']]).validate(c['instance']);actual=True
  except AssertionError:actual=False
  assert actual==c['expected_accept'],c['id'];results.append({'id':c['id'],'actual':actual,'expected':c['expected_accept']})
 for c in physical:assert (re.search(c['pattern'],c['value'])is not None)==c['expected'],c['id']
 models=fixtures();mr=[]
 for c in models:
  before=copy.deepcopy(c['state']);after,response,calls=reduce(c['state'],c['command'],c['request'],c['caller'],c['evidence'])
  assert response==c['expected_response'],c['id']
  assert calls==c['expected_calls'],c['id']
  assert after==c['expected_after'],c['id']
  for k in ['content','history','baselines','revision']:assert after[k]==before[k],c['id']+k
  Draft202012Validator(roots['h2-design_binding_'+c['command']+'-response.schema.json']).validate(response)
  mr.append({'id':c['id'],'response':response,'calls':calls,'state_unchanged':after==before,'content_history_baselines_revision_unchanged':True})
 deliveries=delivery_fixtures();dr=[]
 for c in deliveries:
  display,status=deliver(c['display'],c['pending'],c['response'],c['current'])
  assert display==c['expected_display'] and status==c['expected_status'],c['id']
  dr.append({'id':c['id'],'status':status,'formal_ACK':'NOT CALLED','content_mutation':'NOT CALLED'})
 write('delivery-fixtures.json',deliveries);write('delivery-results.json',dr)
 feature='Feature: Exact proposed open and get observable cases\n  Background:\n    Given document attachment policies await independent review and Owner adoption\n  Rule: Only the current authorized view receives an unchanged document projection\n'
 for c in models:
  outcome='the current immutable projection is returned' if c['expected_response']['ok'] else c['expected_response']['error']['code']+' is reported'
  feature+='    Scenario: '+c['id']+'\n      Given the document attachment condition named '+c['id'].replace('BG-','').replace('-',' ')+'\n      When the view requests '+('an attachment' if c['command']=='open' else 'its current projection')+'\n      Then '+outcome+'\n      And document content, history and baselines remain unchanged\n'
 for c in deliveries:
  feature+='    Scenario: '+c['id']+'\n      Given a projection response is pending for the original view\n      And the current view condition is '+c['id'].replace('BG-delivery-','').replace('-',' ')+'\n      When the response arrives\n      Then the delivery decision is '+c['expected_status']+'\n      And no document acknowledgement is applied\n'
 (P/'case-scenarios.feature').write_text(feature,encoding='utf8')
 write('traceability.json',[{'Requirement':'BG-authorized-attach-and-observe','BDD':c['id'],'Contract':'C1-C9','TDD':'document_model fixture '+c['id'],'level':'DOCUMENT_MODEL_ONLY','result':'AUTHOR_CHECKED','product_TDD':'NOT RUN','task':'BG-PREP-OPEN-GET'} for c in models+deliveries])
 write('lexical-audit.json',audit);write('root-occurrence-trace.json',trace);write('lexical-fixtures.json',cases);write('pattern-fixtures.json',physical);write('fixtures.json',models);write('model-results.json',mr)
 write('all-string-constraints.json',[{'root':n,'pointer':p,'constraints':s} for n,r in roots.items() for p,s in walk(r) if s.get('type')=='string' or isinstance(s.get('type'),list)and 'string'in s['type']])
 node=json.loads(subprocess.check_output(['node',str(P/'probe.cjs')],text=True));assert not node['mismatches']
 write('verification.json',{'status':'AUTHOR_DOCUMENT_CHECKED_PENDING_INDEPENDENT_REVIEW','author':'/root/m03_binding_lifecycle_packet','independent_acceptance':'PENDING','python_root_cases':len(results),'python_definition_cases':len(physical),'model_cases':len(mr),'delivery_cases':len(dr),'node':node,'old_suites':'NOT RERUN','fullDraft':'NOT RUN','product':'NOT RUN','native':'NOT RUN','RED':'NOT RUN','build':'NOT RUN','Owner':'NOT ADOPTED','module_complete':False})
 print(json.dumps({'document_roots':len(roots),'root_cases':len(results),'definition_cases':len(physical),'model_cases':len(mr),'delivery_cases':len(dr),'node':node}))
if __name__=='__main__':run()
