"""Proposed command document model; never imports or exercises product code."""
import copy, json, pathlib, decimal, hashlib
from schema_subset import Draft202012Validator
P=pathlib.Path(__file__).parent
def read(n): return json.loads((P/n).read_text(encoding='utf8'))
def error(code, details=None): return {'ok':False,'error':{'code':code,'details':details or {}},'replayed':False}
def validate(req,res):
 Draft202012Validator(read('request.schema.json')).validate(req)
 Draft202012Validator(read('response.schema.json')).validate(res)
 if res['ok']:
  assert res['value']['request_id']==req['request_id']
  assert res['value']['captured_revision']==req['expected_revision']
  assert res['value']['installable']==(not bool(res['value']['unsupported']))
def inner(text):
 def pairs(items):
  d={}
  for k,v in items:
   if k in d: raise ValueError('duplicate:'+k)
   d[k]=v
  return d
 def number(token):
  if len(token)>4096:raise ValueError('C1 number_token_bytes')
  return decimal.Decimal(token)
 d=json.loads(text,object_pairs_hook=pairs,parse_float=number,parse_int=number)
 assert d['format']=='sgenaxis.design' and d['formatVersion']==1
 assert d['product_pass'] is False
 assert not set(d)-{'format','formatVersion','meta','nodes','selection','product_pass'}
 return d
def model(c):
 r=c['request']; s=c['state']; calls=[]
 out={'revision':s['revision'],'history':s['history'],'commits':0,'FileCommit':0,'ACK':0,'consume':False,'deliver':False,'slot':s['slot'],'calls':calls}
 def done(response): return dict(out,response=response)
 if not s['authorized']: return done(error('UnauthorizedCaller'))
 if s['closed']: return done(error('MissingBinding'))
 if not s['writer']: return done(error('WriterRequired'))
 if s['generation']!=r['expected_generation']: return done(error('StaleOwner'))
 if s['retained']:
  if s['retained']['request']!=r:return done(error('RequestConflict'))
  out['deliver']=True
  return done(dict(s['retained']['response'],replayed=True))
 if s['revision']!=r['expected_revision']:return done(error('StaleRevision',{'expected':r['expected_revision'],'observed':s['revision']}))
 for dep in ['C1_CODEC','ESS_PROJECTOR','M04_OWNER_INTEGRATION','M05_MATERIAL']:
  if s['dependency']==dep:return done(error('DependencyNotReady',{'dependency':dep}))
 calls.append('C1 guarded inner text')
 try:d=inner(r['design_json'])
 except (ValueError,AssertionError,KeyError,TypeError):return done(error('CodecRejected',{'message':'C1 rejected; no typed document returned'}))
 calls.extend(['ESS semantic projection','M04 owner read','M05 prepare material'])
 if s['material']!='Ready':return done(error('MaterialReadRejected',{'reason':s['material']}))
 if not s['proof']:return done(error('ProofMismatch'))
 if s['late_owner']:return done(error('StaleOwner'))
 out.update(slot='candidate-new',deliver=True)
 return done({'ok':True,'value':{'candidate_ref':'candidate-new','request_id':r['request_id'],'captured_revision':s['revision'],'unsupported':s['unsupported'],'installable':not bool(s['unsupported'])},'replayed':False})
def proofcheck(p,t):
 assert p==t,'immutable issuer lookup mismatch'
 assert p['issuer']=='M05' and p['purpose']=='Candidate' and p['state']=='ReadResolved'
 assert p['owner']==p['capture']['owner'] and p['generation']==p['capture']['generation']
 assert p['revision']==p['capture']['revision'] and p['request_id']==p['capture']['request_id']
 assert set(map(tuple,p['versions']))==set(map(tuple,p['capture']['versions']))
 assert p['formal_IO']==p['ACK']==False
def main():
 results=[]
 def record(id,fn,accept=True):
  try:fn(); actual=True
  except (AssertionError,ValueError,KeyError,TypeError):actual=False
  assert actual==accept,id
  results.append({'id':id,'expected_accept':accept,'observed_accept':actual,'status':'PASS_DOCUMENT_MODEL'})
 f=read('fixtures.json'); req=f['request']; response=f['response']
 for name,value in [('request',req),('response',response)]:record(name+'-root',lambda name=name,value=value:Draft202012Validator(read(name+'.schema.json')).validate(value))
 for name,value in [('request',req),('response',response)]:
  for key in value:
   b=copy.deepcopy(value);del b[key]
   record(name+'-missing-'+key,lambda name=name,b=b:Draft202012Validator(read(name+'.schema.json')).validate(b),False)
  b=copy.deepcopy(value);b['formal_ACK']=True
  record(name+'-unexpected-ACK',lambda name=name,b=b:Draft202012Validator(read(name+'.schema.json')).validate(b),False)
 for key,value in [('request_id','other'),('captured_revision','8'),('installable','true')]:
  b=copy.deepcopy(response);b['value'][key]=value
  record('candidate-'+key,lambda b=b:validate(req,b),False)
 for c in f['cases']:
  def run(c=c):
   got=model(c)
   Draft202012Validator(read('request.schema.json')).validate(c['request'])
   Draft202012Validator(read('response.schema.json')).validate(got['response'])
   validate(c['request'],got['response'])
   assert got==c['expected'],(c['id'],got,c['expected'])
  record(c['id'],run)
 for code,fields in [('NoUndo',{}),('RevisionOverflow',{}),('Closed',{}),('RevisionConflict',{}),('NotReady',{}),('Busy',{}),('InvalidInput',{'field':'expected_revision'})]:
  for replay in [False,True]:
   r={'ok':False,'error':{'code':'DomainRejected','details':{'code':code,'fields':fields}},'replayed':replay}
   record('typed-'+code+str(replay),lambda r=r:Draft202012Validator(read('response.schema.json')).validate(r))
   b=copy.deepcopy(r); b['error']['details']['fields']='{}'
   record('reject-untyped-'+code+str(replay),lambda b=b:Draft202012Validator(read('response.schema.json')).validate(b),False)
 for field in ['expected_generation','expected_revision']:
  for v in ['0','9007199254740993','18446744073709551615','7\n','18446744073709551616','01',7]:
   r=dict(req);r[field]=v
   record(field+repr(v),lambda r=r:Draft202012Validator(read('request.schema.json')).validate(r),v in ['0','9007199254740993','18446744073709551615'])
 t=read('trusted-fixture-authority.json');record('proof-complete',lambda:proofcheck(t,t))
 for key,v in [('issuer','M04'),('state','Unknown'),('generation','4'),('versions',[])]:
  p=copy.deepcopy(t);p[key]=v;record('proof-'+key,lambda p=p:proofcheck(p,t),False)
 for path,h in read('source-hashes.json').items():assert hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()==h,path
 verification={'status':'AUTHOR_DOCUMENT_MODEL_ONLY','author':'/root/m03_candidate_prepare_packet','independent_acceptance':'PENDING','cases':len(results),'results':results,'fullDraft':'NOT RUN','product':'NOT RUN','native':'NOT RUN','RED':'NOT RUN','GREEN':'NOT RUN','build_package_install':'NOT RUN','Owner_adoption':'NOT ADOPTED','Skeleton':'NOT CREATED','module_complete':False}
 (P/'verification.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'document_cases':len(results),'status':verification['status']}))
if __name__=='__main__':main()
