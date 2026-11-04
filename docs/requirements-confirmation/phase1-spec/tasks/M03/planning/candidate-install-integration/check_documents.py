"""Candidate DOCUMENT behavior model. Not product implementation or acceptance."""
import copy,json,pathlib,hashlib,uuid
from schema_subset import Draft202012Validator
P=pathlib.Path(__file__).parent
ROOT=pathlib.Path.cwd()
def read(n):return json.loads((P/n).read_text(encoding='utf8'))
def validate(req,res):
 Draft202012Validator(read('request.schema.json')).validate(req)
 Draft202012Validator(read('response.schema.json')).validate(res)
 if res['ok']:
  v=res['value'];assert v['replayed']==res['replayed']
  if v['outcome']=='NoChange':assert v['revision']==req['expected_revision']==v['projection']['revision']
  else:
   assert v['before_revision']==req['expected_revision']
   assert int(v['after_revision'])==int(v['before_revision'])+1
   assert v['projection']['revision']==v['after_revision']

def model(case):
 s=copy.deepcopy(case['state']);r=case['request']
 out={'outcome':None,'revision':s['live_revision'],'history':s['history_depth'],'redo':s['redo_depth'],'commits':0,'consume':False,'deliver':False,'render':False,'retain':True,'pin_state':s['pin_state'],'release':False,'FileCommit':False,'formal_ACK':False}
 def fail(code,uncertain=False):
  return dict(out,outcome=code,consume='Unknown' if uncertain else False)
 if not s['authorized']:return fail('UnauthorizedCaller')
 if s['closed']:return fail('MissingBinding')
 if not s['writer']:return fail('WriterRequired')
 if s['owner_generation']!=r['expected_generation']:return fail('StaleOwner')
 if s['terminal']:
  if s['capture']!=r:return fail('RequestConflict')
  return dict(out,**s['terminal'],deliver=True,render=s['live_revision']==s['terminal']['revision'],commits=0)
 if not s['candidate_present']:return fail('CandidateMissing')
 if s['candidate_used']:return fail('CandidateUsed')
 if s['candidate_generation']!=r['expected_generation']:return fail('StaleOwner')
 if s['live_revision']!=r['expected_revision'] or s['candidate_revision']!=r['expected_revision']:return fail('StaleRevision')
 if not all(s[k] for k in ['C1_ready','M04_ready','M05_ready']):return fail('DependencyNotReady')
 if s['owner_outcome']=='Unknown':return fail('UnverifiedOutcome',True)
 if not s['proof_verified'] or s['pin_state']!='Held':return fail('Indeterminate',True)
 if s['owner_outcome']=='NoChange':return dict(out,outcome='NoChange',consume=True,deliver=True,render=True)
 if int(s['live_revision'])==18446744073709551615:return fail('RevisionOverflow')
 return dict(out,outcome='AppliedRetentionDeferred' if s['root_stage'] else 'Applied',revision=str(int(s['live_revision'])+1),history=str(int(s['history_depth'])+1),redo='0',commits=1,consume=True,deliver=True,render=True)

def proofcheck(proof, trusted):
 # Lookup records are supplied immutable trusted premises; no caller body is an authority.
 assert proof['capture']==trusted['capture']
 for k in ['mutation','pin','roots']:assert proof[k]==trusted[k],k+' issuer record mismatch'
 c,m,p,z=(proof[k] for k in ['capture','mutation','pin','roots'])
 for record,role in [(m,'install'),(p,'pin'),(z,'transfer-live')]:
  assert record['ordinal']=='0' and record['operation_id']==str(uuid.uuid5(uuid.UUID(c['workflow_id']),role+'/0'))
 assert m['issuer']=='M04' and m['kind']=='DocumentMutation' and m['role']=='install'
 assert p['issuer']==z['issuer']=='M05' and p['purpose']=='Candidate'
 assert m['context']==p['context']==z['context']==c
 assert m['candidate_ref']==c['candidate_ref'] and m['pin_id']==p['pin_id']
 assert m['before_revision']==c['expected_revision'] and int(m['after_revision'])==int(m['before_revision'])+1
 assert int(m['history_after'])==int(m['history_before'])+1 and m['redo_after']=='0'
 assert p['actual_state']=='Held' and z['complete'] and z['fenced']
 kinds={'LiveDocuments','UndoHistory','RedoHistory','RecoverySnapshots','InFlightTransactions'}
 assert set(z['before'])==set(z['after'])==kinds
 pairs=lambda x:{tuple(v) for v in x}
 for kind in kinds:
  a,b=z['before'][kind],z['after'][kind]
  assert a['provider']==b['provider']=='fixture:'+kind
  assert a['epoch']==b['epoch']==z['epoch'] and a['complete'] and b['complete']
  assert int(b['version'])==int(a['version'])+(kind in {'LiveDocuments','UndoHistory','RedoHistory'})
 assert pairs(z['before']['LiveDocuments']['material_versions'])==pairs(m['outgoing'])
 assert pairs(z['after']['LiveDocuments']['material_versions'])==pairs(m['installed'])
 assert pairs(z['after']['UndoHistory']['material_versions'])==pairs(z['before']['UndoHistory']['material_versions'])|pairs(m['outgoing'])
 assert z['after']['RedoHistory']['material_versions']==[]
 # Only this fenced fixture has unchanged independent producers; no generic concurrency claim.
 for kind in ['RecoverySnapshots','InFlightTransactions']:assert z['before'][kind]==z['after'][kind]
 assert pairs(m['outgoing']+m['installed'])<=pairs(p['material_versions'])
 assert proof['io']=={'FileCommit':'NOT CALLED','formal_save_ack':'NOT CALLED','formal_root_transfer':'NOT CALLED'}

def main():
 results=[]
 def record(id,fn,expected=True):
  try:fn();actual=True
  except (AssertionError,ValueError,TypeError,KeyError):actual=False
  assert actual==expected,id
  results.append({'id':id,'expected_accept':expected,'observed_accept':actual,'status':'PASS_DOCUMENT_MODEL'})
 f=read('fixtures.json');req,res=f['request'],f['response']
 record('schema-positive',lambda:validate(req,res))
 nochange=copy.deepcopy(res);nochange['value']={'outcome':'NoChange','projection':dict(res['value']['projection'],revision='7'),'replayed':False,'revision':'7','history_depth':'2'}
 record('schema-NoChange',lambda:validate(req,nochange))
 bad=copy.deepcopy(req);bad['design_json']='{}'
 record('request-payload-injection',lambda:validate(bad,res),False)
 bad=copy.deepcopy(res);bad['value']['formal_ACK']=True
 record('response-formal-ACK-injection',lambda:validate(req,bad),False)
 for value in ['0','9007199254740993','18446744073709551615']:
  r=copy.deepcopy(req);r['expected_revision']=value
  record('u64-valid-'+value,lambda r=r:Draft202012Validator(read('request.schema.json')).validate(r))
 for value in ['18446744073709551616','99999999999999999999','01','-1','1.0',7,None,'']:
  r=copy.deepcopy(req);r['expected_revision']=value
  record('u64-reject-'+str(value),lambda r=r:Draft202012Validator(read('request.schema.json')).validate(r),False)
 for value in ['18446744073709551616',7,'01']:
  r=copy.deepcopy(res);r['value']['projection']['owner_generation']=value
  record('response-u64-'+str(value),lambda r=r:validate(req,r),False)
 for code in ['NoUndo','RevisionOverflow','Closed','RevisionConflict','NotReady','Busy','InvalidInput']:
  fields={'field':'expected_revision'} if code=='InvalidInput' else {}
  for replay in [False,True]:
   r={'ok':False,'error':{'code':'DomainRejected','details':{'code':code,'fields':fields}},'replayed':replay}
   record('domain-'+code+'-'+str(replay),lambda r=r:validate(req,r))
   for bad in ['',dict(fields,unexpected='x')]:
    b=copy.deepcopy(r);b['error']['details']['fields']=bad
    record('domain-reject-'+code+'-'+str(replay)+'-'+str(bad),lambda b=b:validate(req,b),False)
 for c in f['lifecycle']:
  actual=model(c)
  def check(c=c,actual=actual):
   for k,v in c['expected'].items():assert actual[k]==v,(c['id'],k,actual[k],v)
   assert actual['release'] is False and actual['FileCommit'] is False and actual['formal_ACK'] is False
  record(c['id'],check)
 trusted=read('trusted-fixture-authority.json');record('proof-complete',lambda:proofcheck(trusted,trusted))
 mutations=[('mutation','issuer','M05'),('mutation','after_revision','9'),('mutation','candidate_ref','other'),('pin','actual_state','Unknown'),('pin','material_versions',[]),('roots','fenced',False),('roots','complete',False)]
 for section,key,v in mutations:
  p=copy.deepcopy(trusted);p[section][key]=v
  record('proof-tamper-'+section+'-'+key,lambda p=p:proofcheck(p,trusted),False)
 # Relation checks also exercised independently from lookup equality by deliberately
 # constructing alternate *fixture premises*. These are relation tests, not attacks.
 for kind,key,v in [('LiveDocuments','material_versions',[['X','v1']]),('UndoHistory','material_versions',[]),('RedoHistory','material_versions',[['Z','v1']]),('LiveDocuments','version','9'),('RecoverySnapshots','version','3')]:
  p=copy.deepcopy(trusted);p['roots']['after'][kind][key]=v
  record('relation-'+kind+'-'+key,lambda p=p:proofcheck(p,p),False)
 p=copy.deepcopy(trusted);p['pin']['material_versions']=[]
 record('relation-pin-membership',lambda:proofcheck(p,p),False)
 for path,h in read('source-hashes.json').items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h,path
 verification={'status':'AUTHOR_DOCUMENT_MODEL_CHECK_ONLY','author':'/root/m03_candidate_install_packet','independent_acceptance':'PENDING_SEPARATE_REVIEW','cases':len(results),'results':results,'fullDraft':'NOT RUN; jsonschema dependency MISSING; generic subset interpreter is not full Draft conformance','product_tests':'NOT RUN','native':'NOT RUN','RED':'NOT RUN','GREEN':'NOT RUN','build':'NOT RUN','Owner_adoption':'NOT ADOPTED','module_complete':False}
 (P/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'document_cases':len(results),'status':verification['status']}))
if __name__=='__main__':main()
