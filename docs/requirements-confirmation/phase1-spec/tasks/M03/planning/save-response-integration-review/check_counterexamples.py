import json,ast,re,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent;S=D.parent/'save-response-integration'
r=json.loads((D/'review.json').read_text(encoding='utf-8'));W=next(p for p in D.parents if (p/'apps/sgenaxis-desktop').exists())
assert all(hashlib.sha256((W/p).read_bytes()).hexdigest()==h for p,h in r['preservation']['reviewed_hashes'].items())
t=ast.parse((S/'check_documents.py').read_text());f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='validate');ns={'re':re};exec(compile(ast.Module(body=[f],type_ignores=[]),'<isolated validator>','exec'),ns)
req=json.loads((S/'request.schema.json').read_text());resp=json.loads((S/'response.schema.json').read_text())
rows=json.loads((D/'counterexamples.json').read_text(encoding='utf-8'))
for row in rows:
 if row['kind'] in ['request_schema','response_precision_gap']:
  z=req if row['kind']=='request_schema' else resp
  assert ns['validate'](z,row['input'],z)==row['observed_subset_admitted']
 else:
  v=row['input'];c=v['capture'];q=v['receipt'];good=q['target_path']==c['canonical_target'] and q['previous_digest']==c['expected_previous_raw'] and q['committed_digest']==c['encoded_raw'] and bool(q['transaction_id'])
  o={'outcome':'UnverifiedOutcome','ack_calls':0} if not good else ({'outcome':'Saved','ack_calls':1} if v['condition']=='acked' else {'outcome':'CommittedAckDeferred','ack_calls':0})
  assert o==row['observed_declared_model']
print(json.dumps({'novel_probes_reproduced':len(rows),'product_tests':'NOT RUN','full_validator':'NOT RUN'}))
