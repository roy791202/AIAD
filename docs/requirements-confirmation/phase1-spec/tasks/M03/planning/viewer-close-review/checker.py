"""Independent bounded document review. Run python -B; no candidate writes."""
import copy, hashlib, importlib.util, json, pathlib, re, subprocess, sys
sys.dont_write_bytecode=True
P=pathlib.Path(__file__).resolve().parent
C=P.parent/'viewer-close-integration'
R=P.parents[6]
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name):
 s=importlib.util.spec_from_file_location('review_'+name,C/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
model=load('document_model')
req=read(C/'request.schema.json');res=read(C/'response.schema.json')
# Independently written evaluator, bounded to physical keywords present here.
def valid(root,x,s=None):
 s=root if s is None else s
 if '$ref' in s:
  t=root
  for k in s['$ref'][2:].split('/'):t=t[k]
  return valid(root,x,t)
 if 'oneOf' in s and sum(valid(root,x,t) for t in s['oneOf'])!=1:return False
 if 'const' in s and (type(x)!=type(s['const']) or x!=s['const']):return False
 if 'enum' in s and not any(type(x)==type(v) and x==v for v in s['enum']):return False
 kinds=s.get('type');kinds=[kinds] if isinstance(kinds,str) else kinds
 if kinds and not any({'object':type(x)==dict,'array':type(x)==list,'string':type(x)==str,'boolean':type(x)==bool,'null':x is None}.get(k,False) for k in kinds):return False
 if type(x)==dict:
  if set(s.get('required',[]))-set(x):return False
  if s.get('additionalProperties') is False and set(x)-set(s.get('properties',{})):return False
  if any(not valid(root,x[k],v) for k,v in s.get('properties',{}).items() if k in x):return False
 if type(x)==str:
  if not s.get('minLength',0)<=len(x)<=s.get('maxLength',10**8):return False
  if 'pattern' in s and re.search(s['pattern'],x) is None:return False
 if type(x)==list and 'items' in s and any(not valid(root,v,s['items']) for v in x):return False
 return True
err={'$defs':res['$defs'],'$ref':'#/$defs/Error'}
records=[];failures=[]
def record(name,kind,expected,actual,fixture=None):
 row={'id':'VC-R-'+str(len(records)+1).zfill(4),'name':name,'category':kind,'expected':expected,'actual':actual,'pass':expected==actual}
 if fixture is not None:row['fixture']=fixture
 records.append(row)
 if not row['pass']:failures.append(row)
seed=read(C/'fixtures.json')[0]
def probe(name,mutate,code=None,retired=False,delivered=False):
 c=copy.deepcopy(seed);c.pop('expected',None);mutate(c)
 a=model.close(c,lambda v:valid(req,v),lambda v:valid(err,v))
 expected={'code':code,'retired':retired,'delivered':delivered,'automatic_retry':False,'protected_equal':True,'response_valid':True,'ui':'Closed' if delivered else 'CloseUncertain'}
 protected=set(c['before'])-{'preview_active','mock','capabilities','slots'}
 actual={'code':a['response'].get('error',{}).get('code'),'retired':not a['state']['preview_active'],'delivered':a['delivered'],'automatic_retry':a['automatic_retry'],'protected_equal':all(a['state'][k]==c['before'][k] for k in protected),'response_valid':valid(res,a['response']),'ui':a['ui']}
 record(name,'behavior',expected,actual,{'input':c,'observed':a})
 return a
probe('success with rich protected-state sentinel',lambda c:c['before'].update(content={'nested':[1,False,None]},history=[{'op':'undo'}],ACK={'pending':True},binding_attached=True),retired=True,delivered=True)
for slots in (1,4):
 a=probe('release exactly one slot '+str(slots),lambda c:c['before'].update(slots=slots),retired=True,delivered=True)
 record('slot arithmetic '+str(slots),'capacity',slots-1,a['state']['slots'])
 a2=probe('repeated close '+str(slots),lambda c:c.update(before=copy.deepcopy(a['state'])),'PreviewClosed',retired=True)
 record('repeat never calls provider '+str(slots),'repeat',False,'provider.preview.close' in a2['calls'])
for key,code in [('consumer','UnauthorizedCaller'),('window_instance','UnauthorizedCaller'),('root_instance','MissingBinding'),('runtime_epoch','MissingBinding'),('project_uuid','MissingBinding'),('document_uuid','MissingBinding'),('session_uuid','MissingBinding'),('generation','StaleOwner'),('preview_session','PreviewClosed')]:
 value='8' if key=='generation' else ('bbcdef01-abcd-4abc-8abc-abcdef012345' if key.endswith('uuid') or key=='preview_session' else 'foreign')
 probe('capture foreign '+key,lambda c,k=key,v=value:c['provider']['capture'].update({k:v}),code)
 a=probe('late delivery '+key,lambda c,k=key,v=value:c['provider']['delivery'].update({k:v}),code,retired=True)
 record('late response never delivers '+key,'late',False,'ui.closed.deliver' in a['calls'])
for stage in ('capture','delivery'):
 for k,v in [('revoked',True),('native_live',False)]:
  probe(stage+' '+k,lambda c,s=stage,k=k,v=v:c['provider'][s].update({k:v}),'PreviewClosed' if stage=='delivery' or k=='revoked' else 'UnauthorizedCaller',retired=stage=='delivery')
for stage in ('capture','delivery'):
 for key in seed['provider'][stage]:
  for bad in (None,[],{},0,True):
   if type(seed['provider'][stage][key]) is bool and type(bad) is bool:continue
   probe(stage+' mistyped '+key+' '+repr(bad),lambda c,s=stage,k=key,v=bad:c['provider'][s].update({k:v}),'DependencyNotReady')
  probe(stage+' missing '+key,lambda c,s=stage,k=key:c['provider'][s].pop(k),'DependencyNotReady')
for key in seed['provider']['closed_observation']:
 probe('proof missing '+key,lambda c,k=key:c['provider']['closed_observation'].pop(k),'DependencyNotReady')
 for bad in (None,0,False,[],{}):
  probe('proof invalid '+key+' '+repr(bad),lambda c,k=key,v=bad:c['provider']['closed_observation'].update({k:v}),'DependencyNotReady')
for outcome in ('Busy','Unknown',None,True,{}, {'code':'Busy','details':{'extra':True}}, {'code':'UnauthorizedCaller','details':{}}):
 probe('invalid/unsupported outcome '+repr(outcome),lambda c,v=outcome:c['provider'].update(outcome=v),'DependencyNotReady')
probe('valid provider Busy before commit',lambda c:c['provider'].update(outcome={'code':'Busy','details':{}}),'Busy')
probe('response lost after commit preserves retirement',lambda c:c['provider'].update(outcome='ResponseLostAfterCommit'),'DependencyNotReady',retired=True)
probe('unauthorized plus invalid request',lambda c:(c.update(request={}),c['provider'].update(trusted_local=False)),'UnauthorizedCaller')
probe('malformed native plus invalid request',lambda c:(c.update(request={}),c['provider']['capture'].pop('consumer')),'DependencyNotReady')
probe('invalid request plus stale owner',lambda c:(c.update(request={}),c['provider']['capture'].update(generation='8')),'InvalidRequest')
probe('proof malformed plus late foreign',lambda c:(c['provider'].update(closed_observation={}),c['provider']['delivery'].update(consumer='foreign')),'DependencyNotReady')
# Closed request and response roots; enumerate all original root examples without author rerun.
record('valid exact request','schema',True,valid(req,seed['request']))
for bad in (None,[],{},dict(seed['request'],extra=True),{'preview_session':True},{'preview_session':seed['request']['preview_session']+'\n'}):record('request negative '+repr(bad),'schema',False,valid(req,bad),bad)
roots=[]
for row in read(C/'root-probes.json'):
 if row['valid'] and row['value'] not in roots:roots.append(row['value'])
for i,root in enumerate(roots):
 record('root valid '+str(i),'schema',True,valid(res,root),root)
 for key in root:
  bad=copy.deepcopy(root);bad.pop(key);record('root missing '+str(i)+key,'schema',False,valid(res,bad),bad)
 bad=dict(root,unlisted=True);record('root extra '+str(i),'schema',False,valid(res,bad),bad)
# Test exact parsed pattern strings against independent semantic lexical oracles.
patterns={}
def walk(s,path):
 if type(s)==dict:
  if 'pattern' in s:patterns[path]=s['pattern']
  for k,v in s.items():walk(v,path+'/'+k)
 elif type(s)==list:
  for i,v in enumerate(s):walk(v,path+'/'+str(i))
for label,schema in [('request',req),('response',res),('observation',read(C/'provider-observation.schema.json'))]:walk(schema,label)
for path,pattern in patterns.items():
 if '[1-9]' in pattern:
  values=['0','1',str(2**64-1),str(2**64),'00','01','-1','+1','1.0','1e0','1\n','1\r\n','1\u2028','1\u2029','١','1x']
  # Physical lexical pattern alone intentionally does not enforce the semantic u64 cap.
  oracle=lambda x:re.fullmatch('0|[1-9][0-9]*',x) is not None
  if path.startswith('observation/$defs/'):
   # Unused carried definitions are original patterns, not reachable native tuple schemas.
   oracle=lambda x:re.search('^(0|[1-9][0-9]*)$',x) is not None
 elif '{8}' in pattern:
  uuid=seed['request']['preview_session'];values=[uuid,uuid.upper(),uuid+'\n',uuid+'\r\n',uuid+'\u2028',' '+uuid,uuid.replace('-4','-3',1),uuid.replace('-8','-7',1)]
  oracle=lambda x:re.fullmatch('[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',x) is not None
 else:continue
 for value in values:record(path+' '+repr(value),'parsed-pattern',oracle(value),re.search(pattern,value) is not None,{'pattern':pattern,'value':value})
for file,digest in read(C/'artifact-hashes.json').items():record('sealed candidate '+file,'hash',digest,sha(C/file))
for file,digest in read(C/'preserved-inputs.json').items():
 if file!='docs/board.json':record('original '+file,'hash',digest,sha(R/file))
for stage in ('capture','delivery'):
 for value in ('18446744073709551616','01','1\n','-1','1e0'):
  probe('semantic u64 '+stage+' '+repr(value),lambda c,s=stage,v=value:c['provider'][s].update(generation=v),'DependencyNotReady')
authority_path=R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json'
authority=read(authority_path)
for file,digest in authority['source_hashes'].items():record('796 authority '+file,'product-hash',digest,sha(R/file))
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
record('current HEAD','authority','5b709343a890503ebbe24a802e43cda5647df124',head)
record('authority inventory length','authority',796,len(authority['source_hashes']))
record('candidate authority hash','authority',read(C/'source-current.json')['authority_sha256'],sha(authority_path))
spec=read(C/'module-spec.json')
for row in spec['policy_rows']:record('policy pending '+row['area'],'policy','PROPOSED_PENDING_OWNER',row['status'])
html=(C/'index.html').read_text(encoding='utf-8');embedded=re.search('<script type="application/json" id="module-spec">(.*?)</script>',html,re.S)
record('candidate embedded structured spec','projection',spec,json.loads(embedded.group(1)))
result={'status':'PASS_VIEWER_CLOSE_DOCUMENT_ONLY_PENDING_OWNER' if not failures else 'CHANGES_REQUIRED','reviewer':'/root/m03_viewer_close_review','author':'/root/m03_viewer_close_packet','checks':len(records),'failures':len(failures),'new_behavior_probes':sum(r['category']=='behavior' for r in records),'parsed_pattern_checks':sum(r['category']=='parsed-pattern' for r in records),'candidate_seal_files':len(read(C/'artifact-hashes.json')),'preserved_originals':len(read(C/'preserved-inputs.json')),'source_files':len(authority['source_hashes']),'head':head,'historical_head':authority['head'],'management_board_hash':sha(R/'docs/board.json'),'board_note':'Management hash recorded separately; board is not part of product 796 authority. No board modifications by reviewer.','native':'NOT RUN','build':'NOT RUN','product_tests':'NOT RUN','valid_RED':'NOT RUN','full_Draft_validator':'NOT RUN','old_author_suites':'NOT RERUN','owner_adoption':False,'module_complete':False,'parent_light':'Yellow'}
for name,value in [('fixtures-results.json',records),('results.json',result),('findings.json',failures),('parsed-patterns.json',patterns)]: (P/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
review={'identity':result,'scope':'Independent document review; no product or original writes','contracts':['exact closed wire roots','typed native/provider observations','preview-only retirement and protected state preservation','no retry and no false unchanged after committed lost response','late-response authority recheck'],'trust_premises':['native provenance is authenticated by assumption','provider retirement and slot decrement atomicity are assumptions','missing/malformed proof unchanged modeled confirmed state does not prove real rollback'],'pending_owner':['repeat returns PreviewClosed without tombstone','capacity releases one slot','strict-end lexical amendments','eager observation precedence and exact native tuple'],'traceability':'fixtures-results.json maps each independent probe to input/expected/observed output; categories identify review obligation','acceptance':'Only scoped document consistency. No adoption, native acceptance, valid RED, module completion or release authorization.'}
result['preserved_originals_matched_excluding_board']=sum(r['category']=='hash' and r['name'].startswith('original ') for r in records)
result['board_at_candidate_seal']=read(C/'preserved-inputs.json')['docs/board.json']
result['board_drift']=result['board_at_candidate_seal']!=result['management_board_hash']
result['lexical_note']='U64 physical regex is lexical, semantic overflow rejected by capture/delivery model; original unused observation $defs retain dollar anchors. No claim of strict unused definitions or full Draft validation.'
(P/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'traceability.json').write_text(json.dumps([{'id':r['id'],'obligation':r['category'],'case':r['name'],'result':'PASS' if r['pass'] else 'FAIL','evidence':'fixtures-results.json#'+r['id']} for r in records],indent=2)+'\n',encoding='utf-8')
(P/'review-spec.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
from html import escape
body='<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>M03 Viewer Close Independent Review</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;line-height:1.6;background:#111827;color:#e5e7eb}pre{white-space:pre-wrap}a{color:#93c5fd}</style><h1>M03 Viewer Close Independent Review</h1><p>'+escape(result['status'])+'</p><p>Independent reviewer /root/m03_viewer_close_review; author /root/m03_viewer_close_packet. Parent remains Yellow; Owner adoption pending.</p><h2>Review scope and architecture</h2><p>Viewer → command → DispatchHost preview owner → detached mock retirement. DocumentSession remains content/history SSOT. Native/provider observations enter through proposed seams; real authenticity and atomicity are premises.</p><h2>Behavior and verification</h2><pre>'+escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre><h2>Owner decisions and limitations</h2><pre>'+escape(json.dumps(review,ensure_ascii=False,indent=2))+'</pre><p><a href="fixtures-results.json">Independent fixtures, expected outcomes and observed evidence</a> · <a href="parsed-patterns.json">Physical parsed patterns</a> · <a href="findings.json">Findings</a></p><script type="application/json" id="review-spec">'+json.dumps(review,ensure_ascii=False).replace('</','<\/')+'</script></html>'
(P/'index.html').write_text(body,encoding='utf-8')
seal={f.name:sha(f) for f in sorted(P.iterdir()) if f.is_file() and f.name!='artifact-hashes.json'}
(P/'artifact-hashes.json').write_text(json.dumps(seal,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result));sys.exit(bool(failures))
