import pathlib,json,ast,sys,hashlib,copy,subprocess
P=pathlib.Path(__file__).resolve().parent
C=P.parent/'binding-transfer-integration'
ROOT=P.parents[6]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):(P/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
frozen={p.name:sha(p) for p in C.iterdir() if p.is_file()}
save('candidate-frozen-hashes.json',frozen)
sys.path.insert(0,str(C));sys.dont_write_bytecode=True
# Extract only pure schema/model/checker definitions. Do not execute author's mutation pipeline.
from document_model import fresh,observation,Authority,transfer,delivery,UUID,IDENTITY
from schema_subset import Draft202012Validator
results=[]
def record(name,expected,actual):results.append(dict(name=name,expected=expected,actual=actual,pass_=expected==actual))
r=dict(binding_ref=UUID,expected_generation='7',expected_revision='9',target_window='ui-editor')
caller=('main','source-1','tauri://localhost',True)
def run(outcome='commit',provider=True,change=None):
 s=fresh();o=observation(s)
 if change:change(o)
 a=Authority();t=a.mint(o);before=copy.deepcopy(s);z=transfer(s,r,caller,a,t,provider,outcome)
 return z,s,before
# Trusted observation records remain genuine. Malformed provider result is injected at
# the model's explicit outcome seam, not by attacker editing Authority.records.
for outcome in ('COMMIT','timeout',None,False,0,{},[]):
 z,s,b=run(outcome=outcome)
 record('unknown outcome '+repr(outcome),'fail closed without commit', 'committed' if s['transfers'] else 'fail closed without commit')
for provider in (1,'ready',{}):
 z,s,b=run(provider=provider)
 record('provider type '+repr(provider),'fail closed without commit','committed' if s['transfers'] else 'fail closed without commit')
z,s,b=run(outcome='timeout')
save('counterexample-state.json',dict(pointer='../binding-transfer-integration/document_model.py:transfer',injection=dict(outcome='timeout',provider=True),result=z,before=b,after=s,expected='typed enum guard before mutation; no retry or new semantics',claim='document model only; trusted fixture enum malformed at explicit seam, not IPC/native attack'))
# Independent type matrix on all boolean native fields, preserving trusted premise:
# issuer minting bad typed observations must be rejected, not treated as IPC authority.
for field in ('source_live','target_live','target_ready','target_consent','target_revoked','target_dirty','discard_confirmed','unique_owner','target_unique'):
 for value in (0,1,'true',None):
  z,s,b=run(change=lambda o,f=field,v=value:o.__setitem__(f,v))
  record('native type '+field+' '+repr(value),'ProofMismatch',z)
for field in IDENTITY:
 z,s,b=run(change=lambda o,f=field:o.__setitem__(f,'other'))
 record('identity fence '+field,'IdentityConflict',z)
for outcome in ('commit','ack-lost'):
 z,s,b=run(outcome)
 record('document invariant '+outcome,b['document'],s['document'])
 record('late source delivery '+outcome,False,delivery(s,'7'))
 record('no formal IO ACK '+outcome,False,any(s['forbidden_calls'].values()))
 record('consumed candidate '+outcome,[],s['candidates'])
 record('retired preview '+outcome,[],s['previews'])
z,s,b=run('rollback');record('known rollback','IoFailure',z);record('rollback state',b,s)
z,s,b=run('unknown');record('unknown distinct','Indeterminate',z)
# Independent root semantics; full JSON Schema implementation remains NOT RUN.
for name in ('request','response'):
 schema=json.loads((C/(name+'.schema.json')).read_text())
 for bad in (True,1,False,0,[],None):
  try:Draft202012Validator(schema).validate(bad);ok=True
  except AssertionError:ok=False
  record(name+' rejects non-object '+repr(bad),False,ok)
validresponse=dict(ok=True,replayed=False,value=dict(transferred=True,content_changed=False,owner_generation='8',revision='9',ack_state='UNKNOWN'))
try:Draft202012Validator(json.loads((C/'response.schema.json').read_text())).validate(validresponse);ok=True
except AssertionError:ok=False
record('unknown receipt ack enum',False,ok)
# Read-only AST-selected root helper re-evaluation, not author checker execution.
tree=ast.parse((C/'checker.py').read_text()); selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('resolve','witness','routes')]
ns={"UUID":UUID};exec(compile(ast.Module(body=selected,type_ignores=[]),'author-root-helper-extract','exec'),ns)
count=0
for name in ('request','response'):
 schema=json.loads((C/(name+'.schema.json')).read_text())
 for path,choices,pattern in ns['routes'](schema,schema):
  value=ns['witness'](schema,schema,list(choices));cur=value
  for k in path[:-1]:cur=cur[k]
  good='a'*64 if '{64}' in pattern else UUID if '[89ab]' in pattern else '7'
  for suffix in ('\x00','\t','\u0085','\u2028'):
   cur[path[-1]]=good+suffix
   try:Draft202012Validator(schema).validate(value);ok=True
   except AssertionError:ok=False
   record(name+' independent lexical '+str(path)+repr(suffix),False,ok);count+=1
snapshot=json.loads((C/'source-current.json').read_text());authority=ROOT/snapshot['authority'];a=json.loads(authority.read_text())['source_hashes']
sourcebad=[n for n,h in a.items() if not (ROOT/n).is_file() or sha(ROOT/n)!=h or snapshot['current_hashes'].get(n)!=h]
record('796 current source paths',[],sourcebad);record('authority hash',snapshot['authority_sha256'],sha(authority))
record('candidate unchanged',frozen,{p.name:sha(p) for p in C.iterdir() if p.is_file()})
save('new-probes.json',results)
save('verification.json',dict(status='CHANGES_REQUIRED_DOCUMENT_MODEL_ONLY',reviewer='/root/m03_binding_transfer_review',author='/root/m03_binding_transfer_packet',checks=len(results),passed=sum(x['pass_'] for x in results),failed=sum(not x['pass_'] for x in results),root_extra_cases=count,source_files=len(a),source_drift=sourcebad,HEAD=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),FullDraft='NOT RUN',product_native_RED='NOT RUN',product_tests='NOT RUN',build='NOT RUN',Owner='NOT RUN',module_complete=False))
print(json.dumps(json.loads((P/'verification.json').read_text()),indent=2))

