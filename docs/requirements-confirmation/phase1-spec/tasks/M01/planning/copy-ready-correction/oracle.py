"""PROPOSED document oracle only. Never performs CAS, IO, mutation or native validation."""
import copy, hashlib, json, pathlib, uuid
from types import MappingProxyType
P=pathlib.Path(__file__).resolve().parent
SCHEMA=json.loads((P/'candidate.schema.json').read_text(encoding='utf8'))
# Frozen lookup is a DOCUMENT premise, loaded outside classify, never supplied by caller.
AUTHORITY=MappingProxyType({k:json.dumps(v,sort_keys=True) for k,v in json.loads((P/'authority-fixtures.json').read_text(encoding='utf8')).items()})

def digest(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def shape_errors(value,schema,path='$'):
 kind=schema['type']; errors=[]
 expected={'object':dict,'string':str,'boolean':bool}
 if type(value) is not expected[kind]: return [path+':type']
 if kind=='object':
  keys=set(value); required=set(schema['required']); properties=schema['properties']
  errors += [path+'.'+k+':missing' for k in sorted(required-keys)]
  errors += [path+'.'+k+':unknown' for k in sorted(keys-set(properties))]
  for key in sorted(keys & set(properties)):
   errors += shape_errors(value[key],properties[key],path+'.'+key)
 elif kind=='string':
  if len(value)<schema.get('minLength',0):errors.append(path+':empty')
  if any(0xD800<=ord(ch)<=0xDFFF for ch in value):errors.append(path+':unicode')
 if 'enum' in schema and value not in schema['enum']:errors.append(path+':enum')
 return errors

def observe(fixture):
 calls=dict(classifier=1,authority_lookup=0,relational_comparison=0,CAS=0,native_IO=0,model_mutation=0,retry=0,cleanup=0)
 def result(status,error,details=None):
  return {'result':status,'error':error,'details':details or [],'state_calls':calls,'state':'UNCHANGED_DOCUMENT_INPUT'}
 errors=shape_errors(fixture,SCHEMA)
 if errors:return result('RejectedBeforeMutation','CandidateShape',errors)
 r=fixture['request']; b=r['body']; c=r['context']
 if digest(r)!=fixture['request_digest']:return result('ProofMismatch','RequestDigestMismatch')
 # UUID parsing has a narrow declared failure; no catch-all error masking.
 try: workflow=uuid.UUID(c['workflow_id'])
 except ValueError:return result('RejectedBeforeMutation','InvalidWorkflowIdentity')
 if r['operation_id']!=str(uuid.uuid5(workflow,'publish/0')):return result('ProofMismatch','TransitionMismatch')
 if b['new_project_uuid']!=c['project_uuid'] or b['new_document_uuid']!=c['document_uuid'] or b['source_project_uuid']==b['new_project_uuid'] or b['source_document_uuid']==b['new_document_uuid']:
  return result('RejectedBeforeMutation','IdentityConflict')
 if fixture['target_existing'] or not fixture['identity_valid']:return result('RejectedBeforeMutation','TargetOrIdentityRejected')
 records=fixture['issuer_records']; provider=records['provider-1']; catalog=records['catalog-1']; complete=records['copy-1']; ready=records['ready-1']
 if provider['status']!='Verified' or catalog['status']!='Verified':return result('DependencyNotReady','DependencyUnverified')
 if complete['status']!='Complete':return result('RejectedBeforeMutation','CopyIncomplete')
 calls['authority_lookup']+=1
 encoded=AUTHORITY.get(fixture['authority_fixture_id'])
 if encoded is None:return result('ProofMismatch','IssuerRecordUnavailable')
 authority=json.loads(encoded)
 # Each comparison consumes the real field, independent of the caller's rehashed DTO.
 for key in ['provider-1','catalog-1','copy-1','ready-1']:
  proof=records[key]; trusted=authority['issuer_records'][key]
  calls['relational_comparison']+=1
  if proof!=trusted:return result('ProofMismatch','IssuerRecordMismatch',[key])
  if proof['context']!=c:return result('ProofMismatch','IssuerContextMismatch',[key])
  for field,expected in trusted['binding'].items():
   calls['relational_comparison']+=1
   if b[field]!=expected:return result('ProofMismatch','IssuerBindingMismatch',[key,field])
 if b['provider_proof_id']!='provider-1' or b['catalog_proof_id']!='catalog-1' or b['copy_proof_id']!='copy-1':return result('ProofMismatch','IssuerReferenceMismatch')
 if ready['receipt_id']!='ready-1' or ready['request_digest']!=digest(r):return result('ProofMismatch','ReadyRequestMismatch')
 for proof_key,body_key in [('target_native_identity','target_native_identity'),('target_path','marker_path'),('previous_digest','expected_quarantine_raw'),('committed_digest','ready_raw'),('catalog_index_raw','catalog_index_raw'),('blob_manifest_digest','blob_manifest_digest'),('material_root_digest','material_root_digest')]:
  calls['relational_comparison']+=1
  if ready[proof_key]!=b[body_key]:return result('ProofMismatch','ReadyRelationMismatch',[body_key])
 if provider['target_native_identity']!=b['target_native_identity'] or b['marker_path']!=b['final_canonical_path']+'\\.sgenaxis\\copy-state.v1.json':return result('ProofMismatch','TargetRelationMismatch')
 if fixture['ready_cas']!=authority['ready_cas']:return result('ProofMismatch','CASFixtureMismatch')
 if authority['ready_cas']!='Verified':return result('UncertainPublication','ReadyUncertain')
 if not fixture['owner_current']:return result('DeliveryDeferred','OwnerDeliveryDeferred')
 if not fixture['source_ack']:return result('CommittedAckDeferred','SourceAckDeferred')
 return result('VerifiedPublished','None')

def classify(fixture):return observe(fixture)['result']
