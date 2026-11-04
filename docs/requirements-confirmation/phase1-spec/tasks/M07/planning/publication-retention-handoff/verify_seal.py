from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
s=json.loads((P/'seal.json').read_text(encoding='utf-8'))
for name,h in s['hashes'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==h,name
assert set(s['hashes'])=={p.name for p in P.iterdir() if p.is_file() and p.name!='seal.json'}
print('Seal verified',len(s['hashes']),'files; document integrity only')
