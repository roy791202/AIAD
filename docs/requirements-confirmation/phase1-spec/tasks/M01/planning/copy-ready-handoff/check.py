"""DOCUMENT oracle; no IO provider/Port/product implementation."""
import pathlib,json,hashlib,copy,uuid
P=pathlib.Path(__file__).resolve().parent
ROOT=P.parents[6]
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def classify(f):
 r=f['request']; b=r['body']; c=r['context']; records=f['issuer_records']
 if digest(r)!=f['request_digest']: return 'ProofMismatch'
 if r['role']!='publish' or r['operation_id']!=str(uuid.uuid5(uuid.UUID(c['workflow_id']),'publish/0')):return 'ProofMismatch'
 if b['new_project_uuid']!=c['project_uuid'] or b['new_document_uuid']!=c['document_uuid'] or b['source_project_uuid']==b['new_project_uuid'] or b['source_document_uuid']==b['new_document_uuid']:return 'RejectedBeforeMutation'
 if f['target_existing'] or not f['identity_valid']:return 'RejectedBeforeMutation'
 provider=records[b['provider_proof_id']]; catalog=records[b['catalog_proof_id']]; complete=records[b['copy_proof_id']]; ready=records['ready-1']
 for proof in [provider,catalog,complete,ready]:
  if proof['context']!=c:return 'ProofMismatch'
 if provider['issuer']!='NativeProvider' or provider['target_native_identity']!=b['target_native_identity'] or provider['status']!='Verified':return 'DependencyNotReady'
 if catalog['issuer']!='M05' or catalog['status']!='Verified':return 'DependencyNotReady'
 if catalog['catalog_index_raw']!=b['catalog_index_raw']:return 'ProofMismatch'
 if complete['issuer']!='M06' or complete['status']!='Complete':return 'RejectedBeforeMutation'
 for k in ['blob_manifest_digest','material_root_digest']:
  if complete[k]!=b[k]:return 'ProofMismatch'
 if ready['issuer']!='M01' or ready['kind']!='ProjectCopyReady' or ready['request_digest']!=digest(r):return 'ProofMismatch'
 for proof_key,body_key in [('target_native_identity','target_native_identity'),('target_path','marker_path'),('previous_digest','expected_quarantine_raw'),('committed_digest','ready_raw'),('catalog_index_raw','catalog_index_raw'),('blob_manifest_digest','blob_manifest_digest'),('material_root_digest','material_root_digest')]:
  if ready[proof_key]!=b[body_key]:return 'ProofMismatch'
 if not ready['transaction_id'] or b['marker_path']!=b['final_canonical_path']+'\\.sgenaxis\\copy-state.v1.json':return 'ProofMismatch'
 if f['ready_cas']!='Verified':return 'UncertainPublication'
 if not f['owner_current']:return 'DeliveryDeferred'
 if not f['source_ack']:return 'CommittedAckDeferred'
 return 'VerifiedPublished'
def main():
 cases=json.loads((P/'fixtures.json').read_text(encoding='utf8')); results=[]
 for c in cases:
  actual=classify(c['fixture']); assert actual==c['expected'],(c['id'],actual);results.append({'id':c['id'],'result':actual})
 probes=0
 for key in cases[0]['fixture']['request']['body']:
  f=copy.deepcopy(cases[0]['fixture']);f['request']['body'][key]='changed';assert classify(f)=='ProofMismatch';probes+=1
 for key in ['context','target_native_identity','target_path','previous_digest','committed_digest','request_digest','catalog_index_raw','blob_manifest_digest','material_root_digest']:
  f=copy.deepcopy(cases[0]['fixture']);f['issuer_records']['ready-1'][key]={} if key in ['context','target_native_identity'] else 'changed';assert classify(f)=='ProofMismatch';probes+=1
 sources=json.loads((P/'source-bindings.json').read_text(encoding='utf8'))
 for name,expected in sources['source_hashes'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
 html=(P/'index.html').read_text(encoding='utf8'); embedded=html.split('id="module-spec">')[1].split('</script>')[0];assert json.loads(embedded)==json.loads((P/'module-spec.json').read_text(encoding='utf8'))
 result={'layer':'DOCUMENT_ORACLE_ONLY','cases':results,'mutation_probes':probes,'source_bindings':len(sources['source_hashes']),'status':'PASS_DOCUMENT_CHECK_ONLY','product':'NOT RUN','valid_RED':'NOT RUN','independent':'NOT RUN'}
 print(json.dumps(result,indent=2));(P/'document-check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
