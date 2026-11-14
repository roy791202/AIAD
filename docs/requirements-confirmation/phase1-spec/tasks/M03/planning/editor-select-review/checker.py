"""Independent bounded document review; python -B checker.py. No author checker execution."""
from pathlib import Path
import sys,json,hashlib,copy,subprocess,html,re
P=Path(__file__).resolve().parent; C=P.parent/'editor-select-integration'; ROOT=Path.cwd()
sys.dont_write_bytecode=True
sys.path.insert(0,str(C))
from document_model import run,fresh,U,KEYS
from schema_eval import valid
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
put=lambda n,x:(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
hashfile=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
req=read(C/'request.schema.json');resp=read(C/'response.schema.json');provider=read(C/'provider-observation.schema.json')
authority=read(P.parents[2]/'M01/planning/s2-green/source-current.json')
products=authority['source_hashes'];assert len(products)==796
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='5b709343a890503ebbe24a802e43cda5647df124'
for n,h in products.items():assert hashfile(ROOT/n)==h,n
original=read(C/'preserved-inputs.json');assert len(original)==8
original_current={n:hashfile(ROOT/n) for n in original}
input_drift={n:{'candidate_snapshot':h,'review_entry':original_current[n]} for n,h in original.items() if original_current[n]!=h}
assert set(input_drift)<= {'docs\\board.json'},input_drift
candidate={p.name:hashfile(p) for p in C.iterdir() if p.is_file()}
for n,h in read(C/'artifact-hashes.json').items():assert candidate[n]==h,n
base=P.parents[2]/'integration-contract-revision-v3'
for kind in ('request','response'):assert read(C/(kind+'.schema.json'))==read(base/('h2-design_editor_select-'+kind+'.schema.json'))
assert set(req['required'])=={'binding_ref','expected_generation','expected_revision','node_id'} and req['additionalProperties'] is False
s=fresh();s['selection']='previous';r=dict(binding_ref=U,expected_generation='7',expected_revision='9',node_id='node-1')
p=dict(capture=copy.deepcopy(s['identity']),delivery=copy.deepcopy(s['identity']),role='ui-editor',origin='tauri://localhost',native_live=True,ready=True,outcome='Selected')
rows=[]
def probe(name,mut,code=None,calls=2,delivered=True):
 c=dict(before=copy.deepcopy(s),request=copy.deepcopy(r),provider=copy.deepcopy(p));mut(c)
 out=run(c,lambda v:valid(req,v));actual=None if out['response']['ok'] else out['response']['error']['code']
 assert actual==code,(name,out,code)
 assert len(out['calls'])==calls,(name,out)
 assert out['delivered'] is delivered,(name,out)
 assert valid(resp,out['response']),(name,out)
 expected=copy.deepcopy(c['before'])
 if code is None:expected['selection']=c['request']['node_id']
 assert out['state']==expected,(name,out)
 assert out['automatic_retry'] is False
 rows.append(dict(id=name,input=c,expected_code=code,expected_calls=calls,expected_delivery=delivered,observed=out,response_schema=True))
probe('null-clear-from-existing-highlight',lambda c:c['request'].update(node_id=None))
probe('stable-id-with-duplicate-human-label-premise',lambda c:c['before']['nodes'].append(dict(node_id='node-2',document_uuid=U)))
probe('label-is-not-stable-id',lambda c:c['request'].update(node_id='Human Label'),'IdentityConflict',1)
probe('caller-label-escape',lambda c:c['request'].update(window_label='editor-1'),'InvalidRequest',0)
for key in KEYS:
 probe('capture-'+key,lambda c,k=key:c['provider']['capture'].update({k:'8' if k=='generation' else 'other'}),'MissingBinding',1)
 probe('late-delivery-'+key,lambda c,k=key:c['provider']['delivery'].update({k:'8' if k=='generation' else 'other'}),None,2,False)
for key in ('ready','native_live'):
 for value in (0,1,None,[],{},'false'):
  probe('typed-'+key+'-'+repr(value),lambda c,k=key,v=value:c['provider'].update({k:v}),'ProofMismatch',1)
for key in ('capture','delivery','role','origin','outcome','ready','native_live'):
 probe('missing-provider-'+key,lambda c,k=key:c['provider'].pop(k),'DependencyNotReady',1,key!='delivery')
probe('closed-provider-extra',lambda c:c['provider'].update(extra=True),'DependencyNotReady',1)
probe('closed-capture-extra',lambda c:c['provider']['capture'].update(extra=True),'ProofMismatch',1)
probe('closed-delivery-extra',lambda c:c['provider']['delivery'].update(extra=True),'ProofMismatch',1,False)
for key in ('expected_generation','expected_revision'):
 for value in (True,1,None,'01','-1','1\n','18446744073709551616'):
  probe('request-'+key+'-'+repr(value),lambda c,k=key,v=value:c['request'].update({k:v}),'InvalidRequest',0)
probe('invalid-envelope-before-revoked',lambda c:(c['request'].update(expected_revision=True),c['provider'].update(native_live=False)),'InvalidRequest',0)
probe('typed-before-unauthorized',lambda c:c['provider'].update(role='ui-viewer',ready=1),'ProofMismatch',1)
probe('unauthorized-before-stale',lambda c:(c['provider'].update(native_live=False),c['request'].update(expected_revision='8')),'UnauthorizedCaller',1)
probe('generation-before-revision',lambda c:c['request'].update(expected_generation='8',expected_revision='8'),'StaleOwner',1)
probe('revision-before-not-ready',lambda c:(c['request'].update(expected_revision='8'),c['provider'].update(ready=False)),'StaleRevision',1)
probe('not-ready-before-membership',lambda c:(c['request'].update(node_id='absent'),c['provider'].update(ready=False)),'DependencyNotReady',1)
probe('revoked-before-select',lambda c:c['provider'].update(native_live=False),'UnauthorizedCaller',1)
for outcome in ('Rejected','selected','', 'UnknownFuture'):
 probe('unknown-outcome-'+repr(outcome),lambda c,v=outcome:c['provider'].update(outcome=v),'DependencyNotReady',2)
probe('main-current-native-owner',lambda c:c['provider'].update(role='main'))
probe('foreign-document-membership',lambda c:c['before']['nodes'][0].update(document_uuid='other'),'IdentityConflict',1)
probe('duplicate-id-clear',lambda c:(c['request'].update(node_id=None),c['before']['nodes'].append(copy.deepcopy(c['before']['nodes'][0]))),'IdentityConflict',1)
# Parsed patterns recorded verbatim; no double-escaping diagnosis from source rendering.
patterns={k:v.get('pattern') for k,v in req['properties'].items() if 'pattern'in v}
assert patterns['expected_revision']=='^(0|[1-9][0-9]*)$'
notes=[
 'Error precedence, unknown outcome mapping, delivery discard and no-auto-retry are proposals pending Owner, not conflicts with approved policy.',
 'Provider is closed and typed; role/origin/outcome are intentionally open strings with semantic authorization/outcome classification, not closed enums.',
 'Late exact-tuple mismatch discards response after modeled selection. Real revocation between capture/select is not representable: atomic provider premise, not demonstrated native behavior.',
 'Projection proves stable node_id plus document_uuid membership only; no label authority. Extra label metadata is outside the closed projection shape.',
 'All probes compare entire state, permitting selection change only on success; content/history/revision/dirty/baseline/pins/ACK preserved. FileCommitACK N/A.',
 'Historical authority metadata HEAD 31babe is distinguished from independently checked current HEAD 5b709343a890503ebbe24a802e43cda5647df124.'
]
result=dict(status='PASS_SCOPED_DOCUMENT_REVIEW_PENDING_OWNER',author='/root/m03_editor_select_packet',reviewer='/root/m03_editor_select_review',command='design_editor_select',independent_probes=len(rows),product_hashes=len(products),original_inputs=len(original),candidate_files=len(candidate),findings=[],management_snapshot_drift=input_drift,notes=notes,parsed_regex=patterns,product_tests='NOT RUN',native='NOT RUN',build='NOT RUN',valid_RED='NOT RUN',full_Draft2020='NOT RUN',FileCommitACK='N/A',owner='PENDING',module_complete=False)
put('input-drift.json',input_drift);put('fixtures.json',rows);put('results.json',result);put('candidate-hashes.json',candidate);put('original-hashes.json',original);put('traceability.json',[dict(probe=x['id'],contract='Exact native identity; closed typed admission; ephemeral selection only',result='PASS',evidence='fixtures.json') for x in rows])
(P/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Independent Editor Select Review</title><style>body{max-width:1100px;margin:3rem auto;font:16px system-ui}pre{white-space:pre-wrap}</style><h1>Independent Editor Select Review</h1><p>PASS, bounded document review; pending Owner. Yellow parent unchanged.</p><h2>Scope and limitations</h2><pre>'+html.escape(json.dumps(result,indent=2))+'</pre><h2>Independent counterexamples and observations</h2><pre>'+html.escape(json.dumps(rows,indent=2))+'</pre><script type="application/json" id="module-spec">'+json.dumps(result).replace('<','\\u003c')+'</script></html>',encoding='utf-8')
assert candidate=={p.name:hashfile(p) for p in C.iterdir() if p.is_file()}
for n,h in original_current.items():assert hashfile(ROOT/n)==h,n
put('artifact-hashes.json',{p.name:hashfile(p) for p in P.iterdir() if p.is_file() and p.name not in ('artifact-hashes.json','seal.json')})
put('seal.json',dict(status='SEALED_ONE_COMMAND_INDEPENDENT_DOCUMENT_REVIEW',probes=len(rows),product_hashes=796,original_inputs=8,candidate_files=len(candidate),owner='PENDING'))
print(json.dumps(result))


