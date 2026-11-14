"""Build bounded DOCUMENT candidate artifacts. Does not touch original inputs."""
import pathlib,json,copy,hashlib,importlib.util,html,subprocess,uuid
P=pathlib.Path(__file__).resolve().parent; H=P.parent/'copy-ready-handoff'; V=P.parent/'copy-ready-review'; ROOT=P.parents[6]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(name,v):(P/name).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
old=load('old',H/'check.py'); originals=read(H/'fixtures.json'); baseline=originals[0]['fixture']; body=baseline['request']['body']
# Migration: raw names now mean exact UTF8 text bytes, not digest strings masquerading as bytes.
raw={
 'definition_raw':json.dumps({'schema':'document-fixture-definition','project_uuid':body['new_project_uuid']},sort_keys=True),
 'document_raw':json.dumps({'schema':'document-fixture-document','project_uuid':body['new_project_uuid'],'document_uuid':body['new_document_uuid'],'content':[]},sort_keys=True),
 'catalog_index_raw':json.dumps({'schema':'document-fixture-catalog','generation':'2','roots':['Held-copy']},sort_keys=True),
 'manifest_raw':json.dumps({'schema':'document-fixture-manifest','entries':[]},sort_keys=True),
}
def fields(b,names):return {name:copy.deepcopy(b[name]) for name in names}
provider_keys=['final_canonical_path','marker_path','target_native_identity','native_lease_id']
catalog_keys=['catalog_generation','catalog_index_raw','manifest_raw','material_root_digest','new_project_uuid','new_document_uuid']
copy_keys=['new_project_uuid','new_document_uuid','source_project_uuid','source_document_uuid','definition_raw','document_raw','manifest_raw','blob_manifest_digest','material_root_digest','source_snapshot_digest']

def enrich(f):
 f=copy.deepcopy(f); b=f['request']['body']
 for key,value in raw.items():
  if b.get(key)==body[key]:b[key]=value
 # Only migration of unchanged legacy Ready field value; negative mutations remain negative.
 if f['issuer_records']['catalog-1']['catalog_index_raw']==body['catalog_index_raw']:f['issuer_records']['catalog-1']['catalog_index_raw']=raw['catalog_index_raw']
 if f['issuer_records']['ready-1']['catalog_index_raw']==body['catalog_index_raw']:f['issuer_records']['ready-1']['catalog_index_raw']=raw['catalog_index_raw']
 return f
base=enrich(baseline)
def attach_bindings(f):
 b=f['request']['body']; rec=f['issuer_records']
 for key,names in [('provider-1',provider_keys),('catalog-1',catalog_keys),('copy-1',copy_keys),('ready-1',list(b))]:rec[key]['binding']=fields(b,names)
 f['request_digest']=old.digest(f['request']);rec['ready-1']['request_digest']=f['request_digest']
 return f
base=attach_bindings(base);base['authority_fixture_id']='coherent-A'
authorities={}
def authority(f):return {'premise':'DOCUMENT ONLY: coherent issuer lookup, held native lease and reported CAS outcome assumed; no native authenticity or durable proof established','issuer_records':copy.deepcopy(f['issuer_records']),'ready_cas':f['ready_cas']}
authorities['coherent-A']=authority(base)
authorities['unknown-CAS']=authority(base);authorities['unknown-CAS']['ready_cas']='Unknown'
# A second independently coherent immutable domain fixture demonstrates relational acceptance.
variant=copy.deepcopy(base);variant['authority_fixture_id']='coherent-B';b=variant['request']['body'];c=variant['request']['context']
c['project_uuid']=str(uuid.uuid5(uuid.NAMESPACE_URL,'document-coherent-B-project'));c['document_uuid']=str(uuid.uuid5(uuid.NAMESPACE_URL,'document-coherent-B-document'));c['workflow_id']=str(uuid.uuid5(uuid.NAMESPACE_URL,'document-coherent-B-workflow'));c['owner_generation']='9';c['captured_revision']='12'
b['new_project_uuid']=c['project_uuid'];b['new_document_uuid']=c['document_uuid'];b['final_canonical_path']='D:\\fixture-B\\project';b['marker_path']=b['final_canonical_path']+'\\.sgenaxis\\copy-state.v1.json';b['target_native_identity']['volume_id']='V-B';b['target_native_identity']['file_id']='F-B';b['native_lease_id']='lease-B';b['catalog_generation']='17';b['definition_raw']=json.dumps({'project_uuid':c['project_uuid'],'name':'B'});b['document_raw']=json.dumps({'document_uuid':c['document_uuid'],'project_uuid':c['project_uuid'],'content':['different bytes']});b['catalog_index_raw']='{"generation":"17","roots":["Held-B"]}';b['manifest_raw']='{"entries":["B"]}';b['source_snapshot_digest']=hashlib.sha256(b'B-source').hexdigest();b['blob_manifest_digest']=hashlib.sha256(b'B-blob').hexdigest();b['material_root_digest']=hashlib.sha256(b'B-root').hexdigest()
variant['request']['operation_id']=str(uuid.uuid5(uuid.UUID(c['workflow_id']),'publish/0'))
for rec in variant['issuer_records'].values():rec['context']=copy.deepcopy(c)
variant['issuer_records']['provider-1']['target_native_identity']=copy.deepcopy(b['target_native_identity']);variant['issuer_records']['catalog-1']['catalog_index_raw']=b['catalog_index_raw']
for key in ['blob_manifest_digest','material_root_digest']:variant['issuer_records']['copy-1'][key]=b[key]
r=variant['issuer_records']['ready-1'];r['transaction_id']='tx-B'
for pk,bk in [('target_native_identity','target_native_identity'),('target_path','marker_path'),('catalog_index_raw','catalog_index_raw'),('blob_manifest_digest','blob_manifest_digest'),('material_root_digest','material_root_digest')]:r[pk]=copy.deepcopy(b[bk])
variant=attach_bindings(variant);authorities['coherent-B']=authority(variant)
write('authority-fixtures.json',authorities)
# Exact recursively closed root schema; every object has required and additionalProperties=false.
def schema(value):
 if type(value) is dict:return {'type':'object','properties':{k:schema(v) for k,v in value.items()},'required':list(value),'additionalProperties':False}
 if type(value) is bool:return {'type':'boolean'}
 assert type(value) is str
 return {'type':'string','minLength':1}
s=schema(base)
def at(path):
 node=s
 for part in path.split('.'):node=node['properties'][part]
 return node
for path,choices in {'request.protocol':['COPY-READY-CANDIDATE-v1'],'request.issuer':['M01'],'request.role':['publish'],'request.ordinal':['0'],'ready_cas':['Verified','Unknown']}.items():at(path)['enum']=choices
for key,issuer,statuses in [('provider-1','NativeProvider',['Verified','Unknown']),('catalog-1','M05',['Verified','Unknown']),('copy-1','M06',['Complete','Incomplete']),('ready-1','M01',None)]:
 at('issuer_records.'+key+'.issuer')['enum']=[issuer]
 if statuses:at('issuer_records.'+key+'.status')['enum']=statuses
at('issuer_records.ready-1.kind')['enum']=['ProjectCopyReady']
s['$schema']='https://json-schema.org/draft/2020-12/schema';s['title']='PROPOSED_PENDING_OWNER closed DOCUMENT fixture root; not existing publish schema'
write('candidate.schema.json',s)
# Migrate each old case; binding records come from baseline, not the mutated request.
def migrate(f,authority_id='coherent-A'):
 old_request_digest=old.digest(f['request']);g=enrich(f);g['authority_fixture_id']=authority_id
 for key in g['issuer_records']:g['issuer_records'][key]['binding']=copy.deepcopy(base['issuer_records'][key]['binding'])
 if f['request_digest']==old_request_digest:g['request_digest']=old.digest(g['request'])
 if f['issuer_records']['ready-1']['request_digest']==old_request_digest:g['issuer_records']['ready-1']['request_digest']=old.digest(g['request'])
 return g
migrated=[]
for item in originals:
 f=migrate(item['fixture'],'unknown-CAS' if item['fixture']['ready_cas']=='Unknown' else 'coherent-A')
 migrated.append({**item,'fixture':f,'migration':'PROPOSED_PENDING_OWNER CR-D1..D3; exact raw byte representation + immutable fixture lookup + issuer bindings; expected output unchanged'})
write('fixtures.json',migrated)
review=read(V/'new-fixtures.json'); ids={x['id'] for x in read(V/'review.json')['counterexamples']}
closure=[{**item,'fixture':migrate(item['fixture']),'before':item['actual'],'expected':item['expected']} for item in review if item['id'] in ids]
write('closure-fixtures.json',closure)
new=[]
def probe(name,mutate,expected,reseal=False):
 f=copy.deepcopy(base);mutate(f)
 if reseal:
  f['request_digest']=old.digest(f['request']);f['issuer_records']['ready-1']['request_digest']=f['request_digest']
 new.append({'id':'CC-'+str(len(new)+1).zfill(3),'name':name,'fixture':f,'expected':expected})
for key in body:
 def mutate(f,k=key):
  v=f['request']['body'][k]
  if isinstance(v,dict):v['file_id']='other-file'
  else:f['request']['body'][k]=v+'-changed'
 probe('rehashed body '+key,mutate,'RejectedBeforeMutation' if key in ['new_project_uuid','new_document_uuid'] else 'ProofMismatch',True)
# Attacker changes every visible binding coherently and reseals Ready DTO. Frozen lookup is unchanged.
def forge(f):
 f['request']['body']['native_lease_id']='forged-lease'
 for rec in f['issuer_records'].values():
  if 'native_lease_id' in rec['binding']:rec['binding']['native_lease_id']='forged-lease'
probe('caller forged coherent lease records',forge,'ProofMismatch',True)
def forge_path(f):
 b=f['request']['body'];b['final_canonical_path']='C:\\forged';b['marker_path']=b['final_canonical_path']+'\\.sgenaxis\\copy-state.v1.json';f['issuer_records']['ready-1']['target_path']=b['marker_path']
 for rec in f['issuer_records'].values():
  for k in ['final_canonical_path','marker_path']:
   if k in rec['binding']:rec['binding'][k]=b[k]
probe('caller forged coherent path records',forge_path,'ProofMismatch',True)
probe('unknown authority reference',lambda f:f.__setitem__('authority_fixture_id','unissued'),'ProofMismatch')
probe('missing full root',lambda f:f.pop('issuer_records'),'RejectedBeforeMutation')
probe('unknown root',lambda f:f.__setitem__('extra',1),'RejectedBeforeMutation')
probe('null root request',lambda f:f.__setitem__('request',None),'RejectedBeforeMutation')
probe('wrong root boolean numeric',lambda f:f.__setitem__('target_existing',0),'RejectedBeforeMutation')
probe('unknown CAS enum',lambda f:f.__setitem__('ready_cas','Future'),'RejectedBeforeMutation')
probe('empty body native identity',lambda f:f['request']['body'].__setitem__('target_native_identity',{}),'RejectedBeforeMutation',True)
probe('empty lease identity',lambda f:f['request']['body'].__setitem__('native_lease_id',''),'RejectedBeforeMutation',True)
probe('both owner and ACK lost',lambda f:(f.__setitem__('owner_current',False),f.__setitem__('source_ack',False)),'DeliveryDeferred')
probe('unknown CAS precedes owner loss',lambda f:(f.__setitem__('authority_fixture_id','unknown-CAS'),f.__setitem__('ready_cas','Unknown'),f.__setitem__('owner_current',False)),'UncertainPublication')
probe('schema precedes target conflict',lambda f:(f.__setitem__('target_existing',True),f.__setitem__('owner_current','false')),'RejectedBeforeMutation')
# Exhaustively cover deletion/unknown/type at every schema object / leaf, not only one file.
def walk(node,path=()):
 yield path,node
 if node['type']=='object':
  for k,v in node['properties'].items():yield from walk(v,path+(k,))
def edit(f,path,op):
 node=f
 for k in path[:-1]:node=node[k]
 op(node,path[-1])
for path,node in walk(s):
 if path:
  probe('missing '+'.'.join(path),lambda f,p=path:edit(f,p,lambda n,k:n.pop(k)),'RejectedBeforeMutation')
  probe('wrong type '+'.'.join(path),lambda f,p=path:edit(f,p,lambda n,k:n.__setitem__(k,[])),'RejectedBeforeMutation')
 if node['type']=='object':
  def extra(f,p=path):
   target=f
   for k in p:target=target[k]
   target['unknown']=True
  probe('unknown field at '+('.'.join(path) or '$'),extra,'RejectedBeforeMutation')
new.append({'id':'CC-'+str(len(new)+1).zfill(3),'name':'coherent immutable domain variation B','fixture':variant,'expected':'VerifiedPublished'})
for cas in ['Verified','Unknown']:
 f=copy.deepcopy(base);f['ready_cas']=cas;f['authority_fixture_id']='coherent-A' if cas=='Verified' else 'unknown-CAS';new.append({'id':'CC-'+str(len(new)+1).zfill(3),'name':'coherent CAS premise '+cas,'fixture':f,'expected':'VerifiedPublished' if cas=='Verified' else 'UncertainPublication'})
write('targeted-fixtures.json',new)
print(json.dumps({'original':len(migrated),'closure':len(closure),'targeted':len(new),'authority_fixtures':len(authorities)},indent=2))


