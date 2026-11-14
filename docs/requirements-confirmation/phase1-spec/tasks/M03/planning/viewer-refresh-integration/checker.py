"""Author checks only; not independent acceptance or full Draft2020 validation."""
import copy,hashlib,json,pathlib,subprocess
from document_model import refresh
from schema_eval import audit,valid
P=pathlib.Path(__file__).resolve().parent;ROOT=P.parents[6]
def load(n):return json.loads((P/n).read_text(encoding='utf8'))
def put(n,x):(P/n).write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    req=load('request.schema.json');res=load('response.schema.json');audit(req);audit(res)
    obs=load('provider-observation.schema.json');audit(obs)
    projection={'$defs':res['$defs'],'$ref':'#/$defs/Preview'}
    checks=0;cases=[];mutations=[]
    baseline=load('new-fixtures.json')[0]['provider'];assert valid(obs,baseline);checks+=1
    for path in [('trusted_local',),('ready',),('capture','closed'),('delivery','closed'),('capture','revision'),('delivery','generation')]:
        bad=copy.deepcopy(baseline);target=bad
        for k in path[:-1]:target=target[k]
        target[path[-1]]='false' if path[-1] in ('closed','ready','trusted_local') else True
        assert not valid(obs,bad);checks+=1
    for path in [(),('capture',),('delivery',)]:
        bad=copy.deepcopy(baseline);target=bad
        for k in path:target=target[k]
        target['extra']=True;assert not valid(obs,bad);checks+=1
    for c in load('new-fixtures.json'):
        result,after,calls=refresh(c,lambda x:valid(req,x),lambda x:valid(projection,x),lambda x:valid({'$defs':res['$defs'],'$ref':'#/$defs/Error'},x))
        for actual,expected in [(result,c['expected']),(after,c['expected_after']),(calls,c['expected_calls'])]:
            assert actual==expected,(c['id'],actual,expected);checks+=1
        assert valid(res,result),(c['id'],'response root',result);checks+=1
        for field in ('content','history','dirty','saved_baseline','owner_sessions','preview_count'):
            assert after[field]==c['before'][field];checks+=1
        cases.append({'id':c['id'],'status':'PASS_AUTHOR_DOCUMENT_MODEL'})
        def walk(x,path=()):
            if type(x)is dict:
                yield path,x
                for k,v in x.items():yield from walk(v,path+(k,))
            elif type(x)is list:
                for k,v in enumerate(x):yield from walk(v,path+(k,))
        for path,node in walk(result):
            for key in [None,*node]:
                bad=copy.deepcopy(result);target=bad
                for k in path:target=target[k]
                if key is None:target['forged']=True
                else:del target[key]
                assert not valid(res,bad),(c['id'],path,key);checks+=1
                mutations.append({'fixture':c['id'],'path':list(path),'key':key,'rejected':True})
        bad=copy.deepcopy(result);bad['replayed']=True
        assert not valid(res,bad);checks+=1
    authority_path=ROOT/load('source-current.json')['authority'];authority=json.loads(authority_path.read_text(encoding='utf8'))['source_hashes']
    assert len(authority)==796
    drift=[p for p,h in authority.items() if sha(ROOT/p)!=h];assert not drift,drift
    preserved=load('preserved-inputs.json');assert all(sha(ROOT/p)==h for p,h in preserved.items())
    checks+=len(authority)+len(preserved)
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();assert head=='5b709343a890503ebbe24a802e43cda5647df124';checks+=1
    # Lifecycle witnesses: repeated explicit refresh after success uses fresh provider UUID;
    # retired old UUID is no longer resolvable; failure leaves old values inert.
    c=copy.deepcopy(load('new-fixtures.json')[0]);out,s,calls=refresh(c,lambda x:valid(req,x),lambda x:valid(projection,x),lambda x:False);c['before']=s
    out,s2,calls=refresh(c,lambda x:valid(req,x),lambda x:valid(projection,x),lambda x:False);assert out['error']['code']=='PreviewClosed' and s2['projection']==s['projection'] and not s2['can_act'];checks+=1
    put('negative-probes.json',mutations)
    put('results.json',{'status':'PASS_AUTHOR_DOCUMENT_ONLY','author':'/root/m03_viewer_refresh_packet','cases':len(cases),'checks':checks,'negative_schema_probes':len(mutations),'source_authority_count':796,'source_matched':796,'preserved_input_count':len(preserved),'head':head,'historical_head':load('source-current.json')['historical_head'],'independent_review':'NOT RUN','native':'NOT RUN','product_tests':'NOT RUN','build':'NOT RUN','valid_RED':'NOT RUN','module_acceptance':'NOT RUN','results':cases})
    page=(P/'index.html').read_text(encoding='utf8');start=page.find('<section id="author-results">')
    if start!=-1:page=page[:start]+page[page.index('</section>',start)+10:]
    summary='<section id="author-results"><h2>Author document checks</h2><p>'+str(len(cases))+' new fixtures · '+str(checks)+' checks PASS · 796 authority hashes preserved · '+str(len(preserved))+' source inputs preserved. Native/build/product tests/valid RED/independent review NOT RUN.</p></section>'
    (P/'index.html').write_text(page.replace('</html>',summary+'</html>'),encoding='utf8')
    put('artifact-hashes.json',{f.name:sha(f) for f in sorted(P.iterdir()) if f.is_file() and f.name not in ('artifact-hashes.json','seal.json')})
    put('seal.json',{'status':'SEALED_AUTHOR_DOCUMENT_ONLY_PENDING_OWNER','artifact_manifest_sha256':sha(P/'artifact-hashes.json'),'artifact_count':len(load('artifact-hashes.json')),'fixtures':len(cases),'checks':checks,'authority_matched':796,'preserved_inputs':len(preserved),'independent_review':'NOT RUN'})
    print(json.dumps(load('seal.json'),indent=2))
if __name__=='__main__':main()
