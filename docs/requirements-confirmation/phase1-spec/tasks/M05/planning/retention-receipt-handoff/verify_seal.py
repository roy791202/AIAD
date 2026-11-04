from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent
s=json.loads((P/'seal.json').read_text(encoding='utf-8'))
assert set(s['files'])=={p.name for p in P.iterdir() if p.is_file() and p.name!='seal.json'}
for n,h in s['files'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
print('PASS seal',len(s['files']),'files')
