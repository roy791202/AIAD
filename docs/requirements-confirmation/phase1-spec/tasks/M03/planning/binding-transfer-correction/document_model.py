"""PROPOSED document model only. No native provider and no product implementation.

The fixture combines a sole M04 owner double (writer/generation/document) and
M03 derived caches for observing one atomic transition. This is not permission
for a facade to store a second authoritative writer or document registry.
Authority.mint is a privileged fixture premise, never an IPC-supplied object.
"""
from copy import deepcopy
import pathlib, json
from schema_subset import Draft202012Validator
MISSING=object()
REQUEST=json.loads(pathlib.Path(__file__).with_name('request.schema.json').read_text(encoding='utf-8'))

UUID = 'abcdef01-abcd-4abc-8abc-abcdef012345'
IDENTITY = ('binding_ref','document_uuid','session_uuid','project_uuid','root_instance','runtime_epoch')
class Authority:
    def __init__(self): self.records = {}
    def mint(self, record):
        token = object(); self.records[token] = deepcopy(record); return token
    def read(self, token): return deepcopy(self.records.get(token))

def fresh():
    return dict(identity={k: UUID for k in IDENTITY}, generation='7', revision='9',
        writer='source-1', source_active=True, target_active=True, captured_target='target-1',
        candidates=['c1'], previews=['p1'], disclosure=['install1'], inflight=['install1','save1'],
        tombstones=[], capacity=2, transfers=0,
        document=dict(content='source',history=['h0','h1'],revision='9',dirty=True,
            formal_baseline='f0',live_roots=['r1'],history_roots=['r0'],closed=False),
        forbidden_calls=dict(S1_constructor=0,content_mutation=0,formal_IO=0,ACK=0,material_release=0))

def observation(s):
    return dict(s['identity'], source='source-1',target='target-1',source_label='main',
        target_label='ui-editor',source_live=True,target_live=True,target_ready=True,
        target_consent=True,target_revoked=False,target_dirty=False,discard_confirmed=False,
        owner_generation=s['generation'],revision=s['revision'],unique_owner=True,target_unique=True)

def typed(o):
    return type(o) is dict and all(type(o.get(k)) is str for k in (*IDENTITY,'source','target','source_label','target_label','owner_generation','revision')) and all(type(o.get(k)) is bool for k in ('source_live','target_live','target_ready','target_consent','target_revoked','target_dirty','discard_confirmed','unique_owner','target_unique'))

def state_typed(s):
    return type(s) is dict and type(s.get('identity')) is dict and all(type(s['identity'].get(k)) is str for k in IDENTITY) and all(type(s.get(k)) is str for k in ('generation','revision','writer','captured_target')) and all(type(s.get(k)) is bool for k in ('source_active','target_active')) and type(s.get('capacity')) is int and s['capacity']>=0 and type(s.get('transfers')) is int and all(type(s.get(k)) is list for k in ('candidates','previews','disclosure','inflight','tombstones'))

def transfer(s,r,caller,a,token,provider=MISSING,outcome=MISSING):
    # Injected native identity, never request fields. Exact nonce, not label equality.
    if type(caller) is not tuple or len(caller)!=4 or caller[0] not in ('main','ui-editor') or caller[1]!='source-1' or caller[2]!='tauri://localhost' or type(caller[3]) is not bool or not caller[3]: return 'UnauthorizedCaller'
    try: Draft202012Validator(REQUEST).validate(r)
    except AssertionError: return 'InvalidRequest'
    if type(provider) is not bool or not provider: return 'DependencyNotReady'
    if type(outcome) is not str or outcome not in ('commit','rollback','unknown','ack-lost'): return 'Indeterminate'
    if not state_typed(s): return 'ProofMismatch'
    o=a.read(token)
    if not typed(o): return 'ProofMismatch'
    if caller[0]!=o['source_label']: return 'UnauthorizedCaller'
    if any(o[k]!=s['identity'][k] for k in IDENTITY) or not o['unique_owner']: return 'IdentityConflict'
    if r['binding_ref']!=s['identity']['binding_ref']: return 'MissingBinding'
    if s['writer']!=o['source'] or not s['source_active'] or not o['source_live']: return 'StaleOwner'
    if r['expected_generation']!=s['generation'] or o['owner_generation']!=s['generation']: return 'StaleOwner'
    if r['expected_revision']!=s['revision'] or o['revision']!=s['revision']: return 'StaleRevision'
    if o['target_label']!=r['target_window'] or o['target_label'] not in ('main','ui-editor') or o['target']==o['source']: return 'UnauthorizedCaller'
    if not s['target_active'] or not o['target_live'] or o['target_revoked']: return 'MissingBinding'
    if not o['target_unique'] or o['target']!=s['captured_target']: return 'DependencyNotReady'
    if not o['target_ready'] or not o['target_consent']: return 'DependencyNotReady'
    # transfer does not discard shared document dirtiness; guard protects target local state.
    if o['target_dirty'] and not o['discard_confirmed']: return 'Busy'
    if s['generation']=='18446744073709551615': return 'RevisionOverflow'
    if len(s['tombstones'])>=s['capacity']: return 'CapacityExceeded'
    if outcome=='rollback': return 'IoFailure'
    if outcome=='unknown': return 'Indeterminate' # Never claim unchanged or retry.
    old=s['generation']; s['generation']=str(int(old)+1); s['writer']=o['target']
    s['source_active']=False; s['candidates']=[];s['previews']=[];s['disclosure']=[]
    s['tombstones'].append(dict(identity=deepcopy(s['identity']),source=o['source'],generation=old))
    s['transfers']+=1
    return 'TransferredAckDeferred' if outcome=='ack-lost' else 'Transferred'

def delivery(s,issued):
    return s['source_active'] and issued==s['generation'] and s['writer']=='source-1'

def exercise(mode):
    s=fresh();a=Authority();o=observation(s);r=dict(binding_ref=UUID,expected_generation='7',expected_revision='9',target_window='ui-editor')
    caller=('main','source-1','tauri://localhost',True);provider=True;outcome='commit'
    if mode=='viewer':caller=('ui-viewer','source-1','tauri://localhost',True)
    if mode=='remote':caller=('main','source-1','https://remote.invalid',True)
    if mode=='forged-label':caller=('main','replacement-1','tauri://localhost',True)
    if mode=='numeric-caller-live':caller=('main','source-1','tauri://localhost',1)
    if mode=='editor-source':caller=('ui-editor','source-1','tauri://localhost',True);o['source_label']='ui-editor'
    if mode=='provider':provider=False
    if mode=='identity':o['session_uuid']='foreign'
    if mode=='duplicate-owner':o['unique_owner']=False
    if mode=='generation':r['expected_generation']='6'
    if mode=='revision':r['expected_revision']='8'
    if mode=='missing-binding':r['binding_ref']='00000000-0000-4000-8000-000000000000'
    if mode=='missing-target':o['target_live']=False
    if mode=='ambiguous-target':o['target_unique']=False
    if mode=='changed-target-instance':o['target']='target-2'
    if mode=='revoked-target':o['target_revoked']=True
    if mode=='unready-target':o['target_ready']=False
    if mode=='no-consent':o['target_consent']=False
    if mode=='viewer-target':o['target_label']='ui-viewer'
    if mode=='dirty-target':o['target_dirty']=True
    if mode=='discard-target':o['target_dirty']=True;o['discard_confirmed']=True
    if mode=='typed-false':o['target_live']=0
    if mode=='overflow':s['generation']=r['expected_generation']=o['owner_generation']='18446744073709551615'
    if mode=='capacity':s['tombstones']=[{},{}]
    if mode in ('rollback','unknown','ack-lost'):outcome=mode
    token=a.mint(o)
    if mode=='forged-proof':token=object()
    before=deepcopy(s);result=transfer(s,r,caller,a,token,provider,outcome)
    if mode=='target-dead-after-commit':
        assert result=='Transferred';s['target_active']=False
        # Native target destruction retires authority separately; no source restoration.
        result='TransferredTargetUnavailable'
        assert s['writer']=='target-1' and not s['source_active']
    if mode in ('repeat','late-install','late-ack','late-get'):
        assert result=='Transferred'
        if mode=='repeat':result=transfer(s,r,caller,a,token,True,'commit')
        else:result='Discarded' if not delivery(s,'7') else 'Delivered'
    assert s['document']==before['document']
    assert not any(s['forbidden_calls'].values())
    assert s['inflight']==before['inflight']
    if s['transfers']:
        assert s['writer']=='target-1' and s['generation']=='8' and not s['source_active']
        assert not s['candidates'] and not s['previews'] and not s['disclosure']
    elif outcome!='unknown':assert s==before
    return dict(result=result,transfers=s['transfers'],document_unchanged=True,
        uncertainty='no assertion of native unchanged' if outcome=='unknown' else None,
        late_delivery=delivery(s,'7'))
