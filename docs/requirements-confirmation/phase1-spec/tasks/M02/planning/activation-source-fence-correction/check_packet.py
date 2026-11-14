"""Bounded DOCUMENT evaluator, not Draft JSON Schema or product behavior."""
from pathlib import Path
import copy,hashlib,json,re
ROOT=Path(__file__).resolve().parent
SUPPORTED={'type','required','additionalProperties','properties','items','minItems','maxItems','minLength','maxLength','minimum','maximum','enum','pattern','anyOf'}
def validate_schema(v,r):
 if set(r)-SUPPORTED:raise ValueError('unsupported schema keywords')
 if 'anyOf' in r:
  errors=[]
  for b in r['anyOf']:
   try:validate_schema(v,b);return
   except ValueError as e:errors.append(str(e))
  raise ValueError('no alternative')
 kinds={'object':dict,'array':list,'string':str,'integer':int,'boolean':bool,'null':type(None)}
 t=r.get('type')
 if t not in kinds or type(v) is not kinds[t]:raise ValueError('type')
 if 'enum' in r and v not in r['enum']:raise ValueError('enum')
 if t=='object':
  if not set(r.get('required',[]))<=set(v):raise ValueError('required')
  if r.get('additionalProperties') is not False:raise ValueError('open schema unsupported')
  if set(v)-set(r['properties']):raise ValueError('unknown property')
  for k,x in v.items():validate_schema(x,r['properties'][k])
 if t=='array':
  if not r.get('minItems',0)<=len(v)<=r.get('maxItems',16):raise ValueError('array bounds')
  for x in v:validate_schema(x,r['items'])
 if t=='string':
  if not r.get('minLength',0)<=len(v)<=r.get('maxLength',256):raise ValueError('string bounds')
  if 'pattern' in r and re.fullmatch(r['pattern'],v,flags=re.ASCII) is None:raise ValueError('pattern')
 if t=='integer' and not r.get('minimum',0)<=v<=r.get('maximum',18446744073709551615):raise ValueError('u64 bounds')
def audit_schema(r):
 if set(r)-SUPPORTED:raise ValueError('unsupported schema keywords')
 for b in r.get('anyOf',[]):audit_schema(b)
 for b in r.get('properties',{}).values():audit_schema(b)
 if 'items' in r:audit_schema(r['items'])
def fields(x,excluded=()):return {k:v for k,v in x.items() if k not in excluded}
def decide(o,a):
 # Order below is PROPOSED_PENDING_OWNER. Existing error precedence preserved.
 if o['implicit_save_calls']:return 'ForbiddenImplicitSave'
 if o['automatic_retry_count']:return 'ForbiddenAutomaticRetry'
 if o['owner_before_cas']!=o['owner_captured']:return 'StaleOwnerBeforeCAS'
 d=o['design_saved_proof']
 if not d['verified'] or fields(d,('verified',))!=a['design_saved_proof'] or d['captured_revision']!=o['owner_captured']['captured_revision'] or d['digest']!=o['sources'][2]['captured']['typed_digest']:return 'DesignSaveRequired'
 if o['request']!=a['request'] or o['owner_captured']!=a['owner'] or [fields(x,('verified',)) for x in o['approved_refs']]!=a['approved_refs']:return 'DependencyNotReady'
 if not all(s['producer_coverage_complete'] for s in o['sources']) or not all(x['verified'] and x['state']=='Approved' for x in o['approved_refs']) or not all((o['template']['golden14_verified'],o['template']['transitive_lock_verified'],o['native']['identity_verified'],o['native']['provider_verified'],o['projector']['verified'])):return 'DependencyNotReady'
 if o['template']['immutable_digest']!=a['template_digest'] or o['projector']['typed_profile']!=a['profile'] or o['native']['target_identity']!=a['native_target'] or o['expected_active']!=a['active']:return 'DependencyNotReady'
 sources=o['sources']
 if len(sources)!=len(a['sources']) or [s['captured'] for s in sources]!=a['sources']:return 'SourceFenceInvalid'
 if any(s['captured']['project_uuid']!=o['owner_captured']['project_uuid'] or s['captured']['owner_generation']!=o['owner_captured']['owner_generation'] or not s['reservation_held'] or s['captured']!=s['held'] for s in sources) or o['mutation_attempt']['changed']:return 'SourceFenceInvalid'
 if o['mutation_attempt']['attempted'] and o['mutation_attempt']['result'] not in ('Busy','defer'):return 'SourceFenceInvalid'
 if not o['seal']['verified'] or not o['seal']['exact_files_verified'] or fields(o['seal'],('verified','exact_files_verified'))!=a['seal']:return 'VersionSealedNotActivated'
 if o['cas']['outcome']=='unknown':return 'UncertainPublication'
 if o['cas']['outcome']=='rejected':return 'VersionSealedNotActivated'
 r=o['cas']['receipt'];e=a['active']
 if not r or not r['issuer_record_present'] or r['kind']!='GenerationActivation' or not r['transaction_id'] or r['target_identity']!=a['native_target'] or r['previous_raw_digest']!=e['previous_raw_digest'] or r['committed_raw_digest']!=e['committed_raw_digest']:return 'UnverifiedOutcome'
 return 'GenerationActivated' if o['owner_delivery']==o['owner_captured'] else 'ActivatedDeliveryDeferred'
def evaluate(packet,records=None,schema=None):
 before=copy.deepcopy(packet);calls=['validate_schema']
 try:
  rule=schema or json.loads((ROOT/'schema.json').read_text());audit_schema(rule);validate_schema(packet,rule)
 except ValueError:return {'result':'SchemaRejected','calls':calls,'mutation':False}
 records=records or json.loads((ROOT/'immutable-records.json').read_text())
 a=records.get(packet['fixture_id']);calls.append('immutable_fixture_lookup')
 if a is None:result='DependencyNotReady'
 else:calls.append('relational_body_comparison');result=decide(packet['observation'],a)
 assert packet==before
 return {'result':result,'calls':calls,'mutation':False}
def main():
 load=lambda n:json.loads((ROOT/n).read_text(encoding='utf8'))
 results=[]
 for c in load('fixtures.json'):
  r=evaluate(c['input']);assert r['result']==c['expected'],(c['id'],r,c['expected']);results.append({'id':c['id'],**r})
 for c in load('closures.json'):
  r=evaluate(c['input']);assert r['result'] in c['allowed_after'],(c['id'],r);results.append({'id':c['id'],'before':c['before'],**r})
 for c in load('targeted.json'):
  r=evaluate(c['input']);assert r['result']==c['expected'],(c['id'],r,c['expected']);results.append({'id':c['id'],**r})
 for kw in ['format','not','oneOf','$ref']:
  r=evaluate(load('fixtures.json')[0]['input'],schema={'type':'object',kw:True});assert r['result']=='SchemaRejected'
 embedded=(ROOT/'index.html').read_text(encoding='utf8').split('<script type="application/json" id="module-spec">')[1].split('</script>')[0]
 assert json.loads(embedded)==load('module-spec.json')
 # Original raw fixture outputs are compared without claiming legacy input passes the proposed schema.
 import importlib.util
 oldpath=ROOT.parent/'activation-source-fence-handoff/check_packet.py'
 oldspec=importlib.util.spec_from_file_location('legacy_document_oracle',oldpath)
 oldmodule=importlib.util.module_from_spec(oldspec);oldspec.loader.exec_module(oldmodule)
 for c in load('legacy-fixtures.json')['cases']:assert oldmodule.oracle(c['observation'])==c['expected']
 hashes=load('artifact-hashes.json')
 for n,h in hashes.items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
 seal=load('seal.json');assert seal['artifact_count']==len(hashes);assert seal['manifest_sha256']==hashlib.sha256((ROOT/'artifact-hashes.json').read_bytes()).hexdigest()
 print(json.dumps({'document_self_check':'PASS','cases':len(results),'original_behaviors':22,'review_closures':12,'targeted':len(load('targeted.json')),'unsupported_keyword_probes':4,'hashes':len(hashes),'results':results,'independent_acceptance':'NOT RUN','valid_RED':'NOT RUN','product':'NOT RUN'},indent=2))
if __name__=='__main__':main()
