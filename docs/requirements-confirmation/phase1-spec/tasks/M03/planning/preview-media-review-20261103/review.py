"""Independent bounded document oracle. Never executes product or historical suites."""
import copy, hashlib, html, json, pathlib, re, subprocess, datetime
ROOT=pathlib.Path('D:/AIAD'); OUT=pathlib.Path(__file__).resolve().parent
BASE=OUT.parent/'preview-media-candidate-20261103'
def read(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def write(n,v): (OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
c=read(BASE/'candidate.json'); refs=[]
def walk(o):
    if isinstance(o,dict):
        if {'path','sha256','pointer'} <= o.keys(): refs.append(o)
        for v in o.values(): walk(v)
    elif isinstance(o,list):
        for v in o: walk(v)
walk(c)
bindings=[]
for r in refs:
    p=ROOT/r['path']; actual=sha(p); ptr=r['pointer']; valid=True
    if ptr.startswith('/'):
        try:
            value=read(p)
            for token in ptr.split('/')[1:]:
                token=token.replace('~1','/').replace('~0','~'); value=value[int(token)] if isinstance(value,list) else value[token]
        except (KeyError,ValueError,IndexError): valid=False
    elif ptr.startswith('lines:'): valid=ptr=='lines:210..334; next function line335'
    bindings.append({**r,'actual_sha256':actual,'pointer_resolves':valid,'status':'PASS' if actual==r['sha256'] and valid else 'DRIFT'})
def semantic(x):
    assert x['approval'] is None and x['owner_exact_selection'] is None
    assert [r['id'] for r in x['rows']]==['MM%02d'%i for i in range(1,9)]
    for r in x['rows']:
        assert r['support']=='UNSELECTED_NOT_APPROVED'
        assert all(r[k] is None for k in ['decoder_sdk','version','limits','approved_media_formats','format_decision','thresholds','owner_exact_selection'])
        assert r['oracle']['status']=='PLANNED_NOT_RUN'
        assert r['current_static_fact'] and r['planned_capability'] and r['source_refs']
    assert x['preview_boundary']['function_span']==[210,334] and x['preview_boundary']['next_function_line']==335
    assert x['module_complete'] is False
semantic(c)
probes=[]
mutations=[('false_owner_approval',lambda x:x.update(approval='APPROVED')),('invented_codec',lambda x:x['rows'][3].update(decoder_sdk='INVENTED')),('duplicate_dimension',lambda x:x['rows'][7].update(id='MM01')),('native_evidence_laundering',lambda x:x['rows'][0]['oracle'].update(status='PASS')),('wrong_source_function_seam',lambda x:x['preview_boundary'].update(function_span=[210,342]))]
for name,mut in mutations:
    x=copy.deepcopy(c);mut(x)
    try: semantic(x); rejected=False
    except AssertionError: rejected=True
    probes.append({'id':name,'expected':'REJECT','actual':'REJECT' if rejected else 'ACCEPT','pass':rejected,'mutation':'in-memory candidate copy only'})
for name,field,value in [('source_hash_perturbation','sha256','0'*64),('source_pointer_perturbation','pointer','/rows/999')]:
    r=copy.deepcopy(c['rows'][0]['source_refs'][0]);r[field]=value
    rejected=sha(ROOT/r['path'])!=r['sha256']
    if not rejected:
        try: read(ROOT/r['path'])['rows'][999]
        except IndexError: rejected=True
    probes.append({'id':name,'expected':'REJECT','pass':rejected,'mutation':'in-memory binding only'})
inv=read(ROOT/c['authority']['product_inventory']['path']); mismatches=[p for p,h in inv['source_hashes'].items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
commands=[]
checker='docs/requirements-confirmation/phase1-spec/tasks/M01/planning/remaining-action-oracle-correction-20261103/check.py'
for flag in ['--packet','--deliverables']:
    run=subprocess.run(['python','-B',checker,flag,'M03'],cwd=ROOT,text=True,capture_output=True)
    commands.append({'command':['python','-B',checker,flag,'M03'],'exit':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
h=(BASE/'index.html').read_text(encoding='utf-8'); embedded=re.search(r'<script[^>]*id="module-spec"[^>]*>(.*?)</script>',h,re.S)
parity=bool(embedded and json.loads(embedded.group(1))==c)
write('bindings.json',bindings)
write('probes.json',probes)
write('results.json',{'reviewer':'/root/m03_preview_media_review','author':c['author'],'scope':'bounded document review only','source_ref_count':len(c['source_refs']),'binding_occurrences':len(bindings),'unique_source_paths':len({r['path'] for r in bindings}),'bindings_with_drift':[b for b in bindings if b['status']!='PASS'],'product_authority_count':len(inv['source_hashes']),'product_hash_mismatches':mismatches,'HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'HEAD_diff_from_historical':subprocess.check_output(['git','diff','--name-only',inv['head'],'HEAD'],cwd=ROOT,text=True).splitlines(),'HTML_embedded_parity':parity,'document_check_commands':commands,'historical_PASS_suites':'NOT RERUN','product_native_runtime_decode_actual_build_RED_GREEN':'NOT RUN','mutation_probes_pass':all(p['pass'] for p in probes)})
print(json.dumps({'bindings':len(bindings),'drift':[b['path'] for b in bindings if b['status']!='PASS'],'parity':parity,'product_mismatches':mismatches,'checks':[x['exit'] for x in commands]}))
