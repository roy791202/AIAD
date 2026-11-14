"""Proposed DOCUMENT model only. Native identity and C1 results are trusted fixture premises."""
import copy, re
MAX=18446744073709551615
ACTIONS={'Activate':{},'SetToggle':{'checked':bool},'SetText':{'text':str},'SetNumber':{'number_text':str},'SelectItem':{'item_id':str}}
TYPES={'Button':'Activate','CheckBox':'SetToggle','TextBox':'SetText','NumberInput':'SetNumber','ComboBox':'SelectItem'}
def u64(x):return type(x)is str and re.fullmatch(r'0|[1-9][0-9]*',x)is not None and len(x)<=20 and int(x)<=MAX
def intent(c):
    r=c['request']; p=c['premises']; s=copy.deepcopy(c['before']); calls=[]
    def fail(code,details=None):return {'ok':False,'error':{'code':code,'details':details or {}},'replayed':False},s,calls
    def invalid(field,reason):return fail('InvalidRequest',{'field':field,'reason':reason})
    if not p['trusted_local']:return fail('UnauthorizedCaller')
    fields=['preview_session','expected_revision','sequence','node_id','action','payload']
    if type(r)is not dict:return invalid('/','Type')
    unknown=sorted(set(r)-set(fields))
    if unknown:return invalid('/'+unknown[0].replace('~','~0').replace('/','~1'),'UnknownField')
    for k in fields:
        if k not in r:return invalid('/'+k,'MissingField')
        if type(r[k])is not (dict if k=='payload' else str):return invalid('/'+k,'Type')
    if re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',r['preview_session'])is None:return invalid('/preview_session','InvalidUuid')
    for k in ['expected_revision','sequence']:
        if not u64(r[k]):return invalid('/'+k,'Range' if re.fullmatch(r'0|[1-9][0-9]*',r[k]) else 'InvalidNumber')
    a=r['action']; payload=r['payload']; node=r['node_id']
    if a not in ACTIONS or set(payload)!=set(ACTIONS[a]) or any(type(payload[k])is not t for k,t in ACTIONS.get(a,{}).items()):return invalid('/payload','InvalidActionPayload')
    if not node:return invalid('/node_id','Range')
    for field,value,limit,token in [('/node_id',node,256,'node_id_utf8'),('/payload/text',payload.get('text',''),4096,'text_payload_utf8'),('/payload/number_text',payload.get('number_text',''),128,'number_text_bytes')]:
        if len(value.encode('utf8'))>limit:return fail('ResourceLimit',{'field':field,'limit':token})
    if a=='SetNumber' and re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?',payload['number_text'])is None:return invalid('/payload/number_text','InvalidNumber')
    calls.append('native.preview.resolve')
    if r['preview_session']!=s['preview_session'] or s['closed']:return fail('PreviewClosed')
    if not p['consumer_matches']:return fail('UnauthorizedCaller')
    if not p['owner_present']:return fail('MissingBinding')
    if not p['document_matches']:return fail('MissingBinding')
    if p['observed_generation']!=s['generation']:return fail('StaleOwner')
    observed=p['observed_revision']
    if not u64(observed):return fail('DependencyNotReady',{'dependency':'M01_NATIVE_IDENTITY'})
    if observed!=s['revision']:return fail('StaleRevision',{'expected':s['revision'],'observed':observed})
    if r['expected_revision']!=s['revision']:return fail('StaleRevision',{'expected':r['expected_revision'],'observed':s['revision']})
    if r['sequence']!=s['sequence']:return fail('SequenceConflict',{'expected':s['sequence'],'received':r['sequence']})
    if not p['provider_ready']:return fail('DependencyNotReady',{'dependency':'M04_OWNER_INTEGRATION'})
    calls.append('immutable.capability.read')
    n=c['nodes'].get(node)
    if n is None:return fail('NodeMissing',{'node_id':node})
    if n['scope'] not in [None,'ui'] or TYPES.get(n['type'])!=a or a not in n['allowed_actions']:return fail('UnsupportedAction',{'node_id':node,'action':a})
    if n.get('asset_missing'):return fail('MissingMaterial',{'node_id':node,'asset_id':n['asset_missing']})
    if n.get('target_missing'):return fail('MissingBindingTarget',{'node_id':node,'target_id':n['target_missing']})
    if a=='SelectItem' and (not n.get('items_valid') or payload['item_id'] not in n['item_ids']):return fail('UnsupportedAction',{'node_id':node,'action':a})
    if a=='SetNumber':
        calls.append('C1.number.guard')
        if not p['number_ready']:return fail('DependencyNotReady',{'dependency':'C1_CODEC'})
        if not p['number_accepted']:return fail('CodecRejected',{'message':p['number_error']})
        # Canonical string is a C1 provider result, not a float/Decimal approximation here.
        delta={'kind':'Number','number_text':p['number_canonical']}
    else:
        delta={'Activate':{'kind':'Action'},'SetToggle':{'kind':'Toggle',**payload},'SetText':{'kind':'Text',**payload},'SelectItem':{'kind':'Selection',**payload}}[a]
    calls.append('native.delivery.recheck')
    change=p['delivery_change']
    if change=='consumer':return fail('UnauthorizedCaller')
    if change=='document':return fail('MissingBinding')
    if change=='generation':return fail('StaleOwner')
    if change=='closed':return fail('PreviewClosed')
    if change=='revision':
        actual=p.get('delivery_observed_revision')
        if not u64(actual) or actual==s['revision']:return fail('DependencyNotReady',{'dependency':'M01_NATIVE_IDENTITY'})
        return fail('StaleRevision',{'expected':s['revision'],'observed':actual})
    if int(s['sequence'])==MAX:
        s['closed']=True;calls.append('preview.close.overflow');return fail('SequenceOverflow')
    calls.append('detached.mock.commit')
    s['sequence']=str(int(s['sequence'])+1);s['mock'][node]=delta
    if a=='Activate':s['activation_count'][node]=s['activation_count'].get(node,0)+1
    return {'ok':True,'value':{'consumed_sequence':r['sequence'],'next_sequence':s['sequence'],'mock_delta':delta,'content_changed':False},'replayed':False},s,calls
