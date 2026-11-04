import json,hashlib,subprocess,html,copy
from pathlib import Path
from datetime import datetime
ROOT=Path.cwd(); OUT=Path(__file__).resolve().parent; P=OUT.parent/'golden14-engineering-verification-20261104'; C=OUT.parent/'golden14-candidate-20261104'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
checks=[]
def check(n,v):checks.append({'id':n,'pass':bool(v)})
before={str(f.relative_to(P)):sha(f) for f in P.rglob('*') if f.is_file() and 'target' not in f.relative_to(P).parts}
d=read(P/'results.json');cmd={x['id']:x for x in d['commands']}
for k,v in read(P/'seal.json')['files'].items():check('sealed:'+k,sha(P/k)==v)
for k,v in d['source_before'].items():check('candidate:'+k,sha(C/k)==v and d['source_after'][k]==v)
for k in cmd:check('log:'+k,read(P/(k+'.json'))==cmd[k])
check('exact-toolchain-failure',cmd['cargo-check']['exit']==1 and 'not installed' in cmd['cargo-check']['stderr'] and cmd['cargo-check']['argv']==['cargo','check','--locked','--offline'])
check('only-stable-installed','stable-x86_64-pc-windows-msvc' in cmd['rustup-installed']['stdout'] and '1.99.1-x86_64-pc-windows-msvc' not in cmd['rustup-installed']['stdout'])
check('stable-versions','rustc 1.99.1' in cmd['stable-rust-version']['stdout'] and 'cargo 1.99.1' in cmd['stable-cargo-version']['stdout'])
check('timeout-not-failure',cmd['stable-check-diagnostic']['timeout'] and cmd['stable-check-diagnostic']['exit'] is None)
check('diagnostic-icon',cmd['stable-check-resume']['exit']==101 and 'icons/icon.ico` not found' in cmd['stable-check-resume']['stderr'] and 'Windows Resource' in cmd['stable-check-resume']['stderr'])
check('icon-actually-absent',not (P/'scratch/program/src-tauri/icons/icon.ico').exists())
config=read(P/'scratch/program/src-tauri/tauri.conf.json');ui=read(P/'scratch/ui-ux/ui-schema.json')
check('frontend-exists',(P/'scratch/program/src-tauri'/config['build']['frontendDist']).resolve().exists())
check('window-positive',all(x['width']>0 and x['height']>0 for x in config['app']['windows']))
check('bundle-false',config['bundle']['active'] is False)
check('example-only',config['identifier']=='org.example.golden14candidate' and d['selected'] is None and d['adoption'] is None)
check('no-ui-actions',ui['controls']==[] and ui['events']==[])
node=subprocess.run(['node','--check',str(P/'scratch/ui-ux/app.js')],capture_output=True,text=True);check('independent-node-parse',node.returncode==0)
check('no-product-pass',d['product_pass'] is False and d['status']=='PARTIAL_ENGINEERING_VERIFICATION')
check('technical-owner-free',all(x.get('owner_decision_required') is False for x in d['classification']))
check('selected-null',all(x['selected'] is None for x in d['owner_questions']))
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();check('live-head',head==cmd['git-head']['stdout'].strip())
a=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')['source_hashes'];drift=[k for k,v in a.items() if not (ROOT/k).exists() or sha(ROOT/k)!=v];check('authority796',len(a)==796 and not drift)
def evidence_valid(x):
 z={y['id']:y for y in x['commands']}
 return x['product_pass'] is False and x['selected'] is None and x['adoption'] is None and x['status']=='PARTIAL_ENGINEERING_VERIFICATION' and z['cargo-check']['exit']==1 and 'not installed' in z['cargo-check']['stderr'] and z['stable-check-resume']['exit']==101 and 'icons/icon.ico` not found' in z['stable-check-resume']['stderr'] and z['stable-check-diagnostic']['timeout'] is True and z['node-syntax']['exit']==0
probes=[]
for name,mut in [('false-product-pass',lambda x:x.update(product_pass=True)),('false-build-success',lambda x:next(y for y in x['commands'] if y['id']=='stable-check-resume').update(exit=0)),('missing-icon-proof',lambda x:next(y for y in x['commands'] if y['id']=='stable-check-resume').update(stderr='')),('named-toolchain-false-pass',lambda x:next(y for y in x['commands'] if y['id']=='cargo-check').update(exit=0)),('timeout-treated-complete',lambda x:next(y for y in x['commands'] if y['id']=='stable-check-diagnostic').update(timeout=False)),('false-node-pass',lambda x:next(y for y in x['commands'] if y['id']=='node-syntax').update(exit=1)),('unauthorized-adoption',lambda x:x.update(adoption='APPROVED')),('false-complete',lambda x:x.update(status='PASS'))]:
 x=copy.deepcopy(d);mut(x);probes.append({'id':name,'rejected':not evidence_valid(x)})
check('negative-probes',all(x['rejected'] for x in probes))
after={str(f.relative_to(P)):sha(f) for f in P.rglob('*') if f.is_file() and 'target' not in f.relative_to(P).parts};check('candidate-unchanged',before==after)
r={'reviewer':'/root/golden_engineering_review','author':d['author'],'verdict':'BOUNDED_ENGINEERING_EVIDENCE_REVIEW_PASS' if all(x['pass'] for x in checks) else 'CHANGES_REQUESTED','checks':checks,'probes':probes,'head':head,'authority_count':len(a),'drift':drift,'scope':'Fresh diagnostic evidence and claim boundaries only. No long compile repeated. No historical PASS rerun.','facts':['Exact named 1.99.1 channel is absent. Installed stable alias reports version1.99.1; same version does not establish installed named channel.','Explicit stable diagnostic failed exit101 at tauri-build missing icons/icon.ico; engineering resource gap, not valid behavioral RED.','Node parse/config structural PASS does not prove runtime/product acceptance.','Adopted Windows11 target is not reasked; GT-D3 technical installation/lock/build evidence belongs engineering.'],'product_native_build_acceptance':'NOT RUN / no PASS claimed','candidate_unchanged':before==after}
(OUT/'results.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');(OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Golden14 engineering evidence review</title><h1>'+r['verdict']+'</h1><p>Independent reviewer /root/golden_engineering_review; author '+d['author']+'</p><p>'+str(len(checks))+' checks; 8 new rejection probes.</p><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in r['facts'])+'</ul><p>Product/native acceptance NOT RUN. Original candidate and engineering package unchanged.</p><p><a href="results.json">Exact results</a></p>',encoding='utf-8')
(OUT/'seal.json').write_text(json.dumps({'reviewer':r['reviewer'],'sealed_at':datetime.now().astimezone().isoformat(),'files':{f.name:sha(f) for f in OUT.iterdir() if f.is_file() and f.name!='seal.json'}},indent=2),encoding='utf-8');print(r['verdict'],len(checks),len(probes));print([x for x in checks if not x['pass']])
