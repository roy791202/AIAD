"""Bounded schema keyword evaluator + document-model probes, not Draft2020 validator."""
import copy, hashlib, json, pathlib, re
from document_model import begin
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
    results=[];negatives=[]
    for c in load('fixtures.json'):
        response,after,calls=begin(c,lambda x:valid(req,x))
        assert response==c['expected'],(c['id'],response,c['expected'])
        assert valid(res,response),(c['id'],'response schema')
        assert calls==c['expected_calls'],c['id']
        expected_after=copy.deepcopy(c['before']);expected_after['preview_count']+=int(response['ok'])
        assert after==expected_after,c['id']
        results.append({'id':c['id'],'result':'PASS_DOCUMENT_MODEL','calls':calls})
        # Every response object is closed: extra and missing properties at each occurrence.
        def walk(x,path=[]):
            if type(x)is dict:
                yield path,x
                for k,z in x.items():yield from walk(z,path+[k])
            elif type(x)is list:
                for k,z in enumerate(x):yield from walk(z,path+[k])
        for path,node in walk(response):
            for action,key in [('extra','forged')]+[('missing',k) for k in node]:
                bad=copy.deepcopy(response);target=bad
                for k in path:target=target[k]
                if action=='extra':target[key]=True
                else:del target[key]
                assert not valid(res,bad),(c['id'],path,action,key)
                negatives.append({'fixture':c['id'],'path':path,'mutation':action,'key':key,'rejected':True})
    # Every u64 occurrence in a successful root, including expected_sequence.
    u64=['','00','01','-1','1.0','1e3','18446744073709551616','18446744073709551615\n',1,True,None]
    good=load('fixtures.json')[0]['expected']
    for field in ['source_revision','expected_sequence']:
        for badvalue in u64:
            bad=copy.deepcopy(good);bad['value'][field]=badvalue
            assert not valid(res,bad),(field,badvalue)
            negatives.append({'field':field,'bad':badvalue,'rejected':True})
    for field in ['expected_generation','expected_revision']:
        for badvalue in u64:
            bad=copy.deepcopy(load('fixtures.json')[0]['request']);bad[field]=badvalue
            assert not valid(req,bad),(field,badvalue)
            negatives.append({'request_field':field,'bad':badvalue,'rejected':True})
    for n in ['0','9007199254740993','18446744073709551615']:
        assert valid({'$defs':res['$defs'],'$ref':'#/$defs/U64Decimal'},n)
    for bad in [dict(good,error={'code':'MissingBinding','details':{}}),dict(good,replayed=True),dict(good,value={'kind':'fake'})]:
        assert not valid(res,bad);negatives.append({'mutation':'contradictory-root/replay/wrong-value','rejected':True})
    # Type-specific root probes, not only property closure.
    for index in range(5):
        bad=copy.deepcopy(good);bad['value']['mock_state'][index]['value']['kind']='Forged'
        assert not valid(res,bad);negatives.append({'mutation':'mock-tag','index':index,'rejected':True})
    authority=load('source-comparison.json');assert authority['count']==796 and authority['matched']==796
    repo=P.parents[6]
    authority_data=json.loads((repo/authority['authority']).read_text(encoding='utf8'))
    assert all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==h for p,h in authority_data['source_hashes'].items())
    assert all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==h for p,h in load('current-source-input-hashes.json').items())
    assert all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==h for p,h in load('preserved-inputs.json').items())
    verification={'status':'PASS_AUTHOR_DOCUMENT_MODEL_ONLY','fixtures':len(results),'negative_probes':len(negatives),'authority_sources':authority['count'],'authority_matched':authority['matched'],'schema_engine':'Bounded evaluator, supported keywords audited; NOT full Draft2020 validator','product_tests':'NOT RUN','valid_RED':'NOT RUN','native':'NOT RUN','independent_acceptance':'NOT RUN','owner_adoption':'PROPOSED_PENDING_OWNER'}
    for n,data in [('model-results.json',results),('negative-probes.json',negatives),('verification.json',verification)]:
        (P/n).write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
    (P/'artifact-hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(P.iterdir()) if p.is_file() and p.name!='artifact-hashes.json'},indent=2)+'\n',encoding='utf8')
    print(json.dumps(verification))
if __name__=='__main__':main()
