"""Author correction fixture and new negative probes; does not run legacy builder."""
import datetime,hashlib,json,pathlib,subprocess,sys,tempfile,shutil
P=pathlib.Path(__file__).resolve().parent
C=P.with_name('golden14-candidate-20261104')
def sha(b):return hashlib.sha256(b).hexdigest()
def write(name,value):(P/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
seal=json.loads((C/'seal.json').read_text(encoding='utf8'))
assert all(sha((C/r).read_bytes())==h for r,h in seal['files'].items())
rows=json.loads((C/'candidate.json').read_text(encoding='utf8'))['rows']
# Bind all sealed original payloads including source and toolchain reports. No body is embedded.
write('bindings.json',{'origin':'../golden14-candidate-20261104','consumer_sha256':sha((P/'check.py').read_bytes()),'original_seal_sha256':sha((C/'seal.json').read_bytes()),'files':seal['files'],'paths':[r['path'] for r in rows],'authority':'Author correction proposed bindings; reviewer must independently accept this exact manifest. Modifying both manifest and input is a new proposal, never admitted automatically.'})
probes=[]
def run(candidate,output=None):
 args=[sys.executable,str(P/'check.py'),'--candidate',str(candidate),'--manifest',str(P/'bindings.json')]
 if output:args+=['--output',str(output)]
 r=subprocess.run(args,capture_output=True);return {'argv':args,'exit':r.returncode,'stdout':r.stdout.decode('utf8','replace'),'stderr':r.stderr.decode('utf8','replace')}
before=sha((C/'seal.json').read_bytes())
with tempfile.TemporaryDirectory(prefix='golden14-correction-') as td:
 T=pathlib.Path(td)
 first=run(C,T/'out1');second=run(C,T/'out2')
 assert first['exit']==second['exit']==0
 actual1={str(p.relative_to(T/'out1')):p.read_bytes() for p in (T/'out1').rglob('*') if p.is_file()}
 actual2={str(p.relative_to(T/'out2')):p.read_bytes() for p in (T/'out2').rglob('*') if p.is_file()}
 assert actual1==actual2 and len(actual1)==14
 probes.append({'id':'P01-two-isolated-renders','pass':True,'first':first,'second':second,'files':14})
 targets=['input.json','templates/ui-ux/app.js','expected/ui-ux/app.js','expected/program/src-tauri/Cargo.lock','templates/program/src-tauri/Cargo.lock','toolchain-evidence.json','source-bindings.json']
 for i,rel in enumerate(targets):
  copy=T/('negative'+str(i));shutil.copytree(C,copy);p=copy/rel;p.write_bytes(p.read_bytes()+b'X');result=run(copy)
  assert result['exit']!=0;probes.append({'id':'tamper-'+rel,'pass':True,'result':result})
 copy=T/'missing';shutil.copytree(C,copy);(copy/'expected/ui-ux/index.html').unlink();result=run(copy);assert result['exit']!=0;probes.append({'id':'missing-path','pass':True,'result':result})
 copy=T/'extra';shutil.copytree(C,copy);(copy/'templates/extra.txt').write_bytes(b'x');result=run(copy);assert result['exit']!=0;probes.append({'id':'extra-path','pass':True,'result':result})
 copy=T/'missing-lock';shutil.copytree(C,copy);(copy/'expected/program/src-tauri/Cargo.lock').unlink();result=run(copy);assert result['exit']!=0;probes.append({'id':'missing-lock','pass':True,'result':result})
assert before==sha((C/'seal.json').read_bytes()) and all(sha((C/r).read_bytes())==h for r,h in seal['files'].items())
write('results.json',{'status':'AUTHOR_CORRECTION_CHECK_PASS','probes':probes,'original_unchanged':True,'independent_review':'PENDING','build_product_native':'NOT RUN','historical_pass_rerun':False})
(P/'index.html').write_text('''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Golden14 消費式補正</title><h1>Golden14 新候選驗證補正</h1><p>原候選完整保留。check.py 只讀原封存模板、input、expected、完整獨立lock及來源/工具鏈紀錄，不內嵌候選body、不重寫golden、不呼叫原build.py。</p><p>以兩個獨立暫存輸出目錄實際渲染14檔，再與既有expected逐byte比較；input、template、expected、lock、source、toolchain被改或缺檔/額外路徑時，程序非零FAIL_CLOSED，拒絕輸出。bindings.json是明示待獨立審查的信任輸入；同時改manifest不是授權。</p><p><a href="bindings.json">逐檔綁定</a> · <a href="results.json">新執行與負向probes</a> · <a href="check.py">唯讀consumer</a> · <a href="../golden14-candidate-20261104/index.html">原候選／四項selected=null產品決策</a></p><p>獨立審查PENDING；僅候選文件/bytes證據，非Owner採納、產品RED/GREEN、build/native驗收。原有歷史PASS未重跑。</p></html>''',encoding='utf8')
write('seal.json',{'sealed_at':datetime.datetime.now().astimezone().isoformat(),'files':{p.name:sha(p.read_bytes()) for p in P.iterdir() if p.is_file() and p.name!='seal.json'}})
print(json.dumps({'probes':len(probes),'pass':True,'original_unchanged':True}))
