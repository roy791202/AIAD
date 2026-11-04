"""Bounded document checks, not independent acceptance or full JSON Schema validation."""
import json,hashlib,re
from pathlib import Path
from model import evaluate
D=Path(__file__).resolve().parent
W=next(p for p in D.parents if (p/'apps/sgenaxis-desktop').exists())
def read(n):return json.loads((D/n).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 rows=read('fixtures.json');results=[]
 for r in rows:
  got=evaluate(r['input'])
  assert all(got.get(k)==v for k,v in r['expected'].items()),(r['id'],got,r['expected'])
  assert got['release_calls']==0,r['id']
  if got['outcome']!='RejectedMalformed':assert got['snapshot']==r['input']['snapshot']
  results.append({'id':r['id'],'observed':got})
 inputs=read('inputs.json');drift=[p for p,h in inputs['source_inputs'].items()if sha(W/p)!=h]
 assert not drift,drift
 authority=json.loads((W/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf-8'))
 assert len(authority['source_hashes'])==796
 source_drift=[p for p,h in authority['source_hashes'].items()if sha(W/p)!=h]
 assert not source_drift,source_drift
 spec=read('module-spec.json');embedded=re.search(r'<script type="application/json" id="module-spec">(.*?)</script>',(D/'index.html').read_text(encoding='utf-8'),re.S).group(1)
 assert json.loads(embedded)==spec
 seal=read('seal.json');assert all(sha(D/p)==h for p,h in seal['artifacts'].items())
 print(json.dumps({'status':'PASS_DOCUMENT_MODEL_ONLY','fixtures':len(results),'authority_files':796,'source_drift':source_drift,'input_drift':drift,'sealed_files':len(seal['artifacts']),'independent_review':'NOT RUN','full_draft_2020_12':'NOT RUN','results':results},indent=2))
if __name__=='__main__':main()
