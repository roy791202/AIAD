"""Independent bounded document review; no author main/batch rerun."""
from pathlib import Path
import copy,json,hashlib,importlib.util,subprocess,html
R=Path(__file__).resolve().parent; W=R.parents[6]; P=R.parent/'activation-source-fence-correction'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(R/n).write_text(json.dumps(v,indent=2)+'\n',encoding='utf8')
s=importlib.util.spec_from_file_location('candidate',P/'check_packet.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
base=read(P/'fixtures.json')[0]['input']; schema=read(P/'schema.json'); records=read(P/'immutable-records.json'); probes=[]
def run(name,p,expected,rs=None,sc=None):
 before=copy.deepcopy(p); r=m.evaluate(p,records=rs,schema=sc)
 probes.append(dict(id=name,input=p,records=rs,result=r,expected=expected,unchanged=p==before,passed=r['result'] in expected))
def change(name,path,value,expected):
 p=copy.deepcopy(base);n=p['observation']
 for k in path[:-1]:n=n[k]
 if value=='DELETE':del n[path[-1]]
 else:n[path[-1]]=value
 run(name,p,expected)
reject=['SchemaRejected','DependencyNotReady','DesignSaveRequired','SourceFenceInvalid','VersionSealedNotActivated']
for field in ['plan_id','operation_id']:change('request-'+field,['request',field],'00000000-0000-4000-8000-000000000098',reject)
change('request-preview',['request','preview_digest'],'e'*64,reject)
for field,value in [('project_uuid','00000000-0000-4000-8000-000000000098'),('owner_generation',99)]:change('owner-'+field,['owner_captured',field],value,reject+['StaleOwnerBeforeCAS'])
for field,value in [('module','M88'),('revision',998),('content_hash','e'*64)]:change('approved-'+field,['approved_refs',0,field],value,reject)
change('saved-issuer',['design_saved_proof','issuer'],'M88',reject)
for field,value in [('generation_id','e'*32),('manifest_digest','e'*64),('directory_identity','other-directory')]:change('seal-'+field,['seal',field],value,reject)
for i in range(3):
 change('source-held-'+str(i),['sources',i,'held','revision_or_epoch'],998,reject)
 change('source-captured-'+str(i),['sources',i,'captured','revision_or_epoch'],998,reject)
for name,path,value in [('CAS-enum',['cas','outcome'],'surprise'),('digest',['approved_refs',0,'content_hash'],'g'*64),('UUID',['request','plan_id'],'bad'),('u64-low',['owner_captured','owner_generation'],-1),('u64-high',['owner_captured','owner_generation'],2**64),('u64-bool',['owner_captured','owner_generation'],True),('missing',['request','plan_id'],'DELETE'),('type',['request','plan_id'],12),('closure',['request','unexpected'],True)]:change(name,path,value,['SchemaRejected'])
for keyword in ['not','format','oneOf','$ref']:
 sc=copy.deepcopy(schema);sc['properties']['observation']['properties']['request'][keyword]=True
 run('unsupported-recursive-'+keyword,copy.deepcopy(base),['SchemaRejected'],sc=sc)
# Fresh coherent record: all private UUIDs/digests transformed consistently, no frozen expected fixture.
def transform(x):
 if isinstance(x,dict):return {k:transform(v) for k,v in x.items()}
 if isinstance(x,list):return [transform(v) for v in x]
 if isinstance(x,str) and len(x)==64 and all(c in '0123456789abcdef' for c in x):return hashlib.sha256(x.encode()).hexdigest()
 if isinstance(x,str) and len(x)==36 and x.count('-')==4:return '12345678'+x[8:]
 return x
p=transform(copy.deepcopy(base));p['fixture_id']='fresh-independent';rs={'fresh-independent':transform(copy.deepcopy(records[base['fixture_id']]))};run('fresh-consistent-authority',p,['GenerationActivated'],rs=rs)
# Twelve exact closure cases are checked, without rerunning 54+4 author batch.
closures=[]
for c in read(P/'closures.json'):
 r=m.evaluate(c['input']);closures.append(dict(id=c['id'],before=c['before'],after=r,allowed_after=c['allowed_after'],pass_closure=r['result'] in c['allowed_after'] and r['result']!='GenerationActivated'))
legacy=read(P/'legacy-fixtures.json')['cases'];canonical=read(P/'fixtures.json')
migration=dict(raw_count=len(legacy),canonical_count=len(canonical),same_ids=[x['id'] for x in legacy]==[x['id'] for x in canonical],same_expected=[x['expected'] for x in legacy]==[x['expected'] for x in canonical],raw_executed=False,canonical_executed=False,representation=read(P/'module-spec.json')['proposals'],note='22 historical output expectations retained; canonical UUID/u64 inputs are proposed migration, not unchanged legacy schema. R09-R11 VersionSealedNotActivated pending Owner, not amended approved tests.')
inv=read(W/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json');manifest=read(P/'artifact-hashes.json');sources=read(P/'sources.json')['read_only_sources']
checks=dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip(),historical_inventory_head=inv['head'],inventory_count=len(inv['source_hashes']),product_drift=[n for n,h in inv['source_hashes'].items() if sha(W/n)!=h],author_payload_count=len(manifest),author_payload_drift=[n for n,h in manifest.items() if sha(P/n)!=h],author_seal=read(P/'seal.json')['manifest_sha256']==sha(P/'artifact-hashes.json'),source_drift=[n for n,h in sources.items() if sha(W/n)!=h],board_management_diff='Reported separately; never product inventory drift')
guarded=all(x['result']['calls']==['validate_schema'] and x['result']['mutation'] is False for x in probes if x['expected']==['SchemaRejected'])
passed=all(x['passed'] and x['unchanged'] for x in probes) and all(c['pass_closure'] for c in closures) and guarded and not checks['product_drift'] and not checks['author_payload_drift']
result=dict(status='PASS_DOCUMENT_CORRECTION_PENDING_OWNER' if passed else 'CHANGES_REQUIRED_DOCUMENT_ORACLE',reviewer='/root/m02_activation_correction_review',author='/root/m02_activation_oracle_correction',fresh_probes=len(probes),passed=sum(x['passed'] for x in probes),closure_count=len(closures),guards_before_lookup=guarded,checks=checks,migration=migration,gates=read(P/'module-spec.json')['gates'],module_PASS=False,next_action='Owner adoption of representation/body/error policy; missing provider/native identity and atomicity, golden14/full lock/projector gates before Skeleton. Native/build/product/validRED/fullDraft NOT RUN.')
write('fixtures.json',probes);write('closure-trace.json',closures);write('review.json',result)
(R/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M02 correction independent review</title><h1>'+result['status']+'</h1><p>Document evidence only. Yellow retained. No module PASS. Native/build/product/valid RED/full Draft NOT RUN.</p><p><a href="fixtures.json">New complete probes and calls</a> · <a href="closure-trace.json">12 closure trace</a> · <a href="check_review.py">Checker</a></p><pre>'+html.escape(json.dumps(result,indent=2))+'</pre><script type="application/json" id="review-spec">'+json.dumps(result).replace('<','\\u003c')+'</script>',encoding='utf8')
write('input-hashes.json',{str(p.relative_to(W)):sha(p) for p in [P/n for n in manifest]+[P/'artifact-hashes.json',P/'seal.json',W/'AGENTS.md',W/'docs/board.json',R.parent/'current-state.json']})
files=['check_review.py','fixtures.json','closure-trace.json','review.json','index.html','input-hashes.json'];write('artifact-hashes.json',{n:sha(R/n) for n in files});write('seal.json',dict(artifact_count=len(files),manifest_sha256=sha(R/'artifact-hashes.json'),status=result['status']))
print(json.dumps(result,indent=2))
