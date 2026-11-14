"""One-command AUTHOR candidate checks. Not independent acceptance or native proof."""
import pathlib,json,copy,re,subprocess,hashlib
from document_model import exercise,UUID
from schema_subset import Draft202012Validator
P=pathlib.Path(__file__).resolve().parent
ROOT=P.parents[6]
def load(n):return json.loads((P/n).read_text(encoding='utf-8'))
def save(n,d):(P/n).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
req=load('request.schema.json');resp=load('response.schema.json');checks=[]
def check(name,condition):
 assert condition,name
 checks.append(name)
def valid(s,x):
 try:Draft202012Validator(s).validate(x);return True
 except AssertionError:return False
r=dict(binding_ref=UUID,expected_generation='7',expected_revision='9',target_window='ui-editor')
v=dict(ok=True,value=dict(transferred=True,content_changed=False,owner_generation='8',revision='9',ack_state='Delivered'),replayed=False)
roots=[]
def probe(name,s,x,want):
 actual=valid(s,x);check(name,actual==want);roots.append(dict(name=name,expected=want,actual=actual))
probe('valid request',req,r,True);probe('valid response',resp,v,True)
for x in (None,[],True,False,0,'text'):
 probe('request root '+repr(x),req,x,False);probe('response root '+repr(x),resp,x,False)
for field in r:
 x=copy.deepcopy(r);del x[field];probe('request missing '+field,req,x,False)
for extra in ('request_id','discard_unsaved','native_instance','target_consent'):
 x=dict(r);x[extra]=True;probe('request forged '+extra,req,x,False)
for field in ('ok','replayed'):
 x=copy.deepcopy(v);x[field]=int(x[field]);probe('typed bool '+field,resp,x,False)
for field in ('transferred','content_changed'):
 x=copy.deepcopy(v);x['value'][field]=int(x['value'][field]);probe('typed bool value '+field,resp,x,False)
for state in ('Delivered','Deferred'):
 x=copy.deepcopy(v);x['value']['ack_state']=state;probe('ack '+state,resp,x,True)
# Physical patterns, including unreachable common inline $defs, are parsed as stored.
patterns=[]
def walk(x,path,root):
 if isinstance(x,dict):
  if 'pattern' in x:patterns.append(dict(root=root,path=path,pattern=x['pattern']))
  for k,y in x.items():walk(y,path+'/'+k,root)
 elif isinstance(x,list):
  for i,y in enumerate(x):walk(y,path+'/'+str(i),root)
for name,s in [('request',req),('response',resp)]:walk(s,'',name)
lex=[]
for p in patterns:
 pat=p['pattern'];regex=re.compile(pat)
 if '{64}' in pat:good=['a'*64];bad=['A'*64,'a'*63,'a'*65]
 elif '[89ab]' in pat:good=[UUID];bad=[UUID.upper(),UUID[:-1],'not-uuid']
 else:good=['0','1','18446744073709551615'];bad=['00','-1','18446744073709551616','184467440737095516150']
 for x in good:check(p['root']+p['path']+' valid '+x,bool(regex.search(x)))
 for x in bad+[good[0]+c for c in ('\n','\r','\r\n','\u2028','\u2029','x')]:check(p['root']+p['path']+' invalid '+repr(x),not regex.search(x))
 lex.append(p)
save('lexical-audit.json',dict(physical_patterns=len(patterns),patterns=lex,strict_end='(?![\\s\\S]) actual parsed patterns'))
domain=[e for e in resp['$defs']['Error']['oneOf'] if e['properties']['code'].get('const')=='DomainRejected']
check('seven DomainRejected',len(domain)==7)
for i,e in enumerate(domain):
 fields=e['properties']['details']['properties']['fields'];payload={k:'field' for k in fields['required']}
 err=dict(ok=False,replayed=False,error=dict(code='DomainRejected',details=dict(code=e['properties']['details']['properties']['code']['const'],fields=payload)))
 probe('domain '+str(i),resp,err,True)
 x=copy.deepcopy(err);x['error']['details']['fields']['unknown']=True;probe('domain closed '+str(i),resp,x,False)
# Exact common fragment lineage, including rootType branch.
close=json.loads((P.parent/'binding-close-integration/response.schema.json').read_text(encoding='utf-8'))
original=[e for e in close['$defs']['Error']['oneOf'] if e['properties']['code'].get('const')=='DomainRejected']
check('domain exact carried source',domain==original)
rootbranches=[e for e in resp['$defs']['Error']['oneOf'] if e['properties']['code'].get('enum')==['InvalidRequest']]
check('InvalidRequest exact source',rootbranches==[e for e in close['$defs']['Error']['oneOf'] if e['properties']['code'].get('enum')==['InvalidRequest']])
probe('non-object Type diagnostic exact generic branch',resp,dict(ok=False,replayed=False,error=dict(code='InvalidRequest',details=dict(field='',reason='Type'))),True)
# Root reachability is distinct from physical definition lexical checks.
def resolve(s,r):
 for k in r[2:].split('/'):s=s[k]
 return s
def witness(root,s,choices):
 if '$ref' in s:return witness(root,resolve(root,s['$ref']),choices)
 if 'oneOf' in s:return witness(root,s['oneOf'][choices.pop(0) if choices else 0],choices)
 if 'const' in s:return s['const']
 if 'enum' in s:return s['enum'][0]
 if s.get('type')=='object':return {k:witness(root,z,choices) for k,z in s.get('properties',{}).items() if k in s.get('required',[])}
 if s.get('type')=='array':return [witness(root,s['items'],choices)]
 if s.get('type')=='boolean':return False
 if 'pattern' in s:return 'a'*64 if '{64}' in s['pattern'] else UUID if '[89ab]' in s['pattern'] else '7'
 return 'value'
def routes(root,s,path=(),choices=(),seen=()):
 if '$ref' in s:
  if s['$ref'] not in seen:yield from routes(root,resolve(root,s['$ref']),path,choices,seen+(s['$ref'],))
  return
 if 'pattern' in s:yield path,choices,s['pattern']
 for i,z in enumerate(s.get('oneOf',[])):yield from routes(root,z,path,choices+(i,),seen)
 for k,z in s.get('properties',{}).items():yield from routes(root,z,path+(k,),choices,seen)
 if 'items' in s:yield from routes(root,s['items'],path+(0,),choices,seen)
traces=[]
for name,s in [('request',req),('response',resp)]:
 for path,choices,pattern in routes(s,s):
  value=witness(s,s,list(choices));cursor=value
  for k in path[:-1]:cursor=cursor[k]
  good='a'*64 if '{64}' in pattern else UUID if '[89ab]' in pattern else '7'
  cursor[path[-1]]=good;probe(name+' root lexical '+str(path),s,value,True)
  for suffix in ('\n','\r','\u2028','\u2029','x'):
   bad=copy.deepcopy(value);c=bad
   for k in path[:-1]:c=c[k]
   c[path[-1]]=good+suffix;probe(name+' root lexical negative '+str(path)+repr(suffix),s,bad,False)
  traces.append(dict(root=name,path=list(path),branches=list(choices),pattern=pattern))
save('root-occurrence-trace.json',traces)
save('root-probes.json',roots)
model=[]
for f in load('fixtures.json'):
 out=exercise(f['mode']);check(f['id']+' '+f['mode'],out['result']==f['expected']);model.append(dict(f,result=out))
 # Every model result has a complete response, not a string-only pseudo-error.
 outcome=out['result']
 if out['transfers']:
  response=dict(ok=True,replayed=False,value=dict(transferred=True,content_changed=False,owner_generation='8',revision='9',ack_state='Deferred' if outcome in ('TransferredAckDeferred','TransferredTargetUnavailable','Discarded') else 'Delivered'))
  # Repeat is a fresh rejected command, not replayed success.
  if outcome=='StaleOwner':response=dict(ok=False,replayed=False,error=dict(code='StaleOwner',details={}))
 else:
  if outcome=='RevisionOverflow':err=dict(code='DomainRejected',details=dict(code='RevisionOverflow',fields={}))
  else:
   details={}
   if outcome=='DependencyNotReady':details=dict(dependency='M04_OWNER_INTEGRATION')
   if outcome=='IdentityConflict':details=dict(reference=UUID)
   if outcome=='StaleRevision':details=dict(expected='8',observed='9')
   err=dict(code=outcome,details=details)
  response=dict(ok=False,replayed=False,error=err)
 probe(f['id']+' concrete response root',resp,response,True)
 model[-1]['response']=response
save('model-results.json',model)
save('root-probes.json',roots)
snapshot=load('source-current.json');authority=ROOT/snapshot['authority'];a=json.loads(authority.read_text(encoding='utf-8'))['source_hashes']
check('796 authority count',len(a)==796)
check('authority hash fixed',sha(authority)==snapshot['authority_sha256'])
sourcechecks=[]
for name,expected in a.items():
 actual=sha(ROOT/name) if (ROOT/name).is_file() else None
 check('source '+name,actual==expected==snapshot['current_hashes'][name]);sourcechecks.append(dict(path=name,expected=expected,actual=actual,match=actual==expected))
save('source-comparison.json',sourcechecks)
for name,expected in load('source-input-hashes.json').items():check('input '+name,sha(ROOT/name)==expected)
# JS patterns use same stored regex strings; no normalized surrogate tests.
node="""const fs=require('fs');const p=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));let n=0;for(const x of p.patterns){const r=new RegExp(x.pattern);const g=x.pattern.includes('{64}')?'a'.repeat(64):x.pattern.includes('[89ab]')?'abcdef01-abcd-4abc-8abc-abcdef012345':'18446744073709551615';if(!r.test(g))throw Error(x.path);for(const s of ['\\n','\\r','\\r\\n','\\u2028','\\u2029','x']){if(r.test(g+s))throw Error(x.path+s);n++}}console.log(JSON.stringify({checks:n,status:'PASS_NODE_LEXICAL_ONLY'}));"""
(P/'probe.cjs').write_text(node,encoding='utf-8')
result=subprocess.check_output(['node',str(P/'probe.cjs'),str(P/'lexical-audit.json')],text=True);save('node-results.json',json.loads(result))
verification=dict(status='AUTHOR_CANDIDATE_CHECKS_PASS',author='/root/m03_binding_transfer_packet',independent_acceptance='NOT RUN',checks=len(checks),model_cases=len(model),source_files=len(sourcechecks),source_current='each of 796 authority paths compared',FullDraft='NOT COMPLETE; subset only',product_native_RED='NOT RUN',product_tests='NOT RUN',build='NOT RUN',Owner='NOT RUN',module_complete=False,command='python docs/requirements-confirmation/phase1-spec/tasks/M03/planning/binding-transfer-integration/checker.py')
save('verification.json',verification)
page=(P/'index.html').read_text(encoding='utf-8')
start='<!--AUTHOR-RESULTS-->';end='<!--END-AUTHOR-RESULTS-->'
if start in page:page=page[:page.index(start)]+page[page.index(end)+len(end):]
import html
block=start+'<section><h2>Author candidate evidence (not acceptance)</h2><pre>'+html.escape(json.dumps(verification,indent=2))+'</pre><p>Trusted fixture premises: Authority.mint is privileged test-only; native registry, target consent, M04 unique owner and atomic commit are assumed inputs. No native implementation, runtime atomicity, or real window behavior is proven.</p><ul>'+''.join('<li><a href="'+n+'">'+n+'</a></li>' for n in ['request.schema.json','response.schema.json','document_model.py','fixtures.json','model-results.json','root-probes.json','root-occurrence-trace.json','lexical-audit.json','node-results.json','source-current.json','source-comparison.json','source-input-hashes.json','before-after.json','owner-choices.json','module.feature','steps.py','step-definition-stubs.json','traceability.json','lessons.json','pending-automation.json','verification.json'])+'</ul></section>'+end
page=page.replace('</html>',block+'</html>');(P/'index.html').write_text(page,encoding='utf-8')
save('artifact-hashes.json',{f.name:sha(f) for f in P.iterdir() if f.is_file() and f.name!='artifact-hashes.json'})
print(json.dumps(verification,indent=2))
