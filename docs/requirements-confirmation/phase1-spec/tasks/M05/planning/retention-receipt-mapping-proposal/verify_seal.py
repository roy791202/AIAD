from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent
s=json.loads((P/'seal.json').read_text(encoding='utf-8'))
assert {p.name for p in P.iterdir() if p.is_file() and p.name!='seal.json'}==set(s['files'])
assert all(hashlib.sha256((P/n).read_bytes()).hexdigest()==h for n,h in s['files'].items())
print('PASS seal',len(s['files']),'files; seal excluded')
