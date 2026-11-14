import pathlib,json,re,copy,subprocess,hashlib,sys
sys.dont_write_bytecode=True
P=pathlib.Path(__file__).resolve().parent; C=P.parent/'candidate-prepare-correction'; O=P.parent/'candidate-prepare-integration'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def patterns(x,p=''):
 out={}
 if isinstance(x,dict):
  for k,v in x.items():
   if k=='pattern':out[p+'/pattern']=v
   else:out.update(patterns(v,p+'/'+k))
 elif isinstance(x,list):
  for i,v in enumerate(x):out.update(patterns(v,p+'/'+str(i)))
 return out
def strip(x):
 if isinstance(x,dict):return {k:strip(v) for k,v in x.items() if k!='pattern'}
 if isinstance(x,list):return [strip(v) for v in x]
 return x
def resolve(s,root):
 while '$ref' in s:
  t=root
  for k in s['$ref'][2:].split('/'):t=t[k]
  s=t
 return s
def routes(s,root,path=(),branches=()):
 s=resolve(s,root);out=[]
 if 'pattern'in s:out.append((path,branches,s['pattern']))
 for i,b in enumerate(s.get('oneOf',[])):out+=routes(b,root,path,branches+(i,))
 for k,v in s.get('properties',{}).items():out+=routes(v,root,path+(k,),branches)
 return out
def seed(s,root,branches):
 s=resolve(s,root)
 if 'oneOf'in s:return seed(s['oneOf'][branches[0] if branches else 0],root,branches[1:])
 if 'const'in s:return s['const']
 if 'enum'in s:return s['enum'][0]
 t=s.get('type');t=t[0] if isinstance(t,list) else t
 if t=='object':return {k:seed(v,root,branches) for k,v in s.get('properties',{}).items() if k in s.get('required',[])}
 if t=='array':return []
 if t=='boolean':return False
 if t=='null':return None
 if 'pattern'in s:return '11111111-1111-4111-8111-111111111111' if '{8}-' in s['pattern'] else '0'
 return 'x'
sys.path.insert(0,str(C));from schema_subset import Draft202012Validator
checks=[]; vectors=[]; physical=[]; root_count=0
for name in ['request.schema.json','response.schema.json']:
 a=read(O/name);b=read(C/name);assert strip(a)==strip(b)
 pa=patterns(a);pb=patterns(b);assert pa.keys()==pb.keys()
 for ptr,pat in pb.items():
  before=pa[ptr]; changed=before!=pat
  assert (before.endswith('$') and pat==before[:-1]+r'(?![\s\S])') if changed else pat.endswith(r'(?![\s\S])')
  kind='uuid' if '{8}-' in pat else ('digest' if '{64}'in pat else 'u64')
  values={'uuid':['11111111-1111-4111-8111-111111111111'],'digest':['a'*64],'u64':['0','1','18446744073709551614','18446744073709551615']}[kind]
  bad={'uuid':['11111111-1111-5111-8111-111111111111','AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA'],'digest':['A'*64,'a'*63,'a'*65],'u64':['01','-1','18446744073709551616']}[kind]
  for v in values:
   vectors.append({'pattern':pat,'value':v,'expected':True});assert re.search(pat,v),(kind,ptr,pat,v)
   for tail in ['\n','\r\n','\r','\u2028','\u2029','\0','x','\\']:
    vectors.append({'pattern':pat,'value':v+tail,'expected':False});assert not re.search(pat,v+tail)
  for v in bad:vectors.append({'pattern':pat,'value':v,'expected':False});assert not re.search(pat,v)
  physical.append({'schema':name,'pointer':ptr,'kind':kind,'changed':changed,'tail_codepoints':[ord(c) for c in pat[-10:]]})
 for path,branches,pat in routes(b,b):
  root_count+=1; obj=seed(b,b,branches); target=obj
  for k in path[:-1]:target=target[k]
  vals=['0','18446744073709551615'] if '{8}-' not in pat else ['11111111-1111-4111-8111-111111111111']
  for val in vals:
   target[path[-1]]=val;Draft202012Validator(b).validate(obj)
   for tail in ['\n','\r\n','\u2028','\0']:
    neg=copy.deepcopy(obj);t=neg
    for k in path[:-1]:t=t[k]
    t[path[-1]]=val+tail
    try:Draft202012Validator(b).validate(neg);raise RuntimeError('accepted invalid root')
    except AssertionError:pass
   checks.append({'schema':name,'path':path,'branches':branches,'valid':val,'suffixes_rejected':4})
assert len(physical)==8 and root_count==9
assert sum(x['changed'] for x in physical)==4
preserved=read(C/'before-after.json')['preserved']
for n in preserved:assert (C/n).read_bytes()==(O/n).read_bytes()
node="const fs=require('fs');const a=JSON.parse(fs.readFileSync(0,'utf8'));for(const x of a){if(new RegExp(x.pattern).test(x.value)!==x.expected)throw Error(JSON.stringify(x))}console.log(a.length)"
r=subprocess.run(['node','-e',node],input=json.dumps(vectors),text=True,capture_output=True,check=True)
result={'physical':physical,'root_routes':root_count,'root_properties':checks,'python_regex_cases':len(vectors),'node_regex_cases':int(r.stdout),'preserved_byte_files':list(preserved),'fullDraft':'NOT RUN','native':'NOT RUN','product':'NOT RUN','Owner':'NOT RUN'}
(P/'probe-results.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({'physical':len(physical),'routes':root_count,'python_node_each':len(vectors),'root_properties':len(checks),'preserved':len(preserved)}))


