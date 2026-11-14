import json,pathlib,re,hashlib,subprocess,copy,sys,html
sys.dont_write_bytecode=True
from document_model import exercise, Authority, delivery, fresh, TUPLE
from schema_subset import Draft202012Validator
P=pathlib.Path(__file__).resolve().parent
J=lambda n:json.loads((P/n).read_text(encoding='utf-8-sig'))
def put(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
results=[]
for case in J('fixtures.json'):
 r=exercise(case['mode']);assert r['result']==case['expected'],(case,r);results.append({'id':case['id'],'mode':case['mode'],**r,'status':'PASS_DOCUMENT_MODEL_ONLY'})
put('model-results.json',results)
# Independent-of-caller delivery authority probes in this author-owned document model.
obs=fresh()['observation'];delivery_cases=[]
for key in list(TUPLE)+['attachment_active','native_live']:
 for bad in ['MISSING',None,False,17,[],{}]:
  if key in ('attachment_active','native_live') and bad is False:expected=False
  else:expected=False
  altered=copy.deepcopy(obs)
  if bad=='MISSING':altered.pop(key)
  else:altered[key]=bad
  a=Authority();token=a.mint(altered);actual=delivery(a,token,obs)
  assert actual is False,(key,bad)
  delivery_cases.append({'field':key,'value':bad,'delivered':False})
a=Authority();assert delivery(a,a.mint(obs),obs) is True
for key in TUPLE:
 altered=copy.deepcopy(obs);altered[key]+='-changed';assert delivery(a,a.mint(altered),obs) is False
 delivery_cases.append({'field':key,'value':'changed trusted tuple','delivered':False})
put('trusted-delivery-probes.json',delivery_cases)

# Inventory every physical pattern, including unused $defs; probe with the actual parsed string.
patterns=[]
def walk(x,path,root):
 if isinstance(x,dict):
  for k,v in x.items():
   if k=='pattern':
    kind='uuid' if '-4[0-9a-f]'in v else 'digest' if '{64}'in v else 'u64'
    patterns.append({'root':root,'pointer':path+'/pattern','kind':kind,'pattern':v})
   else:walk(v,path+'/'+k,root)
 elif isinstance(x,list):
  for i,v in enumerate(x):walk(v,path+'/'+str(i),root)
for n in ['request.schema.json','response.schema.json']:walk(J(n),'',n)
U='abcdef01-abcd-4abc-8abc-abcdef012345'
for p in patterns:
 valid={'uuid':U,'digest':'a'*64,'u64':'18446744073709551615'}[p['kind']]
 invalid=[valid+'\n',valid+'\r',valid+'\r\n',valid+'\u2028',valid+'\u2029',valid+'\u0000','', ' '+valid,valid+' ']
 invalid+= {'uuid':[U.upper(),U.replace('-4','-5',1)],'digest':['A'*64,'a'*63,'a'*65],'u64':['18446744073709551616','01','-1','1.0','１']}[p['kind']]
 assert re.search(p['pattern'],valid)
 for v in invalid:assert re.search(p['pattern'],v)is None,(p,v)
 p['positive']=valid;p['negative']=invalid
put('lexical-audit.json',patterns)
put('root-occurrence-trace.json',[{'root':p['root'],'pointer':p['pointer'],'kind':p['kind'],'reachability':('inline complete request root' if '/properties/'in p['pointer'] and not '/$defs/'in p['pointer'] else 'U64Decimal reachable through response StaleRevision/SequenceConflict details; direct request u64 has inline pattern' if p['kind']=='u64' else 'retained common $defs; unused in close roots; actual parsed pattern probed without claiming reachable close field')} for p in patterns])
# Complete root positive/negative probes, not regex-only checks.
req={'binding_ref':U,'expected_generation':'7','expected_revision':'9','discard_unsaved':False}
roots=[]
def probe(root,value,expected,label):
 try:Draft202012Validator(J(root)).validate(value);actual=True
 except AssertionError:actual=False
 assert actual==expected,(label,value,actual)
 roots.append({'root':root,'label':label,'value':copy.deepcopy(value),'expected':expected,'actual':actual})
probe('request.schema.json',req,True,'request complete')
for field in req:
 x=copy.deepcopy(req);del x[field];probe('request.schema.json',x,False,'missing '+field)
for field in ['native_live','attachment_active','request_id','target_window','force']:
 x=copy.deepcopy(req);x[field]=True;probe('request.schema.json',x,False,'unknown '+field)
for value in [None,True,1,'',[]]:probe('request.schema.json',value,False,'non-object')
for field in ['binding_ref','expected_generation','expected_revision']:
 for val in [None,True,7,[],{},req[field]+'\n']:
  x=copy.deepcopy(req);x[field]=val;probe('request.schema.json',x,False,'typed '+field)
for val in ['0','18446744073709551615']:
 x=copy.deepcopy(req);x['expected_generation']=val;x['expected_revision']=val;probe('request.schema.json',x,True,'u64 boundary')
for val in ['18446744073709551616','01','-1']:
 x=copy.deepcopy(req);x['expected_revision']=val;probe('request.schema.json',x,False,'u64 reject')
closed={'ok':True,'value':{'closed':True,'content_changed':False},'replayed':False};probe('response.schema.json',closed,True,'close success')
x=copy.deepcopy(closed);x['value']['content_changed']=True;probe('response.schema.json',x,False,'content mutation forbidden')
errors=J('response.schema.json')['$defs']['Error']['oneOf']
variants=[x for x in errors if x['properties']['code'].get('const')=='DomainRejected'];assert len(variants)==7
for variant in variants:
 details=variant['properties']['details'];code=details['properties']['code']['const'];fields={} if code!='InvalidInput' else {'field':'design_json'}
 v={'ok':False,'error':{'code':'DomainRejected','details':{'code':code,'fields':fields}},'replayed':False};probe('response.schema.json',v,True,'typed DomainRejected '+code)
 v['error']['details']['fields']='Debug text';probe('response.schema.json',v,False,'reject string fields '+code)

# Expand each concrete error branch and every reachable pattern occurrence through actual roots.
rs=J('response.schema.json')
def resolve(sc):
 while '$ref' in sc:
  target=rs
  for k in sc['$ref'][2:].split('/'):target=target[k]
  sc=target
 return sc
def sample(sc):
 sc=resolve(sc)
 if 'const'in sc:return sc['const']
 if 'enum'in sc:return sc['enum'][0]
 if 'oneOf'in sc:return sample(sc['oneOf'][0])
 t=sc.get('type')
 if isinstance(t,list):t=t[0]
 if t=='object':return {k:sample(sc['properties'][k]) for k in sc.get('required',[])}
 if t=='array':return []
 if t=='boolean':return False
 if t=='null':return None
 if t=='string':
  pat=sc.get('pattern','')
  return U if '-4[0-9a-f]'in pat else 'a'*64 if '{64}'in pat else '7' if pat else 'fixture'
 raise AssertionError(sc)
def lexical_paths(sc,value,path=()):
 sc=resolve(sc)
 if 'pattern'in sc:yield path,sc['pattern'],value
 if type(value)is dict:
  for k,v in value.items():yield from lexical_paths(sc['properties'][k],v,path+(k,))
 if type(value)is list and value:
  for i,v in enumerate(value):yield from lexical_paths(sc['items'],v,path+(i,))
reachable=[]
for idx,branch in enumerate(errors):
 error=sample(branch);packet={'ok':False,'error':error,'replayed':False}
 probe('response.schema.json',packet,True,'error branch '+str(idx))
 for path,pattern,valid in lexical_paths(branch,error):
  reachable.append({'root':'response.schema.json','error_branch':idx,'path':['error']+list(path),'pattern':pattern})
  for suffix in ['\n','\r','\r\n','\u2028','\u2029','\u0000']:
   altered=copy.deepcopy(packet);cursor=altered['error']
   for k in path[:-1]:cursor=cursor[k]
   cursor[path[-1]]=valid+suffix
   probe('response.schema.json',altered,False,'error lexical branch '+str(idx)+' '+str(path)+repr(suffix))
put('reachable-root-patterns.json',reachable)
put('root-probes.json',roots)
# Node uses actual JSON strings from lexical-audit plus complete parsed schema root fixtures.
node=subprocess.run(['node',str(P/'probe.cjs')],capture_output=True,text=True);assert node.returncode==0,node.stderr
put('node-results.json',json.loads(node.stdout))
sources=J('source-input-hashes.json');R=pathlib.Path('D:/AIAD');assert all(hashlib.sha256((R/p).read_bytes()).hexdigest()==h for p,h in sources.items())
verification={'status':'PASS_AUTHOR_DOCUMENT_CHECK_ONLY','model_cases':len(results),'trusted_delivery_cases':len(delivery_cases)+1,'root_cases':len(roots),'physical_pattern_occurrences':len(patterns),'node':'PASS','source_inputs_unchanged':True,'independent_acceptance':'NOT RUN','Owner':'NOT RUN','fullDraft':'NOT COMPLETE','product_native_RED':'NOT RUN','build':'NOT RUN','product_tests':'NOT RUN'};put('verification.json',verification)
mod=J('module-spec.json'); sections=[('Executive summary',mod),('Architecture and dependency diagrams',mod['architecture']),('Contracts and invariants',mod['contracts']),('Owner choices; all proposed',J('owner-choices.json')),('BDD coverage and tasks',mod['tasks']),('BDD to TDD traceability',J('traceability.json')),('Verification; author check only',verification),('Lifecycle fixture results',results),('Physical lexical pattern inventory',patterns),('Before and after',J('before-after.json')),('Known risks and deferred automation',J('pending-automation.json')),('Lessons',J('lessons.json')),('Source current versus historical', {k:v for k,v in J('source-current.json').items() if k!='current_hashes'})]
doc='<!doctype html><meta charset="utf-8"><title>M03 close binding candidate</title><style>body{font:16px system-ui;max-width:1200px;margin:40px auto;color:#223;background:#f7f8fa}section{background:white;padding:22px;margin:20px 0;border:1px solid #ddd}pre{white-space:pre-wrap;overflow-wrap:anywhere}h1{color:#875600}nav a{margin-right:18px}</style><h1>M03 design_binding_close — planning candidate</h1><p>PROPOSED_PENDING_INDEPENDENT_REVIEW_AND_OWNER · Author checks only · Transfer DEFERRED · FullDraft NOT COMPLETE · Product/native RED, build and Owner NOT RUN.</p><nav>'+''.join(f'<a href="#s{i}">{html.escape(t)}</a>' for i,(t,v) in enumerate(sections))+'</nav>'
doc+='<section><h2>Approved-shaped architecture proposal</h2><pre>Native UI → Trusted Tauri adapter → M03 close port → derived facade → M04 detach_view port → sole M04 S1 owner\nM03 candidates / previews / replay disclosure ← exact attachment revocation\nM04 content / history / formal baseline / material roots remain untouched\nTransaction: authenticate → validate → preflight → trusted M04 detached observation → revoke derived authority\nFailure before confirmation: no partial facade effect. Actual native atomicity still pending.</pre></section>'
for i,(t,v) in enumerate(sections):doc+=f'<section id="s{i}"><h2>{html.escape(t)}</h2><pre>{html.escape(json.dumps(v,ensure_ascii=False,indent=2))}</pre></section>'
doc+='<section><h2>Gherkin specification</h2><pre>'+html.escape((P/'module.feature').read_text(encoding='utf-8'))+'</pre></section>'
doc+='<script type="application/json" id="module-spec">'+json.dumps(mod,ensure_ascii=False).replace('<','\\u003c')+'</script>'
(P/'index.html').write_text(doc,encoding='utf-8')
put('artifact-hashes.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(P.iterdir()) if p.is_file() and p.name!='artifact-hashes.json'})
print(json.dumps(verification))
