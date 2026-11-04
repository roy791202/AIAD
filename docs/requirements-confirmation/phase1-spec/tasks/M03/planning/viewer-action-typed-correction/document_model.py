"""PROPOSED_PENDING_OWNER: document-only typed provider admission, not native code."""
import copy, importlib.util, pathlib, re
P = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('original_viewer_model', P.parent/'viewer-action-integration'/'document_model.py')
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
BOOLS = ('trusted_local','consumer_matches','owner_present','document_matches','provider_ready','number_ready','number_accepted')
STRINGS = ('observed_generation','observed_revision','number_canonical','number_error','delivery_change')
CHANGES = ('none','consumer','document','generation','closed','revision')
NUMBER = r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?'

def provider_fault(c):
    """Closed record checked eagerly; no coercion or truthiness admission."""
    p = c.get('premises')
    if type(p) is not dict:
        return 'M01_NATIVE_IDENTITY'
    required = set(BOOLS + STRINGS)
    allowed = required | {'delivery_observed_revision'}
    if set(p)-allowed or required-set(p):
        return 'M01_NATIVE_IDENTITY'
    if any(type(p[k]) is not bool for k in BOOLS):
        return 'M01_NATIVE_IDENTITY'
    if any(type(p[k]) is not str for k in STRINGS):
        return 'M01_NATIVE_IDENTITY'
    if not original.u64(p['observed_generation']) or not original.u64(p['observed_revision']):
        return 'M01_NATIVE_IDENTITY'
    if p['delivery_change'] not in CHANGES:
        return 'M01_NATIVE_IDENTITY'
    if 'delivery_observed_revision' in p and not original.u64(p['delivery_observed_revision']):
        return 'M01_NATIVE_IDENTITY'
    if p['delivery_change'] == 'revision' and 'delivery_observed_revision' not in p:
        return 'M01_NATIVE_IDENTITY'
    if re.fullmatch(NUMBER, p['number_canonical']) is None or not p['number_error']:
        return 'C1_CODEC'
    nodes = c.get('nodes')
    if type(nodes) is not dict:
        return 'M04_OWNER_INTEGRATION'
    required = {'type','scope','allowed_actions'}
    allowed = required | {'asset_missing','target_missing','items_valid','item_ids'}
    for key,n in nodes.items():
        if type(key) is not str or not key or type(n) is not dict:
            return 'M04_OWNER_INTEGRATION'
        if required-set(n) or set(n)-allowed:
            return 'M04_OWNER_INTEGRATION'
        # Unknown node type and non-ui scope are legitimate unsupported capability values.
        if type(n['type']) is not str or not n['type']:
            return 'M04_OWNER_INTEGRATION'
        if n['scope'] is not None and type(n['scope']) is not str:
            return 'M04_OWNER_INTEGRATION'
        if type(n['allowed_actions']) is not list or any(type(a) is not str or a not in original.ACTIONS for a in n['allowed_actions']):
            return 'M04_OWNER_INTEGRATION'
        for field in ('asset_missing','target_missing'):
            if field in n and (type(n[field]) is not str or not n[field]):
                return 'M04_OWNER_INTEGRATION'
        if 'items_valid' in n and type(n['items_valid']) is not bool:
            return 'M04_OWNER_INTEGRATION'
        if 'item_ids' in n and (type(n['item_ids']) is not list or any(type(i) is not str for i in n['item_ids'])):
            return 'M04_OWNER_INTEGRATION'
        if n['type'] == 'ComboBox' and not {'items_valid','item_ids'} <= set(n):
            return 'M04_OWNER_INTEGRATION'
    return None

def intent(c):
    dependency = provider_fault(c)
    if dependency is not None:
        return ({'ok':False,'error':{'code':'DependencyNotReady','details':{'dependency':dependency}},'replayed':False}, copy.deepcopy(c['before']), [])
    return original.intent(c)
