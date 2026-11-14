import pathlib,subprocess,json,os
p=pathlib.Path('docs/requirements-confirmation/phase1-spec/tasks/IO-PREREQ/implementation').resolve();cwd=pathlib.Path('apps/sgenaxis-desktop').resolve()
checks=[('ports-adapters-lib',['cargo','test','-p','sgenaxis-ports','-p','sgenaxis-adapters','--lib','--locked']),('work',['cargo','test','-p','sgenaxis-work','--locked']),('host-lib',['cargo','test','-p','sgenaxis-host','--lib','--locked']),('adapter-build',['cargo','build','-p','sgenaxis-adapters','--lib','--locked'])]
results=[]
for name,cmd in checks:
 r=subprocess.run(cmd,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace');(p/(name+'.txt')).write_text(r.stdout,encoding='utf-8');item={'name':name,'argv':cmd,'cwd':str(cwd),'exit_code':r.returncode};results.append(item);print(name,r.returncode,r.stdout[-600:],flush=True)
(p/'regression.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
