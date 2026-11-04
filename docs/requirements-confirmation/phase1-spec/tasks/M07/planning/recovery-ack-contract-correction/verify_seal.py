from pathlib import Path
import json,hashlib,re
P=Path(__file__).resolve().parent
s=json.loads((P/'seal.json').read_text(encoding='utf-8-sig'))
assert sorted(s['sha256'])==sorted(f.name for f in P.iterdir() if f.is_file() and f.name!='seal.json')
for n,h in s['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
spec=json.loads((P/'module-spec.json').read_text(encoding='utf-8-sig'))
embedded=re.search(r'<script type="application/json" id="module-spec">(.*?)</script>',(P/'index.html').read_text(encoding='utf-8'),re.S).group(1)
assert json.loads(embedded)==spec
assert spec['module_complete'] is False
print(json.dumps(dict(status='PASS_CANDIDATE_SEAL_ONLY',entries=len(s['sha256']),embedded_spec_equal=True)))
