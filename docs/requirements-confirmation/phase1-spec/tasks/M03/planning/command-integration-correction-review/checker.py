"""Independent bounded CIHR-F1 document re-review; python -B checker.py. Never runs author generators."""
import ast, copy, hashlib, html, importlib.util, json, pathlib, subprocess
P=pathlib.Path(__file__).resolve().parent; B=P.parent; R=P.parents[6]; C=B/'command-integration-correction'; H=B/'command-integration-handoff'; V=B/'command-integration-review'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,x): (P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pointer(x,s):
 if s and not s.startswith('/'): raise ValueError(s)
 for k in s.split('/')[1:] if s else []:
  k=k.replace('~1','/').replace('~0','~'); x=x[int(k)] if isinstance(x,list) else x[k]
 return x
def constants(x,path=''):
 out=[]
 if isinstance(x,(dict,list)):
  for k,v in x.items() if isinstance(x,dict) else enumerate(x): out+=constants(v,path+'/'+str(k).replace('~','~0').replace('/','~1'))
 elif isinstance(x,(str,bool)) and (path.endswith('/const') or '/enum/' in path): out.append({'pointer':path,'value':x})
 return out
checks=[]
def ck(name,ok,detail=None): checks.append({'id':name,'pass':bool(ok),'detail':detail})
frozen={p.relative_to(R).as_posix():sha(p) for d in (H,V,C) for p in d.iterdir() if p.is_file()}
rows=read(C/'command-coverage.json'); prior=read(H/'command-coverage.json'); independent=read(V/'root-trace.json'); traces=[]
def derive(row):
 folder=B/row['effective_candidate']; matches=list(folder.glob('*response.schema.json'))
 assert len(matches)==(2 if row['effective_candidate']=='binding-open-get-correction' else 1)
 path=next(p for p in matches if p.name==('h2-'+row['command']+'-response.schema.json' if len(matches)==2 else 'response.schema.json'))
 return path
expected={x['command']:derive(x) for x in rows}
def gate(row,root_pointer=''):
 try:
  p=expected[row['command']]; d=read(p)
  return (B/row['response_root_source']).resolve()==p.resolve() and sha(p)==row['response_root_sha256'] and root_pointer=='' and pointer(d,root_pointer)==row['response_root_schema'] and constants(d)==row['response_root_constants'] and all(pointer(d,x['pointer'])==x['value'] for x in row['response_root_constants'])
 except (OSError,ValueError,KeyError,IndexError,TypeError): return False
for row in rows:
 p=expected[row['command']]; d=read(p); old=next(x for x in prior if x['command']==row['command']); reviewed=next(x for x in independent if x['command']==row['command'])
 ck(row['command']+':independent-root',gate(row) and p.relative_to(B).as_posix()==reviewed['response_schema'].replace('\\','/'))
 ck(row['command']+':only-provenance-changed',all(row[k]==v for k,v in old.items() if k!='response_root_source') and set(row)-set(old)=={'response_root_sha256','response_root_schema','request_root_source','request_root_sha256'})
 traces.append({'command':row['command'],'file':p.relative_to(B).as_posix(),'sha256':sha(p),'root_pointer':'','keys':list(d),'constants':constants(d)})
ck('13-commands-1499-constants',len(rows)==13 and sum(len(x['constants']) for x in traces)==1499)
mutations=[]
for row in rows:
 for kind in ('existing-wrong-file','missing-file','wrong-hash','nonexistent-constant-pointer','existing-wrong-constant-pointer','wrong-root-schema','nonroot-pointer','missing-constant','altered-constant'):
  x=copy.deepcopy(row); ptr=''
  if kind=='existing-wrong-file': x['response_root_source']='command-integration-correction/module-spec.json'; x['response_root_sha256']=sha(C/'module-spec.json')
  elif kind=='missing-file': x['response_root_source']='command-integration-correction-review/missing.schema.json'
  elif kind=='wrong-hash': x['response_root_sha256']='f'*64
  elif kind=='nonexistent-constant-pointer': x['response_root_constants'][0]['pointer']='/not/there'
  elif kind=='existing-wrong-constant-pointer': x['response_root_constants'][0]['pointer']='/$schema'
  elif kind=='wrong-root-schema': x['response_root_schema']=read(expected[row['command']])['$defs']
  elif kind=='nonroot-pointer': ptr='/$defs'
  elif kind=='missing-constant': x['response_root_constants'].pop()
  else: x['response_root_constants'][0]['value']='REVIEW_MUTATION'
  rejected=not gate(x,ptr); ck(row['command']+':'+kind,rejected); mutations.append({'command':row['command'],'mutation':kind,'root_pointer':ptr,'mutated_row':x,'rejected':rejected})
for n in ('original-62-trace.json','bdd-categories.json','composition-gaps.json'): ck('unchanged:'+n,read(C/n)==read(H/n))
ck('62-and-B1-B12',len(read(C/'original-62-trace.json'))==62 and [x['id'] for x in read(C/'bdd-categories.json')]==['B'+str(i) for i in range(1,13)])
inputs=read(H/'source-input-hashes.json'); drift=[k for k,v in inputs.items() if not (R/k).is_file() or sha(R/k)!=v]; ck('original440',len(inputs)==440 and not drift,drift)
authpath=R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json'; authority=read(authpath); drift796=[k for k,v in authority['source_hashes'].items() if sha(R/k)!=v]; ck('authority796',len(authority['source_hashes'])==796 and not drift796,drift796)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(); ck('HEAD-current-distinct-historical',head=='5b709343a890503ebbe24a802e43cda5647df124' and head!='31babe87a7ef1e40a0d4bedc523077e7a45d63ab')
for folder in (H,V,C):
 manifest=read(folder/'artifact-hashes.json'); ck(folder.name+':manifest',all(sha(folder/k)==v for k,v in manifest.items()))
source=(C/'checker.py').read_text(encoding='utf-8-sig'); tree=ast.parse(source); ck('generator-provenance-local-isolation',"response=schema_path(row,'response')" in source and "row['response_root_source']=response.relative_to(B).as_posix()" in source and not any(isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='response' for n in ast.walk(tree)))
# Re-execute document models through independently chosen callbacks; no author generator.
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
refresh=load('review_refresh',B/'viewer-refresh-integration/document_model.py'); close=load('review_close',B/'viewer-close-integration/document_model.py'); schema=load('review_schema',B/'viewer-refresh-integration/schema_eval.py')
w=read(H/'new-sequence-witness.json'); case=copy.deepcopy(w['fixture']); rq=read(B/'viewer-refresh-integration/request.schema.json'); rs=read(B/'viewer-refresh-integration/response.schema.json')
callbacks=[lambda x:schema.valid(rq,x),lambda x:schema.valid({'$defs':rs['$defs'],'$ref':'#/$defs/Preview'},x),lambda x:schema.valid({'$defs':rs['$defs'],'$ref':'#/$defs/Error'},x)]
a,s1,_=refresh.refresh(case,*callbacks); c2=copy.deepcopy(case); c2['before']=s1; b,s2,_=refresh.refresh(c2,*callbacks)
branch=close.close({'before':s1,'request':{'preview_session':s1['preview_session']},'provider':case['provider']},lambda x:True,lambda x:True)
strict=close.close({'before':s2,'request':{'preview_session':s2['preview_session']},'provider':case['provider']},lambda x:True,lambda x:True)
controlcase=next(x for x in read(B/'viewer-close-integration/fixtures.json') if x['provider'].get('outcome')=='Closed'); cq=read(B/'viewer-close-integration/request.schema.json'); cr=read(B/'viewer-close-integration/response.schema.json'); control=close.close(copy.deepcopy(controlcase),lambda x:schema.valid(cq,x),lambda x:schema.valid({'$defs':cr['$defs'],'$ref':'#/$defs/Error'},x))
claimed=read(C/'new-sequence-witness.json'); ck('branch-from-s1',branch==claimed['branch_close']); ck('strict-from-s2',strict==claimed['strict_sequence']['close'] and strict['state']==s2); ck('compatible-control',control==claimed['compatible_control'] and control['delivered']); ck('original-refresh-records',a==w['steps'][0]['response'] and b==w['steps'][1]['response'])
spec=read(C/'module-spec.json'); ck('Owner-unadopted-module-incomplete',spec['owner']=='PENDING' and spec['module_complete'] is False and read(C/'composition-gaps.json')[0]['status']=='PROPOSED_PENDING_OWNER')
ck('preserve-originals-after-review',all(sha(R/k)==v for k,v in frozen.items()))
put('root-trace.json',traces); put('negative-fixtures.json',mutations); put('sequence-results.json',{'branch_from':'after1','branch':branch,'strict_from':'after2','strict':strict,'compatible_control':control,'interpretation':'Document-model provider/state seam, not runtime architecture defect; no proposal union or Owner adoption.'}); put('preserved-originals.json',frozen)
board=read(R/'docs/board.json')
def findcard(x):
 if isinstance(x,dict):
  if x.get('id')=='PD-P1-M03-PREP-01': return x
  for v in x.values():
   found=findcard(v)
   if found: return found
 elif isinstance(x,list):
  for v in x:
   found=findcard(v)
   if found: return found
 return None
card=findcard(board); ck('board-yellow-readonly',card is not None and (card.get('zone')=='yellow' or card.get('new_zone')=='yellow' or card.get('light')=='Yellow'))
put('board-card-readonly.json',card)
management_diff=subprocess.check_output(['git','diff','--name-only','31babe87a7ef1e40a0d4bedc523077e7a45d63ab',head],cwd=R,text=True).splitlines(); ck('historical-to-current-management-only',management_diff==['docs/board.json'],management_diff)
put('management-classification.json',{'board_sha256':sha(R/'docs/board.json'),'classification':'Management-only drift; not included in 796 product authority. Board remains read-only.','current_state':read(B/'current-state.json'),'authority_file':authpath.relative_to(R).as_posix(),'authority_sha256':sha(authpath),'head':head,'historical_head':'31babe87a7ef1e40a0d4bedc523077e7a45d63ab'})
result={'reviewer':'/root/m03_handoff_correction_review','author':'/root/m03_handoff_trace_correction','status':'PASS_SCOPED_CORRECTION_ONLY_PENDING_OWNER' if all(x['pass'] for x in checks) else 'FAIL','checks':checks,'counts':{'checks':len(checks),'commands':13,'constants':1499,'new_negative_mutations':len(mutations),'original_inputs':len(inputs),'product_authority':len(authority['source_hashes']),'BDD':62,'categories':12,'document_model_calls':5},'module_complete':False,'Owner':'PENDING','CIH-G1':'PROPOSED_PENDING_OWNER','native':'NOT RUN','build':'NOT RUN','product':'NOT RUN','valid_RED':'NOT RUN','full_Draft':'NOT RUN','full_module_acceptance':'NOT RUN'}
put('results.json',result)
(P/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>M03 CIHR-F1 independent review</title><style>body{font:16px system-ui;background:#14222d;color:#eef4fa;max-width:1100px;margin:36px auto}pre{white-space:pre-wrap}a{color:#9cddff}</style><h1>M03 CIHR-F1 independent correction review</h1><h2>'+result['status']+'</h2><p>Yellow remains. Owner choices and CIH-G1 pending. No semantic union, module completion, Skeleton or implementation authorization.</p><p>13 independently derived actual response schema files, hashes and root pointers; 1499 string/boolean const/enum pointers. 117 new negative mutations across all 13 commands. Original 62 BDD, B1–B12, candidate/review traces preserved.</p><p>Generator correction uses a response-local path outside outcome iteration. Original defect remains preserved for audit.</p><p>Close branch consumes after1; strict sequence consumes retired-handle after2. Both document-model refusals reproduce. A compatible provider fixture closes successfully. This is a model/provider composition seam, not proof of a runtime architecture defect.</p><p>440 original inputs and 796 product-authority hashes verified. Current HEAD 5b709343a890503ebbe24a802e43cda5647df124 is distinct from historical 31babe. Board drift is management-only and excluded from product authority.</p><p>Native/build/product/valid RED/full Draft/full module acceptance: NOT RUN.</p><p><a href="results.json">Results</a> · <a href="root-trace.json">Actual roots</a> · <a href="negative-fixtures.json">New mutations</a> · <a href="sequence-results.json">Branch / strict / compatible control</a> · <a href="preserved-originals.json">Preserved originals</a></p><script type="application/json" id="module-spec">'+json.dumps(result,ensure_ascii=False).replace('</','<\\/')+'</script></html>',encoding='utf-8')
manifest={p.name:sha(p) for p in P.iterdir() if p.is_file() and p.name not in ('artifact-hashes.json','seal.json')}; put('artifact-hashes.json',manifest); put('seal.json',{'status':result['status'],'manifest_sha256':sha(P/'artifact-hashes.json'),'payload_artifacts':len(manifest),'total_files':len(manifest)+2,'counts':result['counts'],'module_complete':False,'Owner':'PENDING'})
print(json.dumps({'status':result['status'],'counts':result['counts'],'failed':[x for x in checks if not x['pass']]}))




