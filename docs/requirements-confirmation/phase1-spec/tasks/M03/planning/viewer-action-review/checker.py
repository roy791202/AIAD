"""Independent document review. Never invokes author main or writes author files."""
import copy, hashlib, importlib.util, json, pathlib, re, subprocess, sys
P=pathlib.Path(__file__).resolve().parent
A=P.parent/'viewer-action-integration'
R=P.parents[6]
sys.dont_write_bytecode=True
sys.path.insert(0,str(A))
from checker import valid
from document_model import intent
def read(p): return json.loads(p.read_text(encoding='utf8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    results=[]; fixtures=[]
    def check(name,condition,detail=None):
        results.append({'id':name,'status':'PASS' if condition else 'FAIL','detail':detail})
    originals={str(p.relative_to(R)):sha(p) for p in A.iterdir() if p.is_file()}
    cases=read(A/'fixtures.json'); base=cases[0]; req=read(A/'request.schema.json'); res=read(A/'response.schema.json')
    def probe(name,mutate,expected):
        c=copy.deepcopy(base); mutate(c); before=copy.deepcopy(c); out,after,calls=intent(c)
        fixtures.append({'id':name,'input':before,'actual':out,'after':after,'calls':calls})
        code='OK' if out['ok'] else out['error']['code']
        check(name,code==expected,{'expected':expected,'actual':code})
        check(name+'/immutable',all(after[k]==c['before'][k] for k in ['history','content_hash','saved_hash','dirty','revision','generation']) and c==before)
        check(name+'/root',valid(res,out))
        if not out['ok'] and code!='SequenceOverflow':check(name+'/failure-state',after==c['before'])
    for key in base['request']:
        bad=copy.deepcopy(base['request']);del bad[key];check('request-missing-'+key,not valid(req,bad))
    for action in ['Activate','SetToggle','SetText','SetNumber','SelectItem']:
        for payload in [{},{'checked':True},{'text':'a'},{'number_text':'0.5'},{'item_id':'a'}]:
            q=copy.deepcopy(base['request']);q.update(action=action,payload=payload)
            expected={'Activate':{},'SetToggle':{'checked':True},'SetText':{'text':'a'},'SetNumber':{'number_text':'0.5'},'SelectItem':{'item_id':'a'}}[action]
            check('oneOf-'+action+'-'+str(payload),valid(req,q)==(payload==expected))
    for suffix in ['\n','\r','x',' ','s','S','\\']:
        q=copy.deepcopy(base['request']);q['preview_session']+=suffix
        check('parsed-uuid-tail-'+repr(suffix),not valid(req,q),repr(req['$defs']['UUID']['pattern']))
    for value in [None,False,7,{},[], '07','7\n','18446744073709551616']:
        probe('typed-revision-'+repr(value),lambda c,v=value:c['premises'].update(observed_revision=v),'DependencyNotReady')
    for value in [None,False,7,{},[], '7','7\n','18446744073709551616']:
        probe('delivery-revision-'+repr(value),lambda c,v=value:c['premises'].update(delivery_change='revision',delivery_observed_revision=v),'DependencyNotReady')
    for key,code in [('consumer','UnauthorizedCaller'),('document','MissingBinding'),('generation','StaleOwner'),('closed','PreviewClosed')]:
        probe('delivery-'+key,lambda c,v=key:c['premises'].update(delivery_change=v),code)
    for value in ['0','2','01','-1',None,True]:
        probe('sequence-'+repr(value),lambda c,v=value:c['request'].update(sequence=v),'SequenceConflict' if value in ['0','2'] else 'InvalidRequest')
    probe('overflow',lambda c:(c['before'].update(sequence=str(2**64-1)),c['request'].update(sequence=str(2**64-1))),'SequenceOverflow')
    for node in [{'type':'Button','scope':'domain','allowed_actions':['Activate']},{'type':'Button','scope':'ui','allowed_actions':[]},{'type':'Unknown','scope':'ui','allowed_actions':['Activate']}]:
        probe('closed-capability-'+str(node),lambda c,n=node:c['nodes'].update(button=n),'UnsupportedAction')
    c=copy.deepcopy(base);out,state,_=intent(c);c['before']=state;out,after,_=intent(c)
    check('sequential-replay',out['error']['code']=='SequenceConflict' and after==state and state['activation_count']['button']==1)
    authority=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
    matched=sum(sha(R/p)==h for p,h in authority['source_hashes'].items())
    check('796-authority',matched==len(authority['source_hashes'])==796)
    preserved=read(A/'preserved-inputs.json');drift=[p for p,h in preserved.items() if sha(R/p)!=h]
    check('original-candidate-hashes',all(p=='docs/board.json' for p in drift),{'management_snapshot_drift':drift,'candidate_drift':[p for p in drift if p!='docs/board.json']})
    check('author-package-unchanged',all(sha(R/p)==h for p,h in originals.items()))
    spec=read(A/'module-spec.json');check('pending-no-adoption',spec['status']=='PROPOSED_PENDING_OWNER' and spec['command']=='design_viewer_intent')
    check('filecommit-ack-na',all(not set(f['calls'])&{'FileCommit','ACK','save','history.write','content.write'} for f in fixtures))
    diagnostics=[]
    for key,value in [('delivery_change','unexpected'),('consumer_matches','false'),('provider_ready','false')]:
        c=copy.deepcopy(base);c['premises'][key]=value;out,after,calls=intent(c)
        diagnostics.append({'premise':key,'value':value,'result':out,'calls':calls,'classification':'OUTSIDE_DECLARED_TRUSTED_PREMISE_DOMAIN','reason':'Provider inputs explicitly trusted fixtures, not client admission. Packet does not claim malformed provider validation. Require typed seam definition before executable Skeleton; these are not native counterexamples.'})
    (P/'provider-premise-diagnostics.json').write_text(json.dumps(diagnostics,indent=2)+'\n',encoding='utf8')
    summary={'status':'PASS_DOCUMENT_SCOPE_PENDING_OWNER' if all(x['status']=='PASS' for x in results) else 'FINDINGS','reviewer':'/root/m03_viewer_intent_review','author':'/root/m03_viewer_action_packet','checks':len(results),'passed':sum(x['status']=='PASS' for x in results),'new_fixtures':len(fixtures),'provider_domain_diagnostics':len(diagnostics),'product_hashes_matched':matched,'preserved_inputs':len(preserved),'management_snapshot_drift':drift,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'historical_head':'31babe87a7ef1e40a0d4bedc523077e7a45d63ab','product_tests':'NOT RUN','native':'NOT RUN','build':'NOT RUN','valid_RED':'NOT RUN','FileCommit_ACK':'N/A','module_complete':False,'limitations':['Bounded schema evaluator reused; independent mutation cases, not full Draft2020 validation.','Native/C1/capability providers are trusted fixture premises. Their authenticity, malformed premise admission, atomicity and real delivery remain unproved.','Three out-of-domain provider diagnostics commit: unknown delivery enum and truthy nonboolean flags. Trust is not type validation; closed typed provider admission must be defined before Skeleton approval. Current packet expressly trusts these fixture premises and claims no runtime or general malformed-provider acceptance proof, so these do not invalidate bounded document verdict.','Owner must adopt exact roots, error precedence, capability policy and named seams; C1 CP1-CP3, Skeleton and valid RED remain pending.','Board snapshot drift is management evidence only, not product authority.']}
    for name,data in [('new-fixtures.json',fixtures),('results.json',results),('review.json',summary),('input-hashes.json',originals),('traceability.json',[{'check':x['id'],'contract':'exact mock-only intent / immutable authoritative state / bounded provider premises'} for x in results])]:
        (P/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    html='<html><meta charset="utf-8"><title>M03 independent intent review</title><h1>M03 design_viewer_intent independent document review</h1><p>Author and reviewer are distinct. Yellow preparation only; no adoption or native acceptance.</p><pre>'+__import__('html').escape(json.dumps(summary,indent=2,ensure_ascii=False))+'</pre><script type="application/json" id="review-spec">'+json.dumps(summary).replace('</','<\\/')+'</script><p><a href="results.json">Results</a> · <a href="new-fixtures.json">Independent fixtures</a> · <a href="traceability.json">Traceability</a> · <a href="input-hashes.json">Sealed input hashes</a></p></html>'
    (P/'index.html').write_text(html,encoding='utf8')
    (P/'artifact-hashes.json').write_text(json.dumps({p.name:sha(p) for p in P.iterdir() if p.is_file() and p.name!='artifact-hashes.json'},indent=2)+'\n',encoding='utf8')
    print(json.dumps(summary))
if __name__=='__main__':main()
