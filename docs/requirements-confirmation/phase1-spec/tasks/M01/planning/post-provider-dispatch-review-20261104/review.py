import json,hashlib,copy,subprocess,re,html
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[7]
BASE=ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning'
C=BASE/'post-provider-dispatch-20261104';FIX=BASE/'post-provider-dispatch-correction-20261104';OUT=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def ck(n,v):checks.append({'name':n,'pass':bool(v)})
def snap(p):return {str(x.relative_to(p)):sha(x) for x in p.rglob('*') if x.is_file()}
before={str(p):snap(p) for p in [C,FIX]}
a=json.loads((C/'audit.json').read_text(encoding='utf-8'));b=json.loads((ROOT/'docs/board.json').read_text(encoding='utf-8'));s=json.loads((C/'source-bindings.json').read_text(encoding='utf-8'))
for p in [C,FIX]:
 seal=json.loads((p/'seal.json').read_text(encoding='utf-8'))
 for name,h in seal['files'].items():ck('seal:'+p.name+':'+name,sha(p/name)==h)
rows=a['rows'];expected=[i for light in ['Yellow','Gray','Red'] for i in b['items'] if i['light']==light]
ck('31exactorderedboardIDs',[r['id'] for r in rows]==[i['id'] for i in expected]);ck('counts',a['counts']==dict(Counter(i['light'] for i in b['items']))|{'Blue':0})
ck('grouporder',[r['light'] for r in rows]==['Yellow']*8+['Gray']*18+['Red']*5)
ck('sixsuperseded',sum(r['disposition']=='SUPERSEDED_PRESERVE_NO_REDISPATCH' for r in rows)==6)
for r in rows:
 ck('rowconditions:'+r['id'],bool(r['attempts'] and r['missing_conditions'] and r['provider'] and r['original_task']))
 ck('nullselection:'+r['id'],r['selected'] is None)
 t=r['original_task'];ck('originalfallback:'+r['id'],t['path']!='docs/board.json' or t['pointer'].endswith('/legacyTask'))
bindings=[]
def walk(v):
 if isinstance(v,dict):
  if all(k in v for k in ['path','sha256','pointer']):bindings.append(v)
  for z in v.values():walk(z)
 elif isinstance(v,list):
  for z in v:walk(z)
walk(s);walk(rows)
for n,t in enumerate(bindings):
 p=ROOT/t['path'];ck('bindinghash:'+str(n),p.exists() and sha(p)==t['sha256'])
 if t['pointer']:
  d=json.loads(p.read_text(encoding='utf-8'))
  for k in t['pointer'].strip('/').split('/'):d=d[int(k)] if isinstance(d,list) else d[k.replace('~1','/').replace('~0','~')]
  ck('pointer:'+str(n),d is not None)
auth=json.loads((ROOT/s['authority']['path']).read_text(encoding='utf-8'))['source_hashes'];ck('authority796',len(auth)==796 and all((ROOT/k).exists() and sha(ROOT/k)==h for k,h in auth.items()))
ck('HEAD',subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==a['live_head']);ck('branch',subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()==a['branch']);ck('distincthistorical',a['live_head']!=a['historical_product_head'])
original=json.loads((ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M02/planning/golden14-candidate-20261104/candidate.json').read_text(encoding='utf-8'));ck('actual14candidate',len(original['rows'])==14 and all((ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M02/planning/golden14-candidate-20261104'/r['expected']['path']).exists() for r in original['rows']))
m2=next(r for r in rows if r['id']=='PD-P1-M02-PREP-01');ck('Golden14PRESENT','PRESENT, not missing' in m2['technical_work'] and 'GT-D1' in m2['semantic_decision'])
ck('boundedfuture','not a claim that all possible future' in a['known_action_window']);ck('noadoption',a['selected'] is None and a['product_pass'] is False)
links=re.findall(r'href=[\"\']([^\"\']+)',(FIX/'index.html').read_text(encoding='utf-8'))
for i,l in enumerate(links):
 if not l.startswith(('http','#','mailto:')):ck('correctedHTMLlink:'+str(i),(FIX/html.unescape(l.split('#')[0])).resolve().exists())
ck('44correctedlinks',len(links)==44)
osinfo=subprocess.check_output(['powershell','-NoProfile','-Command','Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,OSArchitecture | ConvertTo-Json -Compress'],text=True,errors="replace");ck('Win10host','19045' in osinfo and '10' in osinfo)
# Independent semantic rejection oracle: no mutation can satisfy current admitted routing invariants.
def valid(d):
 rr=d['rows'];return len(rr)==31 and [x['id'] for x in rr]==[x['id'] for x in expected] and [x['light'] for x in rr]==['Yellow']*8+['Gray']*18+['Red']*5 and all(x['selected'] is None for x in rr) and d['selected'] is None and d['product_pass'] is False and 'PRESENT, not missing' in next(x for x in rr if x['id']=='PD-P1-M02-PREP-01')['technical_work'] and 'not a claim that all possible future' in d['known_action_window'] and sum(x['disposition']=='SUPERSEDED_PRESERVE_NO_REDISPATCH' for x in rr)==6
probes=[]
for name,mut in [('staleGolden14missing',lambda d:d['rows'][1].update(technical_work='all golden bytes missing')),('zerocards',lambda d:d.update(rows=[])),('dropOnHold',lambda d:d['rows'].pop(8)),('autoapproval',lambda d:d['rows'][0].update(selected='approved')),('swappedorder',lambda d:d['rows'].reverse()),('globalblocked',lambda d:d.update(known_action_window='all future preparation blocked')),('productpass',lambda d:d.update(product_pass=True)),('redispatchsuperseded',lambda d:d['rows'][8].update(disposition='READY'))]:
 d=copy.deepcopy(a);mut(d);v=not valid(d);probes.append({'name':name,'rejected':v});ck('negative:'+name,v)
for p in [C,FIX]:ck('unchanged:'+p.name,before[str(p)]==snap(p))
status='BOUNDED_DOCUMENT_REVIEW_PASS' if all(c['pass'] for c in checks) else 'CHANGES_REQUESTED'
result={'status':status,'author':a['author'],'reviewer':'/root/post_provider_audit_review','checks':checks,'probes':probes,'OS_observation':osinfo,'limits':['Read-only documentary routing review; not product/native acceptance','Original HTML relative links defective; corrected sibling is canonical human projection','No historical PASS rerun; supplied current gates only, not all future preparation blocked']}
(OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Post-provider routing independent review</title><h1>'+status+'</h1><p>31 cards: 8 Yellow, 18 Gray, 5 Red; six superseded preserved. Golden14 candidate contents and standalone lock PRESENT, formal admission pending. Existing adopted decisions not reopened.</p><p>Original HTML had relative-link defects; sibling correction is canonical projection. All 44 corrected links checked. No product/native approval.</p><pre>'+html.escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre>',encoding='utf-8')
files={x.name:sha(x) for x in OUT.iterdir() if x.is_file() and x.name!='seal.json'};(OUT/'seal.json').write_text(json.dumps({'reviewer':'/root/post_provider_audit_review','status':status,'files':files},indent=2),encoding='utf-8')
print(status,len(checks),[x for x in checks if not x['pass']])


