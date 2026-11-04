from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
seal=json.loads((P/'seal.json').read_text(encoding='utf-8'))
for n,h in seal['files'].items():
 assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
print('PASS bounded review seal',len(seal['files']))
