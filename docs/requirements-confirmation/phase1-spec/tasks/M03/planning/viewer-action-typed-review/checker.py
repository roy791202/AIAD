"""Independent bounded DOCUMENT review. Run python -B checker.py; no native proof."""
import copy, hashlib, html, importlib.util, itertools, json, pathlib, subprocess, sys
sys.dont_write_bytecode = True
P = pathlib.Path(__file__).resolve().parent
ROOT = P.parents[6]
C = P.parent / 'viewer-action-typed-correction'
O = P.parent / 'viewer-action-integration'
V = P.parent / 'viewer-action-review'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n, x): (P/n).write_text(json.dumps(x, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def module(name,p):
    spec=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def main():
    model=module('independent_target',C/'document_model.py')
    sys.modules['document_model']=model.original
    schema=module('bounded_schema_reader',O/'checker.py')
    response_schema=load(O/'response.schema.json')
    snapshots={str(p.relative_to(ROOT)):sha(p) for d in (C,O,V) for p in d.iterdir() if p.is_file()}
    for p in (ROOT/'AGENTS.md',ROOT/'docs/board.json',P.parent/'current-state.json'):
        snapshots[str(p.relative_to(ROOT))]=sha(p)
    checks=[]; fixtures=[]; traces=[]
    def record(label, condition):
        assert condition,label
        checks.append({'id':label,'status':'PASS'})
    def invoke(label,c,expected):
        before=copy.deepcopy(c)
        got=model.intent(c)
        record(label,got==expected and c==before and schema.valid(response_schema,got[0]))
        fixtures.append({'id':label,'input':before,'expected':expected,'actual':got,'response_schema_valid':True})
        return got
    def reject(label,c,dep):
        return invoke(label,c,({'ok':False,'error':{'code':'DependencyNotReady','details':{'dependency':dep}},'replayed':False},copy.deepcopy(c['before']),[]))
    prior=load(O/'fixtures.json'); base=copy.deepcopy(prior[0])
    # Verify candidate seal before executing any of its model behavior.
    manifest=load(C/'artifact-hashes.json')
    record('candidate-seal',sha(C/'artifact-hashes.json')==load(C/'seal.json')['manifest_sha256'])
    for n,h in manifest.items(): record('candidate-hash/'+n,sha(C/n)==h)
    for n in ('request.schema.json','response.schema.json'):
        record('schema-bytewise/'+n,(C/n).read_bytes()==(O/n).read_bytes())
    for c in prior:
        expected=(c['expected'],c['expected_after'],c['expected_calls'])
        got=model.intent(c)
        record('prior-response-state/'+c['id'],got[:2]==expected[:2])
        if got[2]!=expected[2]: traces.append({'id':c['id'],'before':expected[2],'after':got[2]})
    for row in load(V/'new-fixtures.json'):
        got=model.intent(row['input'])
        record('restricted-review-response-state/'+row['id'],got[:2]==(row['actual'],row['after']))
        if got[2]!=row['calls']: traces.append({'id':'review/'+row['id'],'before':row['calls'],'after':got[2]})
    claimed=load(C/'prior-trace-changes.json')
    record('nineteen-explicit-trace-proposals',len(traces)==19 and {x['id'] for x in traces}=={x['id'] for x in claimed} and all(x['after']==[] for x in traces) and all('PROPOSED_PENDING_OWNER' in x['reason'] for x in claimed))
    for t in traces:
        match=next(x for x in claimed if x['id']==t['id'])
        record('exact-trace/'+t['id'],t['before']==match['before_calls'] and t['after']==match['after_calls'])
    for c in load(C/'new-fixtures.json'):
        got=model.intent(c)
        record('author-fixture/'+c['id'],got==(c['expected'],c['expected_after'],c['expected_calls']))
    # Independently replay exactly the prior diagnostic payloads; no reinterpretation of prior PASS.
    for d in load(V/'provider-premise-diagnostics.json'):
        c=copy.deepcopy(base);c['premises'][d['premise']]=d['value']
        old=model.original.intent(c)
        record('diagnostic-before/'+d['premise'],old[0]==d['result'] and old[2]==d['calls'] and old[1]!=c['before'])
        reject('diagnostic-after/'+d['premise'],c,'M01_NATIVE_IDENTITY')
    # Distinct cross-product: each malformed layer dominates multiple simultaneous ordinary errors.
    faults=[('identity','M01_NATIVE_IDENTITY'),('codec','C1_CODEC'),('capability','M04_OWNER_INTEGRATION')]
    ordinary=['bad-request','untrusted','closed','stale','sequence','overflow']
    for (fault,dep),other in itertools.product(faults,ordinary):
        c=copy.deepcopy(base)
        if fault=='identity':c['premises']['consumer_matches']=1
        if fault=='codec':c['premises']['number_canonical']='1\n'
        if fault=='capability':c['nodes']['combo']['items_valid']=0
        if other=='bad-request':c['request']={'unexpected':True}
        if other=='untrusted':c['premises']['trusted_local']=False
        if other=='closed':c['before']['closed']=True
        if other=='stale':c['premises']['observed_revision']='8'
        if other=='sequence':c['request']['sequence']='0'
        if other=='overflow':c['before']['sequence']=c['request']['sequence']='18446744073709551615'
        reject('independent/precedence/'+fault+'/'+other,c,dep)
    for i,identity in enumerate((False,True)):
        c=copy.deepcopy(base);c['nodes']['button']['allowed_actions']=[None];c['premises']['number_error']=''
        if identity:c['premises']['observed_generation']='02'
        reject('independent/combined-layer/'+str(i),c,'M01_NATIVE_IDENTITY' if identity else 'C1_CODEC')
    # Invalid unrelated node still rejects before native read, including foreign dict key types.
    for value in (False,1,0.0,None,{},['Activate'],{'type':'Button','scope':'ui','allowed_actions':['activate']}):
        c=copy.deepcopy(base);c['nodes']['unrequested']=value
        reject('independent/foreign-node/'+repr(value),c,'M04_OWNER_INTEGRATION')
    for key in ('',0,False,None):
        c=copy.deepcopy(base);c['nodes'][key]=copy.deepcopy(c['nodes']['button'])
        reject('independent/node-key/'+repr(key),c,'M04_OWNER_INTEGRATION')
    for field in ('trusted_local','consumer_matches','owner_present','document_matches','provider_ready','number_ready','number_accepted'):
        for value in (0.0,1.0,'true','FALSE'):
            c=copy.deepcopy(base);c['premises'][field]=value
            reject('independent/exact-bool/'+field+'/'+repr(value),c,'M01_NATIVE_IDENTITY')
    for value in ('None','consumer\x00','revision\r','NONE',' generation',42,False):
        c=copy.deepcopy(base);c['premises']['delivery_change']=value
        reject('independent/delivery-enum/'+repr(value),c,'M01_NATIVE_IDENTITY')
    for value in (None,False,2,'selectitem','SetText\n'):
        c=copy.deepcopy(base);c['nodes']['button']['allowed_actions']=['Activate',value]
        reject('independent/action-enum/'+repr(value),c,'M04_OWNER_INTEGRATION')
    # All typed booleans, optional U64 observations, false branches and open compatibility values preserve originals.
    for field in model.BOOLS:
        c=copy.deepcopy(base);c['premises'][field]=False
        invoke('independent/legal-false/'+field,c,model.original.intent(c))
    for value in model.CHANGES:
        c=copy.deepcopy(base);c['premises']['delivery_change']=value
        if value=='revision':c['premises']['delivery_observed_revision']='8'
        invoke('independent/legal-delivery/'+value,c,model.original.intent(c))
    for field,value in [('scope','future-scope'),('scope',None),('type','FutureWidget'),('allowed_actions',[]),('allowed_actions',['Activate','Activate'])]:
        c=copy.deepcopy(base);c['nodes']['button'][field]=value
        invoke('independent/legal-capability/'+field+'/'+repr(value),c,model.original.intent(c))
    number=next(c for c in prior if c['request'].get('action')=='SetNumber' and c['expected'].get('ok'))
    for field in ('number_ready','number_accepted'):
        c=copy.deepcopy(number);c['premises'][field]=False
        invoke('independent/legal-number-false/'+field,c,model.original.intent(c))
    for gen,rev in [('0','7'),('2','0'),('18446744073709551615','18446744073709551615')]:
        c=copy.deepcopy(base);c['premises'].update(observed_generation=gen,observed_revision=rev)
        invoke('independent/legal-stale/'+gen+'/'+rev,c,model.original.intent(c))
    for value in ('0','18446744073709551615'):
        c=copy.deepcopy(base);c['premises']['delivery_observed_revision']=value
        invoke('independent/legal-unused-optional/'+value,c,model.original.intent(c))
    authority=load(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
    record('authority-count-796',len(authority['source_hashes'])==796)
    for path,h in authority['source_hashes'].items(): record('product-preservation/'+path,sha(ROOT/path)==h)
    for path,h in snapshots.items(): record('review-input-unchanged/'+path,sha(ROOT/path)==h)
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    record('current-head',head=='5b709343a890503ebbe24a802e43cda5647df124')
    review={'status':'PASS_DOCUMENT_SCOPE_PENDING_OWNER','reviewer':'/root/m03_viewer_typed_review','author':'/root/m03_viewer_intent_typed_packet','checks':len(checks),'passed':len(checks),'independent_cases':len(fixtures),'additional_independent_cases':len(fixtures)-3,'exact_diagnostics_closed':3,'prior_cases':77,'previous_review_cases':30,'author_mutation_cases':150,'explicit_early_trace_changes':19,'product_hashes':796,'head':head,'historical_head':'31babe87a7ef1e40a0d4bedc523077e7a45d63ab','original_restricted_PASS':'PRESERVED','Owner_adoption':'PENDING','product_tests':'NOT RUN','native':'NOT RUN','build':'NOT RUN','valid_RED':'NOT RUN','FileCommit_ACK':'N/A; no authority','module_complete':False,'findings':[],'limitations':['Independent document probes and bounded reused response-schema evaluator only.','Provider authenticity, observation acquisition and native atomicity are not proven.','Eager validation and all 19 early call-trace changes are proposals awaiting Owner, not approved behavior.','No product Skeleton, valid RED, native acceptance or release authority. Parent remains Yellow.']}
    write('review.json',review);write('results.json',checks);write('new-fixtures.json',fixtures);write('trace-changes.json',traces);write('input-hashes.json',snapshots)
    report='<!doctype html><meta charset="utf-8"><title>M03 Typed Independent Review</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;background:#101823;color:#e9eef5}pre{white-space:pre-wrap}h1,h2{color:#9ad8ff}</style><h1>M03 typed observation independent review</h1><p>PASS document scope only; Owner adoption pending; parent Yellow. Original restricted PASS preserved.</p><h2>Review and boundaries</h2><pre>'+html.escape(json.dumps(review,ensure_ascii=False,indent=2))+'</pre><h2>Evidence</h2><p>checker.py · results.json · new-fixtures.json · trace-changes.json · input-hashes.json · artifact-hashes.json · seal.json</p><h2>Trace changes</h2><pre>'+html.escape(json.dumps(traces,indent=2))+'</pre><script type="application/json" id="module-review">'+json.dumps(review).replace('</','<\/')+'</script>'
    embedded={'checker':{'file':'checker.py','sha256':sha(P/'checker.py'),'source':(P/'checker.py').read_text(encoding='utf-8')},'results':checks,'input_hashes':snapshots,'trace':traces,'results_sha256':sha(P/'results.json'),'fixtures_sha256':sha(P/'new-fixtures.json')}
    report+='<script type="application/json" id="review-evidence">'+json.dumps(embedded,ensure_ascii=False).replace('</','<\/')+'</script>'
    (P/'index.html').write_text(report,encoding='utf-8')
    write('artifact-hashes.json',{p.name:sha(p) for p in sorted(P.iterdir()) if p.is_file() and p.name not in ('artifact-hashes.json','seal.json')})
    write('seal.json',{'status':'BOUNDED_INDEPENDENT_REVIEW_COMPLETE','manifest_sha256':sha(P/'artifact-hashes.json'),'module_complete':False})
    print(json.dumps(review,indent=2))
if __name__=='__main__':main()
