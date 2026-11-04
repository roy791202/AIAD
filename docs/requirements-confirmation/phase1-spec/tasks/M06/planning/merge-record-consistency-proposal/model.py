"""Bounded DOCUMENT consistency validator; frozen identity is a premise, not authentication.

This deliberately recognizes one retained fixture domain, not arbitrary native records.
Every declared field is checked by the generated closed schema, including evidence
whose native producer is unavailable. No state writer or new Port exists here.
"""
from pathlib import Path
import copy
import importlib.util
import json
import re
from functools import lru_cache

P = Path(__file__).resolve().parent
S = P.parent / 'merge-retention-handoff'
spec = importlib.util.spec_from_file_location('retained_document_oracle', S / 'model.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
legacy.read = lru_cache(maxsize=None)(legacy.read)

@lru_cache(maxsize=None)
def read(name):
    return json.loads((P / name).read_text(encoding='utf-8-sig'))

def evaluate(request, records=None):
    retained = read('retained-issuer-fixture.json')
    records = copy.deepcopy(retained if records is None else records)
    shape = legacy.read('fixture-input.schema.json')
    schema = read('record-domain.schema.json')
    # Proposed precedence: caller shape, record domain, existing proof checks,
    # observations. Record contradictions cannot reach document commit.
    if not legacy.valid(request, shape, shape):
        return run_legacy(request, retained)
    normalized = normalize_catalog_generations(records, retained)
    if normalized is None or not legacy.valid(normalized, schema, schema):
        result = run_legacy(request, retained)
        result.update(result='RecordConsistencyRejected', before=copy.deepcopy(retained['before']),
                      after=copy.deepcopy(retained['before']),
                      calls={key: 0 for key in result['calls']},
                      claim='bounded documentary record domain rejection; no native authenticity claim')
        return result
    return run_legacy(request, records)

def normalize_catalog_generations(records, retained):
    """One coherent CAS offset is allowed; owner generations/revisions stay frozen.

    Request digests are recomputed from complete requests, never patched literals.
    Each committed generation must remain expected+1 at its mapped transition.
    """
    value = copy.deepcopy(records)
    try:
        start = records['import_request']['body']['expected_catalog_generation']
        if type(start) is not str or not re.fullmatch(r'0|[1-9][0-9]*', start):
            return None
        delta = int(start) - int(retained['import_request']['body']['expected_catalog_generation'])
        def visit(actual, frozen):
            if isinstance(frozen, dict):
                if type(actual) is not dict or set(actual) != set(frozen):return False
                for key, old in frozen.items():
                    if key in ('expected_catalog_generation','expected_generation','committed_generation') and ('request_digest' in frozen or key=='expected_catalog_generation'):
                        new=actual[key]
                        if type(new) is not str or not re.fullmatch(r'0|[1-9][0-9]*',new) or int(new)>18446744073709551615 or int(new)!=int(old)+delta:return False
                        actual[key]=old
                    elif not visit(actual[key],old):return False
            elif isinstance(frozen,list):
                if type(actual) is not list or len(actual)!=len(frozen):return False
                return all(visit(a,b) for a,b in zip(actual,frozen))
            return True
        if not visit(value,retained):return None
        requests=[records['import_request']]+records['merge_transfer']+records['undo_transfer']
        frozen_requests=[retained['import_request']]+retained['merge_transfer']+retained['undo_transfer']
        actual_records=[records['import_record']]+records['transfer_records']
        normalized_records=[value['import_record']]+value['transfer_records']
        for record,norm,req,frozen in zip(actual_records,normalized_records,requests,frozen_requests):
            if record['request_digest']!=legacy.digest(req):return None
            norm['request_digest']=legacy.digest(frozen)
        return value
    except (KeyError,TypeError,ValueError):
        return None

def run_legacy(request, records):
    original = legacy.read
    legacy.read = lambda name: copy.deepcopy(records) if name == 'immutable-issuer-fixture.json' else original(name)
    try:
        return legacy.evaluate(copy.deepcopy(request))
    finally:
        legacy.read = original
