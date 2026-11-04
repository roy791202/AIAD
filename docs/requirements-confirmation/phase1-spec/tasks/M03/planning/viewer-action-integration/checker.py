"""Bounded schema keyword evaluator + document-model probes, not Draft2020 validator."""
import copy, hashlib, json, pathlib, re
from document_model import intent
P=pathlib.Path(__file__).resolve().parent
def load(n):return json.loads((P/n).read_text(encoding='utf8'))
KEYWORDS={'$schema','$id','$defs','$ref','type','properties','required','additionalProperties','oneOf','const','enum','minLength','maxLength','pattern','items'}
def audit(s):
    assert not (set(s)-KEYWORDS),set(s)-KEYWORDS
    for key in ['properties','$defs']:
        for item in s.get(key,{}).values():audit(item)
    for item in s.get('oneOf',[]):audit(item)
    if 'items'in s:audit(s['items'])
def valid(root,x):
    def v(s,x):
        if '$ref'in s:
            dest=root
            for k in s['$ref'][2:].split('/'):dest=dest[k]
            return v(dest,x)
        if 'oneOf'in s:return sum(v(a,x) for a in s['oneOf'])==1
        if 'const'in s and (type(x)!=type(s['const']) or x!=s['const']):return False
        if 'enum'in s and not any(type(x)==type(a) and x==a for a in s['enum']):return False
        types={'object':type(x)is dict,'array':type(x)is list,'string':type(x)is str,'boolean':type(x)is bool,'null':x is None}
        t=s.get('type')
        if t and not any(types.get(k,False) for k in (t if isinstance(t,list) else [t])):return False
        if isinstance(x,str):
            if not s.get('minLength',0)<=len(x)<=s.get('maxLength',10**9):return False
            if 'pattern'in s and re.search(s['pattern'],x)is None:return False
        if type(x)is dict:
            if any(k not in x for k in s.get('required',[])):return False
            if s.get('additionalProperties')is False and set(x)-set(s.get('properties',{})):return False
            if any(k in x and not v(a,x[k]) for k,a in s.get('properties',{}).items()):return False
        if type(x)is list and 'items'in s and not all(v(s['items'],a) for a in x):return False
        return True
    return v(root,x)

def main():
    req=load('request.schema.json');res=load('response.schema.json');audit(req);audit(res)
    cases=load('fixtures.json');results=[];probes=[]
    def probe(kind,value,schema):
        assert not valid(schema,value),(kind,value)
        probes.append({'kind':kind,'rejected':True})
    def paths(x,path=()):
        yield path,x
        if type(x)is dict:
            for k,z in x.items():yield from paths(z,path+(k,))
        if type(x)is list:
            for k,z in enumerate(x):yield from paths(z,path+(k,))
    for c in cases:
        result,after,calls=intent(c)
        assert result==c['expected'],(c['id'],result,c['expected'])
        assert after==c['expected_after'],(c['id'],'state',after,c['expected_after'])
        assert calls==c['expected_calls'],(c['id'],calls,c['expected_calls'])
        assert valid(res,result),(c['id'],'response schema')
        # Admission schema checks syntax/types; number grammar and byte limits are semantic guards.
        syntax_bad=result.get('error',{}).get('code')=='InvalidRequest' and result['error']['details'].get('reason') not in ['InvalidNumber','Range']
        if syntax_bad:assert not valid(req,c['request']),c['id']
        for key in ['content_hash','history','saved_hash','dirty','revision','generation']:
            assert after[key]==c['before'][key],(c['id'],key)
        assert not any(k in calls for k in ['save','FileCommit','ACK','content.write','history.write'])
        results.append({'id':c['id'],'status':'PASS_AUTHOR_DOCUMENT_MODEL','request_schema':valid(req,c['request']),'expected':result,'calls':calls})
        for path,node in paths(result):
            if type(node)is dict:
                changes=[('extra','forged')]+[('missing',k) for k in node]
                for kind,key in changes:
                    bad=copy.deepcopy(result);target=bad
                    for k in path:target=target[k]
                    if kind=='extra':target[key]=True
                    else:del target[key]
                    probe(c['id']+'/'+str(path)+'/'+kind+'/'+str(key),bad,res)
            else:
                for replacement in [None,True,1,{},[],'forged']:
                    if type(replacement)is type(node):continue
                    bad=copy.deepcopy(result)
                    if not path:bad=replacement
                    else:
                        target=bad
                        for k in path[:-1]:target=target[k]
                        target[path[-1]]=replacement
                    probe(c['id']+'/type/'+str(path)+'/'+type(replacement).__name__,bad,res)
    u= {'$defs':req['$defs'],'$ref':'#/$defs/U64Decimal'}
    for n in ['0','9007199254740993','18446744073709551615']:assert valid(u,n)
    for bad in ['', '00','01','-1','1.0','1e3','18446744073709551616','18446744073709551615\n',True,1,None]:probe('strict-u64',bad,u)
    for c in cases[:6]:
        for extra in ['owner','generation','window','target_path','command','ack','save']:
            bad=copy.deepcopy(c['request']);bad[extra]=True;probe('request-authority/'+extra,bad,req)
    # Consecutive actions are driven from first actual model state; replay is not a fixture-only claim.
    c=copy.deepcopy(cases[0]);first,s,_=intent(c);assert first['ok']
    c['before']=s;second,after,_=intent(c)
    assert second=={'ok':False,'error':{'code':'SequenceConflict','details':{'expected':'2','received':'1'}},'replayed':False}
    assert after==s and s['activation_count']['button']==1
    R=P.parents[6]
    preserved=load('preserved-inputs.json')
    for p,h in preserved.items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h,('input drift',p)
    source=load('source-comparison.json');authority=json.loads((R/source['authority']).read_text(encoding='utf8'))
    assert len(authority['source_hashes'])==796
    for p,h in authority['source_hashes'].items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h,('product drift',p)
    spec=load('module-spec.json');assert spec['command']=='design_viewer_intent'
    embedded=re.search(r'<script type="application/json" id="module-spec">(.*?)</script>',(P/'index.html').read_text(encoding='utf8'),re.S)
    assert embedded and json.loads(embedded.group(1))==spec
    for c in cases:assert c['id'] in (P/'module.feature').read_text(encoding='utf8')
    verification={'status':'PASS_AUTHOR_DOCUMENT_MODEL_ONLY','fixtures':len(cases),'passed':len(results),'negative_probes':len(probes),'sequential_replay_probes':1,'authority_sources':796,'authority_matched':796,'preserved_input_files':len(preserved),'actual_head':source['actual_head'],'historical_authority_head':source['historical_head'],'schema_engine':'Audited bounded keyword evaluator; NOT full Draft2020 validator','owner_adoption':'PROPOSED_PENDING_OWNER','product_tests':'NOT RUN','native':'NOT RUN','build':'NOT RUN','valid_RED':'NOT RUN','independent_acceptance':'NOT RUN','module_complete':False}
    for n,d in [('model-results.json',results),('negative-probes.json',probes),('verification.json',verification)]:
        (P/n).write_text(json.dumps(d,indent=2)+'\n',encoding='utf8')
    seal={'status':'SEALED_AUTHOR_DOCUMENT_PACKAGE_ONLY','command':'design_viewer_intent','fixtures':len(cases),'negative_probes':len(probes),'trace_rows':len(load('traceability.json')),'source_match':'796/796','not_runtime':True}
    (P/'seal.json').write_text(json.dumps(seal,indent=2)+'\n',encoding='utf8')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(P.iterdir()) if p.is_file() and p.name!='artifact-hashes.json'}
    (P/'artifact-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf8')
    print(json.dumps(verification))
if __name__=='__main__':main()
