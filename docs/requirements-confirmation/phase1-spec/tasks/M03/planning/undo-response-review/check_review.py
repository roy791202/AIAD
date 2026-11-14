"""Independent read-only candidate audit. Writes only sibling review artifacts."""
import ast, copy, hashlib, html, json, pathlib, random, re, subprocess

R = pathlib.Path.cwd()
O = pathlib.Path(__file__).resolve().parent
P = O.parent / 'undo-response-integration'
def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name, value):
    (O/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf8')

# Load definitions only: author top-level test loop writes verification.json and is not executed.
tree = ast.parse((P/'check_documents.py').read_text(encoding='utf8'))
nodes = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef))]
ns = {'__file__': str(P/'check_documents.py'), 'P': P}
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<candidate-definitions-only>', 'exec'), ns)
def accepted(f, *args):
    try:
        f(*args)
        return True
    except AssertionError:
        return False

before = {str(p.relative_to(R)): sha(p) for p in P.iterdir() if p.is_file()}
source = read(P/'source-current.json')
assert all(sha(R/p)==h for p,h in source['sources'].items()), 'effective source drift'
baseline = read(R/source['authority_manifest'])['source_hashes']
assert len(baseline)==796
drift = [p for p,h in baseline.items() if sha(R/p)!=h]
assert not drift, '796 source authority drift'
required = ['AGENTS.md']
base = 'docs/requirements-confirmation/phase1-spec/tasks/'
required += [base+f'{m}/planning/module-spec.json' for m in ['M03','M04','M05']]
required += [base+'M03/planning/current-state.json']
required += [base+f'{m}/planning/{v}/module-spec.json' for m,v in [('M03','cx-h2-revision-v3'),('M04','cx-revision-v3'),('M05','cx-revision-v3')]]
for p in required:
    (R/p).read_text(encoding='utf-8-sig') # fail closed
work = (R/'apps/sgenaxis-desktop/crates/sgenaxis-work/src/document_edit.rs').read_text(encoding='utf8')
assert 'pub fn undo' in work and 'ok_or(EditError::NoUndo)' in work

cases = []
fixtures = read(P/'fixtures.json')
for f in fixtures:
    assert accepted(ns['validate'],f['request'],f['response'])==f['valid'], f['id']
cases.append({'id':'AUTHOR-FIXTURES', 'cases':len(fixtures), 'result':'PASS', 'layer':'document fixtures only; no top-level author script rerun'})
request = fixtures[0]['request']
errors = read(P/'work-error-map.json')
assert len(errors)==7
assert {e['wire']['error']['details']['code'] for e in errors}=={'NotReady','InvalidInput','RevisionConflict','RevisionOverflow','Busy','NoUndo','Closed'}
# New counterexample: retained known failure replay preserves diagnostics but marks replay.
failure = copy.deepcopy(next(e['wire'] for e in errors if e['WORK']=='NoUndo'))
failure['replayed'] = True
assert accepted(ns['Draft202012Validator'](read(P/'response.schema.json')).validate, failure)
assert not accepted(ns['validate'],request,failure)
cases.append({'id':'IR-CX1', 'input':failure, 'expected':'Accept retained authorized terminal error replay with unchanged typed diagnostic', 'observed':'Wire schema accepts; candidate semantic checker rejects exact whole-response equality', 'classification':'DOCUMENT_CHECKER_DEFECT', 'finding':'UNDO-IR-F1'})
# New counterexample: command-specific policy forbids converting NoUndo into success NoChange.
nochange = copy.deepcopy(fixtures[0]['response'])
nochange['value'] = {'outcome':'NoChange','projection':copy.deepcopy(nochange['value']['projection']), 'replayed':False,'revision':'7','history_depth':'0'}
nochange['value']['projection']['revision'] = '7'
assert accepted(ns['validate'],request,nochange)
cases.append({'id':'IR-CX2','input':nochange,'expected':'Reject NoChange for Undo: no no-op behavior exists in WORK and decision UNDO-D5 explicitly preserves NoUndo error','observed':'Candidate command semantic checker accepts','classification':'DOCUMENT_CHECKER_DEFECT','finding':'UNDO-IR-F2'})
# Deliberately unsupported behavioral evidence: proof verification is not an issuer oracle.
proof = read(P/'proof-model.json')
for key,value in [('capture.request_id','different-request'),('pin_evidence.operation_role','save'),('io.formal_save_ack','CALLED')]:
    bad=copy.deepcopy(proof); target=bad
    for part in key.split('.')[:-1]: target=target[part]
    target[key.split('.')[-1]]=value
    assert accepted(ns['proofcheck'],bad)
    cases.append({'id':'IR-GAP-'+key,'mutation':{key:value},'observed':'Synthetic proofcheck accepts; narrative policy forbids this','classification':'EVIDENCE_GAP_ONLY_NOT_PRODUCT_DEFECT'})

# Independent deterministic integer oracle tests schema pattern directly at every boundary.
rng=random.Random(34603)
values=['0','18446744073709551615','18446744073709551616','18446744073709551615\n','01','-1','1e3']
values += [str(rng.randrange(10**21)) for _ in range(5000)]
values += [str(18446744073709551615+i) for i in range(-100,101)]
for schema in ['request.schema.json','response.schema.json']:
    pattern=read(P/schema)['$defs']['U64Decimal']['pattern']
    for value in values:
        expected=bool(re.fullmatch(r'0|[1-9][0-9]*',value)) and int(value)<=2**64-1
        assert bool(re.search(pattern,value))==expected,(schema,value)
cases.append({'id':'IR-U64','result':'PASS','comparisons':len(values)*2,'oracle':'canonical decimal regex plus Python exact integer bound; independent of author strict()'})
life=read(P/'replay-lifecycle-vectors.json')
assert len(life)==5
assert life[0]['current_revision']=='11' and 'do not overwrite live R11' in life[0]['expected']
cases.append({'id':'IR-LIFECYCLE','classification':'EVIDENCE_GAP_ONLY_NOT_PRODUCT_DEFECT','result':'Five narrative lifecycle oracles present; candidate checker only checks expected text presence/capture=7; no replay execution or UI race proof'})

findings=[
 {'id':'UNDO-IR-F1','priority':'P2','classification':'DOCUMENT_CHECKER_DEFECT','source':'check_documents.py:43-44 (validate DomainRejected full-wire equality)','problem':'All seven mappings include replayed=false. Matching retained terminal rejection replayed=true is schema-valid and required by generic retained-result replay policy, but semantic validation rejects it.','fix':'Compare exact error diagnostic shape independently of replay flag; add authorized error replay and revoked replay vectors. If error results are intentionally not retained, specify that lifecycle exception and obtain Owner review.'},
 {'id':'UNDO-IR-F2','priority':'P2','classification':'DOCUMENT_CHECKER_DEFECT','source':'check_documents.py:47-50 (validate NoChange branch exemption)','problem':'Undo-specific checker accepts successful NoChange with empty history despite UNDO-D5 and WORK::undo requiring NoUndo. Keeping shared v3 wire vocabulary does not establish command-specific validity.','fix':'Keep shared schema if required, but reject NoChange for this Undo semantic validator and add explicit negative fixture.'}
]
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
review={'status':'CHANGES_REQUIRED_UNDO_DOCUMENT_CHECKER_ONLY','reviewer':'/root/m03_undo_independent_review','author':'/root/m03_next_command_packet','independent':True,'scope':'readonly candidate/spec/source comparison; writes only undo-response-review','head':head,'branch':branch,'historical_authority_head':source['historical_authority_head'],'authority_entries':796,'authority_drift':drift,'findings':findings,'preserved': ['M04/WORK owns document/history; M03 facade projection only','No formal save FileCommit/ACK/IO on Undo','Confirmed commit remains actual revision with AppliedRetentionDeferred; uncertain M04 => Indeterminate','Complete root version-set narrative includes five providers; Live/Undo/Redo stage order and conservative unresolved pin retention','NoUndo/overflow/Closed/Busy plus seven exact DomainRejected variants','Replay R7→R8 must not overwrite live R11; close/revoke suppress delivery','U64 strictly bounded canonical decimal schemas'], 'evidence_gaps':['Synthetic proof model does not verify issuer authenticity/context/operation binding/root membership','Lifecycle vectors are narrative presence-only, not executable state transition evidence'], 'owner_adoption':'NOT ADOPTED','fullDraft':'MISSING','product_tests':'NOT RUN','native_runtime':'NOT RUN','RED':'NOT RUN','GREEN':'NOT RUN','BUILD':'NOT RUN','module_complete':False,'board':'UNCHANGED; no green/Done'}
assert before=={str(p.relative_to(R)):sha(p) for p in P.iterdir() if p.is_file()},'review mutated candidate'
write('review.json',review)
write('counterexamples.json',cases)
write('reviewed-hashes.json',{'candidate_original_hashes':before,'sources_original_hashes':source['sources'],'additional_reviewed_sources':{p:sha(R/p) for p in required},'authority_manifest':source['authority_manifest'],'authority_manifest_sha256':sha(R/source['authority_manifest'])})
write('verification.json',{'status':'PASS_INDEPENDENT_REVIEW_CHECKER_ONLY','review_verdict':review['status'],'candidate_files_unchanged':True,'authority_entries':796,'authority_drift':0,'independent_counterexamples':2,'evidence_gap_probes':3,'u64_comparisons':len(values)*2,'product_tests':'NOT RUN','native':'NOT RUN','BUILD':'NOT RUN','RED':'NOT RUN'})
body='<h1>M03 Undo 獨立文件複驗</h1><p><strong>CHANGES_REQUIRED — 僅文件 checker</strong></p><p>作者與驗證者不同。Owner 尚未採納；FullDraft 缺失；產品測試、native、RED、GREEN、Build 全為 NOT RUN。未改看板、產品或候選。</p>'
body+='<h2>必修項</h2>'+''.join('<h3>'+html.escape(f['id'])+'</h3><p>'+html.escape(f['problem'])+'</p><p>'+html.escape(f['fix'])+'</p>' for f in findings)
body+='<h2>證據界線</h2><p>Lifecycle 只有 presence 檢查；proof 是 synthetic fixture。未驗證 issuer、完整 membership、撤權競態或新 revision 不被覆寫；這些列為 evidence gap，不是產品缺陷。</p><h2>完整審查資料</h2><pre>'+html.escape(json.dumps(review,ensure_ascii=False,indent=2))+'</pre>'
(O/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>M03 Undo independent review</title><style>body{max-width:1050px;margin:40px auto;font:16px/1.6 system-ui;color:#172331}pre{white-space:pre-wrap;background:#eef3f7;padding:20px}h1{color:#8a4b00}</style>'+body+'</html>',encoding='utf8')
write('artifact-hashes.json',{p.name:sha(p) for p in O.iterdir() if p.is_file() and p.name!='artifact-hashes.json'})
print(json.dumps({'verdict':review['status'],'findings':len(findings),'u64_comparisons':len(values)*2,'authority_entries':796,'drift':0}))

