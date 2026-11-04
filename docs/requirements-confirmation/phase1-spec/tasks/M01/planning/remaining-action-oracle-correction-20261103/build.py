import copy, datetime, hashlib, html, importlib.util, json, pathlib, subprocess, sys
sys.dont_write_bytecode=True
O=pathlib.Path(__file__).resolve().parent; R=O.parents[6]; B=O.parent/'remaining-action-correction-20261103'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v): (O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
s=importlib.util.spec_from_file_location('oracle',O/'check.py'); c=importlib.util.module_from_spec(s); s.loader.exec_module(c)
fixtures=[]
def probe(name,p,expected,fn=c.validate):
    try: fn(p); observed='ACCEPT'; reason=''
    except (AssertionError,KeyError,TypeError,ValueError,AttributeError) as e: observed='REJECT'; reason=str(e)
    fixtures.append(dict(id=name,input=p,expected=expected,observed=observed,passed=observed==expected,reason=reason))
for original in c.PACKETS:
    m=original['primary_module'];probe('positive_'+m,copy.deepcopy(original),'ACCEPT')
    p=copy.deepcopy(original);p['review_annotation']='legal additive metadata';probe('metadata_'+m,p,'ACCEPT')
    mutations=[('wrong_authorization',{'authority':'Approved production implementation and release authorized'}),('wrong_state',{'state':'READY_FOR_AI_IMPLEMENTATION'}),('missing_authority',{'authority':None}),('empty_authority',{'authority':''}),('authority_type',{'authority':[]}),('missing_commands',{'commands':[]}),('command_string',{'commands':'echo check.py --packet '+m}),('echo',{'commands':['echo check.py --packet '+m]}),('spoof_checker',{'commands':['python malicious/check.py --packet '+m,original['commands'][1]]}),('chain',{'commands':[original['commands'][0]+'; echo done',original['commands'][1]]}),('wrong_module',{'commands':[original['commands'][0][:-3]+('M02' if m=='M03' else 'M03'),original['commands'][1]]}),('extra_arg',{'commands':[original['commands'][0]+' --approve',original['commands'][1]]}),('duplicate_mode',{'commands':[original['commands'][0],original['commands'][0]]}),('unterminated_quote',{'commands':['python "',original['commands'][1]]}),('null_command',{'commands':[None,original['commands'][1]]}),('mixed_modules',{'allowed_modules':['M02','M03']}),('outside_scope',{'allowed_files':['apps/sgenaxis-desktop/candidate.json']})]
    for name,changes in mutations:
        p=copy.deepcopy(original);p.update(changes);probe(name+'_'+m,p,'REJECT')
    p=copy.deepcopy(original);p['allowed_files'][0]=p['allowed_files'][0].replace('/candidate.json','/../candidate.json');probe('traversal_'+m,p,'REJECT')
    p=copy.deepcopy(original);p['source_refs'].append('missing-not-present.json');probe('missing_source_'+m,p,'REJECT')
for name,p in [('null_packet',None),('list_packet',[]),('missing_fields',{}),('module_unhashable',{'primary_module':[]})]:probe(name,p,'REJECT')
cards=read(B/'31-card-actions.json');c.check_cards(cards)
p=copy.deepcopy(cards['cards'][0]);p['provider']='Owner exact candidate disposition';probe('F01_provider_regression',p,'REJECT',c.io_validate)
p=copy.deepcopy(cards['cards'][0]);p['provider']='Windows11 fixture provider; No new Owner adoption required; native reparse and 8.3 fixture';probe('F01_legal_provider_variant',p,'ACCEPT',c.io_validate)
write('adversarial-fixtures.json',fixtures)
# Reproduce original two F03 counterexamples without running their command strings.
closure=[]
for name,changes in [('wrong_authorization',{'authority':'Approved production implementation and release authorized'}),('non_executable_command',{'commands':['echo check.py --packet M03']})]:
    p=copy.deepcopy(c.PACKETS[0]);p.update(changes)
    c.prior.validate(p)
    try:c.validate(p);new='ACCEPT'
    except ValueError:new='REJECT'
    closure.append(dict(id=name,original='ACCEPT',corrected=new,closed=new=='REJECT'))
write('closure.json',{'F03':closure,'F01':'provider checks preserved','F02':'prior scope/source/deliverable checks retained plus exact approved output paths','limit':'Closed two document packets only; not a generic arbitrary semantic validator. Commands are parsed and compared, never executed from packet content.'})
commands=[]
for m in ['M02','M03']:
    argv=[sys.executable,'-B',str(O/'check.py'),'--packet',m]
    result=subprocess.run(argv,cwd=R,capture_output=True,text=True)
    commands.append(dict(argv=argv,exit=result.returncode,stdout=result.stdout,stderr=result.stderr))
write('checkcommands-log.json',commands)
authority=read(O.parent/'s2-green/source-current.json'); mismatch=[n for n,h in authority['source_hashes'].items() if not (R/n).is_file() or sha(R/n)!=h]
sourcepaths=[R/'AGENTS.md',R/'docs/board.json',R/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-M01-PREP-01.json',O.parent/'s2-green/source-current.json']
for folder in [B,O.parent/'remaining-action-correction-review-20261103']:
    sourcepaths += [p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
write('source-hashes.json',{'sources':{p.relative_to(R).as_posix():sha(p) for p in sourcepaths},'authority_count':len(authority['source_hashes']),'authority_mismatches':mismatch,'live_HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'historical_HEAD':authority['head'],'owner_instruction_timestamp':'2026-11-03T14:17:07.534Z'})
write('diff.json',{'scope':'Only new sibling remaining-action-oracle-correction-20261103 files','retained':'Original candidate/review/packets/cards unchanged; board/product/tests/spec/hooks/roles not modified by author','changes':['Exact existing document-only state and authority values','Two approved checker invocation shapes parsed as tokens with exact script/mode/module binding; no shell or eval','Exact original allowed-file list retained; F01 provider and F02 prior checks reused'],'product_contract_BDD_threshold_changes':False,'product_valid_RED':'N/A','document_tool_RED_GREEN':'Original counterexamples accepted; corrected rejects. Author tool self-check only, not product TDD or independent acceptance.'})
assert all(f['passed'] for f in fixtures) and all(x['exit']==0 for x in commands) and not mismatch and all(x['closed'] for x in closure)
write('author-checks.json',{'status':'PASS_AUTHOR_DOCUMENT_TOOL_SELF_CHECK_ONLY','author':'/root/dispatch_oracle_correction','independent_acceptance':'NOT RUN','fixture_count':len(fixtures),'product_tests_build_native_package':'NOT RUN','valid_RED_product':'N/A','deliverable_checks':'NOT RUN: M02/M03 outputs not authored; prior deliverable function preserved','authority_hashes':len(authority['source_hashes']),'mismatches':mismatch})
body='<html lang="zh-Hant"><meta charset="utf-8"><title>F03 document oracle correction</title><style>body{max-width:1100px;margin:40px auto;font:16px system-ui;line-height:1.6}pre{white-space:pre-wrap;background:#eee;padding:16px}</style><h1>F03 文件 oracle 最小補正</h1><p>PASS_AUTHOR_DOCUMENT_TOOL_SELF_CHECK_ONLY；作者 /root/dispatch_oracle_correction；獨立驗收 NOT RUN。</p><p>僅封閉既有 M02 / M03 document packet 檢查，不是泛用任意語意 validator。authority/state 使用原已定義 document-only 值；兩核定命令逐 token 白名單比對，絕不執行 packet 外來命令。原 candidate / review 保留。</p><p>產品 contract、BDD、門檻未變。產品 valid RED N/A；產品測試、build、native、package NOT RUN。文件工具紅綠只證明反例封閉，不是產品 TDD 或獨立驗收。</p>'
for name in ['closure.json','author-checks.json','diff.json','checkcommands-log.json']:
    body+='<h2>'+html.escape(name)+'</h2><pre>'+html.escape((O/name).read_text())+'</pre>'
body+='<p>F01 IO provider、F02 scope/source checks 保留。Owner adoption、production envelope、Skeleton / product RED 門檻不變。authority 796 hashes 核對；live 5b709343 與 historical 31babe87 分開。</p><ul>'
for p in sorted(O.iterdir()):body+='<li><a href="'+p.name+'">'+p.name+'</a></li>'
body+='</ul></html>'; (O/'index.html').write_text(body,encoding='utf-8')
write('seal.json',{'sealed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'author':'/root/dispatch_oracle_correction','payload':{p.name:sha(p) for p in sorted(O.iterdir()) if p.is_file() and p.name!='seal.json'},'instruction':'Finalized; author stops writing after this seal. Independent review pending.'})
print(json.dumps({'fixtures':len(fixtures),'commands':[x['exit'] for x in commands],'authority':len(authority['source_hashes']),'mismatches':mismatch,'sealed':True}))
