"""Independent read-only candidate review. Writes only this review directory."""
import ast, copy, hashlib, json, pathlib, re, subprocess, sys, types
sys.dont_write_bytecode=True
P=pathlib.Path(__file__).resolve().parent
C=P.parent/'binding-lifecycle-integration'
R=P.parents[6]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def hashes():return {str(p.relative_to(C)):hashlib.sha256(p.read_bytes()).hexdigest() for p in C.rglob('*') if p.is_file()}
def load(name,selected=None):
 tree=ast.parse((C/(name+'.py')).read_text(encoding='utf8'))
 if selected:tree.body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in selected or isinstance(n,ast.Assign)]
 mod=types.ModuleType(name);mod.__file__=str(C/(name+'.py'));sys.modules[name]=mod
 exec(compile(tree,str(C/(name+'.py')),'exec'),mod.__dict__);return mod
def walk(x,p=''):
 if isinstance(x,dict):
  yield p,x
  for k,v in x.items():yield from walk(v,p+'/'+k)
 elif isinstance(x,list):
  for i,v in enumerate(x):yield from walk(v,p+'/'+str(i))
def main():
 before=hashes();write('candidate-frozen-hashes.json',before)
 validator=load('schema_subset').Draft202012Validator
 model=load('document_model',{'error','success','deliver','reduce'})
 roots={n:read(C/n) for n in read(C/'module-spec.json')['roots']}
 checks=[]
 def check(id,condition,detail=None):checks.append({'id':id,'pass':bool(condition),'detail':detail})
 # Saved fixture replay consumes actual parsed schemas, never calls writer-generating run().
 for c in read(C/'lexical-fixtures.json'):
  try:validator(roots[c['schema']]).validate(c['instance']);got=True
  except AssertionError:got=False
  check('saved-root:'+c['id'],got==c['expected_accept'])
 for c in read(C/'pattern-fixtures.json'):check('saved-pattern:'+c['id'],bool(re.search(c['pattern'],c['value']))==c['expected'])
 for c in read(C/'fixtures.json'):
  after,res,calls=model.reduce(c['state'],c['command'],c['request'],c['caller'],c['evidence'])
  check('saved-model:'+c['id'],(after,res,calls)==(c['expected_after'],c['expected_response'],c['expected_calls']))
 for c in read(C/'delivery-fixtures.json'):check('saved-delivery:'+c['id'],model.deliver(c['display'],c['pending'],c['response'],c['current'])==(c['expected_display'],c['expected_status']))
 probes=[];base=read(C/'fixtures.json')[0]
 # Fresh malformed roots: these are wire values, not edits of trusted M04 observations.
 for req in [None,False,17,'trusted-document',[],[1],['document_reference']]:
  try:
   after,res,calls=model.reduce(base['state'],'open',req,base['caller'],base['evidence']);actual=res
  except Exception as ex:actual={'exception':type(ex).__name__,'message':str(ex)}
  probes.append({'id':'NEW-root-'+repr(req),'input':req,'expected':'InvalidRequest with unchanged state and no dependency calls','actual':actual,'pass':actual.get('error',{}).get('code')=='InvalidRequest'})
 # Same role label cannot substitute a different native instance; read output is detached.
 get=next(x for x in read(C/'fixtures.json') if x['id']=='BG-02-get')
 caller=copy.deepcopy(get['caller']);caller['instance']='native-main-2'
 after,res,calls=model.reduce(get['state'],'get',get['request'],caller,get['evidence'])
 probes.append({'id':'NEW-same-role-other-instance','expected':'UnauthorizedCaller / no dependency calls','actual':res,'pass':res.get('error',{}).get('code')=='UnauthorizedCaller' and calls==[]})
 after,res,calls=model.reduce(get['state'],'get',get['request'],get['caller'],get['evidence']);res['value']['design_json']='mutated consumer projection'
 probes.append({'id':'NEW-projection-detached','pass':after==get['state'] and get['evidence']['observation']['projection']['design_json']!='mutated consumer projection'})
 d=read(C/'delivery-fixtures.json')[0];current=copy.deepcopy(d['current']);current['attachment_active']=False
 display,status=model.deliver(d['display'],d['pending'],d['response'],current)
 probes.append({'id':'NEW-live-window-revoked-attachment','input':current,'expected':'Discard revoked attachment response while native window stays live','actual':status,'pass':status!='InstalledProjectionOnly','note':'Trusted current revocation observation, not attacker replacement of immutable M04 fixture. Candidate current context has no attachment-active seam; unknown flag is ignored.'})
 # New lexical negatives for every physical pattern, including unreachable shared definitions.
 count=0
 for n,root in roots.items():
  for ptr,s in walk(root):
   if 'pattern' not in s:continue
   v='abcdef01-abcd-4abc-8abc-abcdef012345' if '[0-9a-f]{8}' in s['pattern'] else 'a'*64 if '{64}' in s['pattern'] else '18446744073709551615'
   for tail in ['\x01','\x1f','\u200b','\uff10']:
    count+=1;check('NEW-physical:'+n+ptr+repr(tail),re.search(s['pattern'],v+tail) is None)
 # Source authority is historical M01 S2, not candidate claim.
 source=read(C/'source-current.json');auth=read(P.parent.parent.parent/'M01/planning/s2-green/source-current.json')
 authority=auth['source_hashes'];assert len(authority)==796
 drift=[]
 for f,h in authority.items():
  q=R/f
  actual=hashlib.sha256(q.read_bytes()).hexdigest() if q.exists() else None
  if actual!=h:drift.append({'path':f,'expected':h,'actual':actual})
 board=read(R/'docs/board.json');cards=[v for _,v in walk(board) if v.get('id')=='PD-P1-M03-PREP-01']
 write('source-verification.json',{'authority_keys':list(auth),'authority_count':len(authority),'drift':drift,'candidate_historical_HEAD':source['HEAD'],'live_HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'live_branch':subprocess.check_output(['git','branch','--show-current'],cwd=R,text=True).strip(),'board':[{k:c.get(k) for k in ['id','zone','status','light']} for c in cards]})
 write('new-probes.json',probes)
 check('candidate-frozen',before==hashes())
 write('verification.json',{'status':'CHANGES_REQUIRED_OPEN_GET_DOCUMENT_ONLY','reviewer':'/root/m03_binding_open_get_review','author':'/root/m03_binding_lifecycle_packet','checks':len(checks),'check_failures':[c for c in checks if not c['pass']],'new_probes':len(probes),'new_probe_failures':[p['id'] for p in probes if not p['pass']],'new_physical_lexical_cases':count,'candidate_unchanged':before==hashes(),'fullDraft':'NOT RUN','native':'NOT RUN','product':'NOT RUN','RED':'NOT RUN','build':'NOT RUN','Owner':'NOT ADOPTED'})
 print(json.dumps(read(P/'verification.json')))
if __name__=='__main__':main()
