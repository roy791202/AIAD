import sys,json,pathlib,hashlib,copy,subprocess,html,datetime
P=pathlib.Path(__file__).resolve().parent; R=P.parents[6]; C=P.parent/'binding-transfer-correction'; O=P.parent/'binding-transfer-integration'
sys.dont_write_bytecode=True;sys.path.insert(0,str(C));import document_model as m
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
class Spy(m.Authority):
 def __init__(self):super().__init__();self.calls=0
 def read(self,t):self.calls+=1;return super().read(t)
probes=[]
def run(name,provider=True,outcome='commit',expected='Transferred',reads=1,omit=None,caller=None,request=None):
 s=m.fresh(); a=Spy(); token=a.mint(m.observation(s));before=copy.deepcopy(s)
 kw=dict(provider=provider,outcome=outcome)
 if omit:kw.pop(omit)
 result=m.transfer(s,request if request is not None else dict(binding_ref=m.UUID,expected_generation='7',expected_revision='9',target_window='ui-editor'),caller or ('main','source-1','tauri://localhost',True),a,token,**kw)
 assert result==expected,(name,result,expected)
 assert a.calls==reads,(name,a.calls)
 if expected not in ('Transferred','TransferredAckDeferred'):assert s==before,name
 assert s['document']==before['document'];assert not any(s['forbidden_calls'].values())
 probes.append(dict(name=name,provider=repr(provider),outcome=repr(outcome),expected=expected,observed=result,authority_reads=a.calls,before=before,after=s,unchanged=s==before,native_unchanged_claim=False,retry=False))
values=[None,0,1,-1,0.0,1.0,'','false','true',[],{},['commit']]
for v in values+[False]:run('provider exact type '+repr(v),provider=v,expected='DependencyNotReady',reads=0)
run('provider omitted',expected='DependencyNotReady',reads=0,omit='provider')
for v in values+[False,True,'COMMIT',' commit','commit\n','ack_lost','unknown\n']:
 run('outcome exact enum '+repr(v),outcome=v,expected='Indeterminate',reads=0)
run('outcome omitted',expected='Indeterminate',reads=0,omit='outcome')
for out,exp in [('commit','Transferred'),('ack-lost','TransferredAckDeferred'),('rollback','IoFailure'),('unknown','Indeterminate')]:run('declared outcome '+out,outcome=out,expected=exp)
for v in values:
 run('provider precedes invalid outcome '+repr(v),provider=v,outcome=None,expected='DependencyNotReady',reads=0)
 run('caller precedes provider '+repr(v),provider=v,outcome=None,caller=('ui-viewer','source-1','tauri://localhost',True),expected='UnauthorizedCaller',reads=0)
 run('request precedes provider '+repr(v),provider=v,outcome=None,request={},expected='InvalidRequest',reads=0)
# Explicit original/corrected behavioral counterexamples with identical trusted model premise.
import importlib.util
spec=importlib.util.spec_from_file_location('original_model',O/'document_model.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
comparison=[]
for provider,outcome in [(1,'commit'),('true','commit'),(True,'mystery'),(True,None)]:
 rows=[]
 for module in (old,m):
  s=module.fresh();a=Spy();t=a.mint(module.observation(s));b=copy.deepcopy(s)
  result=module.transfer(s,dict(binding_ref=m.UUID,expected_generation='7',expected_revision='9',target_window='ui-editor'),('main','source-1','tauri://localhost',True),a,t,provider,outcome)
  rows.append(dict(result=result,reads=a.calls,before=b,after=s,unchanged=s==b))
 comparison.append(dict(provider=provider,outcome=outcome,original=rows[0],corrected=rows[1]))
preserved={}
for n in json.loads((C/'preserved-bytes.json').read_text(encoding='utf-8')):
 preserved[n]=dict(original=sha(O/n),correction=sha(C/n));assert preserved[n]['original']==preserved[n]['correction']
baseline=json.loads((R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf-8')); hashes=[]
for n,h in baseline['source_hashes'].items():
 actual=sha(R/n) if (R/n).is_file() else None;hashes.append(dict(path=n,expected=h,actual=actual,equal=h==actual))
assert len(hashes)==796;assert all(x['equal'] for x in hashes)
choices=json.loads((C/'owner-choices.json').read_text(encoding='utf-8'));assert all(x['status']=='PROPOSED_PENDING_OWNER' for x in choices)
board=json.loads((R/'docs/board.json').read_text(encoding='utf-8'));cards=[]
def walk(x):
 if isinstance(x,dict):
  if x.get('id')=='PD-P1-M03-PREP-01':cards.append(x)
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
walk(board)
save('independent-probes.json',probes);save('before-after-comparison.json',comparison);save('source-hashes.json',hashes);save('preserved-files.json',preserved)
result=dict(verdict='PASS_DOCUMENT_CORRECTION_ONLY_PENDING_OWNER',reviewer='/root/m03_transfer_correction_review',author='/root/m03_transfer_typed_correction',independent_probes=len(probes),before_after_counterexamples=len(comparison),preserved_files=len(preserved),source_hashes=len(hashes),source_hashes_equal=sum(x['equal'] for x in hashes),branch=subprocess.check_output(['git','branch','--show-current'],cwd=R,text=True).strip(),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),historical_head=baseline['head'],owner_choices=choices,board_observation=cards,current_state=json.loads((P.parent/'current-state.json').read_text(encoding='utf-8')),finding='TR-R1 corrected in document model: exact bool provider and closed exact string outcome enum precede authority read. Legitimate unknown reads once, returns Indeterminate and does not retry. Trusted native observations remain model premises.',product_tests='NOT RUN',build='NOT RUN',native='NOT RUN',production_RED='NOT RUN',module_product_acceptance='NOT GRANTED',limits='No receipt adoption, no native unchanged proof, no production implementation authorization; TR-P1..8 and receiptOwnerchoice remain Owner pending.')
save('review-result.json',result)
(P/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M03 transfer correction independent document review</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto}pre{white-space:pre-wrap}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:8px}</style><h1>M03 transfer correction independent review</h1><h2>'+result['verdict']+'</h2><p>TR-R1 document correction only. Owner adoption remains pending. M04 owns authority; M03 is a projection. No product or native proof.</p><p>'+str(len(probes))+' independent type, enum and precedence probes; 4 original/corrected counterexamples; 11 preserved policy/schema files; 796 source hashes unchanged.</p><h2>Behavior and verification</h2><p>Malformed or omitted provider/outcome observations fail before authority.read with zero reads and no model mutation. Legitimate unknown remains Indeterminate, one read, no retry. These observations are declared trusted model premises.</p><h2>Pending scope</h2><p>TR-P1–8, receiptOwnerchoice and all guard proposals remain pending Owner. Product tests, build, native validation and production RED: NOT RUN. No module/product PASS.</p><h2>Structured evidence</h2><p><a href="independent-probes.json">Independent probes with full before/after states</a> · <a href="before-after-comparison.json">Original/corrected comparison</a> · <a href="source-hashes.json">796 source hashes</a> · <a href="preserved-files.json">11 preserved files</a> · <a href="review-result.json">Result</a></p><script type="application/json" id="module-review">'+json.dumps(result,ensure_ascii=False).replace('</','<\\/')+'</script><pre>'+html.escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre>',encoding='utf-8')
save('artifact-hashes.json',{p.name:sha(p) for p in P.iterdir() if p.is_file() and p.name!='artifact-hashes.json'})
print(json.dumps({k:result[k] for k in ('verdict','independent_probes','before_after_counterexamples','preserved_files','source_hashes_equal','head')}))

