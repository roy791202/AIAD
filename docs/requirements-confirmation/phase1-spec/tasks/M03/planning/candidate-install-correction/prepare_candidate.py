import ast,copy,hashlib,html,json,pathlib,re,shutil,subprocess
P=pathlib.Path(__file__).resolve().parent; R=pathlib.Path.cwd(); C=P.parent/'candidate-install-integration'; S=P.parent/'save-proof-correction'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
# Copy the complete command candidate. Original checker/104 trace retained, not rerun.
for p in C.iterdir():
 if p.is_file():shutil.copyfile(p,P/p.name)
shutil.copyfile(C/'verification.json',P/'historical-author-verification.json')
shutil.copyfile(C/'index.html',P/'historical-candidate.html')
strict=read(S/'request.schema.json')['$defs']['U64Decimal']
assert list(map(ord,strict['pattern'][-10:]))==[40,63,33,91,92,115,92,83,93,41]
changes=[]
def patch(s,path):
 if isinstance(s,dict):
  if 'pattern'in s and s['pattern'].startswith('^(0|[1-9][0-9]'):
   changes.append({'pointer':path,'before':copy.deepcopy(s),'after':copy.deepcopy(strict)})
   s.clear();s.update(copy.deepcopy(strict));return
  for k,v in s.items():patch(v,path+'/'+k.replace('~','~0').replace('/','~1'))
 elif isinstance(s,list):
  for i,v in enumerate(s):patch(v,path+'/'+str(i))
for name in ['request.schema.json','response.schema.json']:
 before=read(C/name);after=copy.deepcopy(before);start=len(changes);patch(after,'');save(name,after)
 for c in changes[start:]:c['file']=name
save('schema-pointer-diff.json',changes)
# A normalization proof: replacing each exact changed node with its original recreates source JSON exactly.
equiv=[]
for name in ['request.schema.json','response.schema.json']:
 restored=read(P/name)
 for c in changes:
  if c['file']!=name:continue
  keys=c['pointer'][1:].split('/');node=restored
  for k in keys[:-1]:node=node[int(k)] if isinstance(node,list) else node[k.replace('~1','/').replace('~0','~')]
  node[keys[-1]]=c['before']
 canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':')).encode()
 a=canonical(read(C/name));b=canonical(restored);assert a==b
 equiv.append({'file':name,'non_U64_canonical_equivalent':True,'original_sha256':digest(C/name),'candidate_sha256':digest(P/name),'restored_canonical_sha256':hashlib.sha256(b).hexdigest()})
unchanged=[{'file':p.name,'before_sha256':digest(p),'after_sha256':digest(P/p.name),'bytes_equal':p.read_bytes()==(P/p.name).read_bytes()} for p in C.iterdir() if p.is_file() and p.name not in ['request.schema.json','response.schema.json','index.html','verification.json','artifact-hashes.json']]
assert all(x['bytes_equal'] for x in unchanged)
save('non-u64-equivalence.json',{'schemas':equiv,'unchanged':unchanged,'policies':'NoChange/consume/retention/replay/proof/model unchanged byte-for-byte; no new policy adoption'})
save('correction-source-hashes.json',{'candidate_source':{str(p.relative_to(R)).replace('\\','/'):digest(p) for p in C.iterdir() if p.is_file()},'strict_definition':{str((S/'request.schema.json').relative_to(R)).replace('\\','/'):digest(S/'request.schema.json')},'review':{str((P.parent/'candidate-install-review/review.json').relative_to(R)).replace('\\','/'):digest(P.parent/'candidate-install-review/review.json')}})
print('complete copy; schema occurrences',len(changes))

