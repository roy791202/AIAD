"""Independent document review only. Does not invoke mutating author checker.main."""
import copy, hashlib, importlib.util, json, pathlib, random, subprocess, sys
P=pathlib.Path(__file__).resolve().parent
R=P.parents[6]
C=P.parent/'preview-begin-integration'
sys.path.insert(0,str(C))
import checker as author
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    baseline={str(p.relative_to(R)):digest(p) for p in C.iterdir() if p.is_file()}
    req=load(C/'request.schema.json');res=load(C/'response.schema.json');base=load(C/'fixtures.json')[0]
    probes=[]
    def record(name,passed,**extra): probes.append(dict(id=name,passed=passed,**extra))
    rng=random.Random(3103)
    for i in range(240):
        n=rng.randrange(0,2**65);s=str(n)
        record('u64-property-'+str(i),author.valid({'$defs':res['$defs'],'$ref':'#/$defs/U64Decimal'},s)==(n<2**64),input=s)
    for suffix in ['\n','\r','x','s','S','\\','\u2028','\x00']:
        for field in ['binding_ref','expected_generation','expected_revision']:
            c=copy.deepcopy(base);c['request'][field]+=suffix
            record('lexical-'+field+'-'+repr(suffix),not author.valid(req,c['request']))
    for count in range(0,7):
        for late in [None,'consumer_instance','document_identity','generation','revision','closed']:
            c=copy.deepcopy(base);c['before']['preview_count']=count;c['premises']['delivery_change']=late
            response,after,calls=author.begin(c,lambda x:author.valid(req,x))
            expected=count<4 and late is None
            record('capacity-delivery-'+str(count)+'-'+str(late),response['ok']==expected and author.valid(res,response) and after['preview_count']==count+int(expected) and (expected or 'preview.publish' not in calls))
    c=copy.deepcopy(base);c['before']['revision']=c['request']['expected_revision']=c['provider_projection']['source_revision']=str(2**64-1);c['premises']['delivery_change']='revision'
    response,after,calls=author.begin(c,lambda x:author.valid(req,x))
    record('PB-IR-F1-max-revision-late-delivery',author.valid(res,response),response=response,request=c['request'],premises=c['premises'])
    authority=load(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')['source_hashes']
    mismatches=[p for p,h in authority.items() if digest(R/p)!=h]
    record('source-authority-796',len(authority)==796 and not mismatches,count=len(authority),mismatches=mismatches)
    record('candidate-preserved',baseline=={str(p.relative_to(R)):digest(p) for p in C.iterdir() if p.is_file()})
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
    finding={'id':'PB-IR-F1','severity':'P2','scope':'document model only','location':'preview-begin-integration/document_model.py:36','counterexample':probes[-3],'meaning':'A valid max revision combined with the unconstrained late revision observation creates an out-of-range observed diagnostic. No native defect is claimed.','requested_change':'Represent actual bounded observed revision in trusted delivery premise, or explicitly constrain this combination unreachable and test the constraint. Do not fabricate max+1 as an observed revision.'}
    result={'verdict':'CHANGES_REQUIRED_DOCUMENT_MODEL_ONLY','author':'/root/m03_preview_begin_packet','reviewer':'/root/m03_viewer_begin_review','head':head,'historical_authority_head':'31babe87a7ef1e40a0d4bedc523077e7a45d63ab','checks':len(probes),'passed':sum(p['passed'] for p in probes),'failed':sum(not p['passed'] for p in probes),'findings':[finding],'authority_count':len(authority),'authority_matched':len(authority)-len(mismatches),'owner':'PENDING','product_tests':'NOT RUN','build':'NOT RUN','native':'NOT RUN','valid_RED':'NOT RUN','acceptance_scope':'Only begin document proposal; no module or whole H2 acceptance','trusted_premises':'Owner snapshot, C1 validated projection, native identity observations remain trusted premises; proposed DTO choices not independently adopted.'}
    for name,data in [('fixtures.json',probes),('results.json',result),('source-hashes.json',baseline),('traceability.json',{'PB-IR-F1':['PB-I2','PB-I5','PB-17','PB-21']})]: (P/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
    import html
    page='<html><meta charset="utf-8"><title>M03 Begin Independent Review</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto}pre{white-space:pre-wrap;background:#eee;padding:20px}</style><h1>M03 design_viewer_begin independent document review</h1><p>CHANGES_REQUIRED_DOCUMENT_MODEL_ONLY — one bounded diagnostic observation seam issue. Yellow parent unchanged. All proposed choices remain pending Owner.</p><p>Review covers full roots, typed mocks/provider outcome premises, immutable owner authority, consumer delivery guards, capacity and u64. No FileCommit or ACK belongs to this read-only slice. Native identity and C1 provider correctness are premises, not runtime proof.</p><pre>'+html.escape(json.dumps(result,indent=2))+'</pre><script type="application/json" id="module-review">'+json.dumps(result).replace('<','\\u003c')+'</script></html>'
    (P/'index.html').write_text(page,encoding='utf8')
    (P/'artifact-hashes.json').write_text(json.dumps({p.name:digest(p) for p in P.iterdir() if p.is_file() and p.name!='artifact-hashes.json'},indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ['verdict','checks','passed','failed','authority_count','authority_matched']}))
if __name__=='__main__':main()

