from pathlib import Path
import hashlib,json
p=Path(__file__).resolve().parent
s=json.loads((p/'seal.json').read_text(encoding='utf-8'))
assert len(s['files'])==s['count']
for n,h in s['files'].items():
    assert hashlib.sha256((p/n).read_bytes()).hexdigest()==h,n
print('PASS_REVIEW_SEAL',s['count'])
