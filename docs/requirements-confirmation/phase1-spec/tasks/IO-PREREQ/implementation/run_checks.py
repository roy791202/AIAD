import pathlib,subprocess,json,os,sys
ROOT=pathlib.Path.cwd();P=pathlib.Path(__file__).resolve().parent;CWD=ROOT/'apps/sgenaxis-desktop'
tag=sys.argv[1] if len(sys.argv)>1 else 'green'
def run(name,args,env=None):
 r=subprocess.run(args,cwd=CWD,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
 (P/(tag+'-'+name+'.txt')).write_text(r.stdout,encoding='utf-8')
 (P/(tag+'-'+name+'.json')).write_text(json.dumps({'argv':args,'exit_code':r.returncode,'cwd':str(CWD)},indent=2),encoding='utf-8')
 return r
normal=run('helper',['cargo','build','-p','sgenaxis-adapters','--example','file_commit_probe','--locked','--message-format=json']);assert normal.returncode==0
checkpoint=run('checkpoint',['cargo','test','-p','sgenaxis-adapters','--example','file_commit_probe','--no-run','--locked','--message-format=json']);assert checkpoint.returncode==0
def executable(output):
 records=[]
 for line in output.splitlines():
  try:d=json.loads(line)
  except ValueError:continue
  if d.get('reason')=='compiler-artifact'and d.get('executable'):records.append(d['executable'])
 assert records
 return records[-1]
env=os.environ.copy();env['FILE_COMMIT_PROBE_PATH']=executable(normal.stdout);env['FILE_COMMIT_CHECKPOINT_PROBE_PATH']=executable(checkpoint.stdout)
compile=run('compile',['cargo','test','-p','sgenaxis-adapters','--test','phase1_file_commit','--no-run','--locked'],env);assert compile.returncode==0
tests=run('tests',['cargo','test','-p','sgenaxis-adapters','--test','phase1_file_commit','--locked','--','--test-threads=1'],env)
(P/(tag+'-environment.json')).write_text(json.dumps({k:env[k]for k in ['FILE_COMMIT_PROBE_PATH','FILE_COMMIT_CHECKPOINT_PROBE_PATH']},indent=2),encoding='utf-8')
print(tests.stdout[-1800:]);print('EXIT',tests.returncode)
