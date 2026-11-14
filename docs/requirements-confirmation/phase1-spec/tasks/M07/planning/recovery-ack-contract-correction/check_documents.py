"""Bounded author DOCUMENT checks, no native or independent acceptance."""
from pathlib import Path
import copy,json,hashlib,runpy,html
P=Path(__file__).resolve().parent
ROOT=P.parents[6]
def read(n):return json.loads((P/n).read_text(encoding='utf-8-sig'))
def put(n,v):(P/n).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 old=runpy.run_path(str(P.parent/'recovery-ack-contract-proposal/check_documents.py'))
 new=runpy.run_path(str(P/'document_oracle.py'))
 original=old['evaluate'];evaluate=new['evaluate'];f=read('immutable-proof.json');base=read('fixtures.json')[0];trace=[]
 for x in read('fixtures.json')+read('positive-cases.json'):
  before=original(copy.deepcopy(x),f);after=evaluate(copy.deepcopy(x),f)
  assert before==after,x['id']
  trace.append(dict(id=x['id'],bdd='RA-C-002',pass_document=True,observed=after))
 for case in read('negative-cases.json'):
  for proof,root in [(True,'Transferred'),(False,'Transferred'),(True,'Unknown'),(True,'Deferred')]:
   x=copy.deepcopy(base);path=case['path']
   if case['action']=='missing_request':del x['request']
   elif not path:x['request']=case['value']
   else:
    d=x['request']
    for k in path[:-1]:d=d[k]
    if case['action']=='delete':del d[path[-1]]
    else:d[path[-1]]=case['value']
   x['proof_available']=proof;x['root_state']=root
   out=evaluate(x,f)
   assert out['result']=='Rejected' and out['state']==x['state'] and out['calls']==dict(ack=0,retry=0,release=0) and out['published'] is False,(case,out)
   trace.append(dict(id=case['id'],bdd='RA-C-001' if proof and root=='Transferred' else 'RA-C-003',proof=proof,root=root,pass_document=True,observed=out))
 closure=[]
 for key in ['body','context']:
  x=copy.deepcopy(base);del x['request'][key]
  try:original(x,f)
  except KeyError as e:observed=type(e).__name__+':'+str(e)
  else:raise AssertionError('Original KeyError not reproduced')
  after=evaluate(x,f);assert after['result']=='Rejected'
  closure.append(dict(missing=key,before=observed,after=after))
 malformed=copy.deepcopy(f);malformed['index']['evidence']={}
 try:evaluate(base,malformed)
 except KeyError:issuer_limit='KeyError reproduced outside trusted-record premise; robustness NOT PROVEN'
 else:raise AssertionError('Expected trusted record limit')
 for n in ['request.schema.json','response.schema.json','request-example.json','response-example.json','immutable-proof.json','fixtures.json']:
  assert (P/n).read_bytes()==(P.parent/'recovery-ack-contract-proposal'/n).read_bytes(),n
 for row in read('source-pointers.json'):assert sha(ROOT/row['path'])==row['sha256'],row['path']
 inv=json.loads((ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf-8-sig'))['source_hashes'];assert len(inv)==796
 for name,h in inv.items():assert sha(ROOT/name)==h,name
 result=dict(status='PASS_BOUNDED_DOCUMENT_CORRECTION_PENDING_REVIEW_OWNER',original_cases=20,ordinal_preservation_cases=3,negative_cases=len(read('negative-cases.json')),negative_precedence_evaluations=len(read('negative-cases.json'))*4,total_evaluations=len(trace),keyerror_closures=closure,issuer_limit=issuer_limit,source_pointers=len(read('source-pointers.json')),inventory_files=796,trace=trace,module_pass=False,not_run=read('module-spec.json')['not_run'])
 put('verification.json',result)
 print(json.dumps({k:v for k,v in result.items() if k not in ['trace','keyerror_closures']}))
if __name__=='__main__':main()
