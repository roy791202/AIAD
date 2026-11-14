"""Independent bounded document review; never imports or executes product code."""
import copy, hashlib, importlib.util, json, re, subprocess
from pathlib import Path
D=Path(__file__).resolve().parent
W=next(p for p in D.parents if (p/'apps/sgenaxis-desktop').exists())
P=D.parent/'save-retention-observation-proposal'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 spec=importlib.util.spec_from_file_location('candidate_readonly',P/'model.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 seed=read(P/'fixtures.json')[0]['input'];rows=[]
 def probe(name,x,expected):
  before=copy.deepcopy(x)
  try:got=m.evaluate(x)
  except Exception as e:got={'exception':type(e).__name__}
  ok=all(got.get(k)==v for k,v in expected.items()) and x==before
  rows.append({'id':name,'input':x,'expected':expected,'observed':got,'input_unchanged':x==before,'pass':ok})
 def change(path,value):
  x=copy.deepcopy(seed);o=x
  for k in path[:-1]:o=o[k]
  o[path[-1]]=value;return x
 zero={'outcome':'RejectedMalformed','root_calls':0,'ack_calls':0,'release_calls':0,'formal_revision':None,'snapshot':None}
 objects=[[],['capture'],['seal'],['held'],['root'],['ack'],['file'],['file','receipt'],['current'],['held','capture'],['root','capture'],['ack','capture']]
 for path in objects:
  o=seed
  for k in path:o=o[k]
  for key in o:
   x=copy.deepcopy(seed);q=x
   for k in path:q=q[k]
   del q[key];probe('missing/'+('/'.join(path+[key])),x,zero)
  x=copy.deepcopy(seed);q=x
  for k in path:q=q[k]
  q['unexpected']=True;probe('closed/'+('/'.join(path) or 'top'),x,zero)
 for path in [['capture'],['seal'],['held'],['root'],['ack'],['file'],['current']]:
  for bad in [None,False,12,[], 'bad']:probe('object/'+str(path)+'/'+repr(bad),change(path,bad),zero)
 captures=[['capture'],['seal'],['held','capture'],['root','capture'],['ack','capture']]
 for path in captures:
  for key in m.KEYS-{'previous_raw'}:
   for bad in [None,False,12]:probe('type/'+('/'.join(path+[key]))+'/'+repr(bad),change(path+[key],bad),zero)
  for key in ['revision','generation']:
   for bad in ['01','-1','18446744073709551616','10\n']:
    probe('u64/'+('/'.join(path+[key]))+'/'+repr(bad),change(path+[key],bad),zero)
  for key in ['semantic','raw']:
   for bad in ['x','A'*64,'a'*64+'\n']:probe('digest/'+('/'.join(path+[key]))+'/'+repr(bad),change(path+[key],bad),zero)
 for name in ['held','root','ack','file']:
  for bad in [None,False,12,[],{},'Other']:probe('enum/'+name+'/'+repr(bad),change([name,'state'],bad),zero)
 for name in ['held','root']:
  for key in ['trusted','fence']:
   for bad in [None,0,1,'true']:probe('bool/'+name+'/'+key+'/'+repr(bad),change([name,key],bad),zero)
  for key in ['issuer','receipt_id']:
   for bad in [None,False,12]:probe('string/'+name+'/'+key+'/'+repr(bad),change([name,key],bad),zero)
 for key in ['attached','authorized']:
  for bad in [None,0,1,'true']:probe('current/'+key+'/'+repr(bad),change(['current',key],bad),zero)
 for key in seed['file']['receipt']:
  for bad in [False,12,[],{}]+([] if key=='previous_digest' else [None,'']):
   probe('receipt-type/'+key+'/'+repr(bad),change(['file','receipt',key],bad),zero)
 for key in ['formal_revision','live_semantic','snapshot']:
  for bad in [None,False,12,[],{}]:probe('top-type/'+key+'/'+repr(bad),change([key],bad),zero)
 for path in captures:
  for bad in [[None],[False],[12],[{}],[{'asset_id':'A','content_digest':'x'}],[{'asset_id':False,'content_digest':'a'*64}],[{'asset_id':'A','content_digest':'a'*64,'extra':1}],seed['capture']['asset_versions']*2]:
   probe('asset-shape/'+('/'.join(path))+'/'+repr(bad),change(path+['asset_versions'],bad),zero)
 for name in ['seal','held','root','ack']:
  path=[name] if name=='seal' else [name,'capture']
  for key in sorted(m.KEYS):
   old=seed['capture'][key]
   value=([{'asset_id':'B','content_digest':'f'*64}] if key=='asset_versions' else 'f'*64 if key in ['semantic','raw','previous_raw'] else '3' if key in ['generation','revision'] else old+'-other')
   probe('tuple/'+name+'/'+key,change(path+[key],value),{'ack_calls':0,'release_calls':0,'formal_revision':'9','snapshot':seed['snapshot']})
 for state in ['Failed','Unknown','Released']:
  probe('root-state/'+state,change(['root','state'],state),{'outcome':'CommittedAckDeferred','retention':'HeldObserved','root_calls':1,'ack_calls':0,'release_calls':0})
 for state in ['PrecommitFailure','Uncertain']:
  probe('file-state/'+state,change(['file','state'],state),{'retention':'HeldObserved','root_calls':0,'ack_calls':0,'release_calls':0})
 for name in ['held','root']:
  for key,value in [('issuer','M04'),('trusted',False),('fence',False),('receipt_id','')]:
   probe('proof/'+name+'/'+key,change([name,key],value),{'ack_calls':0,'release_calls':0,'retention':'NOT_PROVEN' if name=='held' else 'HeldObserved'})
 for state in ['Transferred','Released','Unknown']:
  probe('initial-state/'+state,change(['held','state'],state),{'retention':'NOT_PROVEN','root_calls':0,'ack_calls':0,'release_calls':0})
 for key in seed['file']['receipt']:
  probe('receipt/'+key,change(['file','receipt',key],'different'),{'outcome':'UnverifiedOutcome','retention':'HeldObserved','root_calls':0,'ack_calls':0,'release_calls':0})
 for key in ['attached','authorized']:
  probe('delivery/'+key,change(['current',key],False),{'delivery':False,'retention':'HeldObserved','root_calls':0,'ack_calls':0,'release_calls':0})
 probe('late-ack-newer-baseline',change(['formal_revision'],'11'),{'outcome':'CommittedAckDeferred','formal_revision':'11','ack_calls':0,'release_calls':0})
 probe('captured-semantic-not-raw',copy.deepcopy(seed),{'outcome':'Saved','dirty':True,'formal_revision':'10','ack_calls':1,'release_calls':0,'snapshot':seed['snapshot']})
 probe('semantic-clean',change(['live_semantic'],seed['capture']['semantic']),{'outcome':'Saved','dirty':False,'ack_calls':1,'release_calls':0})
 # Trust premise witnesses are observations, not rejection requirements.
 premises=[]
 for name,x in [('caller-supplied-trusted-booleans',copy.deepcopy(seed)),('different-trusted-root-receipt',change(['root','receipt_id'],'other-issued-record'))]:
  premises.append({'id':name,'observed':m.evaluate(x),'meaning':'Supplied verified M05 observation premise; token authenticity/linkage not independently proved.'})
 auth=read(W/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
 inputs=read(P/'inputs.json');drift=[p for p,h in auth['source_hashes'].items() if sha(W/p)!=h]
 inputdrift=[p for p,h in inputs['source_inputs'].items() if sha(W/p)!=h]
 candidate=read(P/'seal.json');candrift=[p for p,h in candidate['artifacts'].items() if sha(P/p)!=h]
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()
 checkout={'head':head,'authority_head':auth['head'],'authority_files':len(auth['source_hashes']),'product_drift':drift,'input_drift':inputdrift,'candidate_seal_drift':candrift,'board_hash':sha(W/'docs/board.json'),'proposal_board_hash':inputs['management_separate']['docs/board.json'],'head_diff_names':subprocess.check_output(['git','diff','--name-only',auth['head'],head],cwd=W,text=True).splitlines()}
 result={'status':'PASS_DOCUMENT_ONLY_PENDING_OWNER' if all(r['pass'] for r in rows) and not(drift or inputdrift or candrift) else 'FAIL','new_probes':len(rows),'passed':sum(r['pass'] for r in rows),'failed':[r['id'] for r in rows if not r['pass']],'trust_premise_observations':premises,'checkout':checkout,'not_run':['native/UI/IPC','product tests','build/package/install','valid RED/GREEN','full Draft 2020-12 validation']}
 (D/'fixtures.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
 (D/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k!='trust_premise_observations'},indent=2))
 assert result['status']=='PASS_DOCUMENT_ONLY_PENDING_OWNER'
if __name__=='__main__':main()
