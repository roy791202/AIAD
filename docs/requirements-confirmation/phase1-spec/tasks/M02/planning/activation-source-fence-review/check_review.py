"""Independent bounded document probes. Does not execute author main/22 cases."""
from pathlib import Path
import json, hashlib, copy, importlib.util, subprocess, html
R=Path(__file__).resolve().parent
W=R.parents[6]
P=R.parent/'activation-source-fence-handoff'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(R/n).write_text(json.dumps(v,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
sp=importlib.util.spec_from_file_location('reviewed_oracle',P/'check_packet.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
base=read(P/'fixtures.json')['cases'][0]['observation'];schema=read(P/'schema.json');cases=[]
def probe(name,path,value,expect,group):
 o=copy.deepcopy(base);node=o
 for part in path[:-1]:node=node[part]
 if value=='__DELETE__':del node[path[-1]]
 else:node[path[-1]]=value
 before=copy.deepcopy(o)
 try:m.validate_schema(o,schema);valid=True
 except Exception as e:valid=False
 try:actual=m.oracle(o) if valid else 'SchemaRejected'
 except Exception as e:actual=type(e).__name__
 cases.append(dict(id=name,group=group,mutation_path=path,expectation=expect,actual=actual,observation=o,observation_unchanged=o==before,calls=['validate_schema','oracle' if valid else 'oracle NOT CALLED'],product_calls=[],verdict='PASS' if actual in expect else 'COUNTEREXAMPLE'))
reject=['SchemaRejected','DependencyNotReady','UnverifiedOutcome','SourceFenceInvalid','DesignSaveRequired','StaleOwnerBeforeCAS']
probe('R01-request-preview-body',['request','preview_digest'],'unbound-preview',reject,'F1')
probe('R02-unknown-cas-enum',['cas','outcome'],'unrecognized', ['SchemaRejected'],'F2')
probe('R03-malformed-sha',['approved_refs',0,'content_hash'],'not-a-sha',['SchemaRejected'],'F2')
probe('R04-missing-owner-field',['owner_captured','session_id'],'__DELETE__',['SchemaRejected'],'guard')
probe('R05-unknown-body-field',['request','forged_authority'],True,['SchemaRejected'],'guard')
probe('R06-approved-revision',['approved_refs',0,'revision'],'999',reject,'F1')
probe('R07-approved-hash',['approved_refs',0,'content_hash'],'0'*64,reject,'F1')
probe('R08-M04-issuer',['design_saved_proof','issuer'],'M99',reject,'F1')
probe('R09-seal-generation',['seal','generation_id'],'b'*32,reject,'F1')
probe('R10-seal-manifest',['seal','manifest_digest'],'9'*64,reject,'F1')
probe('R11-seal-directory',['seal','directory_identity'],'different-dir',reject,'F1')
for i in range(3):
 o=copy.deepcopy(base['sources']);o[i]['captured']['project_uuid']='other-project';o[i]['held']['project_uuid']='other-project'
 probe('R12-source-owner-'+str(i),['sources'],o,reject,'F1')
probe('R13-owner-preCAS',['owner_before_cas','session_id'],'replacement',['StaleOwnerBeforeCAS'],'boundary')
probe('R14-owner-delivery',['owner_delivery','session_id'],'replacement',['ActivatedDeliveryDeferred'],'boundary')
probe('R15-unknown-CAS',['cas','outcome'],'unknown',['UncertainPublication'],'boundary')
probe('R16-proofloss',['cas','receipt','issuer_record_present'],False,['UnverifiedOutcome'],'boundary')
probe('R17-no-auto-retry',['automatic_retry_count'],1,['ForbiddenAutomaticRetry'],'boundary')
probe('R18-no-hidden-save',['implicit_save_calls'],1,['ForbiddenImplicitSave'],'boundary')
for result in ['Busy','defer','success']:
 probe('R19-held-source-'+result,['mutation_attempt'],dict(attempted=True,result=result,changed=False),['GenerationActivated'] if result!='success' else ['SourceFenceInvalid'],'boundary')
probe('R20-mutation-changed',['mutation_attempt'],dict(attempted=True,result='Busy',changed=True),['SourceFenceInvalid'],'boundary')
for section,key in [('native','provider_verified'),('native','identity_verified'),('projector','verified'),('template','golden14_verified'),('template','transitive_lock_verified')]:
 probe('R21-gate-'+key,[section,key],False,['DependencyNotReady'],'gate')
probe('R22-seal-only',['cas','outcome'],'rejected',['VersionSealedNotActivated'],'boundary')
probe('R23-unsaved-design',['design_saved_proof','verified'],False,['DesignSaveRequired'],'boundary')
spec=read(P/'module-spec.json');pointers=[]
for row in spec['proof_mapping']:
 path,ptr=row['source'].split('#');v=read(P/path)
 for part in ptr.strip('/').split('/'):v=v[part]
 pointers.append(dict(field=row['field'],source=row['source'],body=v,body_sha256=hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest(),comparison='Source body resolved independently; prose mapping does not establish field consumption'))
inventory=read(W/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
drift=[p for p,h in inventory['source_hashes'].items() if not (W/p).is_file() or sha(W/p)!=h]
manifest=read(P/'artifact-hashes.json');seal=read(P/'seal.json');inputs=read(P/'sources.json')['sources']
checks=dict(author_artifact_count=len(manifest),author_artifact_drift=[n for n,h in manifest.items() if sha(P/n)!=h],author_seal_manifest_match=seal['manifest_sha256']==sha(P/'artifact-hashes.json'),inventory_count=len(inventory['source_hashes']),product_drift=drift,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip(),historical_inventory_head=inventory['head'],source_hash_drift=[n for n,h in inputs.items() if sha(W/n)!=h],owner_choices_pending=all(c['status']=='PENDING_OWNER' for c in spec['owner_choices']))
write('fixtures.json',cases);write('source-comparisons.json',pointers);write('input-checks.json',checks)
result=dict(reviewer='/root/m02_activation_handoff_review',author='/root/m02_activation_handoff_packet',status='CHANGES_REQUIRED_DOCUMENT_ORACLE',probes=len(cases),passed=sum(c['verdict']=='PASS' for c in cases),counterexamples=sum(c['verdict']=='COUNTEREXAMPLE' for c in cases),nonmutation=all(c['observation_unchanged'] for c in cases),original_22_rerun=False,scope='Document consistency and synthetic observations only; no native provider identity/atomicity proof',findings=[dict(id='F1',severity='P2',title='Mapped proof and request bodies are not bound by the executable oracle',detail='Request values, approved revision/hash, M04 issuer, seal generation/manifest/directory and source-to-owner project binding can change while result remains GenerationActivated. This is a document evidence gap, not a demonstrated native production defect. Schema type acceptance and a verified boolean cannot demonstrate exact field consumption. Add independently checked expected source/preview/seal bodies and bind them; pending Owner choices stay pending.'),dict(id='F2',severity='P2',title='Closed schema and validator omit enum and digest-format guards',detail='Unknown CAS outcome falls through to confirmed receipt and returns GenerationActivated; malformed approved hash passes schema. Both fields have only string/minLength constraints; the validator also lacks enum/pattern support. Add declared closed enums/formats plus recursive enforcement before oracle; fail closed without calls/mutation.')],gates=spec['gates'],module_PASS=False,next_action='Author corrects only document oracle/fixtures/schema coverage, then fresh independent bounded re-review; Owner adoption and provider/native/projector/golden14/transitive-lock gates remain required.',checks=checks)
write('review.json',result)
(R/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>M02 independent activation handoff review</title><style>body{max-width:1100px;margin:30px auto;font:16px/1.6 system-ui}pre{white-space:pre-wrap}h1{color:#965200}</style><h1>CHANGES_REQUIRED — document oracle only</h1><p>Independent reviewer /root/m02_activation_handoff_review; author /root/m02_activation_handoff_packet. Parent Yellow unchanged. No module PASS. Native, build, product, valid RED and full Draft NOT RUN.</p><p>Fresh boundary probes and full observations/calls/results: <a href="fixtures.json">fixtures</a>. Source pointer/body comparison: <a href="source-comparisons.json">comparisons</a>. <a href="check_review.py">reproduce checker</a>.</p><pre>'+html.escape(json.dumps(result,indent=2))+'</pre><script type="application/json" id="review-spec">'+json.dumps(result).replace('<','\\u003c')+'</script></html>',encoding='utf-8')
files=['check_review.py','fixtures.json','source-comparisons.json','input-checks.json','review.json','index.html'];write('artifact-hashes.json',{n:sha(R/n) for n in files});write('seal.json',dict(scope='Bounded independent document review only',artifact_count=len(files),manifest_sha256=sha(R/'artifact-hashes.json'),status=result['status']))
print(json.dumps({k:result[k] for k in ['status','probes','passed','counterexamples','nonmutation','checks']},indent=2))
