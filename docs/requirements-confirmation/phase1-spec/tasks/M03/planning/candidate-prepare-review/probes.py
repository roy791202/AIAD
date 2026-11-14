"""Independent document probes. Imports candidate read-only; no main() writes."""
import copy, hashlib, importlib.util, json, pathlib, sys
P=pathlib.Path(__file__).resolve().parent
C=P.parent/'candidate-prepare-integration'
sys.dont_write_bytecode=True
sys.path.insert(0,str(C))
import check_documents as candidate

def main():
 f=candidate.read('fixtures.json'); results=[]
 def probe(id,fn,expected):
  try: value=fn(); accepted=True
  except (AssertionError,ValueError,TypeError,KeyError): accepted=False
  results.append(dict(id=id,expected_accept=expected,observed_accept=accepted,match=accepted==expected))
 def request(field,v):
  r=copy.deepcopy(f['request']);r[field]=v
  candidate.Draft202012Validator(candidate.read('request.schema.json')).validate(r)
 for field in ['expected_generation','expected_revision']:
  for value in ['0','1','9007199254740993','18446744073709551615','18446744073709551616','01','-1','1.0','1e0','7\n','7\r','7x','',7,True]:
   probe(field+':'+repr(value),lambda field=field,value=value:request(field,value),type(value)is str and value in ['0','1','9007199254740993','18446744073709551615'])
 for field in ['binding_ref','request_id']:
  probe(field+':trailing-newline',lambda field=field:request(field,f['request'][field]+'\n'),False)
 for code,fields in [('NoUndo',{}),('RevisionOverflow',{}),('Closed',{}),('RevisionConflict',{}),('NotReady',{}),('Busy',{}),('InvalidInput',{'field':'expected_revision'})]:
  for fields_value in [fields,'{}',None,[],{'unbound':True}]:
   r={'ok':False,'error':{'code':'DomainRejected','details':{'code':code,'fields':fields_value}},'replayed':False}
   probe('domain:'+code+':'+repr(fields_value),lambda r=r:candidate.Draft202012Validator(candidate.read('response.schema.json')).validate(r),fields_value==fields)
 for text in ['{"format":"sgenaxis.design","formatVersion":1,"product_pass":false,"meta":{"x":1,"\\u0078":2}}','{"format":"sgenaxis.design","formatVersion":1,"product_pass":false,"n":1}','{','null']:
  probe('inner-reject:'+text,lambda text=text:candidate.inner(text),False)
 text=f['request']['design_json'];probe('inner-exact-decimal',lambda:candidate.inner(text.replace('0.5','0.500')),True)
 # Deliberately limited C1 premise; no claim this is valid complete C1 DesignDoc.
 probe('subset-does-not-validate-node-types',lambda:candidate.inner(text.replace('"nodes":[','"nodes":true,"discarded":[')),False)
 for state_key,bad in [('authorized',False),('closed',True),('writer',False),('generation','4'),('late_owner',True)]:
  x=copy.deepcopy(f['cases'][0]);x['state'][state_key]=bad
  def reject(x=x):assert not candidate.model(x)['response']['ok']
  probe('authority:'+state_key,reject,True)
 for dep in ['C1_CODEC','ESS_PROJECTOR','M04_OWNER_INTEGRATION','M05_MATERIAL']:
  x=copy.deepcopy(f['cases'][0]);x['state']['dependency']=dep
  def reject(x=x):
   o=candidate.model(x);assert o['response']['error']['code']=='DependencyNotReady' and o['slot']=='candidate-old' and not o['FileCommit'] and not o['ACK']
  probe('dependency:'+dep,reject,True)
 t=candidate.read('trusted-fixture-authority.json')
 for key in ['owner','revision','request_id','purpose','issuer','state']:
  x=copy.deepcopy(t);x[key]='substituted'
  probe('immutable-proof:'+key,lambda x=x:candidate.proofcheck(x,t),False)
 x=copy.deepcopy(f['cases'][0]);x['state']['retained']={'request':copy.deepcopy(x['request']),'response':copy.deepcopy(f['response'])};x['state']['slot']='candidate-replacement';x['state']['revision']='8'
 o=candidate.model(x)
 observation={'id':'retained-old-candidate-after-slot-replacement','response':o['response'],'slot':o['slot'],'deliver':o['deliver'],'classification':'OPEN_OWNER_NON_RENDER_REPLAY_POLICY; not approved conflict','required_closure':'Specify historical-only replay rendering/install authority after slot replacement and candidate consumed/revoked; no invented TTL or rejection code.'}
 result={'reviewer':'/root/m03_candidate_prepare_review','author':'/root/m03_candidate_prepare_packet','status':'CHANGES_REQUIRED_LEXICAL_IDENTIFIERS_ONLY','new_probes':len(results),'mismatches':[r for r in results if not r['match']],'results':results,'open_policy_observation':observation,'original_96':'NOT RERUN','fullDraft':'NOT RUN','product':'NOT RUN','native':'NOT RUN','RED':'NOT RUN','build':'NOT RUN'}
 (P/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'probes':len(results),'mismatches':result['mismatches']}))
if __name__=='__main__':main()
