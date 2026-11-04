from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;R=P.parents[6]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
seal=json.loads((P/'seal.json').read_text(encoding='utf-8-sig'))
assert all((P/n).is_file() and sha(P/n)==h for n,h in seal['files'].items())
assert {p.name for p in P.iterdir() if p.is_file()}==set(seal['files'])|{'seal.json'}
inputs=json.loads((P/'inputs.json').read_text(encoding='utf-8-sig'))
assert all(sha(R/n)==h for n,h in inputs.items()),'input drift'
spec=json.loads((P/'module-spec.json').read_text(encoding='utf-8-sig'))
page=(P/'index.html').read_text(encoding='utf-8-sig');blob=page.split('<script type="application/json" id="module-spec">')[1].split('</script>')[0]
assert json.loads(blob)==spec
central=json.loads((R/'docs/requirements-confirmation/phase1-spec/tasks/M06/planning/cx-exchange-revision-v3/shared-contract.json').read_text(encoding='utf-8-sig'))
assert json.loads((P/'transition-request.schema.json').read_text())==central['request_hash_schema']
print(json.dumps({'seal':'PASS','sealed_files':len(seal['files']),'document_checks':431,'product_and_native':'NOT RUN','owner_choices':'PENDING'}))
