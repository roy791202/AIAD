"""Independent bounded document review. python -B checker.py; writes this directory only."""
import copy, hashlib, html, importlib.util, json, pathlib, re, subprocess, sys
sys.dont_write_bytecode=True
P=pathlib.Path(__file__).resolve().parent; A=P.parent/'viewer-refresh-integration'; ROOT=P.parents[6]
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,v):(P/n).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
# Independent implementation of the deliberately small schema vocabulary, not author's evaluator.
def accepts(schema,value,root=None):
 root=schema if root is None else root
 if '$ref' in schema:
  target=root
  for segment in schema['$ref'][2:].split('/'):target=target[segment]
  return accepts(target,value,root)
 if 'oneOf' in schema and sum(accepts(s,value,root) for s in schema['oneOf'])!=1:return False
 if 'const' in schema and (type(value)!=type(schema['const']) or value!=schema['const']):return False
 if 'enum' in schema and not any(type(value)==type(x) and value==x for x in schema['enum']):return False
 types={'string':str,'object':dict,'array':list,'boolean':bool,'null':type(None)}
 if 'type' in schema and type(value) not in [types[t] for t in ([schema['type']] if isinstance(schema['type'],str) else schema['type'])]:return False
 if type(value)==dict:
  props=schema.get('properties',{})
  if not set(schema.get('required',[]))<=set(value):return False
  if schema.get('additionalProperties') is False and set(value)-set(props):return False
  if any(not accepts(props[k],v,root) for k,v in value.items() if k in props):return False
 if type(value)==list and 'items' in schema and any(not accepts(schema['items'],v,root) for v in value):return False
 if type(value)==str:
  if not schema.get('minLength',0)<=len(value)<=schema.get('maxLength',10**9):return False
  if 'pattern' in schema and re.search(schema['pattern'],value) is None:return False
 return True
def main():
 spec=importlib.util.spec_from_file_location('reviewed_document_model',A/'document_model.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 req=read(A/'request.schema.json');res=read(A/'response.schema.json');proj={'$defs':res['$defs'],'$ref':'#/$defs/Preview'};err={'$defs':res['$defs'],'$ref':'#/$defs/Error'}
 base=read(A/'new-fixtures.json')[0]; probes=[]; checks=0
 def run(name,c,code=None):
  nonlocal checks
  before=copy.deepcopy(c['before']); result,after,calls=m.refresh(c,lambda x:accepts(req,x),lambda x:accepts(proj,x),lambda x:accepts(err,x))
  assert accepts(res,result),(name,result);checks+=1
  assert result['ok']==(code is None),(name,result)
  if code is not None:
   assert result['error']['code']==code,(name,result,code)
   expected=copy.deepcopy(before);expected.update(stale=True,can_act=False);assert after==expected,(name,'failure state')
   assert 'preview.atomic.replace' not in calls
  else:
   expected=copy.deepcopy(before);expected.update(retired=before['retired']+[before['preview_session']],preview_session=c['provider']['projection']['preview_session'],projection=c['provider']['projection'],revision=c['provider']['capture']['revision'],sequence='1',stale=False,can_act=True)
   assert after==expected,(name,'success state');assert calls[-1]=='preview.atomic.replace'
  checks+=3;probes.append({'id':name,'input':c,'expected_error':code,'actual':result,'after':after,'calls':calls,'status':'PASS'})
  return after
 for revision in ['0','9007199254740993','18446744073709551615']:
  for count in [1,4]:
   c=copy.deepcopy(base);c['before']['preview_count']=count
   for x in [c['request'],c['provider']['capture'],c['provider']['delivery'],c['provider']['projection']]:x['expected_revision' if x is c['request'] else 'source_revision' if x is c['provider']['projection'] else 'revision']=revision
   run('success-'+revision+'-capacity'+str(count),c)
 for phase in ['capture','delivery']:
  for key,code in [('consumer','UnauthorizedCaller'),('window','UnauthorizedCaller'),('document','MissingBinding'),('session','MissingBinding'),('generation','StaleOwner'),('closed','PreviewClosed'),('revision','StaleRevision')]:
   c=copy.deepcopy(base);c['provider'][phase][key]=True if key=='closed' else '4' if key in ('generation','revision') else 'other';run(phase+'-'+key,c,code)
 for bad in [None,True,0,1.0,'','00','-1','1\n','18446744073709551616']:
  c=copy.deepcopy(base);c['request']['expected_revision']=bad;run('invalid-u64-'+repr(bad),c,'InvalidRequest')
 for phase in ['capture','delivery']:
  for bad in [True,'18446744073709551616','1\n']:
   c=copy.deepcopy(base);c['provider'][phase]['revision']=bad;run('typed-'+phase+repr(bad),c,'DependencyNotReady')
 for name,path,value in [('provider-extra',['extra'],1),('closed-type',['capture','closed'],'false'),('capability',['projection','capabilities',0,'allowed_actions'],['eval']),('mock-kind',['projection','mock_state',0,'value','kind'],'Execute'),('node-extra',['projection','mock_state',0,'extra'],1),('reuse-current',['projection','preview_session'],base['before']['preview_session']),('seq',['projection','expected_sequence'],'2')]:
  c=copy.deepcopy(base);target=c['provider']
  for key in path[:-1]:target=target[key]
  target[path[-1]]=value;run(name,c,'DependencyNotReady')
 for code in ['UnsupportedDocument','CodecRejected','ResourceLimit','AmbiguousStableId','ParentMissing','ParentCycle','DependencyNotReady']:
  matches=[x for x in read(A/'new-fixtures.json') if x['expected'].get('error',{}).get('code')==code and isinstance(x['provider']['outcome'],dict)]
  assert matches,code
  c=copy.deepcopy(base);c['provider']['outcome']=matches[0]['provider']['outcome'];run('domain-'+code,c,code)
 c=copy.deepcopy(base);c['request']={};c['provider']['trusted_local']=False;run('combined-auth-before-request',c,'UnauthorizedCaller')
 c['provider']['delivery']['revision']=True;run('combined-malformed-before-auth',c,'DependencyNotReady')
 c=copy.deepcopy(base);c['request']['z']=1;c['request']['expected_revision']=True;run('combined-unknown-before-type',c,'InvalidRequest')
 c=copy.deepcopy(base);state=run('replay-first',c);c['before']=state;run('replay-old-handle',c,'PreviewClosed')
 # Complete root rejection independent from lifecycle checks.
 roots=0
 for schema,value in [(req,base['request']),(res,probes[0]['actual']),(res,probes[-1]['actual'])]:
  for key in [None,*value]:
   bad=copy.deepcopy(value)
   if key is None:bad['unapproved']=1
   else:del bad[key]
   assert not accepts(schema,bad);roots+=1
 authority=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')['source_hashes'];assert len(authority)==796
 assert all(sha(ROOT/p)==h for p,h in authority.items())
 preserved=read(A/'preserved-inputs.json');drift=[p for p,h in preserved.items() if sha(ROOT/p)!=h];assert set(drift)<= {'docs/board.json'},drift
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();assert head=='5b709343a890503ebbe24a802e43cda5647df124'
 manifest=read(A/'artifact-hashes.json');assert all(sha(A/p)==h for p,h in manifest.items())
 rows=read(A/'before-after.json');assert len(rows)==10 and all(x['status']=='PROPOSED_PENDING_OWNER' for x in rows)
 review={'status':'PASS_SCOPED_DOCUMENT_REVIEW_PENDING_OWNER','reviewer':'/root/m03_viewer_refresh_review','author':'/root/m03_viewer_refresh_packet','independent_probes':len(probes),'behavior_checks':checks,'root_negative_probes':roots,'product_authority_matched':796,'preserved_inputs':len(preserved),'preserved_matches':len(preserved)-len(drift),'management_drift':drift,'author_artifact_hashes_matched':len(manifest),'head':head,'historical_head':'31babe87a7ef1e40a0d4bedc523077e7a45d63ab','before_after_rows_pending_owner':10,'findings':[], 'premises':['Trusted native/provider authenticity and global UUID uniqueness are unproved premises.','Atomic slot replacement/concurrency is a document-model assumption, not native proof.','Capacity1/4 witnesses prove exchange only under supplied valid state; native slot accounting NOT RUN.','Replayed false means no response cache/replay; old handle rejected after retirement; fresh subsequent request requires trusted new UUID.'],'FileCommit':'N/A','ACK':'N/A','product_tests':'NOT RUN','native':'NOT RUN','build':'NOT RUN','valid_RED':'NOT RUN','Owner_adoption':'PENDING','module_acceptance':'NOT RUN'}
 put('fixtures.json',probes);put('before-after-reviewed.json',rows);put('results.json',review);put('traceability.json',{'coverage':{k:[x['id'] for x in probes if k in x['id']] for k in ['success','capture','delivery','invalid','typed','domain','combined','replay']},'source':str(A.relative_to(ROOT)),'scope':'document model only'})
 embedded=json.dumps(review,ensure_ascii=False).replace('</','<\\/')
 (P/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M03 refresh independent review</title><h1>M03 refresh: scoped PASS, Owner pending</h1><p>Independent document review. No product or native execution. All 10 exact policy changes remain proposed. Parent Yellow unchanged.</p><p>Review covers complete roots, exact delivery identities, checked u64, failure preservation, replacement, capacity, typed admission, domain errors, precedence and old-handle replay.</p><pre>'+html.escape(json.dumps(review,indent=2))+'</pre><script type="application/json" id="module-review">'+embedded+'</script><p>Reproduce: python -B docs/requirements-confirmation/phase1-spec/tasks/M03/planning/viewer-refresh-review/checker.py</p>',encoding='utf8')
 put('artifact-hashes.json',{p.name:sha(p) for p in sorted(P.iterdir()) if p.is_file() and p.name not in ['artifact-hashes.json','seal.json']})
 put('seal.json',{'status':review['status'],'independent_probes':len(probes),'checks':checks+roots,'artifact_count':len(read(P/'artifact-hashes.json')),'manifest_sha256':sha(P/'artifact-hashes.json')});print(json.dumps(read(P/'seal.json')))
if __name__=='__main__':main()
