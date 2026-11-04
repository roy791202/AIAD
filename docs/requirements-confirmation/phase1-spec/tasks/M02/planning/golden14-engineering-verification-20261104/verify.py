import json,hashlib,subprocess,shutil,os,html,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[7]
OUT=Path(__file__).resolve().parent
C=ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M02/planning/golden14-candidate-20261104'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snap(p):return {str(x.relative_to(p)):sha(x) for x in p.rglob('*') if x.is_file()}
before=snap(C)
scratch=OUT/'scratch';shutil.copytree(C/'expected',scratch,dirs_exist_ok=True)
commands=[]
def run(name,argv,cwd,timeout=35):
 env=os.environ.copy();env['RUSTUP_AUTO_INSTALL']='0';env['CARGO_NET_OFFLINE']='true';env['CARGO_TARGET_DIR']=str(OUT/'target')
 try:
  r=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
  x={'id':name,'argv':argv,'cwd':str(cwd),'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'timeout':False}
 except subprocess.TimeoutExpired as e:x={'id':name,'argv':argv,'cwd':str(cwd),'exit':None,'stdout':str(e.stdout or ''),'stderr':str(e.stderr or ''),'timeout':True}
 except OSError as e:x={'id':name,'argv':argv,'cwd':str(cwd),'exit':None,'stderr':str(e),'environment_failure':True}
 (OUT/(name+'.json')).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8');commands.append(x);return x
head=run('git-head',['git','rev-parse','HEAD'],ROOT)
branch=run('git-branch',['git','branch','--show-current'],ROOT)
run('rustup-installed',['rustup','toolchain','list'],ROOT)
run('rust-version',['rustc','--version','--verbose'],scratch/'program/src-tauri')
run('cargo-version',['cargo','--version','--verbose'],scratch/'program/src-tauri')
run('node-version',['node','--version'],ROOT)
run('node-syntax',['node','--check',str(scratch/'ui-ux/app.js')],ROOT)
run('cargo-check',['cargo','check','--locked','--offline'],scratch/'program/src-tauri',50)
run('stable-rust-version',['rustc','+stable','--version','--verbose'],ROOT)
run('stable-cargo-version',['cargo','+stable','--version','--verbose'],ROOT)
run('stable-check-diagnostic',['cargo','+stable','check','--locked','--offline'],scratch/'program/src-tauri',50)
config=json.loads((scratch/'program/src-tauri/tauri.conf.json').read_text());ui=json.loads((scratch/'ui-ux/ui-schema.json').read_text())
checks=[{'id':'config-frontend-exists','pass':((scratch/'program/src-tauri')/config['build']['frontendDist']).resolve().is_dir()},{'id':'window-positive','pass':all(w['width']>0 and w['height']>0 for w in config['app']['windows'])},{'id':'bundle-explicit-false','pass':config['bundle']['active'] is False},{'id':'identity-is-example-not-approved','pass':config['identifier']=='org.example.golden14candidate'},{'id':'ui-no-actions-proposed','pass':ui['controls']==[] and ui['events']==[] and ui['status']=='PROPOSED_NOT_ADOPTED'}]
a=json.loads((ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf-8'))['source_hashes'];drift=[k for k,v in a.items() if not (ROOT/k).exists() or sha(ROOT/k)!=v]
after=snap(C);checks += [{'id':'candidate-unchanged','pass':before==after},{'id':'authority796zero','pass':len(a)==796 and not drift}]
result={'author':'/root/golden_engineering_evidence','mode':'CANDIDATE_ENGINEERING_ATTEMPT_ONLY','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':commands,'checks':checks,'source_before':before,'source_after':after,'authority_count':len(a),'authority_drift':drift,'selected':None,'adoption':None,'product_pass':False,'limits':['No product acceptance; isolated proposed skeleton only','No network install or global toolchain mutation','Node parse and structural config checks do not prove browser or Tauri runtime','Exact candidate source preserved; candidate decisions remain pending']}
(OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'commands':[{k:x.get(k) for k in ['id','exit','stderr','timeout']} for x in commands],'checks':checks},ensure_ascii=False))

