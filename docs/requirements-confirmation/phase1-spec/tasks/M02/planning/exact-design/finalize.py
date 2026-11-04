import json, pathlib, hashlib, html, subprocess, collections
from datetime import datetime, timezone
P=pathlib.Path(__file__).resolve().parent
ROOT=next(x for x in P.parents if (x/'.git').exists())
def read(n): return json.loads((P/n).read_text(encoding='utf-8'))
def write(n,d): (P/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
spec=read('module-spec.json'); env=read('envelope.json'); tests=read('test-plan.json')
spec['IPC_and_UI_proposed']['plan_lifecycle']={
 'id':'HOST assigns unique 32-lowercase-hex plan_id; one pending plan per authorized project/session. No wall-clock TTL or new Clock port.',
 'digest':'preview_digest = sha256 of exact UTF-8 preview JSON response bytes stored by HOST; UI echoes the opaque digest. Not a digest reconstructed from UI fields.',
 'invalidate':'New prepare replaces old plan; cancel, successful activation, project switch, session close and restart invalidate it. Stale binding rejects confirmation and requires prepare again.',
 'confirm':'Compare plan_id and preview_digest, then freshly compare definition revision/digest, template raw digest, trusted approvals and base activation under writer lease before mutation.',
 'result':'Tagged response: DefinitionOnly{missing}, Prepared{plan_id,preview_digest,preview}, ActivatedSkeletonOnly{generation_id,activation_sequence}, CancelledBeforeActivation{}, Error{code,message,retryable,recovery_paths}. Error and success payloads are mutually exclusive. Busy/StalePlan/RecoveryRequired are error codes; Publishing is progress only.'}
write('module-spec.json',spec)
for row in tests['cases']: row['fixture']='fixture-catalog.json#'+row['id'].replace('M02-','')
write('test-plan.json',tests)
scenarios=[
 ('T01','Complete confirmed definition','a complete definition and an available approved template','the author prepares generation','the preview contains both program and UI design skeletons and the definition is unchanged'),
 ('T02','Missing decisions','a definition with required decisions still missing','the author prepares generation','the missing decisions are listed and no artifacts are generated'),
 ('T07','Stale preview','a prepared preview whose definition has since changed','the author confirms that preview','generation is refused and a fresh preview is requested'),
 ('T16','Cancel preview','an author reviewing a generation preview','the author cancels','the project files remain unchanged'),
 ('T18','Failure before activation','a project with a previously usable generated version','preparing the replacement files fails','the previously active version remains usable'),
 ('T19','Uncertain activation','a project with a previously usable generated version','activating a replacement reports that recovery is required','the author sees the recovery requirement and no unverified version is presented as usable'),
 ('T20','Late cancellation','activation has already started','the author requests cancellation','the final activation result is shown without falsely claiming cancellation'),
 ('T33','Refresh while publishing','the preview displays a previously verified version','a refresh cannot obtain a verified replacement','the previous preview remains visible and the refresh failure is explained')]
feature=['@proposal_only @M02_EXACT_CB_v1','Feature: Safe generation planning and immutable publication','  Background:','    Given an author has opened an authorized local project','', '  Rule: A new version becomes usable only after verified activation','']
for tid,name,g,w,t in scenarios: feature += ['    @M02-'+tid,'    Scenario: '+name,'      Given '+g,'      When '+w,'      Then '+t,'']
(P/'module.feature').write_text('\n'.join(feature),encoding='utf-8')
baseline=read('authorization-and-baseline.json')
drift=[r['path'] for r in baseline['source_files'] if not (ROOT/r['path']).is_file() or hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()!=r['sha256']]
assert not drift,drift
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(); assert head==baseline['head']
assert len(tests['cases'])==34 and len({x['id'] for x in tests['cases']})==34
assert len(env['slices'])==4
fixtures=read('fixtures.json'); schema_checks=[]
try:
 from jsonschema import Draft202012Validator
 for key,name in [('store','store'),('template','template'),('manifest','artifacts'),('activation','activation')]:
  schema=read('schemas/generation-'+name+'.schema.json'); Draft202012Validator.check_schema(schema); Draft202012Validator(schema).validate(fixtures[key]);schema_checks.append(key)
 schema_status='PASS: four syntax examples validated against Draft 2020-12 schemas; semantic and real-byte fixtures NOT RUN'
except ImportError: schema_status='NOT RUN: jsonschema unavailable; JSON parsing only'
checks={'generated_at':datetime.now(timezone.utc).isoformat(),'head':head,'source_files_checked':len(baseline['source_files']),'source_drift':drift,'scope':'documentation, own board evidence and scheduler update only','json_parse':'PASS','schema_validation':schema_status,'test_plan_cases':34,'slices':4,'product_tests':'NOT RUN','RED':'NOT RUN: no approved Skeleton/test implementation in this delivery','build_package_runtime':'NOT RUN','independent_acceptance':'NOT RUN','architecture_approval':'C+B direction adopted; exact design proposed pending one confirmation'}
write('verification.json',checks)
def render(v):
 if isinstance(v,dict): return '<dl>'+''.join('<dt>'+html.escape(str(k))+'</dt><dd>'+render(x)+'</dd>' for k,x in v.items())+'</dl>'
 if isinstance(v,list): return '<ul>'+''.join('<li>'+render(x)+'</li>' for x in v)+'</ul>'
 return '<span>'+html.escape(str(v))+'</span>'
def section(title,keys): return '<section><h2>'+title+'</h2>'+''.join('<h3>'+html.escape(k)+'</h3>'+render(spec[k]) for k in keys)+'</section>'
page='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M02 C+B exact design</title><style>body{font:16px/1.65 system-ui,sans-serif;color:#193143;background:#eff3f6;margin:0 auto;max-width:1200px;padding:28px}section,header{background:white;padding:24px;margin:20px 0;border-radius:12px}h1,h2,h3{line-height:1.3}dt{font-weight:650;margin-top:14px}dd{margin-left:20px}li{margin:6px 0}pre{white-space:pre-wrap;background:#172c3c;color:white;padding:20px}a{color:#086d94}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd7df;padding:10px;text-align:left;vertical-align:top}.badge{background:#fff0bf;padding:12px;border-left:5px solid #bf8100}code{overflow-wrap:anywhere}</style><header><h1>M02 C+B \u7cbe\u78ba\u8a2d\u8a08\u63d0\u6848</h1><p>2026-11-01 | M02-EXACT-CB-v1</p><p class="badge">\u5df2\u78ba\u8a8d\uff1aC \u7d14\u8a08\u756b\u512a\u5148\uff1bB \u4e0d\u53ef\u8b8a\u7248\u672c\uff0b\u55ae\u4e00\u555f\u7528\u63cf\u8ff0\u6a94\u3002\u4ee5\u4e0b\u7cbe\u78ba\u5951\u7d04\u3001Port\u3001schema \u8207 envelope \u70ba\u5efa\u8b70\u63a1\u7528\uff0c\u96c6\u4e2d\u5f85\u4e00\u6b21\u78ba\u8a8d\u3002\u7522\u54c1\u5be6\u4f5c\u3001Skeleton\u3001RED\u3001build \u5747 NOT RUN\u3002</p><p>Prior direction-choice pending status is superseded by the owner's C+B adoption. Prior publication-gap evidence remains historical. This proposal does not declare a module complete.</p><a href="../publication-gap/index.html">Original publication-gap trace</a> | <a href="module-spec.json">Canonical proposal JSON</a> | <a href="envelope.json">Exact file envelope</a> | <a href="test-plan.json">34 planned tests</a> | <a href="verification.json">Static verification</a></header>'''
page+=section('1. \u610f\u5716\u8207\u9700\u6c42\u57fa\u7dda',['requirement_summary','confirmed','implementation_authority'])
page+=section('2. \u5047\u8a2d\u8207\u5efa\u8b70\u9810\u8a2d',['assumptions','first_template'])
page+='<section><h2>3. \u4efb\u52d9\u62c6\u5206\u8207\u7cbe\u78ba\u7bc4\u570d</h2>'+render(env)+'<h3>BDD / TDD / acceptance</h3><p><a href="module.feature">Stakeholder BDD</a> | <a href="fixture-catalog.json">Planned fixtures</a> | <a href="steps-pending.json">Pending automation</a></p><p>All cases below are PLANNED_NOT_RUN, not valid RED or GREEN. First approval authorizes only S1 Skeleton and valid RED, then independent review. S2-S4 require later slice gates.</p><table><tr><th>ID / slice / level</th><th>Given / When / Then</th><th>Contract / fault</th></tr>'
for r in tests['cases']: page+='<tr><td>'+html.escape(r['id']+' / '+r['slice']+' / '+r['level'])+'</td><td>'+render({k:r[k] for k in ['given','when','then']})+'</td><td>'+render({k:r[k] for k in ['contract','fault','valid_red']})+'</td></tr>'
page+='</table><h3>B1-B12 coverage evaluation</h3>'+render(tests['B1_B12'])+'<h3>Commands and regression gates</h3>'+render({k:tests[k] for k in ['commands','regression','scope_warning']})+'</section>'
page+='<section><h2>4. \u67b6\u69cb\u8207\u5951\u7d04</h2><h3>Hexagonal view</h3><pre>UI / Tests\n  v\nTauri Commands -> DispatchHost -> HOST GenerationUseCase\n                                  |\n                                  v\n                         WORK pure generation policy\n\nHOST -> Output Ports <- Windows adapters\n        FileSystemPort (existing)\n        FileCommitPort (existing single-file activation)\n        GenerationArtifactPort / OwnedGenerationStage / GenerationReadLease (proposed)</pre><h3>Module / ownership / transaction view</h3><pre>M01 immutable definition -> M02 plan -> HOST verified render\n                                         |\n                                         v\n                              owned staging -> sealed version\n                                                   |\n                                        single active.json commit\n                                                   |\nM03 <- verified bounded byte snapshot <- shared read lease + journal check\n\nDefinition: M01 SSOT | Pending plan: HOST session only\nVersions: immutable | Activation: one pointer | Views: derived\nWORK has no FS / OS / serde / concrete adapter dependency.</pre></section>'
page+=section('Detailed proposed architecture',['architecture','pure_C_contract','ports_proposed','layout','wire_contracts','reader_consistency','publication_flow','failure_matrix','IPC_and_UI_proposed'])
page+='<section><h3>Versioned JSON schemas</h3>'+''.join('<p><a href="schemas/'+x.name+'">'+x.name+'</a></p>' for x in sorted((P/'schemas').glob('*.json')))+'<p><a href="schema-semantic-rules.json">Mandatory semantic validation beyond JSON Schema</a> | <a href="fixtures.json">Syntax examples (placeholder digests; not rendering goldens)</a></p></section>'
page+=section('5. \u98a8\u96aa\u8207\u4e00\u6b21\u78ba\u8a8d\u6e05\u55ae',['decision_batch'])
page+='<section><h3>Remaining gates and risks</h3><p>IO product implementation is not complete; its accepted Skeleton/RED stage does not authorize live publication claims. Native locks, crash recovery, reparse aliases, template golden bytes and isolated generated-project build remain to be proved. No automatic deletion of sealed versions is proposed. Future cleanup requires an explicit reference and recovery policy. No unresolved issue prevents other modules from planning or reviewing within their own envelopes.</p>'+render(checks)+'</section>'
page+='<script type="application/json" id="module-spec">'+json.dumps({'spec':spec,'envelope':env,'tests':tests,'verification':checks},ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
(P/'index.html').write_text(page,encoding='utf-8')
print(json.dumps(checks))
