import copy, datetime, hashlib, html, importlib.util, json, pathlib, subprocess, sys
sys.dont_write_bytecode=True
R=pathlib.Path.cwd(); O=pathlib.Path(__file__).resolve().parent; C=O.parent/'remaining-action-oracle-correction-20261103'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v): (O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
s=importlib.util.spec_from_file_location('independent_candidate',C/'check.py'); c=importlib.util.module_from_spec(s); s.loader.exec_module(c)
probes=[]
def probe(name,p,expected,fn=c.validate):
 try: fn(p); observed='ACCEPT'; reason=''
 except Exception as e: observed='REJECT'; reason=type(e).__name__+': '+str(e)
 probes.append(dict(id=name,input=p,expected=expected,observed=observed,passed=observed==expected,reason=reason))
closure=[]
for name,delta in [('wrong_authorization',{'authority':'Approved production implementation and release authorized'}),('non_executable_command',{'commands':['echo check.py --packet M03']})]:
 p=copy.deepcopy(c.PACKETS[0]);p.update(delta); c.prior.validate(p);probe('original_F03_'+name,p,'REJECT');closure.append({'id':name,'original':'ACCEPT','corrected':probes[-1]['observed']})
for p0 in c.PACKETS:
 m=p0['primary_module'];probe('baseline_'+m,copy.deepcopy(p0),'ACCEPT')
 changes=[('authority_trailing_space',{'authority':p0['authority']+' '}),('authority_case',{'authority':p0['authority'].upper()}),('state_boolean',{'state':True}),('module_trailing_space',{'primary_module':m+' '}),('allowed_modules_object',{'allowed_modules':{'0':m}}),('commands_object',{'commands':{'0':p0['commands'][0]}}),('three_commands',{'commands':p0['commands']+[p0['commands'][0]]}),('reverse_commands',{'commands':p0['commands'][::-1]}),('command_empty_second',{'commands':[p0['commands'][0],'']}),('command_case_script',{'commands':[p0['commands'][0].replace('check.py','CHECK.py'),p0['commands'][1]]}),('interpreter_option',{'commands':[p0['commands'][0].replace('python ','python -c '),p0['commands'][1]]}),('absolute_checker',{'commands':[p0['commands'][0].replace('docs/','D:/AIAD/docs/',1),p0['commands'][1]]}),('module_joined_option',{'commands':[p0['commands'][0].replace('--packet ','--packet='),p0['commands'][1]]})]
 for tag,delta in changes:
  p=copy.deepcopy(p0);p.update(delta);probe(tag+'_'+m,p,'REJECT')
 for tag,tail in [('pipe',' | python -c pass'),('and',' && echo approved'),('newline','\nwhoami'),('substitution',' $(whoami)'),('redirection',' > proof.json'),('null','\x00'),('unicode_separator','\u2028echo approved'),('backslash_chain',' \\; echo approved')]:
  p=copy.deepcopy(p0);p['commands'][0]+=tail;probe(tag+'_'+m,p,'REJECT')
 p=copy.deepcopy(p0);p['commands']=['  '+x.replace('python ','"python"\t',1)+'  ' for x in p['commands']];probe('legal_quoted_whitespace_'+m,p,'ACCEPT')
 p=copy.deepcopy(p0);p['review_annotation']={'owner':'not adopted','scope':'review only'};probe('legal_nested_metadata_'+m,p,'ACCEPT')
 p=copy.deepcopy(p0);p['allowed_files'][1]=p['allowed_files'][0];probe('duplicate_output_'+m,p,'REJECT')
 p=copy.deepcopy(p0);p['allowed_files']=p['allowed_files'][::-1];probe('output_order_boundary_'+m,p,'REJECT')
 p=copy.deepcopy(p0);p['source_refs'].append('not-present-independent-probe.json');probe('missing_source_'+m,p,'REJECT')
cards=read(c.BASE/'31-card-actions.json');c.check_cards(cards)
p=copy.deepcopy(cards['cards'][0]);p['provider']='Owner exact candidate disposition';probe('F01_owner_regression',p,'REJECT',c.io_validate)
p=copy.deepcopy(cards['cards'][0]);p['provider']='Windows11 fixture provider; No new Owner adoption required; alternate ordering';probe('F01_legal_provider',p,'ACCEPT',c.io_validate)
commands=[]
# Fixed reviewer-owned argv only. Never execute any packet-supplied command.
for checker in [C/'check.py',c.BASE/'check.py']:
 for m in ['M02','M03']:
  argv=[sys.executable,'-B',str(checker),'--packet',m]; r=subprocess.run(argv,cwd=R,capture_output=True,text=True)
  commands.append(dict(argv=argv,exit=r.returncode,stdout=r.stdout,stderr=r.stderr))
seal=read(C/'seal.json');sealcheck={n:sha(C/n)==v for n,v in seal['payload'].items()}
src=read(C/'source-hashes.json');drift={n:{'sealed':v,'current':sha(R/n)} for n,v in src['sources'].items() if sha(R/n)!=v}
a=read(O.parent/'s2-green/source-current.json');mismatch=[n for n,v in a['source_hashes'].items() if not (R/n).is_file() or sha(R/n)!=v]
h=(C/'index.html').read_text(encoding='utf-8'); htmlcheck={n:html.escape((C/n).read_text(encoding='utf-8').strip()) in h for n in ['closure.json','author-checks.json','diff.json','checkcommands-log.json']}
gitdiff=subprocess.check_output(['git','diff','--name-only',a['head'],'HEAD'],text=True).splitlines()
results=dict(author='/root/dispatch_oracle_correction',reviewer='/root/dispatch_oracle_correction_review',layer='INDEPENDENT_BOUNDED_DOCUMENT_TOOL_REVIEW',timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidate_creation_instruction_timestamp=src['owner_instruction_timestamp'],current_owner_instruction_timestamp='2026-11-03T14:27:07.755Z',closure=closure,probe_count=len(probes),failed_probes=[p['id'] for p in probes if not p['passed']],commands=commands,candidate_seal=sealcheck,html_embedded_json=htmlcheck,source_drift=drift,authority_count=len(a['source_hashes']),authority_mismatches=mismatch,historical_HEAD=a['head'],live_HEAD=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),historical_to_live_paths=gitdiff,board_drift_classification={'observed':'sealed board hash differs from current board','parent_attestation':'Only M01 PREP notes append, that item.updatedAt, root.updatedAt; deepcopy assertion other items equal; FileLock/hash/atomic replace.','independent_limit':'No pre-mutation bytes retained; exact whole-board semantic diff not independently recoverable. No reconstructed old bytes used.'},deliverable_execution='NOT RUN: no M02/M03 candidate outputs authored; retained prior deliverable validator reviewed statically',product_native_build_package='NOT RUN',owner_adoption='NOT GRANTED',valid_RED_product='N/A')
write('probes.json',probes);write('results.json',results)
assert not results['failed_probes'] and all(x['exit']==0 for x in commands) and all(sealcheck.values()) and all(htmlcheck.values()) and not mismatch
assert set(drift)<= {'docs/board.json'} and gitdiff==['docs/board.json']
findings=dict(verdict='PASS_BOUNDED_DOCUMENT_TOOL_REVIEW',F03='CLOSED: original two counterexamples independently reproduced against old oracle and rejected by correction; additional independent probes pass.',F01='Provider regression rejection preserved; no native acceptance.',F02='Single module exact paths and prior source/deliverable checks preserved.',blocking_findings=[],limits=['Closed existing two packet document schema only; arbitrary extra metadata is not authority or generic semantic validation.','Deliverable content validation is retained prior behavior, not newly executed product proof.','Board drift is coordinator-attested evidence append, with no old bytes for independent exact whole-board reconstruction.','No product/native/Owner adoption/production authorization or completion.'])
write('findings.json',findings)
(O/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>F03 independent review</title><style>body{max-width:1100px;margin:40px auto;font:16px system-ui;line-height:1.6}pre{white-space:pre-wrap;background:#eee;padding:16px}</style><h1>F03 獨立文件工具審查</h1><p>PASS_BOUNDED_DOCUMENT_TOOL_REVIEW。作者 /root/dispatch_oracle_correction；審查 /root/dispatch_oracle_correction_review。</p><p>原兩反例閉合；新增獨立 malformed、boundary、command path、module、authority、shell chain probes。固定 reviewer argv 執行兩份 checker 的 M02/M03 packet checks，未執行外來 packet command。產品/native/build/package NOT RUN；Owner 採納未授予。</p>'+''.join('<h2>'+n+'</h2><pre>'+html.escape(json.dumps(v,ensure_ascii=False,indent=2))+'</pre>' for n,v in [('findings',findings),('results',results)])+'<p><a href="probes.json">完整 probes / inputs</a> · <a href="review.py">review source</a></p></html>',encoding='utf-8')
write('seal.json',{'sealed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'/root/dispatch_oracle_correction_review','payload':{p.name:sha(p) for p in sorted(O.iterdir()) if p.is_file() and p.name!='seal.json'},'instruction':'Finalized. Stop all writes to review directory after sealing.'})
print(json.dumps({'verdict':findings['verdict'],'probes':len(probes),'commands':[x['exit'] for x in commands],'drift':list(drift),'authority':len(a['source_hashes'])}))
