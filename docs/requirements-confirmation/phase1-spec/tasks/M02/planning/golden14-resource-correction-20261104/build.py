import json,hashlib,subprocess,shutil,os,time,html
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent;R=Path('D:/AIAD');B=R/'docs/requirements-confirmation/phase1-spec/tasks/M02/planning';C=B/'golden14-candidate-20261104'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sealed=json.loads((C/'seal.json').read_text(encoding='utf-8'))['files'];before={k:sha(C/k) for k in sealed}
shutil.copytree(C/'expected',P/'scratch'); icon=R/'apps/sgenaxis-desktop/src-tauri/icons/icon.ico';dest=P/'scratch/program/src-tauri/icons/icon.ico';dest.parent.mkdir();shutil.copy2(icon,dest)
commands=[]
def run(id,args,cwd,timeout=20):
 t=time.monotonic()
 try:
  q=subprocess.run(args,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout);d=dict(id=id,argv=args,cwd=str(cwd),exit=q.returncode,stdout=q.stdout,stderr=q.stderr,timeout=False)
 except subprocess.TimeoutExpired as e:d=dict(id=id,argv=args,cwd=str(cwd),exit=None,stdout=(e.stdout or b'').decode('utf-8','replace') if isinstance(e.stdout,bytes) else e.stdout,stderr=(e.stderr or b'').decode('utf-8','replace') if isinstance(e.stderr,bytes) else e.stderr,timeout=True)
 d['seconds']=time.monotonic()-t;commands.append(d);(P/(id+'.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');return d
run('head',['git','rev-parse','HEAD'],R);run('icon-history',['git','log','-1','--format=%H %s','--','apps/sgenaxis-desktop/src-tauri/icons/icon.ico'],R);run('installed-toolchains',['rustup','toolchain','list'],R)
os.environ['CARGO_TARGET_DIR']=str(P/'target')
a=run('resource-check-1',['cargo','+stable','check','--offline','--locked'],P/'scratch/program/src-tauri',60)
if a['timeout']:a=run('resource-check-2',['cargo','+stable','check','--offline','--locked'],P/'scratch/program/src-tauri',60)
h=json.loads((R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf-8'))['source_hashes'];drift=[k for k,v in h.items() if not (R/k).exists() or sha(R/k)!=v]
after={k:sha(C/k) for k in sealed}
d={'author':'/root/golden_icon_resource_correction','status':'PARTIAL_TIMEOUT' if a['timeout'] else ('CANDIDATE_DIAGNOSTIC_CHECK_PASS' if a['exit']==0 else 'CANDIDATE_DIAGNOSTIC_CHECK_FAIL'),'selected':None,'adoption':None,'product_pass':False,'resource':{'source':str(icon.relative_to(R)),'sha256':sha(icon),'bytes':icon.stat().st_size,'copy_sha256':sha(dest),'role':'existing project icon reused solely in isolated technical diagnosis; no external distribution license asserted','admission':'ADDITIONAL_RESOURCE_OUTSIDE_GOLDEN14_REPLAN_REQUIRED_BEFORE_FORMAL_TEMPLATE_INCLUSION'},'commands':commands,'authority_count':len(h),'authority_drift':drift,'original_candidate_unchanged':before==after,'original_before':before,'original_after':after,'limits':['Original named toolchain 1.99.1 remains unavailable; +stable explicit diagnostic only.','No resource path/template policy adopted; adding fifteenth resource requires envelope revision before formal admission.','No product/native/runtime/installation/release acceptance; compile failure is not intended RED.']}
(P/'results.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
body='<h1>Golden14 icon resource diagnostic candidate</h1><p>'+html.escape(d['status'])+'</p><p>新增第15項資源只作隔離診斷；正式模板入場需 REPLAN_REQUIRED，不自行採納。既有 icon 來源與 SHA256 有綁定，未聲稱對外散布授權。</p><pre>'+html.escape(json.dumps({k:v for k,v in d.items() if k not in ['original_before','original_after','commands']},ensure_ascii=False,indent=2))+'</pre>'
for x in commands:body+='<h2>'+x['id']+'</h2><pre>'+html.escape(json.dumps(x,ensure_ascii=False,indent=2))+'</pre>'
(P/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Golden14 resource correction</title>'+body+'</html>',encoding='utf-8')
files={str(f.relative_to(P)).replace('\\','/'):sha(f) for f in P.rglob('*') if f.is_file() and not any(x in f.relative_to(P).parts for x in ['target','scratch']) and f.name!='seal.json'}
(P/'seal.json').write_text(json.dumps({'author':d['author'],'sealed_at':datetime.now().astimezone().isoformat(),'files':files},indent=2),encoding='utf-8');print(d['status'],len(h),len(drift),before==after)
