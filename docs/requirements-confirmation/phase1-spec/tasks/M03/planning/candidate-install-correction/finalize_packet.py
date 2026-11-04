import hashlib,html,json,pathlib
P=pathlib.Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text(encoding='utf-8-sig'))
def save(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
v=read('verification.json')
correction={'identity':{'module':'M03','task':'PD-P1-M03-PREP-01','command':'design_candidate_install','author':'/root/m03_install_u64_correction','status':'CANDIDATE_STRICT_U64_DOCUMENT_CORRECTION_NOT_ADOPTED'},'finding':'CI-IR-F1','intent':'Reuse independently reviewed bounded strict-end U64 schema; preserve all original semantic/proof and policy contracts.','scope':'Only this additive candidate-install-correction package; original M03 planning, board and current-state untouched; no next command.','architecture':'Original module-spec.json retained byte-for-byte; no architecture adoption or Skeleton approval.','contracts':'Original effective-source.json, fixture authority, model and all policies unchanged byte-for-byte. Only exact U64 schema node replacement.','BDD':[{'id':'CI-F1-1','given':'An otherwise valid request or response','when':'A reachable numeric decimal contains a terminal or embedded non-digit','then':'The full document is rejected in both schema subset engines'},{'id':'CI-F1-2','given':'An otherwise valid request or response','when':'A reachable numeric decimal is canonical at max-1 or max','then':'The schema admits that field; max+1 is rejected'}],'TDD':{'cases':'new-probes.json','trace':'reachable-u64-trace.json','levels':'document root schema subset and Node equivalent subset; not full Draft conformance','command':'python '+str(P/'check_correction.py'),'valid_RED':'NOT RUN; document-only correction'},'acceptance':['All newly enumerated fullroot probes pass both engines','All 13 original reviewer LF paths close; additional branch/reference occurrences are included','Non-U64 schema canonical equality and unchanged semantic/proof/policy byte hashes hold','796 authoritative source hashes have zero drift'],'not_run':v['not_run'],'policy_status':'CI-P4 and CI-P6 remain NEW_POLICY_REQUIRES_OWNER; original NoChange/consume/retention/replay policies not adopted','lessons':'lessons.md'}
save('module-spec-correction.json',correction)
(P/'correction.feature').write_text('''Feature: Strict bounded decimal admission in the candidate install document
  Background:
    Given an otherwise valid candidate install request or response
  Rule: Numeric decimal fields admit only canonical unsigned 64-bit strings
    Scenario: Reject an actual terminal line feed
      When a numeric decimal contains "1" followed by an actual line feed
      Then the complete document is rejected
    Scenario: Admit the upper bound
      When a numeric decimal is "18446744073709551615"
      Then its numeric schema admits the complete document
    Scenario: Reject overflow
      When a numeric decimal is "18446744073709551616"
      Then the complete document is rejected
''',encoding='utf8')
save('step-definition-stubs.json',{'status':'PENDING_PRODUCT_AUTOMATION','given':'Build otherwise valid fullroot from branch-specific fixtures','when':'Substitute exact scalar and record Unicode codepoints','then':'Assert complete root schema admission equals expected; automated document probes in check_correction.py only'})
save('pending-automation.json',{'pending':v['not_run'],'assumptions':['Schema engines operate without multiline flags','Trusted fixture authenticity remains a premise','Numeric lexical admission alone does not prove cross-property domain acceptance'],'open_questions':['Owner adoption of original command policies remains pending; unaffected by this correction']})
(P/'lessons.md').write_text('''# CI-IR-F1 root cause and prevention

The command packet rebuilt a bounded U64 regex with `$`. Python `re.search` lets `$` match before a terminal LF. Earlier vector success did not prove strict end-of-input behavior. The independent review reproduced 13 whole-root LF admissions; ECMAScript behavior differed.

Reuse the already reviewed `save-proof-correction/request.schema.json` `$defs/U64Decimal` object, including minLength/maxLength and the parsed single-backslash `(?![\\s\\S])` strict end assertion. Do not recreate a command-specific U64 grammar. Future command packets must reuse this reviewed definition and run actual control-codepoint, max-bound and fullroot branch/reference probes. No field-name custom hook or fullmatch bypass may mask a schema error.

The correction inventories four definition sites, including inline request fields and both `$defs`. Reachability expands to 20 branch/reference occurrences. Branch-specific valid base fixtures distinguish Applied, NoChange and AppliedRetentionDeferred, plus both error arms. This includes every original 13 reviewer path/branch case. New 400 cases run in two engines; old 104/367 evidence is preserved, not recounted as progress.

This is author self-check only. Independent acceptance, full Draft validation, native product behavior and valid TDD RED remain NOT RUN. Candidate grammar correction does not adopt architecture or change NoChange/consume/retention/replay policy.
''',encoding='utf8')
save('before-after.json',{'before':'CHANGES_REQUIRED_STRICT_U64_DOCUMENT_CHECK_ONLY: original 13 LF root probes admitted by Python','after':'AUTHOR SELF-CHECK PASS: original LF finding closure plus all 20 schema reference/branch occurrences reject actual LF in both engines','definitions':4,'root_occurrences':20,'new_cases':400,'engine_executions':800,'original_13_LF_closure':'All included; schema/branch trace lists complete coverage','policy_changes':[],'adoption':'NOT RUN; candidate only'})
# Include every human/machine artifact as structured sections; no external network dependency.
files=[p for p in P.iterdir() if p.is_file() and p.suffix in ['.json','.py','.js','.feature','.md'] and p.name!='artifact-hashes.json']
body=['<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>M03 candidate install strict U64 correction</title><style>body{font:16px system-ui;max-width:1200px;margin:40px auto;background:#101820;color:#e6edf3}a{color:#78caff}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#192735;padding:18px}summary{cursor:pointer;padding:12px;border:1px solid #456}section{margin:18px 0}.badge{padding:10px;background:#634c17}</style><h1>M03 / design_candidate_install</h1><p class="badge">CANDIDATE · 文件限定修正 · 作者自查 PASS · 原合約未採納 · 黃燈 planning 保持</p><p>CI-IR-F1：替換4個U64 schema定義位置，保留semantic/proof與NoChange、consume、retention、replay政策。20個branch/reference位置、400個新fullroot案例、800次Python/ECMAScript執行；原13個LF failure全部涵蓋。這些是schema subset證據，不是完整Draft或產品驗收。</p><p>權威：M01 s2-green 796 source hashes無漂移；current HEAD與historical authority分列於verification。104作者案例與367獨立review案例保留歷史追溯，本次未重跑計進度。</p><p>架構、Ports、ownership及transaction原始內容見下方原ModuleSpec與完整候選。Full Draft、product/native、valid RED、build/install、Owner adoption及獨立驗收：NOT RUN。</p><p><a href="historical-candidate.html">完整原始候選人類閱讀面</a> · <a href="check_correction.py">新精確checker</a></p>']
for p in sorted(files,key=lambda x:x.name):
 raw=p.read_text(encoding='utf-8-sig');body.append('<section><details><summary>'+html.escape(p.name)+'</summary><pre>'+html.escape(raw)+'</pre></details></section>')
body.append('<script type="application/json" id="module-spec">'+json.dumps({'correction':correction,'original':read('module-spec.json')},ensure_ascii=False).replace('</','<\\/')+'</script></html>')
(P/'index.html').write_text(''.join(body),encoding='utf8')
save('artifact-hashes.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in P.iterdir() if p.is_file() and p.name!='artifact-hashes.json'})
print('HTML and source/artifact hashes generated; self-check evidence only')

