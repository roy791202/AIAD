"""Read-only author check. Run python -B check_handoff.py. Not independent review."""
import hashlib, importlib.util, json, pathlib
P=pathlib.Path(__file__).resolve().parent
ROOT=P.parents[6]
def read(n):return json.loads((P/n).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
manifest=read('artifact-hashes.json')
assert all(sha(P/n)==v for n,v in manifest.items())
assert sha(P/'artifact-hashes.json')==read('seal.json')['manifest_sha256']
inputs=read('source-input-hashes.json');assert all(sha(ROOT/n)==v for n,v in inputs.items())
rows=read('command-coverage.json');assert len(rows)==13 and len({r['command'] for r in rows})==13
assert all(r['review_evidence'] and r['response_root_constants'] for r in rows)
trace=read('original-62-trace.json');assert len(trace)==62
assert {r['original']['bdd'] for r in trace}=={'M03-H2-B%03d'%n for n in range(1,63)}
assert len(read('bdd-categories.json'))==12
B=P.parent;w=read('new-sequence-witness.json');c=w['fixture']
refresh=module('verify_refresh',B/'viewer-refresh-integration/document_model.py')
schema=module('verify_schema',B/'viewer-refresh-integration/schema_eval.py')
close=module('verify_close',B/'viewer-close-integration/document_model.py')
request=json.loads((B/'viewer-refresh-integration/request.schema.json').read_text(encoding='utf-8'))
response=json.loads((B/'viewer-refresh-integration/response.schema.json').read_text(encoding='utf-8'))
validators=[lambda x:schema.valid(request,x),lambda x:schema.valid({'$defs':response['$defs'],'$ref':'#/$defs/Preview'},x),lambda x:schema.valid({'$defs':response['$defs'],'$ref':'#/$defs/Error'},x)]
out,after,calls=refresh.refresh(c,*validators)
assert (out,after,calls)==tuple(w['steps'][0][k] for k in ['response','after','calls'])
old=dict(c,before=after)
out2,after2,calls2=refresh.refresh(old,*validators)
assert (out2,after2,calls2)==tuple(w['steps'][1][k] for k in ['response','after','calls'])
result=close.close({'before':after,'request':{'preview_session':after['preview_session']},'provider':c['provider']},lambda x:True,lambda x:True)
assert result==w['steps'][2]['result']
assert read('module-spec.json')['health'].startswith('Yellow')
print(json.dumps({'status':'PASS_AUTHOR_READ_ONLY_CHECK','artifacts':len(manifest),'source_inputs':len(inputs),'commands':13,'original_BDD':62,'sequence_steps':3,'independent_review':'NOT RUN','product_native_build_RED':'NOT RUN'}))
