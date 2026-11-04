import copy,hashlib,importlib.util,json,pathlib,re,subprocess,sys
P=pathlib.Path(__file__).resolve().parent;R=pathlib.Path.cwd();C=P.parent/'candidate-install-integration'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('candidate_subset',P/'schema_subset.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
roots={n:read(P/n) for n in ['request.schema.json','response.schema.json']};old={n:read(C/n) for n in roots}
f=read(P/'fixtures.json');nc=copy.deepcopy(f['response']);nc['value']={'outcome':'NoChange','projection':dict(f['response']['value']['projection'],revision='7'),'replayed':False,'revision':'7','history_depth':'2'}
deferred=copy.deepcopy(f['response']);deferred['value'].update(outcome='AppliedRetentionDeferred',stage='LiveRoots',reason='IoFailure')
bases={'request.schema.json':[f['request']],'response.schema.json':[f['response'],nc,deferred]+[{'ok':False,'error':{'code':code,'details':dict.fromkeys(keys,'7')},'replayed':False} for code,keys in [('StaleRevision',['expected','observed']),('SequenceConflict',['expected','received'])]]}
def accepts(s,x):
 try:m.Draft202012Validator(s).validate(x);return True
 except (AssertionError,ValueError,TypeError,KeyError):return False
def get(x,path):
 for k in path:x=x[k]
 return x
def mutate(base,path,value):
 x=copy.deepcopy(base);d=x
 for k in path[:-1]:d=d[k]
 d[path[-1]]=value;return x
trace=[]
def walk(root,s,pointer,path,refs,constraints):
 if '$ref'in s:
  ref=s['$ref'];target=roots[root]
  for k in ref[2:].split('/'):target=target[k]
  walk(root,target,ref[1:],path,refs+[{'at':pointer,'ref':ref}],constraints);return
 if s.get('pattern','').startswith('^(?:0|[1-9][0-9]'):
  valid=[]
  for b in bases[root]:
   try:get(b,path)
   except (KeyError,TypeError):continue
   if accepts(roots[root],b) and all(accepts(dict(z,**{'$defs':roots[root].get('$defs',{})}),get(b,at)) for z,at in constraints):valid.append(b)
  assert valid,(root,path)
  trace.append({'root':root,'path':path,'schema_pointer':pointer,'refs':refs,'base':valid[0]});return
 for k,v in s.get('properties',{}).items():walk(root,v,pointer+'/properties/'+k,path+[k],refs,constraints)
 for i,v in enumerate(s.get('oneOf',[])):walk(root,v,pointer+'/oneOf/'+str(i),path,refs,constraints+[(v,path)])
for root,s in roots.items():walk(root,s,'',[],[],[])
# Independent expected oracle uses lexical codepoints and integer boundary, never changes schema admission.
values=[('zero','0'),('one','1'),('max-1',str(2**64-2)),('max',str(2**64-1)),('max+1',str(2**64)),('LF','1\n'),('CR','1\r'),('CRLF','1\r\n'),('U2028','1\u2028'),('U2029','1\u2029'),('NUL','1\0'),('multiline','1\n2'),('prefix','x1'),('suffix','1x'),('leading-LF','\n1'),('empty',''),('leading-zero','01'),('plus','+1'),('space','1 '),('unicode-digit','١')]
def oracle(v):return bool(v) and all('0'<=c<='9' for c in v) and (v=='0' or v[0]!='0') and int(v)<=2**64-1
cases=[]
for i,t in enumerate(trace):
 for label,v in values:
  x=mutate(t['base'],t['path'],v);expected=oracle(v)
  cases.append({'id':f'CI-F1-{i:02}-{label}','root':t['root'],'path':t['path'],'occurrence':i,'label':label,'scalar':v,'codepoints':list(map(ord,v)),'expected':expected,'python':accepts(roots[t['root']],x),'python_before':accepts(old[t['root']],x),'instance':x})
js=r'''const fs=require('fs');const d=JSON.parse(fs.readFileSync(0,'utf8'));
function valid(root,s,x){if(s.$ref){let t=root;for(const k of s.$ref.slice(2).split('/'))t=t[k];return valid(root,t,x)}
if(s.oneOf)return s.oneOf.filter(z=>valid(root,z,x)).length===1;
if('const'in s&&JSON.stringify(x)!==JSON.stringify(s.const))return false;
if(s.enum&&!s.enum.includes(x))return false;
const kind=x===null?'null':Array.isArray(x)?'array':typeof x;
if(s.type&&!(Array.isArray(s.type)?s.type:[s.type]).includes(kind))return false;
if(typeof x==='string'){if(x.length<(s.minLength||0)||x.length>(s.maxLength||1e9))return false;if(s.pattern&&!new RegExp(s.pattern).test(x))return false}
if(kind==='object'){if((s.required||[]).some(k=>!(k in x)))return false;if(s.additionalProperties===false&&Object.keys(x).some(k=>!(k in(s.properties||{}))))return false;if(Object.entries(s.properties||{}).some(([k,z])=>k in x&&!valid(root,z,x[k])))return false}
if(kind==='array'&&s.items&&x.some(z=>!valid(root,s.items,z)))return false;return true}
process.stdout.write(JSON.stringify(d.cases.map(c=>({id:c.id,accepted:valid(d.roots[c.root],d.roots[c.root],c.instance),before:valid(d.old[c.root],d.old[c.root],c.instance)}))));'''
(P/'ecmascript_root_checker.js').write_text(js,encoding='utf8')
node=json.loads(subprocess.check_output(['node',str(P/'ecmascript_root_checker.js')],input=json.dumps({'roots':roots,'old':old,'cases':cases}),text=True,encoding='utf8'))
for c,n in zip(cases,node):c['ecmascript']=n['accepted'];c['ecmascript_before']=n['before'];c['status']='PASS' if c['python']==c['ecmascript']==c['expected'] else 'FAIL';del c['instance']
assert all(c['status']=='PASS' for c in cases)
lf=[c for c in cases if c['label']=='LF'];assert all(c['python_before'] and not c['python'] and not c['ecmascript'] for c in lf)
authority=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json');drift=[p for p,h in authority['source_hashes'].items() if digest(R/p)!=h]
source=read(P/'correction-source-hashes.json');source_drift=[p for group in source.values() for p,h in group.items() if digest(R/p)!=h]
save('reachable-u64-trace.json',trace);save('new-probes.json',cases)
save('verification.json',{'status':'AUTHOR_SELF_CHECK_PASS_DOCUMENT_CANDIDATE_ONLY','author':'/root/m03_install_u64_correction','independent_acceptance':'NOT RUN; author cannot independently accept own packet','new_fullroot_cases':len(cases),'engine_executions':len(cases)*2,'passed':len(cases),'failed':0,'reachable_occurrences':len(trace),'original_LF_failures_closed':len(lf),'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(),'historical_authority_head':authority['head'],'authority_entries':len(authority['source_hashes']),'authority_drift':drift,'source_drift':source_drift,'tail_codepoints':list(map(ord,roots['request.schema.json']['$defs']['U64Decimal']['pattern'][-10:])),'preserved_historical_evidence':'104 author cases and 367 reviewer probes preserved by source hashes/references; not rerun or counted as new progress','not_run':['full Draft validator','product tests','native/UI/IPC','valid RED/GREEN','build/package/install','Owner adoption','independent acceptance']})
assert not drift and not source_drift
print(json.dumps({'new_fullroot_cases':len(cases),'occurrences':len(trace),'LF_closed':len(lf),'authority_entries':len(authority['source_hashes']),'failures':0}))


