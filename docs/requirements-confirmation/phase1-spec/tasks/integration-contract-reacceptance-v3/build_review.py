import json,hashlib,re,subprocess,html,sys
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
O=Path(__file__).resolve().parent;T=O.parent;R=O.parents[4];P=T/'integration-contract-revision-v3'
sys.path.insert(0,str(R));sys.path.insert(0,str(O))
from document_oracle import errors
from tools.board.board_core.snapshot_safe import split_snapshot,mutate_snapshot_file
from tools.board.board_core.json_store import FileLock
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def put(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dig(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
base=read(T/'M01/planning/s2-green/source-current.json');branch=subprocess.check_output(['git','branch','--show-current'],cwd=R,text=True).strip();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();assert (branch,head)==(base['branch'],base['head']);assert all(sha(R/p)==h for p,h in base['source_hashes'].items())
m=read(P/'module-spec.json');frozen=dict(m['prior_files_sha256'])
for folder in [P]+[(R/x['report']).parent for x in m['children'].values()]:
 for p in folder.iterdir():
  if p.is_file() and p.name!='current-state.json':frozen[p.relative_to(R).as_posix()]=sha(p)
assert all(sha(R/p)==h for p,h in frozen.items())
for folder in [P]+[(R/x['report']).parent for x in m['children'].values()]:assert all(sha(folder/k)==v for k,v in read(folder/'artifact-hashes.json').items())
board=R/'docs/PROJECT-BOARD.html';a,b,c=split_snapshot(board.read_text(encoding='utf-8'));before=json.loads(b);counts=dict(Counter(x['zone'] for x in before['tasks']))
common=read(P/'shared-contract.json');schema=read(P/'h2-design_candidate_install-response.schema.json')
# Concrete mismatch witnesses against new schema roots, NOT actual product commands.
array_error={'ok':False,'error':{'code':'UnsupportedDocument','details':{'nodes':[{'node_id':'n1','type':'Unknown','reason':'unsupported'}]}},'replayed':False}
string_error={'ok':False,'error':{'code':'UnsupportedDocument','details':{'nodes':'not a node list'}},'replayed':False}
open_reason={'ok':False,'error':{'code':'InvalidRequest','details':{'field':'/x','reason':'ARBITRARY_UNDECLARED_REASON'}},'replayed':False}
witness={'typed_nodes_array':{'value':array_error,'schema_errors':errors(schema,array_error,schema)},'invalid_nodes_string':{'value':string_error,'schema_errors':errors(schema,string_error,schema)},'unknown_reason':{'value':open_reason,'schema_errors':errors(schema,open_reason,schema)}}
assert witness['typed_nodes_array']['schema_errors'] and not witness['invalid_nodes_string']['schema_errors'] and not witness['unknown_reason']['schema_errors']
material=read((R/m['children']['M05']['report']).with_name('module-spec.json'))['effective_spec']['errors']['codes'];mapping=common['h2_error_lifecycle']['mapping'];mapped=set(k for x in mapping for k in x['source'].split('|'));unmapped=sorted(set(material)-mapped)
findings=[{'id':'V3-F1','severity':'P2','origin':'V2-F2','pointer':'h2-*-response.schema.json/$defs/Error','problem':'field_schema turns legacy descriptor strings into unrestricted string schemas. UnsupportedDocument.details.nodes is string rather than node array; InvalidRequest.details.reason is arbitrary string rather than the listed closed enum. Local refs resolve but the resulting schema accepts invalid public error payloads and rejects the declared typed node list.','evidence':witness,'required_correction':'Create explicit typed schema per error detail, no prose inference. nodes must array of closed node/type/reason records; InvalidRequest reason must exact enum. Reconcile DomainRejected variant-specific fields and every original closed detail. Add valid/invalid witnesses per error before claiming complete schema closure.'},{'id':'V3-F2','severity':'P2','origin':'V2-F3','pointer':'shared-contract.json/h2_error_lifecycle/mapping versus M05 effective_spec/errors/codes','problem':'Mapping covers all 11 bounded read errors but not all MaterialError codes from pin/resolve/import/root/receipt operations. StaleRoot singular differs from mapped StaleRoots, and Storage/MaterialRecoveryBlocked have no exact conversion. The closed H2 error union cannot deterministically represent these outcomes without a new mapping.','unmapped_material_codes':unmapped,'required_correction':'Map every existing MaterialError code/reason and IO uncertainty stage to exact H2 code/details or verified postcommit deferred outcome; explicitly normalize StaleRoot versus StaleRoots. Storage recovery/uncertain catalog outcome must not become generic unchanged failure. Preserve authority/binding-first lifecycle and no automatic retry.'}]
put(O/'findings.json',findings)
rows=read(O/'vector-admission-check.json');vectors=read(P/'request-hash-vectors.json');refcount=0
for f in P.glob('*.schema.json'):
 root=read(f)
 def walk(x):
  global refcount
  if isinstance(x,dict):
   if '$ref' in x:
    q=root
    for k in x['$ref'][2:].split('/'):q=q[k.replace('~1','/').replace('~0','~')]
    refcount+=1
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(root)
for v in vectors:
 if 'a'in v:
  assert hashlib.sha256(bytes.fromhex(v['a_utf8_hex'])).hexdigest()==v['a_sha256'];assert hashlib.sha256(bytes.fromhex(v['b_utf8_hex'])).hexdigest()==v['b_sha256'];assert v['a_sha256']!=v['b_sha256']
checks={'hash_vectors':{'total':209,'both_bodies_admitted_by_review_subset':173,'structural_faults_rejected':36,'stored_bytes_sha_match':True,'meaning':'Document value/schema subset and byte/hash arithmetic only; product conflict handling NOT RUN'},'schema_roots':38,'local_refs_resolved':refcount,'original_case_trace':769,'common_children_hashes':'PASS_STATIC_ONLY','prior_and_reviewed_files_unchanged':len(frozen),'source796_unchanged':True,'full_jsonschema_validator':'NOT RUN; module unavailable, no dependency installation','subset_oracle':'Review-local explicit type/enum/const/shape/required/pattern/length/oneOf/anyOf and local ref evaluation; no draft metaschema conformance claim'}
put(O/'structural-checks.json',checks)
verdict='CHANGES_REQUIRED_V3_SCHEMA_AND_ERROR_MAPPING_ONLY'
report={'identity':{'task':'CX-V3-READONLY-REACCEPTANCE','at':datetime.now(timezone.utc).isoformat(),'branch':branch,'head':head,'status':verdict},'disposition':{'V2-F1':'PASS_DOCUMENT_CORRECTION_SCOPE_ONLY: full recursive body includes omitted pin purpose/id, actual root contents, import metadata/bundle evidence; 11 roles/import variants and 209 documents checked; executable/provider/canonical parity gates remain','V2-F2':'PARTIAL: 38 local schema roots/1079 refs resolve; error detail type and enum precision still V3-F1','V2-F3':'PARTIAL: runtime loss/replay/11 read errors and binding/restart lifecycle improved; full M05 MaterialError mapping V3-F2 missing'},'findings':findings,'checks':checks,'preserved_hashes':frozen,'gates':read(P/'prerequisite-gates.json'),'limits':'Same assistant separate read-only phase, not delegated independent reviewer. No adoption/Skeleton/product edits; tests/build/RED/GREEN/native NOT RUN.'}
put(O/'module-spec.json',report)
body='<h1>CX v3 另輪唯讀複驗</h1><p><b>'+verdict+'</b></p><p>完整 hash body 的原文件缺口已受限閉合；schema local refs 已閉合，但型別精度與完整 material error mapping 仍需候選補正。不是全 CX PASS 或 Owner 採納。</p>'
for k,v in report['disposition'].items():body+='<h2>'+k+'</h2><p>'+html.escape(v)+'</p>'
body+='<h2>兩項精確差額與文件反例</h2><pre>'+html.escape(json.dumps(findings,ensure_ascii=False,indent=2))+'</pre><h2>驗證範圍</h2><pre>'+html.escape(json.dumps(checks,ensure_ascii=False,indent=2))+'</pre><h2>保留門檻</h2><p>template golden／typed projector／provider writer coverage／Windows11 native 及 Owner 採納均保留。完整 JSON Schema validator NOT RUN；本輪只有 review-local 子集文件 oracle。未執行產品 tests/build/RED/GREEN/native，未建立 Skeleton。</p><p>同一助理另一輪程序，未委派獨立 reviewer；受審包與產品未改。</p>'
(O/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>CX v3 唯讀複驗</title><style>body{max-width:1100px;margin:40px auto;font:16px system-ui;line-height:1.6}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f7;padding:18px}</style>'+body+'<script type="application/json" id="module-spec">'+json.dumps(report,ensure_ascii=False).replace('</','<\/')+'</script></html>',encoding='utf-8')
assert all(sha(R/p)==h for p,h in frozen.items()) and all(sha(R/p)==h for p,h in base['source_hashes'].items())
hashes={p.name:sha(p) for p in O.iterdir() if p.is_file() and p.name not in ['artifact-hashes.json','review-result.json','board-evidence.json']};revision=dig(hashes);put(O/'artifact-hashes.json',hashes);put(O/'review-result.json',{'revision':revision,'verdict':verdict,'source_revision':read(P/'review-request.json')['revision_sha256'],'findings':['V3-F1','V3-F2']})
nav=read(P/'current-state.json');nav['readonly_reacceptance']={'report':(O/'index.html').relative_to(R).as_posix(),'revision':revision,'status':verdict};put(P/'current-state.json',nav)
def mutate(s):
 card=next(x for x in s['tasks'] if x['id']=='PD-P1-ESS-DEC-01');assert card['zone']=='red';card['note']+='\n[V3 readonly reacceptance] '+(O/'index.html').relative_to(R).as_posix()+' revision '+revision+'; '+verdict+'; V2-F1 document-only closed, V3-F1 error schema detail precision and V3-F2 complete material mapping pending. Same assistant separate phase, no delegated reviewer/adoption/Skeleton/product change.'
mutate_snapshot_file(board,mutate,lock_factory=FileLock)
aa,bb,cc=split_snapshot(board.read_text(encoding='utf-8'));after=json.loads(bb);assert(a,c)==(aa,cc);assert {k:v for k,v in before.items() if k!='tasks'}=={k:v for k,v in after.items() if k!='tasks'};assert [x for x in before['tasks'] if x['id']!='PD-P1-ESS-DEC-01']==[x for x in after['tasks'] if x['id']!='PD-P1-ESS-DEC-01'];assert counts==dict(Counter(x['zone'] for x in after['tasks']))
put(O/'board-evidence.json',{'before':counts,'after':counts,'own_card_red':True,'other_cards_shell_root_preserved':True})
print(json.dumps({'verdict':verdict,'revision':revision,'frozen':len(frozen),'counts':counts,'unmapped':unmapped}))
