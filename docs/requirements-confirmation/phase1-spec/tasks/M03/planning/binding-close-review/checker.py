import sys,json,pathlib,hashlib,copy,ast,re,subprocess,datetime,html
sys.dont_write_bytecode=True
P=pathlib.Path(__file__).resolve().parent; C=P.parent/'binding-close-integration'; R=pathlib.Path('D:/AIAD')
sys.path.insert(0,str(C))
from document_model import fresh,Authority,close,delivery,TUPLE
from schema_subset import Draft202012Validator
J=lambda n:json.loads((C/n).read_text(encoding='utf-8-sig'))
results=[]
def check(name,actual,expected):
 assert actual==expected,(name,actual,expected)
 results.append({'id':name,'actual':actual,'expected':expected,'status':'PASS'})
def valid(root,x):
 try:Draft202012Validator(J(root)).validate(x);return True
 except AssertionError:return False
for n in ['request.schema.json','response.schema.json']:
 for x in [None,False,True,0,1,'x',[]]:check(n+' nonobject '+repr(x),valid(n,x),False)
for case in J('root-probes.json'):check('root '+case['label'],valid(case['root'],case['value']),case['expected'])
# All actual parsed physical lexical strings; independently generated suffix and prefix corpus.
patterns=[]
def walk(v,path):
 if isinstance(v,dict):
  for k,x in v.items():
   if k=='pattern':patterns.append((path+'/'+k,x))
   else:walk(x,path+'/'+k)
 elif isinstance(v,list):
  for i,x in enumerate(v):walk(x,path+'/'+str(i))
for n in ['request.schema.json','response.schema.json']:walk(J(n),n)
for path,pattern in patterns:
 s='abcdef01-abcd-4abc-8abc-abcdef012345' if '-4[0-9a-f]' in pattern else 'a'*64 if '{64}'in pattern else '18446744073709551615'
 check(path+' positive',bool(re.search(pattern,s)),True)
 for tail in ['\n','\r','\r\n','\u2028','\u2029','\x00',' ','\t']:
  check(path+repr(tail),bool(re.search(pattern,s+tail)),False)
# Re-execute extracted checker schema probe statements without any candidate file writes.
tree=ast.parse((C/'checker.py').read_text(encoding='utf-8-sig'));check('checker AST parsed',isinstance(tree,ast.Module),True)
for flag in ['ok','replayed']:
 for bad in [0,1,None,'false',[],{}]:
  packet={'ok':True,'value':{'closed':True,'content_changed':False},'replayed':False};packet[flag]=bad
  check('boolean metadata '+flag+repr(bad),valid('response.schema.json',packet),False)
for flag in ['closed','content_changed']:
 for bad in [0,1,None,'false',[],{}]:
  packet={'ok':True,'value':{'closed':True,'content_changed':False},'replayed':False};packet['value'][flag]=bad
  check('boolean value '+flag+repr(bad),valid('response.schema.json',packet),False)
# AST-extract only pure schema sample helpers, never execute author output mutations.
ns={'rs':J('response.schema.json'),'U':'abcdef01-abcd-4abc-8abc-abcdef012345'}
for name in ['resolve','sample']:
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.Module(body=[node],type_ignores=[]),'<independent AST extract>','exec'),ns)
branches=J('response.schema.json')['$defs']['Error']['oneOf'];typed=0
for i,branch in enumerate(branches):
 packet={'ok':False,'error':ns['sample'](branch),'replayed':False}
 check('independent complete error '+str(i),valid('response.schema.json',packet),True)
 if packet['error']['code']=='DomainRejected':typed+=1
 def leaves(x,path=()):
  if isinstance(x,dict):
   for k,v in x.items():yield from leaves(v,path+(k,))
  else:yield path,x
 for path,value in leaves(packet['error']):
  for bad in [None,[],{},True,123]:
   if type(bad)==type(value):continue
   altered=copy.deepcopy(packet);cursor=altered['error']
   for k in path[:-1]:cursor=cursor[k]
   cursor[path[-1]]=bad
   check('error metadata type '+str(i)+str(path)+repr(bad),valid('response.schema.json',altered),False)
check('seven typed errors',typed,7)
# New cross-product authority probes, independent of author exercise modes.
def setup():
 s=fresh();a=Authority();r=dict(binding_ref=s['observation']['binding_ref'],expected_generation='7',expected_revision='9',discard_unsaved=False);caller=dict(role='ui-editor',origin='tauri://localhost',instance='editor-1',native_live=True);o=copy.deepcopy(s['observation']);o['attachment_active']=False
 return s,a,r,caller,o
for key in TUPLE:
 for bad in [None,False,1,[],{},'', 'foreign']:
  s,a,r,c,o=setup();o[key]=bad;before=copy.deepcopy(s)
  check('detach proof '+key+repr(bad),close(s,r,c,a,a.mint(o)),'ProofMismatch');check('unchanged '+key+repr(bad),s,before)
for flag in ['attachment_active','native_live']:
 for bad in [None,'false',0,[],{}]:
  s,a,r,c,o=setup();o[flag]=bad;check('typed detach '+flag+repr(bad),close(s,r,c,a,a.mint(o)),'ProofMismatch')
for role in ['ui-viewer','unknown','',None]:
 s,a,r,c,o=setup();c['role']=role;check('role '+repr(role),close(s,r,c,a,a.mint(o)),'UnauthorizedCaller')
for discard in [False,True]:
 s,a,r,c,o=setup();s['dirty']=True;s['writer']=True;r['discard_unsaved']=discard;check('no M04 confirmation '+str(discard),close(s,r,c,a,a.mint(o),owner_decision=False),'DependencyNotReady')
s,a,r,c,o=setup();before=copy.deepcopy(s);check('close success',close(s,r,c,a,a.mint(o)),'Closed');check('owner unchanged',s['document'],before['document']);check('inflight unchanged',s['inflight'],before['inflight']);check('repeat',close(s,r,c,a,a.mint(o)),'Closed');check('detach only once',s['calls']['detach'],1)
for key in TUPLE:
 obs=copy.deepcopy(before['observation']);obs[key]='foreign';check('late delivery fence '+key,delivery(a,a.mint(obs),before['observation']),False)
check('late delivery detached',delivery(a,a.mint(s['observation']),before['observation']),False)
check('unminted proof',delivery(a,object(),before['observation']),False)
# Current source snapshot is independent from historical SHA evidence.
source=J('source-current.json'); current=source.get('current_hashes',{}); drift=[p for p,h in current.items() if not (R/p).exists() or hashlib.sha256((R/p).read_bytes()).hexdigest()!=h]
check('source-current hashes',drift,[])
inputs=J('source-input-hashes.json');check('source inputs',[p for p,h in inputs.items() if hashlib.sha256((R/p).read_bytes()).hexdigest()!=h],[])
for name,obj in [('new-probes.json',results),('hash.json',{'candidate':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in C.iterdir() if p.is_file()},'source_count':len(current),'source_drift':drift})]:
 (P/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checks':len(results),'patterns':len(patterns),'source_count':len(current),'PASS':True}))

