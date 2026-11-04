import ast,copy,hashlib,json,pathlib,re,subprocess,random,html
P=pathlib.Path(__file__).resolve().parent; R=pathlib.Path.cwd(); C=P.parent/'candidate-install-correction'; O=P.parent/'candidate-install-integration'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
frozen={str(p):digest(p) for p in C.iterdir() if p.is_file()}
ns={'re':re,'copy':copy}
tree=ast.parse((C/'schema_subset.py').read_text());exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.ClassDef)],type_ignores=[]),'subset','exec'),ns)
def accept(s,x):
 try:ns['Draft202012Validator'](s).validate(x);return True
 except AssertionError:return False
roots={n:read(C/n) for n in ['request.schema.json','response.schema.json']}; old={n:read(O/n) for n in roots}
strict=read(P.parent/'save-proof-correction/request.schema.json')['$defs']['U64Decimal'];diff=read(C/'schema-pointer-diff.json');assert len(diff)==4
for n in roots:
 restored=copy.deepcopy(roots[n])
 for d in diff:
  if d['file']!=n:continue
  keys=d['pointer'][1:].split('/');node=restored
  for k in keys[:-1]:node=node[k]
  assert node[keys[-1]]==strict==d['after'];node[keys[-1]]=d['before']
 assert restored==old[n]
unchanged=[p.name for p in O.iterdir() if p.is_file() and p.name not in ['request.schema.json','response.schema.json','index.html','verification.json','artifact-hashes.json']]
assert all((C/n).read_bytes()==(O/n).read_bytes() for n in unchanged)
trace=read(C/'reachable-u64-trace.json');occ=[]
def walk(root,s,path,refs):
 if '$ref'in s:
  ref=s['$ref'];t=roots[root]
  for k in ref[2:].split('/'):t=t[k]
  return walk(root,t,path,refs+[ref])
 if s==strict:occ.append((root,tuple(path),tuple(refs)));return
 for k,z in s.get('properties',{}).items():walk(root,z,path+[k],refs)
 for z in s.get('oneOf',[]):walk(root,z,path,refs)
for n,s in roots.items():walk(n,s,[],[])
assert len(occ)==20
assert sorted(occ)==sorted((t['root'],tuple(t['path']),tuple(x['ref'] for x in t['refs'])) for t in trace)
cases=[]
def oracle(v):return type(v)is str and bool(v) and all('0'<=c<='9' for c in v) and (v=='0' or v[0]!='0') and int(v)<=2**64-1
# New neighboring boundary and unusual lexical inputs, rather than author vector replay.
values=[str(2**64-3),str(2**64+1),'9\u0085','9\u000b','9\u000c','９','9\ufeff',False,[],{}]
for i,t in enumerate(trace):
 assert accept(roots[t['root']],t['base'])
 for j,v in enumerate(values+['7\n']):
  x=copy.deepcopy(t['base']);d=x
  for k in t['path'][:-1]:d=d[k]
  d[t['path'][-1]]=v
  cases.append(dict(id=f'ROOT-{i}-{j}',root=t['root'],instance=x,scalar=v,expected=oracle(v),python=accept(roots[t['root']],x)))
node=json.loads(subprocess.check_output(['node',str(C/'ecmascript_root_checker.js')],input=json.dumps(dict(roots=roots,old=old,cases=cases)),text=True,encoding='utf8'))
for c,n in zip(cases,node):c['node']=n['accepted'];c['old_python']=accept(old[c['root']],c['instance']);c['status']='PASS' if c['python']==c['node']==c['expected'] else 'FAIL';del c['instance']
assert all(c['status']=='PASS' for c in cases)
lf=[c for c in cases if c['scalar']=='7\n'];assert len(lf)==20 and all(c['old_python'] and not c['python'] for c in lf)
rng=random.Random(31103);property_values=[str(rng.randrange(2**64-100,2**64+100)) for _ in range(60)]+[str(rng.randrange(2**64)) for _ in range(40)]
py=[accept(strict,v) for v in property_values]
js=json.loads(subprocess.check_output(['node','-e','const d=JSON.parse(process.argv[1]);console.log(JSON.stringify(d.v.map(x=>new RegExp(d.p).test(x))))',json.dumps(dict(p=strict['pattern'],v=property_values))],text=True))
assert py==js==[oracle(v) for v in property_values]
authority=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json');drift=[p for p,h in authority['source_hashes'].items() if digest(R/p)!=h];assert len(authority['source_hashes'])==796 and not drift
source_drift=[p for group in read(C/'correction-source-hashes.json').values() for p,h in group.items() if digest(R/p)!=h];assert not source_drift
frozen_drift=[n for n,h in read(C/'artifact-hashes.json').items() if digest(C/n)!=h];assert not frozen_drift
assert frozen=={str(p):digest(p) for p in C.iterdir() if p.is_file()}
save('new-probes.json',dict(fullroot=cases,property=[dict(value=v,python=a,node=b,expected=oracle(v)) for v,a,b in zip(property_values,py,js)]))
save('reviewed-hashes.json',frozen)
status='PASS_DOCUMENT_CORRECTION_SCOPE_ONLY_PENDING_OWNER'
v=dict(status=status,reviewer='/root/m03_install_correction_review',author='/root/m03_install_u64_correction',independent=True,head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),historical_authority_head=authority['head'],authority_entries=796,authority_drift=drift,definition_sites=4,reachable_occurrences=20,root_probes=len(cases),property_probes=len(py),failed=0,candidate_unchanged=True,non_u64_canonical_equivalent=True,byte_preserved_files=unchanged,not_run=['full Draft validator dependency absent','product/native/UI/IPC','valid product RED/GREEN','build/package/install','Owner adoption'])
save('verification.json',v)
v['source_input_drift']=source_drift;v['candidate_manifest_drift']=frozen_drift
save('verification.json',v)
review=dict(status=status,scope='CI-IR-F1 strict U64 document correction only; no architecture, policy or product acceptance',finding_closure='Original 13 LF root cases included in 20 reachable branch/reference occurrences; actual LF rejected in both engines. Four precise definition sites equal reviewed strict definition.',findings=[],method='Read-only AST class extraction; full root mutation in both parsed-pattern engines; separate seeded boundary property probes; independent traversal and canonical restoration; no candidate main execution.',preservation='Model/checker, semantic proof, trusted fixture, NoChange, consume, retention, replay and new-policy choices remain byte-identical to original. No field-name or custom validation hook introduced.',owner='CI-P4 / CI-P6 remain NEW_POLICY_REQUIRES_OWNER. Parent card remains yellow; original current-state untouched.',limits=v['not_run'],verification=v)
save('review.json',review)
(P/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>M03 correction independent review</title><style>body{font:16px system-ui;margin:40px;max-width:1100px}pre{white-space:pre-wrap}h1{color:#8b6500}</style><h1>'+status+'</h1><p>獨立文件限定審查：CI-IR-F1 closure。4定義、20完整root occurrence、220新root probes及100 seeded property probes全部通過。父卡黃燈；Owner未採納；非產品驗收。</p><pre>'+html.escape(json.dumps(review,ensure_ascii=False,indent=2))+'</pre><a href="new-probes.json">新獨立證據</a> · <a href="check_review.py">重現checker</a></html>',encoding='utf8')
save('artifact-hashes.json',{p.name:digest(p) for p in P.iterdir() if p.is_file() and p.name!='artifact-hashes.json'})
print(json.dumps(v))
