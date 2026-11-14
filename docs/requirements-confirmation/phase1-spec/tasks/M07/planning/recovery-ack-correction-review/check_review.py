"""Independent bounded documentary review. Run python -B; writes only this directory."""
from pathlib import Path
import ast, copy, hashlib, html, json, re, runpy, subprocess
P=Path(__file__).resolve().parent
ROOT=P.parents[6]
C=P.parent/'recovery-ack-contract-correction'
O=P.parent/'recovery-ack-contract-proposal'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,v): (P/n).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
# Separate recursive schema interpreter, not the author's valid() implementation.
def admit(value, schema):
    if 'oneOf' in schema: return len([s for s in schema['oneOf'] if admit(value,s)])==1
    kind=schema['type']
    types={'object':dict,'array':list,'string':str,'null':type(None),'boolean':bool}
    if type(value) is not types[kind]: return False
    if 'const' in schema and value!=schema['const']: return False
    if 'enum' in schema and value not in schema['enum']: return False
    if kind=='object':
        return all(k in value for k in schema.get('required',[])) and all(k in schema['properties'] and admit(v,schema['properties'][k]) for k,v in value.items())
    if kind=='array': return len(value)<=schema.get('maxItems',10**9) and all(admit(v,schema['items']) for v in value)
    if kind=='string':
        if not schema.get('minLength',0)<=len(value)<=schema.get('maxLength',10**9): return False
        if 'pattern' in schema and re.fullmatch(schema['pattern'],value) is None: return False
        if schema.get('description','').startswith('Checked runtime') and int(value)>2**64-1: return False
    return True
def main():
    new=runpy.run_path(str(C/'document_oracle.py'))['evaluate']
    old=runpy.run_path(str(O/'check_documents.py'))['evaluate']
    base=read(C/'fixtures.json')[0]; proof=read(C/'immutable-proof.json'); schema=read(C/'request.schema.json')
    trace=[]; cases=[]
    # Generate fresh mutations from the parsed request/schema, never reuse author's negative list.
    def walk(value,s,path):
        cases.append((path,'replace',None))
        for bad in [True,42,[],{},'']:
            if not admit(bad,s): cases.append((path,'replace',bad))
        if s.get('type')=='object':
            for k in s['required']:
                cases.append((path+[k],'delete',None)); walk(value[k],s['properties'][k],path+[k])
        elif s.get('type')=='array' and value: walk(value[0],s['items'],path+[0])
    walk(base['request'],schema,[])
    cases.append(([],'absent_request',None))
    unique={json.dumps(c,sort_keys=True):c for c in cases}; cases=list(unique.values())
    for index,(path,action,value) in enumerate(cases):
        x=copy.deepcopy(base)
        if action=='absent_request': del x['request']
        elif not path: x['request']=value
        else:
            obj=x['request']
            for key in path[:-1]: obj=obj[key]
            if action=='delete': del obj[path[-1]]
            else: obj[path[-1]]=value
        assert not admit(x.get('request'),schema),(path,action,value)
        for available,root in [(True,'Transferred'),(False,'Unknown'),(False,'Deferred')]:
            x['proof_available']=available;x['root_state']=root
            before=copy.deepcopy(x); fbefore=copy.deepcopy(proof)
            result=new(x,proof)
            expected=dict(result='Rejected',state=before['state'],calls=dict(ack=0,retry=0,release=0),local_integrity_ready=True,published=False)
            assert result==expected and x==before and proof==fbefore
            trace.append(dict(id=f'IR-C-{index}-{available}-{root}',request=x.get('request'),input_state=before['state'],proof_available=available,root=root,expected=expected,observed=result))
    # Compound-invalid precedence, plus a poison body showing no body key access occurs.
    class Poison(dict):
        def __getitem__(self,k): raise AssertionError('body accessed before admission')
    x=copy.deepcopy(base);x['request']['body']=Poison();x['request']['context']=None;x['proof_available']=False;x['root_state']='Unknown'
    r=new(x,proof);assert r['result']=='Rejected' and r['calls']['ack']==0
    trace.append(dict(id='IR-C-compound-poison-body',observed=r))
    closures=[]
    for key in ['body','context']:
        x=copy.deepcopy(base);del x['request'][key]
        try: old(x,proof)
        except KeyError as e: original_error=str(e)
        else: raise AssertionError('Original counterexample no longer reproduces')
        r=new(x,proof);assert r['result']=='Rejected'
        closures.append(dict(missing=key,original_error=original_error,corrected=r,input_state=x['state']))
    preserved=[]
    for x in read(O/'fixtures.json')+read(C/'positive-cases.json'):
        schema_admitted=admit(x['request'],schema)
        a=old(copy.deepcopy(x),proof);b=new(copy.deepcopy(x),proof);assert a==b
        preserved.append(dict(id=x['id'],schema_admitted=schema_admitted,request=x['request'],expected=a,observed=b))
    # Exact remainder preservation and guard placement; no exception interception.
    oldtext=(O/'check_documents.py').read_text(); newtext=(C/'document_oracle.py').read_text()
    marker=" if not x['proof_available']:"
    assert oldtext[oldtext.index(marker):oldtext.index('\ndef main') if '\ndef main' in oldtext else len(oldtext)].rstrip()==newtext[newtext.index(marker):].rstrip()
    tree=ast.parse(newtext);assert not any(isinstance(n,(ast.Try,ast.ExceptHandler)) for n in ast.walk(tree))
    assert newtext.index("if not valid(q,")<newtext.index("b=q['body']")
    unchanged=['request.schema.json','response.schema.json','request-example.json','response-example.json','immutable-proof.json','fixtures.json']
    for name in unchanged: assert (C/name).read_bytes()==(O/name).read_bytes()
    malformed=copy.deepcopy(proof);malformed['index']['evidence']={}
    try: new(base,malformed)
    except KeyError: issuer_limit='KeyError reproduced; trusted structurally complete issuer fixture premise, NOT FIXED'
    else: raise AssertionError('RA-L3 premise changed')
    inputs={}
    for directory in [C,O]:
        seal=read(directory/'seal.json')['sha256']
        for name,digest in seal.items(): assert sha(directory/name)==digest
        inputs.update({str((directory/name).relative_to(ROOT)):sha(directory/name) for name in seal})
    pointers=read(C/'source-pointers.json');assert len(pointers)==32
    for row in pointers:
        if row['path']!='docs/board.json': assert sha(ROOT/row['path'])==row['sha256']
    authority=ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json'
    inventory=read(authority)['source_hashes'];assert len(inventory)==796
    for name,digest in inventory.items(): assert sha(ROOT/name)==digest
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();assert head=='5b709343a890503ebbe24a802e43cda5647df124'
    put('fixtures.json',[dict(path=p,action=a,value=v) for p,a,v in cases]);put('trace.json',trace);put('preservation.json',preserved);put('closures.json',closures);put('input-hashes.json',inputs)
    result=dict(reviewer='/root/m07_ack_correction_review',author='/root/m07_recovery_ack_correction',verdict='PASS_BOUNDED_CORRECTION_ONLY_PENDING_OWNER',head=head,inventory_head='31babe87a7ef1e40a0d4bedc523077e7a45d63ab',inventory_files=796,source_pointers=len(pointers),correction_seal_entries=len(read(C/'seal.json')['sha256']),proposal_seal_entries=len(read(O/'seal.json')['sha256']),fresh_negative_cases=len(cases),negative_evaluations=len(trace),preservation_cases=len(preserved),original_counterexamples_closed=2,guard_only_semantic_remainder=True,unchanged=unchanged,RA_L1='Ordinal options remain Owner pending; no selection or schema revision',RA_L2='Response relation/stateful replay/restart/atomic baseline response NOT PROVEN',RA_L3=issuer_limit,board_management=dict(sha256=sha(ROOT/'docs/board.json'),classification='Separate management diff, not 796 source authority; readonly'),module_pass=False,not_run=['native','build','product tests','valid RED/GREEN','full Draft2020-12','module acceptance'],next_action='Owner ordinal/protocol/role/hash and PH-G2..4 decisions; keep Yellow, no Skeleton or adoption')
    put('review.json',result)
    (P/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M07 correction independent review</title><h1>M07 bounded correction review</h1><p>PASS correction only, pending Owner. Yellow preserved. Documentary witnesses are not module acceptance.</p><pre>'+html.escape(json.dumps(result,indent=2))+'</pre><script type="application/json" id="module-review">'+json.dumps(result).replace('<','\\u003c')+'</script>',encoding='utf-8')
    put('seal.json',dict(status=result['verdict'],sha256={p.name:sha(p) for p in P.iterdir() if p.is_file() and p.name!='seal.json'}))
    print(json.dumps(result))
if __name__=='__main__': main()
