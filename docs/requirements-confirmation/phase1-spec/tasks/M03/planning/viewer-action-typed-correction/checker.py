"""Author document checks only; not independent acceptance or product TDD."""
import copy, hashlib, importlib.util, json, pathlib, sys
sys.dont_write_bytecode = True
from document_model import intent, original, BOOLS, STRINGS, CHANGES
P=pathlib.Path(__file__).resolve().parent
R=P.parents[6]
def load(p): return json.loads(p.read_text(encoding='utf8'))
def write(n,x): (P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    prior=P.parent/'viewer-action-integration'
    spec=importlib.util.spec_from_file_location('bounded_schema',prior/'checker.py')
    schema=importlib.util.module_from_spec(spec);spec.loader.exec_module(schema)
    cases=load(prior/'fixtures.json'); rows=[]; new=[]
    def check(c,expected,expected_after,expected_calls,label):
        actual,after,calls=intent(c)
        assert actual==expected,(label,actual,expected)
        assert after==expected_after,(label,'state')
        assert calls==expected_calls,(label,'calls',calls,expected_calls)
        assert schema.valid(load(P/'response.schema.json'),actual),(label,'response schema')
        rows.append({'id':label,'response':actual,'after':after,'calls':calls,'response_schema':True,'status':'PASS_AUTHOR_DOCUMENT_MODEL'})
    trace_changes=[]
    for c in cases:
        expected_calls=c['expected_calls']
        if c['id'] in ('VA-074','VA-075','VA-076','VA-077'):
            trace_changes.append({'id':c['id'],'before_calls':expected_calls,'after_calls':[],'reason':'PROPOSED_PENDING_OWNER eager malformed delivery revision admission; same full response and state'})
            expected_calls=[]
        check(c,c['expected'],c['expected_after'],expected_calls,'prior/'+c['id'])
    for old in load(P.parent/'viewer-action-review'/'new-fixtures.json'):
        c=old['input'];actual,after,calls=intent(c)
        assert actual==old['actual'] and after==old['after'],('review semantics',old['id'])
        if calls != old['calls']:
            assert calls==[] and actual.get('error',{}).get('code')=='DependencyNotReady'
            trace_changes.append({'id':'review/'+old['id'],'before_calls':old['calls'],'after_calls':calls,'reason':'PROPOSED_PENDING_OWNER eager typed provider ingress; same complete response and state'})
        check(c,old['actual'],old['after'],calls,'review/'+old['id'])
    base=copy.deepcopy(cases[0]); diagnostics=[]
    def reject(c,label,dependency='M01_NATIVE_IDENTITY'):
        expected={'ok':False,'error':{'code':'DependencyNotReady','details':{'dependency':dependency}},'replayed':False}
        c['id']=label; c['expected']=expected;c['expected_after']=copy.deepcopy(c['before']);c['expected_calls']=[]
        new.append(c);check(c,expected,c['before'],[],label)
    for field,value in [('delivery_change','unexpected'),('consumer_matches','false'),('provider_ready','false')]:
        c=copy.deepcopy(base);c['premises'][field]=value
        before=original.intent(c); reject(c,'diagnostic/'+field)
        diagnostics.append({'field':field,'value':value,'before':{'response':before[0],'after':before[1],'calls':before[2]},'after':rows[-1],'prior_classification':'OUTSIDE_DECLARED_TRUSTED_PREMISE_DOMAIN','new_policy':'PROPOSED_PENDING_OWNER'})
    for field in BOOLS+STRINGS:
        c=copy.deepcopy(base);del c['premises'][field];reject(c,'missing/'+field)
        for value in (None,0,1,[],{},'false',True):
            if type(value) is (bool if field in BOOLS else str):continue
            c=copy.deepcopy(base);c['premises'][field]=value;reject(c,'type/'+field+'/'+type(value).__name__+'/'+str(value))
    for value in ('','None','NONE','revision ','none\n'):
        c=copy.deepcopy(base);c['premises']['delivery_change']=value;reject(c,'enum/'+repr(value))
    c=copy.deepcopy(base);c['premises']['extra']=True;reject(c,'closed/extra')
    for value in (None,False,0,[], 'observation'):
        c=copy.deepcopy(base);c['premises']=value;reject(c,'record/type/'+repr(value))
    c=copy.deepcopy(base);del c['premises'];reject(c,'record/missing')
    for field in ('observed_generation','observed_revision','delivery_observed_revision'):
        for value in ('','00','-1','1e0','18446744073709551616','7\n'):
            c=copy.deepcopy(base);c['premises'][field]=value;reject(c,'u64/'+field+'/'+repr(value))
    c=copy.deepcopy(base);c['premises']['delivery_change']='revision';reject(c,'conditional/missing-delivery-revision')
    for field,value in [('number_canonical','NaN'),('number_canonical',''),('number_error','')]:
        c=copy.deepcopy(base);c['premises'][field]=value;reject(c,'codec/'+field+'/'+repr(value),'C1_CODEC')
    for field,value in [('type',1),('scope',False),('allowed_actions','Activate'),('allowed_actions',['Unknown']),('items_valid','false'),('item_ids',[1]),('asset_missing',False),('target_missing',{}),('extra',True)]:
        c=copy.deepcopy(base);c['nodes']['button'][field]=value;reject(c,'node/'+field+'/'+repr(value),'M04_OWNER_INTEGRATION')
    for field in ('type','scope','allowed_actions'):
        c=copy.deepcopy(base);del c['nodes']['button'][field];reject(c,'node/missing/'+field,'M04_OWNER_INTEGRATION')
    for value in (None,False,0,[], 'nodes'):
        c=copy.deepcopy(base);c['nodes']=value;reject(c,'nodes/type/'+repr(value),'M04_OWNER_INTEGRATION')
    for value in (None,False,0,[], 'node'):
        c=copy.deepcopy(base);c['nodes']['button']=value;reject(c,'node/record-type/'+repr(value),'M04_OWNER_INTEGRATION')
    for field in ('items_valid','item_ids'):
        c=copy.deepcopy(base);del c['nodes']['combo'][field];reject(c,'combo/missing/'+field,'M04_OWNER_INTEGRATION')
    # Explicit precedence proposal: malformed provider admission dominates ordinary client errors.
    for fault in ('malformed-request','unauthorized','closed','stale','overflow'):
        c=copy.deepcopy(base);c['premises']['provider_ready']='false'
        if fault=='malformed-request':c['request']=None
        if fault=='unauthorized':c['premises']['trusted_local']=False
        if fault=='closed':c['before']['closed']=True
        if fault=='stale':c['premises']['observed_revision']='9'
        if fault=='overflow':c['before']['sequence']='18446744073709551615';c['request']['sequence']=c['before']['sequence']
        reject(c,'precedence/'+fault)
    # Unknown capability type remains unsupported (not a malformed provider enum).
    c=copy.deepcopy(base);c['nodes']['button']['type']='FutureWidget'
    check(c,{'ok':False,'error':{'code':'UnsupportedAction','details':{'node_id':'button','action':'Activate'}},'replayed':False},c['before'],['native.preview.resolve','immutable.capability.read'],'semantics/unknown-type')
    # U64 extrema admitted as typed observations then interpreted by unchanged semantics.
    for value in ('0','18446744073709551615'):
        c=copy.deepcopy(base);c['premises']['observed_generation']=value
        check(c,{'ok':False,'error':{'code':'StaleOwner','details':{}},'replayed':False},c['before'],['native.preview.resolve'],'boundary/generation/'+value)
    first,state,calls=intent(base);c=copy.deepcopy(base);c['before']=state
    check(c,{'ok':False,'error':{'code':'SequenceConflict','details':{'expected':'2','received':'1'}},'replayed':False},state,['native.preview.resolve'],'sequence/replay')
    for path,h in load(P/'preserved-inputs.json').items():assert digest(R/path)==h,('preservation',path)
    authority=load(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
    assert len(authority['source_hashes'])==796
    for path,h in authority['source_hashes'].items():assert digest(R/path)==h,('product',path)
    assert (P/'request.schema.json').read_bytes()==(prior/'request.schema.json').read_bytes()
    assert (P/'response.schema.json').read_bytes()==(prior/'response.schema.json').read_bytes()
    write('new-fixtures.json',new);write('before-after-diagnostics.json',diagnostics);write('model-results.json',rows);write('prior-trace-changes.json',trace_changes)
    write('verification.json',{'status':'PASS_AUTHOR_DOCUMENT_SCOPE_PENDING_OWNER','author':'/root/m03_viewer_intent_typed_packet','independent_acceptance':'NOT RUN','cases':len(rows),'prior_cases':len(cases),'new_mutation_cases':len(new),'product_hashes':796,'schemas':'BYTEWISE_PRESERVED','product_tests':'NOT RUN','native':'NOT RUN','build':'NOT RUN','valid_RED':'NOT RUN','module_complete':False})
    print('PASS author document checks:',len(rows),'cases; 796 product hashes; no acceptance claim')
if __name__=='__main__':main()
