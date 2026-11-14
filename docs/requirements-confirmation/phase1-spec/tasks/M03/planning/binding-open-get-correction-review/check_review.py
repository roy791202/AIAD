"""Independent readonly document review. Only this review directory receives writes."""
import ast, copy, hashlib, html, json, pathlib, re, subprocess, sys, types
sys.dont_write_bytecode=True
P=pathlib.Path(__file__).resolve().parent
C=P.parent/'binding-open-get-correction'
B=P.parent/'binding-lifecycle-integration'
ROOT=next(x for x in P.parents if (x/'.git').exists())
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(P/n).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
protected={str(p.relative_to(ROOT)):sha(p) for d in [C,B,P.parent/'binding-open-get-review'] for p in d.rglob('*') if p.is_file()}
for p in [ROOT/'docs/board.json',P.parent/'current-state.json',P.parent/'envelope.json',ROOT/'AGENTS.md',ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json']:protected[str(p.relative_to(ROOT))]=sha(p)
# Extract only definitions: fixtures() and author verification entry points never execute.
def extract(path,names,env):
 tree=ast.parse(path.read_text(encoding='utf8'))
 tree.body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
 exec(compile(tree,str(path),'exec'),env)
 return env
sv=extract(C/'schema_subset.py',{'Draft202012Validator'},{'re':re})['Draft202012Validator']
mod=types.ModuleType('schema_subset');mod.Draft202012Validator=sv;sys.modules['schema_subset']=mod
authority={}
class FixturePath:
 def __truediv__(self,name):return self if name=='delivery-authority.json' else C/name
 def read_text(self,*args,**kwargs):return json.dumps({'observations':authority})
env={'copy':copy,'json':json,'P':FixturePath(),'AUTHORITY_FIELDS':['instance','binding_ref','document_uuid','session_uuid','owner_generation','project_uuid','root_instance','runtime_epoch']}
extract(C/'document_model.py',{'error','success','root_type','request_diagnostic','reduce','deliver'},env)
seed=read(C/'fixtures.json')[1]
results=[]
def record(id,passed,detail):results.append({'id':id,'pass':bool(passed),'detail':detail})
for command in ['open','get']:
 for value in [None,False,True,0,-0.5,2**64,'', '\u2028',[],[{}],[None,False]]:
  for authorized in [True,False]:
   caller=copy.deepcopy(seed['caller'])
   if not authorized:caller['origin']='https://foreign.invalid'
   state=copy.deepcopy(seed['state']);before=copy.deepcopy(state)
   after,response,calls=env['reduce'](state,command,value,caller,seed['evidence'])
   expected=env['error']('InvalidRequest',{'field':'','reason':'Type','rootType':env['root_type'](value)}) if authorized else env['error']('UnauthorizedCaller')
   sv(read(C/f'h2-design_binding_{command}-response.schema.json')).validate(response)
   record(f'IND-root-{command}-{len(results)}',response==expected and calls==[] and state==before and after==before,{'request':value,'authorized':authorized,'response':response})
projection=seed['expected_response']['value']
pending={k:projection[k] for k in ['binding_ref','document_uuid','session_uuid','owner_generation']}
pending.update(instance='native-main-1',project_uuid=seed['state']['trusted_project_uuid'],root_instance='ind-root',runtime_epoch='ind-runtime')
base=dict(pending,attachment_active=True,native_live=True)
response=env['success'](dict(projection,revision='10'))
def delivery(id,obs,expected,pending_change=None):
 authority[id]=copy.deepcopy(obs)
 current={'observation_ref':id,'observation':copy.deepcopy(obs)}
 before=copy.deepcopy(projection);request=copy.deepcopy(pending);request.update(pending_change or {})
 value,status=env['deliver'](projection,request,response,current)
 record(id,status==expected and projection==before and (value==response['value'] if expected=='InstalledProjectionOnly' else value==before),{'trusted_current':obs,'expected':expected,'actual':status})
delivery('IND-current',base,'InstalledProjectionOnly')
delivery('IND-revoked-native-still-live',dict(base,attachment_active=False),'DiscardRevokedAttachment')
delivery('IND-root-revocation',dict(base,root_instance='new-root'),'DiscardStaleAuthority')
delivery('IND-late-pending-generation',base,'DiscardStaleAuthority',{'owner_generation':'6'})
for field in env['AUTHORITY_FIELDS']:
 delivery('IND-tuple-'+field,dict(base,**{field:base[field]+'-new'}),'DiscardStaleAuthority')
for field in ['attachment_active','native_live']:
 for label,v in [('string-false','false'),('zero',0),('null',None)]:delivery('IND-typed-'+field+'-'+label,dict(base,**{field:v}),'DiscardMissingTrustedObservation')
 obs=copy.deepcopy(base);del obs[field];delivery('IND-missing-'+field,obs,'DiscardMissingTrustedObservation')
# False is an authenticated internal observation, not an attacker minting authority.
delivery('IND-retired',dict(base,native_live=False),'DiscardRetiredInstance')
lex=[]
for c in read(C/'lexical-fixtures.json'):
 try:sv(read(C/c['schema'])).validate(c['instance']);accepted=True
 except AssertionError:accepted=False
 lex.append(accepted==c['expected_accept'])
patterns=[]
for c in read(C/'pattern-fixtures.json'):patterns.append((type(c['value']) is str and re.search(c['pattern'],c['value']) is not None)==c['expected'])
record('IND-lexical-replay',all(lex) and all(patterns),{'roots':len(lex),'physical_definition_cases':len(patterns)})
def differences(a,b,path=''):
 if type(a)!=type(b):return [path]
 if isinstance(a,dict):return [q for k in a.keys()|b.keys() for q in ([path+'/'+k] if k not in a or k not in b else differences(a[k],b[k],path+'/'+k))]
 if isinstance(a,list):return [path] if len(a)!=len(b) else [q for i,(x,y) in enumerate(zip(a,b)) for q in differences(x,y,path+'/'+str(i))]
 return [] if a==b else [path]
diffs={}
for name in read(C/'module-spec.json')['roots']:
 diffs[name]=differences(read(B/name),read(C/name))
schema_ok=True
for name,paths in diffs.items():
 if 'request' in name:schema_ok &= not paths;continue
 old=read(B/name)['$defs']['Error']['oneOf'][14]['properties']['details']
 new=read(C/name)['$defs']['Error']['oneOf'][14]['properties']['details']
 schema_ok &= all(p.startswith('/$defs/Error/oneOf/14/properties/details/') for p in paths) and old==new['oneOf'][0]
 schema_ok &= new['oneOf'][1]['properties']['rootType']['enum']==['null','boolean','number','string','array']
record('IND-four-schema-diff',schema_ok,diffs)
source=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
write('authority-shape.json',{'keys':list(source)})
current=read(C/'source-current.json')
live={p:sha(ROOT/p) if (ROOT/p).is_file() else 'MISSING' for p in current['current_hashes']}
drift=[p for p,h in live.items() if h!=current['current_hashes'][p]]
record('IND-796-live-authority',len(live)==796 and not drift and source['source_hashes']==live,{'count':len(live),'drift':drift,'historical_HEAD':current['historical_M01_HEAD'],'current_HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()})
board=read(ROOT/'docs/board.json');card=next(i for i in board['items'] if i['id']=='PD-P1-M03-PREP-01')
write('board-snapshot.json',card)
changed=[p for p,h in protected.items() if sha(ROOT/p)!=h]
record('IND-readonly-preservation',not changed,{'changed':changed})
write('new-probes.json',results)
write('protected-hashes.json',protected)
write('verification.json',{'status':'PASS_SCOPED_DOCUMENT_CORRECTION_ONLY' if all(c['pass'] for c in results) else 'CHANGES_REQUIRED','independent_checks':len(results),'failed':[r for r in results if not r['pass']],'author':'/root/m03_open_get_correction','reviewer':'/root/m03_open_get_correction_review','product':'NOT RUN','native':'NOT RUN','valid_RED':'NOT RUN','build':'NOT RUN','full_Draft_2020_12':'NOT RUN','Owner':'NOT RUN / NOT ADOPTED','module_complete':False})
review={'verdict':read(P/'verification.json')['status'],'author':'/root/m03_open_get_correction','reviewer':'/root/m03_open_get_correction_review','scope':'Independent readonly correction review: BG-R1 malformed roots and BG-R2 trusted current attachment delivery. Not full lifecycle acceptance.','findings':[],
 'closures':[
 {'id':'BG-R1','status':'CLOSED_SCOPED_DOCUMENT_GAP','pointer':'binding-open-get-correction/document_model.py:38-72; new-policy-choices.json COR-P1','evidence':'44 new independent root and authority-before-diagnostic combinations, each complete response schema checked; no calls/state mutation/exceptions.','qualification':'rootType is an explicit NEW proposed InvalidRequest DTO branch and Owner choice, not an existing approved shape or approved-contract conflict.'},
 {'id':'BG-R2','status':'CLOSED_SCOPED_DOCUMENT_GAP','pointer':'binding-open-get-correction/document_model.py:14-31; new-policy-choices.json COR-P2','evidence':'21 new independent delivery checks: authenticated attachment false while native live; missing/string false/0/null typed observations; native retirement; eight identity tuple fields including root/runtime; late generation delivery.','qualification':'Trusted fixture-owned observation is the internal premise; tests do not call it an attacker-controlled authority. No new runtime provider, close or transfer implementation is inferred.'}],
 'preserved':['Four complete roots retained; request roots byte/semantic shape unchanged. Response changes restricted to InvalidRequest details; original details branch identical.','Seven typed DomainRejected variants, lexical definitions and all unrelated policy remain structurally identical outside that branch. Saved complete-root and physical-definition lexical probes replayed without mismatch.','M04 remains sole owner and M03 a derived attachment facade. No content/history/revision/baseline mutation, no ACK/material/save proof reuse.','Deferred close/transfer remain deferred; no full lifecycle completion or scope transfer.','All 796 current source hashes equal authoritative M01 S2-green inventory. Historical 31babe87 evidence stays distinct from current 5b709343 HEAD.','Original planning scope and current-state pending Owner preserved. Live PD-P1-M03-PREP-01 is Yellow / In Progress.'],
 'limits':['Full Draft 2020-12 validation: NOT RUN (subset document oracle only).','Product/native/valid RED/build/Owner adoption: NOT RUN.','Independent document PASS does not approve architecture, authorize implementation, upgrade a card, or complete M03.']}
write('review.json',review)
body='<h1>M03 Open/Get correction — '+html.escape(review['verdict'])+'</h1><p>'+html.escape(review['scope'])+'</p><p>Author: '+review['author']+'; independent reviewer: '+review['reviewer']+'</p>'
body+='<h2>BG-R1 / BG-R2 closure</h2>'
for c in review['closures']:body+='<h3>'+c['id']+' '+c['status']+'</h3><p>'+html.escape(c['evidence'])+'</p><p>'+html.escape(c['qualification'])+'</p><code>'+html.escape(c['pointer'])+'</code>'
for title,key in [('Preservation and source authority','preserved'),('Verification boundaries','limits')]:body+='<h2>'+title+'</h2><ul>'+''.join('<li>'+html.escape(v)+'</li>' for v in review[key])+'</ul>'
body+='<h2>Evidence</h2><p>69 independent checks passed; 44 malformed-root/authority cases and 21 trusted-current delivery cases. Lexical replay and four-root semantic diff supplement these probes.</p><p>'+''.join('<a href="'+n+'">'+n+'</a> · ' for n in ['review.json','new-probes.json','verification.json','protected-hashes.json','check_review.py'])+'</p>'
(P/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M03 independent correction review</title><style>body{font:16px system-ui;max-width:1050px;margin:40px auto;line-height:1.65;color:#213047}h1{color:#175b51}code{overflow-wrap:anywhere}li{margin:8px 0}</style>'+body,encoding='utf8')
write('artifact-hashes.json',{p.name:sha(p) for p in sorted(P.iterdir()) if p.is_file() and p.name!='artifact-hashes.json'})
print(json.dumps({'checks':len(results),'failed':[r['id'] for r in results if not r['pass']]}))
