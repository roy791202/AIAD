"""Document oracle only: consumes immutable observation fields, never calls production."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parent
def oracle(o):
 if o['implicit_save_calls']:return 'ForbiddenImplicitSave'
 if o['automatic_retry_count']:return 'ForbiddenAutomaticRetry'
 if o['owner_before_cas']!=o['owner_captured']:return 'StaleOwnerBeforeCAS'
 if not o['design_saved_proof']['verified'] or o['design_saved_proof']['captured_revision']!=o['owner_captured']['captured_revision'] or o['design_saved_proof']['digest']!=o['sources'][2]['captured']['typed_digest']:return 'DesignSaveRequired'
 if not all(s['producer_coverage_complete'] for s in o['sources']) or not all(a['verified'] and a['state']=='Approved' for a in o['approved_refs']) or not all((o['template']['golden14_verified'],o['template']['transitive_lock_verified'],o['native']['identity_verified'],o['native']['provider_verified'],o['projector']['verified'])):return 'DependencyNotReady'
 if any(not s['reservation_held'] or s['captured']!=s['held'] for s in o['sources']) or o['mutation_attempt']['changed']:return 'SourceFenceInvalid'
 if o['mutation_attempt']['attempted'] and o['mutation_attempt']['result'] not in ('Busy','defer'):return 'SourceFenceInvalid'
 if not o['seal']['verified'] or not o['seal']['exact_files_verified']:return 'VersionSealedNotActivated'
 if o['cas']['outcome']=='unknown':return 'UncertainPublication'
 if o['cas']['outcome']=='rejected':return 'VersionSealedNotActivated'
 r=o['cas']['receipt'];e=o['expected_active']
 if not r or not r['issuer_record_present'] or r['kind']!='GenerationActivation' or not r['transaction_id'] or r['target_identity']!=o['native']['target_identity'] or r['previous_raw_digest']!=e['previous_raw_digest'] or r['committed_raw_digest']!=e['committed_raw_digest']:return 'UnverifiedOutcome'
 return 'GenerationActivated' if o['owner_delivery']==o['owner_captured'] else 'ActivatedDeliveryDeferred'
def validate_schema(value, rule):
 if 'anyOf' in rule:
  for branch in rule['anyOf']:
   try:validate_schema(value,branch);return
   except AssertionError:pass
  raise AssertionError('no schema alternative')
 kind=rule['type'];types={'object':dict,'array':list,'string':str,'integer':int,'boolean':bool,'null':type(None)}
 assert isinstance(value,types[kind]) and not (kind=='integer' and isinstance(value,bool)),kind
 if kind=='object':
  assert set(rule['required'])<=set(value)
  if not rule.get('additionalProperties',True):assert set(value)<=set(rule['properties'])
  for k,v in value.items():validate_schema(v,rule['properties'][k])
 if kind=='array':
  assert len(value)>=rule.get('minItems',0)
  for v in value:validate_schema(v,rule['items'])
 if kind=='string':assert len(value)>=rule.get('minLength',0)
 if kind=='integer':assert value>=rule.get('minimum',value)
def main():
 f=json.loads((ROOT/'fixtures.json').read_text(encoding='utf-8'));results=[]
 for c in f['cases']:
  validate_schema(c['observation'],json.loads((ROOT/'schema.json').read_text()))
  actual=oracle(c['observation']);assert actual==c['expected'],(c['id'],actual,c['expected']);results.append({'id':c['id'],'actual':actual})
 # Renaming scenario labels cannot change computed results; observations carry semantics.
 for case in f['cases']:
  assert oracle(case['observation'])==case['expected']
 spec=json.loads((ROOT/'module-spec.json').read_text(encoding='utf-8'))
 for row in spec['proof_mapping']:
  path,ptr=row['source'].split('#');value=json.loads((ROOT/path).read_text(encoding='utf-8'))
  for part in ptr.strip('/').split('/'):value=value[part]
 hashes=json.loads((ROOT/'artifact-hashes.json').read_text())
 for n,h in hashes.items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
 seal=json.loads((ROOT/'seal.json').read_text())
 assert seal['artifact_count']==len(hashes)
 assert seal['manifest_sha256']==hashlib.sha256((ROOT/'artifact-hashes.json').read_bytes()).hexdigest()
 print(json.dumps({'document_oracle':'PASS','observations':len(results),'hashes':len(hashes),'product_valid_RED':'NOT RUN','independent_acceptance':'NOT RUN','results':results},indent=2))
if __name__=='__main__':main()
