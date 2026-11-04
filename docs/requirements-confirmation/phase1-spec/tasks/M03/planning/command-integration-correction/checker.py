"""CIHR-F1 author correction. python -B checker.py; writes only this new directory."""
import copy, hashlib, html, importlib.util, json, pathlib, subprocess
P=pathlib.Path(__file__).resolve().parent; B=P.parent; H=B/'command-integration-handoff'; ROOT=P.parents[6]
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,d): (P/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def pointer(d,p):
 if p and not p.startswith('/'): raise ValueError('JSON pointer')
 for k in p[1:].split('/') if p else []:
  k=k.replace('~1','/').replace('~0','~'); d=d[int(k)] if isinstance(d,list) else d[k]
 return d
def leaves(d,p=''):
 if isinstance(d,(dict,list)):
  for k,v in (d.items() if isinstance(d,dict) else enumerate(d)): yield from leaves(v,p+'/'+str(k).replace('~','~0').replace('/','~1'))
 else: yield p,d
checks=[]
def check(n,v):
 checks.append({'id':n,'pass':bool(v)}); assert v,n
def schema_path(row,kind):
 folder=B/row['effective_candidate']; standard=folder/(kind+'.schema.json'); named=folder/('h2-'+row['command']+'-'+kind+'.schema.json')
 paths=[p for p in (standard,named) if p.is_file()]; assert len(paths)==1
 return paths[0]
def root_gate(row):
 try:
  actual=schema_path(row,'response'); declared=(B/row['response_root_source']).resolve()
  if declared!=actual.resolve() or sha(declared)!=row['response_root_sha256']: return False
  d=read(declared)
  if d!=row['response_root_schema']: return False
  constants=[{'pointer':p,'value':v} for p,v in leaves(d) if (p.endswith('/const') or '/enum/' in p) and isinstance(v,(str,bool))]
  return constants==row['response_root_constants'] and all(pointer(d,c['pointer'])==c['value'] for c in row['response_root_constants']) and isinstance(d.get('oneOf'),list)
 except (OSError,KeyError,IndexError,TypeError,ValueError): return False
def main():
 inputs=read(H/'source-input-hashes.json'); frozen={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for folder in (H,B/'command-integration-review') for p in folder.iterdir() if p.is_file()}
 authority_path=ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json'; authority=read(authority_path)['source_hashes']
 check('original440',len(inputs)==440 and all(sha(ROOT/k)==v for k,v in inputs.items()))
 check('authority796',len(authority)==796 and all(sha(ROOT/k)==v for k,v in authority.items()))
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(); check('currentHEAD',head=='5b709343a890503ebbe24a802e43cda5647df124')
 rows=read(H/'command-coverage.json'); original=copy.deepcopy(rows); changes=[]; trace=[]
 for row in rows:
  response=schema_path(row,'response'); request=schema_path(row,'request'); d=read(response)
  changes.append({'command':row['command'],'before':row['response_root_source'],'after':response.relative_to(B).as_posix(),'cause':'Generator variable f reused by outcome loop; use separate response_schema_path.'})
  row['response_root_source']=response.relative_to(B).as_posix(); row['response_root_sha256']=sha(response); row['response_root_schema']=d
  row['request_root_source']=request.relative_to(B).as_posix(); row['request_root_sha256']=sha(request)
  check(row['command']+':root-file-hash-shape-pointers',root_gate(row))
  trace.append({'command':row['command'],'request':{'file':row['request_root_source'],'sha256':sha(request),'pointer':''},'response':{'file':row['response_root_source'],'sha256':sha(response),'pointer':'','schema':d},'constant_count':len(row['response_root_constants']),'dynamic_callback_claim':'No command-wide function-root claim. Only explicitly exercised refresh/close callbacks recorded in callback-roots.json.'})
  prior=next(x for x in original if x['command']==row['command']); check(row['command']+':preserve-semantic-fields',all(row[k]==v for k,v in prior.items() if k!='response_root_source'))
 check('commands13',len(rows)==13)
 negative=[]
 for kind in ['wrong-existing-file','nonexistent-file','missing-pointer','wrong-root-shape','wrong-hash']:
  x=copy.deepcopy(rows[0])
  if kind=='wrong-existing-file': x['response_root_source']=rows[2]['response_root_source']; x['response_root_sha256']=rows[2]['response_root_sha256']
  elif kind=='nonexistent-file': x['response_root_source']='command-integration-correction/nonexistent.schema.json'
  elif kind=='missing-pointer': x['response_root_constants'][0]['pointer']='/missing/pointer'
  elif kind=='wrong-root-shape': x['response_root_schema']={'type':'object'}
  else: x['response_root_sha256']='0'*64
  rejected=not root_gate(x); check('negative:'+kind,rejected); negative.append({'id':kind,'rejected':rejected,'scope':'In-memory author document checker mutation; not product valid RED'})
 for name in ['original-62-trace.json','bdd-categories.json','composition-gaps.json']:
  put(name,read(H/name)); check('preserve:'+name,read(P/name)==read(H/name))
 refresh=load('correction_refresh',B/'viewer-refresh-integration/document_model.py'); sc=load('correction_schema',B/'viewer-refresh-integration/schema_eval.py'); close=load('correction_close',B/'viewer-close-integration/document_model.py')
 witness=read(H/'new-sequence-witness.json'); case=copy.deepcopy(witness['fixture']); rq=read(B/'viewer-refresh-integration/request.schema.json'); rs=read(B/'viewer-refresh-integration/response.schema.json')
 validators=[lambda x:sc.valid(rq,x),lambda x:sc.valid({'$defs':rs['$defs'],'$ref':'#/$defs/Preview'},x),lambda x:sc.valid({'$defs':rs['$defs'],'$ref':'#/$defs/Error'},x)]
 out,after,calls=refresh.refresh(case,*validators); old=copy.deepcopy(case); old['before']=after; out2,after2,calls2=refresh.refresh(old,*validators)
 branch=close.close({'before':after,'request':{'preview_session':after['preview_session']},'provider':case['provider']},lambda x:True,lambda x:True)
 sequential=close.close({'before':after2,'request':{'preview_session':after2['preview_session']},'provider':case['provider']},lambda x:True,lambda x:True)
 check('refresh-original',out==witness['steps'][0]['response'] and after==witness['steps'][0]['after'])
 check('retired-original',out2==witness['steps'][1]['response'] and after2==witness['steps'][1]['after'])
 check('branch-original',branch==witness['steps'][2]['result']); check('strict-sequential',sequential['response']==branch['response'] and sequential['state']==after2)
 compatible=next(c for c in read(B/'viewer-close-integration/fixtures.json') if c['provider'].get('outcome')=='Closed'); cq=read(B/'viewer-close-integration/request.schema.json'); cr=read(B/'viewer-close-integration/response.schema.json')
 control=close.close(copy.deepcopy(compatible),lambda x:sc.valid(cq,x),lambda x:sc.valid({'$defs':cr['$defs'],'$ref':'#/$defs/Error'},x)); check('compatible-control',control['response']['ok'] and control['delivered'])
 put('new-sequence-witness.json',{'original_witness_preserved':witness,'branch_label':'Original third call branches from successful refresh state after1; it does not consume retired-handle after2.','strict_sequence':{'refresh':out,'retired_handle':out2,'close':sequential},'branch_close':branch,'compatible_control':control,'conclusion':'Document provider/state record composition seam only, not runtime architecture defect. All identity/UUID/atomicity premises are trusted fixtures; Owner choices remain pending.'})
 callbacks=[]
 for folder,func,defs in [('viewer-refresh-integration','refresh',['Preview','Error']),('viewer-close-integration','close',['Error'])]:
  for kind,pointers in [('request',['']),('response',['']+['/$defs/'+x for x in defs])]:
   f=B/folder/(kind+'.schema.json')
   for ptr in pointers: check(folder+':callback:'+kind+ptr,isinstance(pointer(read(f),ptr),dict)); callbacks.append({'function':folder+'/document_model.py::'+func,'file':f.relative_to(B).as_posix(),'sha256':sha(f),'pointer':ptr,'usage':'Whole response root trace only' if kind=='response' and ptr=='' else 'Actual validator callback root; definition callbacks wrap root $defs plus local $ref'})
 callbacks.append({'function':'viewer-close-integration/document_model.py::close','usage':'Mismatch branch and strict calls use permissive request/error callbacks deliberately; rejection occurs at provider observation before request validation. Compatible control uses exact schema callbacks.'})
 put('callback-roots.json',callbacks); put('command-coverage.json',rows); put('root-trace.json',trace); put('before-after.json',changes); put('negative-probes.json',negative)
 check('original-artifacts-frozen',all(sha(ROOT/k)==v for k,v in frozen.items())); check('post440',all(sha(ROOT/k)==v for k,v in inputs.items())); check('post796',all(sha(ROOT/k)==v for k,v in authority.items()))
 put('preserved-hashes.json',{'original440':inputs,'handoff_and_review':frozen,'authority':{'file':str(authority_path.relative_to(ROOT)).replace('\\','/'),'sha256':sha(authority_path),'matched':796},'board':'Management-only docs/board.json drift excluded from product authority; no board mutation by this package.','head':head,'historical_head':'31babe87a7ef1e40a0d4bedc523077e7a45d63ab'})
 spec=read(H/'module-spec.json'); spec['identity']={'module':'M03','task':'PD-P1-M03-PREP-01','slice':'CIHR-F1 bounded trace correction','author':'/root/m03_handoff_trace_correction','status':'PROPOSED_PENDING_OWNER'}; spec['scope']='NEW command-integration-correction files only; immutable original evidence; document trace correction'; spec['next_ready_action']='New independent document reviewer verifies 13 paths/hashes/root shapes/all constant pointers, 5 negative probes, branch/strict/control labels, preserved 440 inputs and 796 authority hashes, then Owner chooses exact pending seams. No Skeleton or product implementation authorization.'
 spec['verification']={k:'NOT RUN' for k in ['independent_review','native','build','product','valid_RED','full_Draft','full_module_acceptance']}; spec['owner']='PENDING'; spec['module_complete']=False
 put('module-spec.json',spec); put('results.json',{'status':'AUTHOR_DOCUMENT_CHECKS_ONLY','checks':checks,'counts':{'commands':13,'constants':sum(len(x['response_root_constants']) for x in rows),'original_BDD':62,'categories':12,'negative_probes':5,'composition_calls':5,'product_hashes':796,'original_inputs':440},'independent_review':'NOT RUN'})
 table=''.join('<tr><td>'+html.escape(x['command'])+'</td><td>'+html.escape(x['response_root_source'])+'</td><td>'+str(len(x['response_root_constants']))+'</td></tr>' for x in rows)
 (P/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>M03 CIHR-F1 correction</title><style>body{font:16px system-ui;max-width:1200px;margin:30px auto;background:#15212b;color:#edf2f7}td,th{padding:9px;border-bottom:1px solid #678}a{color:#9cd8ff}pre{white-space:pre-wrap}</style><h1>M03 · CIHR-F1 author correction</h1><p>Yellow / REPLAN_REQUIRED · Owner pending · no module PASS</p><h2>Intent and boundaries</h2><p>Repair all 13 provenance paths without changing constants, candidates, reviews, 62 BDD records, B1–B12 or pending decisions. Separate response schema path prevents outcome-loop variable reuse.</p><pre>UI → Tauri → M03 facade → M04 owner / C1 / M05 ports\nM04 owns authoritative state. Wire output grants no native authority.\nPublication revalidates capture/delivery; FileCommit ≠ ACK ≠ retention.</pre><h2>Corrected command matrix</h2><table><tr><th>Command</th><th>Exact response schema</th><th>Constants</th></tr>'+table+'<h2>Behavior and evidence</h2><p>Original close is a branch from after1. Strict close consumes after2 and reproduces refusal; compatible close succeeds. This demonstrates a document seam only, not a runtime architecture defect.</p><p>59 thematic mappings remain partial; B058–B060 unresolved. All B1–B12 Applicable/Deferred. Native/build/product/valid RED/full Draft/independent acceptance NOT RUN.</p><p>'+''.join('<a href="'+n+'">'+n+'</a> · ' for n in ['command-coverage.json','root-trace.json','callback-roots.json','original-62-trace.json','bdd-categories.json','composition-gaps.json','new-sequence-witness.json','before-after.json','negative-probes.json','results.json','preserved-hashes.json'])+'</p><h2>Next review</h2><p>'+html.escape(spec['next_ready_action'])+'</p><script type="application/json" id="module-spec">'+json.dumps(spec,ensure_ascii=False).replace('</','<\\/')+'</script></html>',encoding='utf-8')
 manifest={f.name:sha(f) for f in P.iterdir() if f.is_file() and f.name not in ['artifact-hashes.json','seal.json']}; put('artifact-hashes.json',manifest)
 put('seal.json',{'status':'SEALED_AUTHOR_CORRECTION_PENDING_NEW_INDEPENDENT_REVIEW','manifest_sha256':sha(P/'artifact-hashes.json'),'payload_artifacts':len(manifest),'total_files_including_manifest_and_seal':len(manifest)+2,'checks':len(checks),'counts':read(P/'results.json')['counts'],'next_ready_action':spec['next_ready_action'],'module_complete':False})
 print(json.dumps(read(P/'seal.json')))
if __name__=='__main__': main()
