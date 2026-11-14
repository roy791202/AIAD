"""Executable DOCUMENT oracle, not a runtime implementation or acceptance test.

Fixture authorities stand for existing single M04 owner and M05 issuer lookups.
They do not introduce a product registry, cryptography, persistence or ports.
"""
import copy
import hashlib
import json
import pathlib
import re
import uuid

P = pathlib.Path(__file__).parent


def read(name):
    return json.loads((P / name).read_text(encoding='utf8'))


def strict(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {'expected_revision', 'expected_generation', 'before_revision',
                       'after_revision', 'history_depth', 'revision', 'owner_generation',
                       'history_before', 'history_after', 'redo_before', 'redo_after',
                       'epoch', 'version', 'ordinal'}:
                assert type(item) is str and re.fullmatch(r'0|[1-9][0-9]*', item)
                assert int(item) <= 18446744073709551615
            strict(item)
    elif isinstance(value, list):
        for item in value:
            strict(item)


# Reuse ONLY the schema interpreter source; never import its top-level old suites.
_old = (P.parent / 'undo-response-integration/check_documents.py').read_text(encoding='utf8')
exec(_old[_old.index('class Draft202012Validator:'):_old.index('P=pathlib.Path')])


def validate(req, res):
    Draft202012Validator(read('request.schema.json')).validate(req)
    Draft202012Validator(read('response.schema.json')).validate(res)
    strict(req)
    strict(res)
    if not res['ok'] and res['error']['code'] == 'DomainRejected':
        assert any(res['error'] == row['wire']['error'] for row in read('work-error-map.json'))
    if res['ok']:
        v = res['value']
        assert v['outcome'] != 'NoChange', 'Undo never has NoChange success'
        assert v['replayed'] == res['replayed']
        assert v['projection']['revision'] == v['after_revision']
        assert v['before_revision'] == req['expected_revision']
        assert int(v['after_revision']) == int(v['before_revision']) + 1


def proofcheck(p, trusted):
    """Full typed fixture lookup equality, never accept a caller-minted record."""
    strict(p)
    c = p['capture']
    m = p['mutation']
    pin = p['pin']
    roots = p['roots']
    assert c == trusted['capture'], 'immutable authorized request context'
    assert m == trusted['M04_record'], 'M04 owner immutable lookup'
    assert pin == trusted['M05_pin_record'], 'M05 actual retention lookup'
    assert roots == trusted['M05_root_record'], 'M05 complete version-set lookup'
    assert m['issuer'] == 'M04' and m['kind'] == 'DocumentMutation'
    assert pin['issuer'] == roots['issuer'] == 'M05'
    assert m['context'] == pin['context'] == roots['context'] == c
    assert m['operation_role'] == pin['operation_role'] == 'undo'
    assert m['ordinal'] == pin['ordinal'] == '0'
    assert m['operation_id'] == str(uuid.uuid5(uuid.UUID(c['workflow_id']), 'undo/0'))
    assert pin['transition_role'] == 'pin' and pin['purpose'] == 'Undo'
    assert pin['operation_id'] == str(uuid.uuid5(uuid.UUID(c['workflow_id']), 'pin/0'))
    assert m['pin_id'] == pin['pin_id'] == roots['pin_id']
    assert m['before_revision'] == c['expected_revision']
    assert int(m['after_revision']) == int(m['before_revision']) + 1
    assert int(m['history_after']) == int(m['history_before']) - 1
    assert int(m['redo_after']) == int(m['redo_before']) + 1
    assert pin['actual_state'] == 'Held'
    assert roots['completeness'] == 'Complete' and roots['fenced'] is True
    assert roots['scope'] == c['document_uuid'] + '/' + c['session_uuid']
    kinds = {'LiveDocuments', 'UndoHistory', 'RedoHistory', 'RecoverySnapshots', 'InFlightTransactions'}
    assert set(roots['before']) == set(roots['after']) == kinds
    for kind in kinds:
        old, new = roots['before'][kind], roots['after'][kind]
        assert old['provider'] == new['provider']
        assert old['epoch'] == new['epoch'] == roots['epoch']
        assert old['complete'] is new['complete'] is True
        assert int(new['version']) == int(old['version']) + (kind in {'LiveDocuments', 'UndoHistory', 'RedoHistory'})
    assert m['restored_versions'] == roots['after']['LiveDocuments']['material_versions']
    assert m['surviving_history_versions'] == roots['after']['UndoHistory']['material_versions']
    assert m['outgoing_versions'] == roots['after']['RedoHistory']['material_versions']
    required = {tuple(v) for key in ('restored_versions', 'outgoing_versions') for v in m[key]}
    assert required <= {tuple(v) for v in pin['material_versions']}
    assert p['io'] == {'FileCommit': 'NOT CALLED', 'formal_save_ack': 'NOT CALLED', 'formal_root_transfer': 'NOT CALLED'}


def lifecycle(case):
    """Pure fixture reducer; native authority checks are premises, not proved."""
    s, e = copy.deepcopy(case['state']), case['event']
    result = {'live_revision': s['live_revision'], 'undo_calls': 0,
              'retained': True, 'deliver': False, 'render': False,
              'pin_state': s['pin_state'], 'release': False}
    # Native sender/window and owner binding come from out-of-band fixture state.
    if (not s['authorized'] or s['closed'] or e['sender'] != s['owner_sender']
            or e['generation'] != s['owner_generation']):
        return dict(result, outcome='UnauthorizedCaller')
    if e['capture'] != s['immutable_capture']:
        return dict(result, outcome='ReplayConflict')
    if s['inflight']:
        return dict(result, outcome='InProgress')
    # Uncertainty wins before using any cached terminal candidate.
    if not s['M04_commit_established']:
        return dict(result, outcome='Indeterminate')
    if s['retained_terminal'] is not None:
        terminal = copy.deepcopy(s['retained_terminal'])
        terminal['replayed'] = True
        return dict(result, outcome='RetainedReplay', deliver=True,
                    terminal=terminal, render=terminal.get('revision') == s['live_revision'])
    if not s['retention_verified']:
        return dict(result, outcome='AppliedRetentionDeferred', deliver=True)
    return dict(result, outcome='Applied', deliver=True)


def evidence_decision(presented, trusted, owner_lookup):
    """Decision follows separately resolved M04 fact, not a presented receipt."""
    if owner_lookup is None or owner_lookup != trusted['M04_record']:
        return {'outcome':'Indeterminate','actual_revision':None,'rollback':False,'release':False}
    try:
        proofcheck(presented, trusted)
        outcome = 'Applied'
    except (AssertionError, KeyError, TypeError, ValueError):
        outcome = 'AppliedRetentionDeferred'
    return {'outcome':outcome,'actual_revision':owner_lookup['after_revision'],'rollback':False,'release':False}


def main():
    results = []
    def check(case_id, action, expected=True):
        try:
            action()
            accepted = True
        except (AssertionError, KeyError, TypeError, ValueError):
            accepted = False
        assert accepted == expected, case_id
        results.append({'id': case_id, 'result': 'PASS_DOCUMENT_ORACLE_ONLY'})
    fixtures = read('fixtures.json')
    for row in fixtures['wire']:
        if 'schema_valid' in row:
            check(row['id']+'-shared-schema', lambda row=row: Draft202012Validator(read('response.schema.json')).validate(row['response']), row['schema_valid'])
        check(row['id'], lambda row=row: validate(row['request'], row['response']), row['valid'])
    trust = fixtures['trusted_fixture_records']
    base = fixtures['presented_proof']
    check('CORR-PROOF-BASE', lambda: proofcheck(base, trust))
    assert evidence_decision(base, trust, trust['M04_record']) == {'outcome':'Applied','actual_revision':'8','rollback':False,'release':False}
    for lookup in [None, trust['M05_pin_record']]:
        assert evidence_decision(base, trust, lookup) == {'outcome':'Indeterminate','actual_revision':None,'rollback':False,'release':False}
        results.append({'id':'CORR-UNVERIFIED-M04-'+('missing' if lookup is None else 'M05-not-M04'), 'result':'PASS_DOCUMENT_ORACLE_ONLY'})
    for row in read('mutation-matrix.json'):
        q = copy.deepcopy(base)
        for mutation in row['changes']:
            obj = q
            parts = mutation['path'].split('.')
            for part in parts[:-1]:
                obj = obj[int(part)] if isinstance(obj, list) else obj[part]
            obj[int(parts[-1]) if isinstance(obj, list) else parts[-1]] = mutation['value']
        check(row['id'], lambda q=q: proofcheck(q, trust), False)
        # Separate lookup has already established the real M04 commit at R8.
        # Rejecting a presented proof never turns that authoritative fact into rollback.
        actual_effect = evidence_decision(q, trust, trust['M04_record'])
        assert actual_effect == row['expected_confirmed_commit_effect'], row['id']
    for row in fixtures['lifecycle']:
        actual = lifecycle(row)
        assert actual == row['expected'], (row['id'], actual, row['expected'])
        results.append({'id': row['id'], 'result': 'PASS_DOCUMENT_STATE_ORACLE_ONLY', 'observed': actual})
    for value, valid in fixtures['u64']:
        check('CORR-U64-' + repr(value), lambda value=value: strict({'revision': value}), valid)
    source = read('source-current.json')
    authority_path = pathlib.Path(source['authority_manifest'])
    assert hashlib.sha256(authority_path.read_bytes()).hexdigest() == source['authority_manifest_sha256']
    authority = json.loads(authority_path.read_text(encoding='utf8'))['source_hashes']
    assert len(authority) == source['authority_count_currently_compared'] == 796
    drift = [name for name,digest in authority.items() if not pathlib.Path(name).exists() or hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()!=digest]
    assert drift == source['authority_drift_current']
    for name, digest in source['sources'].items():
        assert hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest() == digest, name
    embedded = re.search(r'<script id="module-spec" type="application/json">(.*?)</script>', (P/'index.html').read_text(encoding='utf8'), re.S)
    assert json.loads(embedded[1]) == read('module-spec.json')
    output = {'status': 'PASS_DOCUMENT_AUTHOR_SELF_CHECK_ONLY', 'author': '/root/m03_undo_correction',
              'independent_acceptance': 'NOT RUN', 'Owner_adoption': 'NOT ADOPTED',
              'product_tests': 'NOT RUN', 'native_runtime': 'NOT RUN', 'RED': 'NOT RUN',
              'GREEN': 'NOT RUN', 'BUILD': 'NOT RUN', 'fullDraft': 'MISSING',
              'skeleton': 'NOT CREATED', 'module_complete': False,
              'old_save181_rerun': False, 'old_undo58_rerun': False,
              'historical_authority_entries_compared':796,'authority_drift_current':drift,
              'new_revision_cases': len(results), 'results': results}
    (P/'verification.json').write_text(json.dumps(output, indent=2)+'\n', encoding='utf8')
    print(json.dumps({k:v for k,v in output.items() if k!='results'}))


if __name__ == '__main__':
    main()
