"""Read-only review-local document schema subset oracle; not a product test or full metaschema validator."""
import json,re,hashlib,copy
from pathlib import Path
P=Path(__file__).resolve().parent.parent/'integration-contract-revision-v3'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def errors(s,v,root,path=''):
 out=[]
 if '$ref' in s:
  t=root
  for k in s['$ref'][2:].split('/'):t=t[k.replace('~1','/').replace('~0','~')]
  return errors(t,v,root,path)
 if 'oneOf' in s:
  if sum(not errors(x,v,root,path) for x in s['oneOf'])!=1:out.append(path+':oneOf')
 if 'anyOf' in s and all(errors(x,v,root,path) for x in s['anyOf']):out.append(path+':anyOf')
 if 'enum' in s and v not in s['enum']:out.append(path+':enum')
 if 'const' in s and v!=s['const']:out.append(path+':const')
 types={'object':lambda x:isinstance(x,dict),'array':lambda x:isinstance(x,list),'string':lambda x:isinstance(x,str),'boolean':lambda x:type(x)==bool,'null':lambda x:x is None}
 if 'type' in s:
  ts=s['type'] if isinstance(s['type'],list) else [s['type']]
  if not any(types[t](v) for t in ts):return out+[path+':type']
 if isinstance(v,str):
  if 'pattern' in s and not re.search(s['pattern'],v):out.append(path+':pattern')
  if len(v)<s.get('minLength',0) or len(v)>s.get('maxLength',10**9):out.append(path+':length')
 if isinstance(v,dict):
  for k in s.get('required',[]):
   if k not in v:out.append(path+'/'+k+':missing')
  for k,x in v.items():
   if k in s.get('properties',{}):out+=errors(s['properties'][k],x,root,path+'/'+k)
   elif s.get('additionalProperties') is False:out.append(path+'/'+k+':unknown')
 if isinstance(v,list) and 'items' in s:
  for i,x in enumerate(v):out+=errors(s['items'],x,root,path+'/'+str(i))
 return out
s=load(P/'transition-request.schema.json');vectors=load(P/'request-hash-vectors.json');rows=[]
for v in vectors:
 if 'a' in v:rows.append({'id':v['id'],'a_errors':errors(s,v['a'],s),'b_errors':errors(s,v['b'],s),'oracle':v['expected'],'pointer':v['changed_pointer']})
 else:rows.append({'id':v['id'],'fault_errors':errors(s,v['value'],s),'oracle':v['expected']})
print(json.dumps({'vectors':len(rows),'valid_a':sum(not x['a_errors'] for x in rows if 'a_errors'in x),'valid_b':sum(not x['b_errors'] for x in rows if 'b_errors'in x),'rejected_faults':sum(bool(x['fault_errors']) for x in rows if 'fault_errors'in x),'invalid_b': [x for x in rows if x.get('b_errors')]}))
(Path(__file__).parent/'vector-admission-check.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
