from pathlib import Path
import copy,json,hashlib
from model import read,evaluate,digest
P=Path(__file__).resolve().parent
results=[]
for case in read('fixtures.json'):
 x=case['input'];original=copy.deepcopy(x);actual=evaluate(x)
 assert actual['result']==case['expected'],(case['id'],actual['result'])
 assert x==original
 assert all(actual['calls'][k]==0 for k in ['release','retry','rollback','formal_save','formal_ack'])
 if actual['result'] in ['ProofMismatch','RejectedBeforeMutation']:
  assert actual['after']==actual['before'] and actual['calls']['merge_commit']==0
 if actual['result']=='MergeAppliedRetentionDeferred':assert actual['after']['revision']=='11' and len(actual['after']['undo'])==1
 if actual['result']=='UndoAppliedRetentionDeferred':assert actual['after']['revision']=='12' and actual['after']['content']==actual['before']['content'] and len(actual['after']['redo'])==1
 results.append({'id':case['id'],'pass':True,'output':actual})
# Fresh probes mutate every leaf of each admitted proof/body/context field; frozen immutable issuer facts cannot be caller-replaced.
base=copy.deepcopy(read('fixtures.json')[1]['input'])
def leaves(v,path=()):
 if type(v)==dict:
  for k,a in v.items():yield from leaves(a,path+(k,))
 elif type(v)==list:
  for i,a in enumerate(v):yield from leaves(a,path+(i,))
 else:yield path,v
probes=0
for path,value in leaves(base):
 if path[0] in ['commit_observation','root_observation','perform_undo','undo_observation','undo_root_observation']:continue
 x=copy.deepcopy(base);target=x
 for k in path[:-1]:target=target[k]
 target[path[-1]]=value+'X' if type(value)==str else None
 out=evaluate(x);assert out['result']=='ProofMismatch' and out['calls']['merge_commit']==0,(path,out)
 probes+=1
report={'status':'PASS_DOCUMENT_ORACLE_ONLY_PENDING_OWNER','scenario_cases':len(results),'leaf_mutation_probes':probes,'passed':len(results)+probes,'results':results,'not_run':['independent review','native/UI/IPC','product tests','build/package/install','valid RED/GREEN','full Draft2020-12','module acceptance'],'preflight64':'NOT RERUN; preserved historical document acceptance'}
(P/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='results'}))
