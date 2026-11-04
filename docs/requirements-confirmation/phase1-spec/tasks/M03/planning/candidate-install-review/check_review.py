import ast,copy,hashlib,json,pathlib,re,subprocess,sys
R=pathlib.Path.cwd(); P=pathlib.Path(__file__).parent; C=P.parent/'candidate-install-integration'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def extract(p,names,ns):
 tree=ast.parse(p.read_text(encoding='utf8')); nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names];exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p),'exec'),ns)
ns={'re':re,'copy':copy};extract(C/'schema_subset.py',['Draft202012Validator'],ns)
ns.update({'json':json,'pathlib':pathlib,'hashlib':hashlib,'uuid':__import__('uuid'),'P':C});extract(C/'check_documents.py',['read','validate','model','proofcheck'],ns)
f=read(C/'fixtures.json'); results=[]
def record(id,expected,actual,details=None):results.append(dict(id=id,expected=expected,actual=actual,status='PASS' if expected==actual else 'FAIL',details=details))
def accepts(schema,value):
 try:ns['Draft202012Validator'](schema).validate(value);return True
 except (AssertionError,ValueError,TypeError,KeyError):return False
roots={n:read(C/n) for n in ['request.schema.json','response.schema.json']}
# Every reachable U64 occurrence is tested in an otherwise valid root; no field-name exception.
req=f['request'];res=f['response']
paths=[('request.schema.json',req,[k]) for k in ['expected_generation','expected_revision']]
paths += [('response.schema.json',res,['value',k]) for k in ['before_revision','after_revision','history_depth']]
paths += [('response.schema.json',res,['value','projection',k]) for k in ['owner_generation','revision']]
nc=copy.deepcopy(res);nc['value']={'outcome':'NoChange','projection':dict(res['value']['projection'],revision='7'),'replayed':False,'revision':'7','history_depth':'2'}
paths += [('response.schema.json',nc,['value',k]) for k in ['revision','history_depth']]
for code,keys in [('StaleRevision',['expected','observed']),('SequenceConflict',['expected','received'])]:
 error={'ok':False,'error':{'code':code,'details':dict.fromkeys(keys,'7')},'replayed':False}
 paths += [('response.schema.json',error,['error','details',k]) for k in keys]
lex=['0','18446744073709551615','18446744073709551616','00','+7','7.0','7\n','7\r','7\r\n','7\u2028','7\u2029','7\t','7 ',' 7','٧',7,None]
for root,base,path in paths:
 for v in lex:
  x=copy.deepcopy(base);d=x
  for k in path[:-1]:d=d[k]
  d[path[-1]]=v; expected=isinstance(v,str) and re.fullmatch('[0-9]+',v) is not None and (v=='0' or not v.startswith('0')) and int(v)<=2**64-1
  record(root+':'+'.'.join(path)+':'+repr(v),expected,accepts(roots[root],x))
# Direct ECMAScript evaluation of parsed patterns, preserving actual control codepoints.
patterns=[s['properties']['expected_revision']['pattern'] for s in [roots['request.schema.json']]]
nodecode='const x=JSON.parse(process.argv[1]);console.log(JSON.stringify(x.values.map(v=>({value:v,accepted:new RegExp(x.pattern).test(v)}))))'
node=json.loads(subprocess.check_output(['node','-e',nodecode,json.dumps({'pattern':patterns[0],'values':['7\n','7\r','7\r\n','7\u2028','7\u2029','7']})],text=True,encoding="utf8"))
save('ecmascript-probes.json',node)
# Seven closed DomainRejected arms, both replay statuses and forbidden fields/types/missing.
for code in ['NoUndo','RevisionOverflow','Closed','RevisionConflict','NotReady','Busy','InvalidInput']:
 for replay in [False,True]:
  fields={'field':'expected_revision'} if code=='InvalidInput' else {}
  base={'ok':False,'error':{'code':'DomainRejected','details':{'code':code,'fields':fields}},'replayed':replay}
  for label,fields2,expected in [('valid',fields,True),('string','',False),('extra',dict(fields,x='bad'),False),('null',None,False),('numeric',7,False)]:
   x=copy.deepcopy(base);x['error']['details']['fields']=fields2;record('domain:'+code+':'+str(replay)+':'+label,expected,accepts(roots['response.schema.json'],x))
# New cross-property state probes, rather than running author's main/104 vectors.
base=f['lifecycle'][0]
for rev in ['8','9','18446744073709551615']:
 for gate in ['authorized','writer','closed','owner_generation','none']:
  c=copy.deepcopy(base);s=c['state'];s['terminal']={'outcome':'Applied','revision':'8','consume':True};s['live_revision']=rev;s['candidate_used']=True
  if gate in ['authorized','writer']:s[gate]=False
  elif gate=='closed':s[gate]=True
  elif gate=='owner_generation':s[gate]='4'
  out=ns['model'](c);record('replay:'+rev+':'+gate,gate=='none',out['deliver']);record('render:'+rev+':'+gate,gate=='none' and rev=='8',out['render']);record('no-recommit:'+rev+':'+gate,0,out['commits'])
for rd in ['0','9','18446744073709551615']:
 c=copy.deepcopy(base);c['state']['owner_outcome']='NoChange';c['state']['redo_depth']=rd;out=ns['model'](c)
 record('nochange-redo:'+rd,rd,out['redo']);record('nochange-consume:'+rd,True,out['consume']);record('nochange-commit:'+rd,0,out['commits'])
for stage in ['transfer-failed','record-lost','root-provider-unavailable']:
 c=copy.deepcopy(base);c['state']['root_stage']=stage;out=ns['model'](c);record('retention-failure:'+stage,('AppliedRetentionDeferred',True,1,False),(out['outcome'],out['consume'],out['commits'],out['release']))
for flag in ['owner_outcome','proof_verified','pin_state']:
 c=copy.deepcopy(base);c['state'][flag]={'owner_outcome':'Unknown','proof_verified':False,'pin_state':'Unknown'}[flag];out=ns['model'](c);record('unknown:'+flag,('Unknown',0,False,False),(out['consume'],out['commits'],out['deliver'],out['release']))
for field,value,expected in [('candidate_used',True,'CandidateUsed'),('candidate_generation','4','StaleOwner'),('candidate_revision','6','StaleRevision'),('C1_ready',False,'DependencyNotReady')]:
 c=copy.deepcopy(base);c['state'][field]=value;record('admission:'+field,expected,ns['model'](c)['outcome'])
t=read(C/'trusted-fixture-authority.json')
for section,path,value in [('capture',['candidate_raw_digest'],'c'*64),('mutation',['context','candidate_semantic_digest'],'c'*64),('pin',['context','candidate_ref'],'foreign'),('roots',['after','LiveDocuments','material_versions'],[['foreign','v9']]),('roots',['after','UndoHistory','material_versions'],[]),('roots',['after','RedoHistory','material_versions'],[['Z','v1']]),('roots',['after','RecoverySnapshots','material_versions'],[]),('roots',['after','InFlightTransactions','material_versions'],[])]:
 p=copy.deepcopy(t);d=p[section]
 for k in path[:-1]:d=d[k]
 d[path[-1]]=value
 try:ns['proofcheck'](p,t);ok=True
 except AssertionError:ok=False
 record('immutable-proof:'+section+':'+'.'.join(path),False,ok)
for key in ['FileCommit','formal_save_ack','formal_root_transfer']:
 p=copy.deepcopy(t);p['io'][key]='CALLED'
 try:ns['proofcheck'](p,t);ok=True
 except AssertionError:ok=False
 record('no-io:'+key,False,ok)
# Relation positive: existing fixed issuer premise passes; synchronized authority mutation NOT an attack.
ns['proofcheck'](t,t);record('fixed-five-roots-positive',True,True)
source=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json'); authority=source['source_hashes']; drift=[p for p,h in authority.items() if digest(R/p)!=h]
inputs=read(C/'source-hashes.json'); inputdrift=[p for p,h in inputs.items() if digest(R/p)!=h]
checked={str(p.relative_to(R)).replace('\\','/'):digest(p) for p in C.iterdir() if p.is_file()}
save('reviewed-hashes.json',checked);save('new-probes.json',results)
save('verification.json',{'status':'CHANGES_REQUIRED_DOCUMENT_ONLY','reviewer':'/root/m03_candidate_install_review','author':'/root/m03_candidate_install_packet','method':'AST extract only selected functions; candidate main and author verification untouched','new_independent_probes':len(results),'passed':sum(x['status']=='PASS' for x in results),'failed':sum(x['status']=='FAIL' for x in results),'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(),'historical_authority_head':source['head'],'authority_entries':len(authority),'authority_drift':drift,'source_input_drift':inputdrift,'candidate_files':len(checked),'not_run':['full Draft validator (dependency absent)','author 104 cases not rerun as progress','product tests','native/UI/IPC','valid RED/GREEN','build/package/install','Owner adoption']})
print(json.dumps({'probes':len(results),'failures':[x['id'] for x in results if x['status']=='FAIL'],'node':node,'authority':len(authority),'drift':drift,'inputdrift':inputdrift}))


