"""Read-only author consistency check; never independent acceptance or native RED."""
import ast, hashlib, json, pathlib, subprocess, sys
sys.dont_write_bytecode=True
P=pathlib.Path(__file__).resolve().parent
O=P.parent/'candidate-prepare-integration'
sys.path.insert(0,str(P))
from schema_subset import Draft202012Validator
def read(n):return json.loads((P/n).read_text(encoding='utf8'))
def drop(x):
 if isinstance(x,dict):return {k:drop(v) for k,v in x.items() if k!='pattern'}
 if isinstance(x,list):return [drop(v) for v in x]
 return x
def main():
 for n in ['request.schema.json','response.schema.json']:
  assert drop(read(n))==drop(json.loads((O/n).read_text(encoding='utf8')))
 for n,entry in read('before-after.json')['preserved'].items():
  assert (P/n).read_bytes()==(O/n).read_bytes()
  assert hashlib.sha256((P/n).read_bytes()).hexdigest()==entry['after']
 for n in ['schema_subset.py','check_documents.py']:
  assert ast.dump(ast.parse((P/n).read_text()))==ast.dump(ast.parse((O/n).read_text()))
 roots={n:read(n) for n in ['request.schema.json','response.schema.json']}
 cases=read('lexical-fixtures.json')
 for c in cases:
  try:Draft202012Validator(roots[c['schema']]).validate(c['instance']);actual=True
  except AssertionError:actual=False
  assert actual==c['expected_accept'],c['id']
 node=json.loads(subprocess.check_output(['node',str(P/'probe.cjs')],text=True));assert not node['mismatches']
 for n,h in read('artifact-hashes.json')['files'].items():
  assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
 print(json.dumps({'status':'AUTHOR_READ_ONLY_CONSISTENCY_PASS','new_root_probes':len(cases),'node':node,'acceptance':'PENDING'}))
if __name__=='__main__':main()
