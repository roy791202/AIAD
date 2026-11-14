"""Document-only candidate oracle. No provider, persistence or authentication."""
import copy,hashlib,json

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def evaluate(fixture,case):
    original=copy.deepcopy(fixture)
    body=copy.deepcopy(fixture['request_body'])
    outcome=case['observation']
    name=case['case']
    if name=='body-change':body['context']['captured_revision']='11'
    if name=='root-change':body['body']['root_manifest']['manifest_id']='changed-root'
    if outcome=='denied': result='PermissionDenied'
    elif outcome=='changed':
        assert digest(body)!=fixture['request_digest']
        result='ReplayConflict'
    elif outcome=='changed-binding':result='ProofMismatch'
    elif outcome=='precommit':result='Held'
    elif outcome in ('unknown','prooflost'):result='Indeterminate'
    elif outcome=='restart-missing':result='UnverifiedOutcome'
    elif outcome=='missing':result='NOT_PROVEN'
    elif outcome in ('same','restart-verified'):result='SameReceipt'
    elif outcome=='verified':result='Transferred'
    else:raise AssertionError('unknown documentary premise')
    assert fixture==original
    return {'outcome':result,'new_cas':1 if result=='Transferred' else 0,'release':0,'ack':0,'catalog_state_claim':'candidate after only under supplied verified CAS' if result=='Transferred' else 'no new write; unknown outcome does not prove before unchanged'}
