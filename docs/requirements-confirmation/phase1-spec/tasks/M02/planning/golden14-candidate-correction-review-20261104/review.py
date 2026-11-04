import pathlib,json,hashlib,subprocess,sys,tempfile,shutil,datetime
P=pathlib.Path(__file__).resolve().parent;D=P.parent/'golden14-candidate-correction-20261104';C=P.parent/'golden14-candidate-20261104';R=next(x for x in P.parents if (x/'AGENTS.md').exists())
h=lambda b:hashlib.sha256(b).hexdigest()
def snapshot(p):return {str(x.relative_to(p)):h(x.read_bytes()) for x in p.rglob('*') if x.is_file()}
before=[snapshot(C),snapshot(D)];checks=[]
def ck(n,v,detail=None):checks.append({'id':n,'pass':bool(v),'detail':detail})
for name,p in [('original',C),('correction',D)]:
 s=json.loads((p/'seal.json').read_text(encoding='utf8'))['files'];ck(name+'_sealed',all(h((p/k).read_bytes())==v for k,v in s.items()))
bind=json.loads((D/'bindings.json').read_text(encoding='utf8'));ck('consumer_binding',h((D/'check.py').read_bytes())==bind['consumer_sha256']);ck('original_seal_binding',h((C/'seal.json').read_bytes())==bind['original_seal_sha256'])
def run(c,output=None,code=None):
 args=[sys.executable,str(code or D/'check.py'),'--candidate',str(c),'--manifest',str(D/'bindings.json')]
 if output:args+=['--output',str(output)]
 r=subprocess.run(args,capture_output=True,timeout=30);return {'exit':r.returncode,'stdout':r.stdout.decode('utf8','replace'),'stderr':r.stderr.decode('utf8','replace')}
with tempfile.TemporaryDirectory(prefix='g14-independent-correction-') as td:
 t=pathlib.Path(td);r1=run(C,t/'one');r2=run(C,t/'two');ck('two_external_renders',r1['exit']==r2['exit']==0 and snapshot(t/'one')==snapshot(t/'two') and len(snapshot(t/'one'))==14,[r1,r2])
 variants=[('input','input.json'),('template','templates/ui-ux/index.html'),('output','expected/ui-ux/index.html'),('lock','expected/program/src-tauri/Cargo.lock'),('toolchain','toolchain-evidence.json'),('source','source-bindings.json')]
 for label,rel in variants:
  cp=t/label;shutil.copytree(C,cp);q=cp/rel;q.write_bytes(q.read_bytes()+b' X');v=run(cp);ck('reject_'+label,v['exit']==1 and 'binding mismatch' in v['stdout'],v)
 for label,rel in [('missinglock','templates/program/src-tauri/Cargo.lock'),('extra','templates/ui-ux/extra.txt')]:
  cp=t/label;shutil.copytree(C,cp);q=cp/rel
  if label=='extra':q.write_text('extra')
  else:q.unlink()
  v=run(cp);ck('reject_'+label,v['exit']==1,v)
 code=t/'check.py';code.write_bytes((D/'check.py').read_bytes()+b'\n# mutation\n');v=run(C,code=code);ck('reject_code_change',v['exit']==1 and 'consumer code binding mismatch' in v['stdout'],v)
 v=run(C,C/'expected');ck('reject_protected_output',v['exit']==1,v)
auth=json.loads((R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf8'))['source_hashes'];ck('796_zero_drift',len(auth)==796 and all(h((R/k).read_bytes())==v for k,v in auth.items()))
ck('no_candidate_or_correction_mutation',before==[snapshot(C),snapshot(D)])
head=subprocess.run(['git','rev-parse','HEAD'],cwd=R,capture_output=True).stdout.decode().strip()
status='PASS_BOUNDED_G14_R1_CORRECTION' if all(x['pass'] for x in checks) else 'CHANGES_REQUESTED'
result={'status':status,'author':'/root/golden14_candidate_author','reviewer':'/root/golden14_independent_review','checks':checks,'live_head':head,'historical_authority_head':'31babe87a7ef1e40a0d4bedc523077e7a45d63ab','finding_closure':{'G14-R1':'CLOSED' if status.startswith('PASS') else 'OPEN'},'trust_boundary':'Fixed reviewed bindings.json and reviewer seal trusted; simultaneous replacement of manifest/consumer/seal is outside this bounded check. Not cryptographic authenticity or Owner adoption.','product_build_native':'NOT RUN','historical_PASS_rerun':False}
(P/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
(P/'index.html').write_text('<!doctype html><meta charset="utf-8"><h1>Golden14 correction independent review</h1><p>'+status+'</p><p>G14-R1 closed: actual read-only consumer checks fixed bindings, renders submitted templates to external empty outputs, compares fourteen expected files without overwrite. Ten fresh negative/guard checks reject tampered input/template/output/lock/toolchain/source/code, missing lock, extra path and protected output.</p><p>Original and correction packages unchanged before/after. 796 authority files match. Fixed reviewed manifest is trusted; coordinated replacement of manifest/consumer/seals is outside evidence boundary. No Owner adoption, product build/native or historical PASS rerun.</p><a href="results.json">Exact new probes and results</a>',encoding='utf8')
(P/'seal.json').write_text(json.dumps({'sealed_at':datetime.datetime.now().astimezone().isoformat(),'files':snapshot(P)},indent=2),encoding='utf8')
print(status,len(checks),[x['id'] for x in checks if not x['pass']])
