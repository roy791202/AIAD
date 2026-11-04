"""Executable DOCUMENT MODEL; trusted providers are explicit fixture premises."""
import copy, re
def begin(c, validate_request):
    state=copy.deepcopy(c['before']); calls=[]; p=c['premises']; r=c['request']
    def fail(code,details=None):return ({'ok':False,'error':{'code':code,'details':details or {}},'replayed':False},state,calls)
    if not p['trusted_local']:return fail('UnauthorizedCaller')
    if not validate_request(r):
        if type(r)is not dict:return fail('InvalidRequest',{'field':'/','reason':'Type'})
        fields=['binding_ref','expected_generation','expected_revision']
        unknown=sorted(set(r)-set(fields))
        if unknown:return fail('InvalidRequest',{'field':'/'+unknown[0].replace('~','~0').replace('/','~1'),'reason':'UnknownField'})
        for field in fields:
            if field not in r:return fail('InvalidRequest',{'field':'/'+field,'reason':'MissingField'})
            if type(r[field])is not str:return fail('InvalidRequest',{'field':'/'+field,'reason':'Type'})
        if not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',r['binding_ref']):return fail('InvalidRequest',{'field':'/binding_ref','reason':'InvalidUuid'})
        for field in fields[1:]:
            value=r[field]
            if not re.fullmatch(r'0|[1-9][0-9]*',value):return fail('InvalidRequest',{'field':'/'+field,'reason':'InvalidNumber'})
            if len(value)>20 or int(value)>18446744073709551615:return fail('InvalidRequest',{'field':'/'+field,'reason':'Range'})
        raise AssertionError('schema/model validation discrepancy')
    if not p['binding_present']:return fail('MissingBinding')
    if r['expected_generation']!=state['generation']:return fail('StaleOwner')
    if r['expected_revision']!=state['revision']:return fail('StaleRevision',{'expected':r['expected_revision'],'observed':state['revision']})
    if state['preview_count']>=4:return fail('ResourceLimit',{'field':'/preview_sessions','limit':'preview_sessions_per_binding'})
    calls.append('owner.snapshot.read')
    if not p['provider_ready']:return fail('DependencyNotReady',{'dependency':'M04_OWNER_INTEGRATION'})
    calls.append('C1.validated_projection.read')
    if p['provider_error']:return fail(p['provider_error']['code'],p['provider_error']['details'])
    value=copy.deepcopy(c['provider_projection'])
    # The provider projection is already validated by premise, not by this model.
    calls.append('delivery.identity.recheck')
    change=p['delivery_change']
    if change=='consumer_instance':return fail('UnauthorizedCaller')
    if change=='document_identity':return fail('MissingBinding')
    if change=='generation':return fail('StaleOwner')
    if change=='revision':return fail('StaleRevision',{'expected':state['revision'],'observed':str(int(state['revision'])+1)})
    if change=='closed':return fail('PreviewClosed')
    calls.append('preview.publish');state['preview_count']+=1
    return ({'ok':True,'value':value,'replayed':False},state,calls)
