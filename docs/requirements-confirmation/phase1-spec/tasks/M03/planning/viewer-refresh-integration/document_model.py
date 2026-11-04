"""PROPOSED_PENDING_OWNER. Author document model; no product/native execution."""
import copy, re
MAX=18446744073709551615
UUID=r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
def u64(x): return type(x)is str and re.fullmatch(r'0|[1-9][0-9]*',x)is not None and len(x)<=20 and int(x)<=MAX
def uuid(x): return type(x)is str and re.fullmatch(UUID,x)is not None
def identity(x):
    return type(x)is dict and set(x)=={'consumer','window','document','session','generation','revision','closed'} and all(type(x[k])is str and x[k] for k in ('consumer','window','document','session')) and u64(x['generation']) and u64(x['revision']) and type(x['closed'])is bool
def refresh(c,valid_request,valid_projection,valid_error):
    s=copy.deepcopy(c['before']);r=c['request'];p=c['provider'];calls=[]
    def fail(code,details=None):
        s['stale']=True;s['can_act']=False
        return {'ok':False,'error':{'code':code,'details':details or {}},'replayed':False},s,calls
    # These are closed trusted-observation records, never user-supplied booleans.
    if type(p)is not dict or set(p)!={'trusted_local','ready','capture','delivery','outcome','projection'} or type(p['trusted_local'])is not bool or type(p['ready'])is not bool or not identity(p['capture']) or not identity(p['delivery']):return fail('DependencyNotReady',{'dependency':'M01_NATIVE_IDENTITY'})
    if not p['trusted_local']:return fail('UnauthorizedCaller')
    if not valid_request(r):
        if type(r)is not dict:return fail('InvalidRequest',{'field':'/','reason':'Type'})
        unknown=sorted(set(r)-{'preview_session','expected_revision'})
        if unknown:return fail('InvalidRequest',{'field':'/'+unknown[0].replace('~','~0').replace('/','~1'),'reason':'UnknownField'})
        for k in ('preview_session','expected_revision'):
            if k not in r:return fail('InvalidRequest',{'field':'/'+k,'reason':'MissingField'})
            if type(r[k])is not str:return fail('InvalidRequest',{'field':'/'+k,'reason':'Type'})
        if not uuid(r['preview_session']):return fail('InvalidRequest',{'field':'/preview_session','reason':'InvalidUuid'})
        return fail('InvalidRequest',{'field':'/expected_revision','reason':'InvalidNumber' if re.fullmatch(r'0|[1-9][0-9]*',r['expected_revision'])is None else 'Range'})
    calls.append('native.preview.resolve')
    if r['preview_session']!=s['preview_session'] or s['closed']:return fail('PreviewClosed')
    cap=p['capture']
    for key,code in [('consumer','UnauthorizedCaller'),('window','UnauthorizedCaller'),('document','MissingBinding'),('session','MissingBinding'),('generation','StaleOwner')]:
        if cap[key]!=s[key]:return fail(code)
    if cap['closed']:return fail('PreviewClosed')
    if r['expected_revision']!=cap['revision']:return fail('StaleRevision',{'expected':r['expected_revision'],'observed':cap['revision']})
    if not p['ready']:return fail('DependencyNotReady',{'dependency':'M04_OWNER_INTEGRATION'})
    calls.append('owner.immutable.snapshot.read')
    o=p['outcome']
    if type(o)is dict:
        if not valid_error(o) or o['code'] not in ('UnsupportedDocument','CodecRejected','ResourceLimit','AmbiguousStableId','ParentMissing','ParentCycle','DependencyNotReady'):return fail('DependencyNotReady',{'dependency':'C1_CODEC'})
        return fail(o['code'],copy.deepcopy(o['details']))
    if type(o)is not str or o!='Ready':return fail('DependencyNotReady',{'dependency':'C1_CODEC'})
    calls.append('C1.projection.validate')
    v=copy.deepcopy(p['projection'])
    if not valid_projection(v) or v['preview_session']==s['preview_session'] or v['source_revision']!=cap['revision'] or v['expected_sequence']!='1' or v['stale']is not False:return fail('DependencyNotReady',{'dependency':'C1_CODEC'})
    ids=[n['node_id'] for n in v['mock_state']];caps=[n['node_id'] for n in v['capabilities']]
    if len(set(ids))!=len(ids) or len(set(caps))!=len(caps) or not set(ids)<=set(caps) or any(n['allowed_actions'] for n in v['capabilities'] if n['node_id'] not in ids):return fail('DependencyNotReady',{'dependency':'C1_CODEC'})
    kinds={'Action':'Activate','Toggle':'SetToggle','Text':'SetText','Number':'SetNumber','Selection':'SelectItem'}
    observed={n['node_id']:n['value'] for n in v['mock_state']}
    for n in v['capabilities']:
        if n['node_id'] in observed:
            mock=observed[n['node_id']]
            if n['allowed_actions']!=[kinds[mock['kind']]]:return fail('DependencyNotReady',{'dependency':'C1_CODEC'})
            if mock['kind']=='Number' and re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?',mock['number_text'])is None:return fail('DependencyNotReady',{'dependency':'C1_CODEC'})
            if mock['kind']=='Selection' and mock['item_id']=='':return fail('DependencyNotReady',{'dependency':'C1_CODEC'})
    calls.append('native.delivery.recheck')
    d=p['delivery']
    for key,code in [('consumer','UnauthorizedCaller'),('window','UnauthorizedCaller'),('document','MissingBinding'),('session','MissingBinding'),('generation','StaleOwner')]:
        if d[key]!=cap[key]:return fail(code)
    if d['closed']:return fail('PreviewClosed')
    if d['revision']!=cap['revision']:return fail('StaleRevision',{'expected':cap['revision'],'observed':d['revision']})
    # One slot exchanged, even at capacity. No sequence/revision arithmetic.
    calls.append('preview.atomic.replace')
    s['retired']=[*s['retired'],s['preview_session']];s['preview_session']=v['preview_session'];s['projection']=v;s['revision']=cap['revision'];s['sequence']='1';s['stale']=False;s['can_act']=True
    return {'ok':True,'value':v,'replayed':False},s,calls
