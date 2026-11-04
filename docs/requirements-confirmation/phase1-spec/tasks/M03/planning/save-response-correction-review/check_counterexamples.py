import json,re,ast,copy,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent; P=D.parent/'save-response-correction'
def read(n):return json.loads((P/n).read_text(encoding='utf-8'))
def validate(s,x,root):
 if '$ref'in s:
  v=root
  for k in s['$ref'][2:].split('/'):v=v[k.replace('~1','/').replace('~0','~')]
  return validate(v,x,root)
 if 'oneOf'in s:return sum(validate(v,x,root)for v in s['oneOf'])==1
 if 'const'in s and x!=s['const']:return False
 if 'enum'in s and x not in s['enum']:return False
 t=s.get('type');types={'string':isinstance(x,str),'object':isinstance(x,dict),'array':isinstance(x,list),'boolean':isinstance(x,bool),'null':x is None}
 if t and not any(types.get(k,False)for k in(t if isinstance(t,list)else[t])):return False
 if isinstance(x,str):
  if len(x)<s.get('minLength',0)or len(x)>s.get('maxLength',10**9):return False
  if 'pattern'in s and re.search(s['pattern'],x)is None:return False
 if isinstance(x,dict):
  if any(k not in x for k in s.get('required',[])):return False
  p=s.get('properties',{})
  if s.get('additionalProperties')is False and any(k not in p for k in x):return False
  if any(k in x and not validate(v,x[k],root)for k,v in p.items()):return False
 if isinstance(x,list)and 'items'in s and any(not validate(s['items'],v,root)for v in x):return False
 return True
# Extract only model function; do not import writer runner or rerun its117 cases.
module=ast.parse((P/'check_documents.py').read_text(encoding='utf-8'))
fn=next(x for x in module.body if isinstance(x,ast.FunctionDef)and x.name=='model');env={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'extracted-model','exec'),env)
req=read('request.schema.json');base=next(x['value']for x in read('request-vectors.json')if x['expected']);probes=[]
for k in ['expected_generation','expected_revision']:
 for value,expected in [('1\n',False),('18446744073709551616',False),('18446744073709551615',True)]:
  x=copy.deepcopy(base);x[k]=value;probes.append({'id':k+'-'+repr(value),'scope':'complete request schema, restricted pattern semantics without special U64 hook','input':x,'desired':expected,'observed':validate(req,x,req)})
life=read('lifecycle-vectors.json')[0]['input']
x=copy.deepcopy(life);x['capture']['semantic']='d'*64;x['ack']['semantic']='d'*64
probes.append({'id':'same-issuer-proof-changed-capture-semantic','scope':'model evidence gap; immutable original issuer proof is unchanged','input':x,'desired':'must establish immutable issuer capture binding before Saved','observed':env['model'](x)})
x=copy.deepcopy(life);x['capture']['raw']='e'*64;x['file_receipt']['raw']='e'*64;x['root_receipt']['formal_raw']='e'*64
probes.append({'id':'same-issuer-proof-changed-capture-raw','scope':'model evidence gap; original issuer proof has no raw/target/transaction capture binding','input':x,'desired':'must establish immutable issuer capture binding before Saved','observed':env['model'](x)})
x=copy.deepcopy(life);x['capture']['asset_versions']=[{'asset_id':'a','digest':'a'*64}];x['root_receipt']['asset_versions']=[{'asset_id':'b','digest':'b'*64}]
probes.append({'id':'root-version-set-mismatch-unmodeled','scope':'missing explicit material version-set input/check; not current product behavior','input':x,'desired':'must define version-set capture and root receipt equality','observed':env['model'](x)})
assert sum(p.get('desired') is False and p['observed']is True for p in probes)==2
assert all(p['observed']==('Saved',1,None)for p in probes[-3:])
(D/'counterexamples.json').write_text(json.dumps(probes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print({'new_probes':len(probes),'schema_false_acceptances':2,'model_evidence_counterexamples':3,'original_cases_rerun':0})
