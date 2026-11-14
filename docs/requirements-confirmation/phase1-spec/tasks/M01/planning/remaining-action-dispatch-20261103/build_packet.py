import json, hashlib, pathlib, subprocess, datetime, html

ROOT = pathlib.Path(__file__).resolve().parents[7]
OUT = pathlib.Path(__file__).resolve().parent
BASE = ROOT / 'docs/requirements-confirmation/phase1-spec/tasks'
sources = {}

def read(path):
    p = ROOT / path
    raw = p.read_bytes()
    sources[path] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    return json.loads(raw.decode('utf-8-sig'))

def rel(p):
    return p.relative_to(ROOT).as_posix()

def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def ref(path, pointer=''):
    if path not in sources:
        p = ROOT / path
        sources[path] = {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
    return {'path': path, 'sha256': sources[path]['sha256'], 'pointer': pointer}

prefix = 'docs/requirements-confirmation/phase1-spec/tasks/'
board = read('docs/board.json')
old = read(prefix+'M01/planning/dispatch-next-actions-20261103/action-matrix.json')
old_review = read(prefix+'M01/planning/dispatch-next-actions-review-20261103/results.json')
decisions = {}
for g in range(1,5):
    decisions[f'G0{g}'] = read(prefix+f'decisions/G0{g}/decision-request.json')
    for f in ('results.json','review.json','binding-results.json','findings.json'):
        p = BASE / f'decisions/G0{g}-review' / f
        if p.exists(): read(rel(p))
for folder in ('input-admission-correction-20261103','input-admission-correction-review-20261103'):
    for p in (BASE/'M08/verification'/folder).glob('*.json'):
        if 'hash' not in p.name and p.stat().st_size < 200000: read(rel(p))
feature_refs = {}
for n in range(1,13):
    found = []
    for p in BASE.rglob('*.json'):
        if f'F{n:02}' in p.parts and any('feature-trace' in s for s in p.parts) and p.name in ('trace.json','feature-trace.json','module-spec.json','results.json','review.json'):
            read(rel(p)); found.append(ref(rel(p)))
    feature_refs[f'F{n:02}'] = found

inventory = read(prefix+'M01/planning/s2-green/source-current.json')
mismatches = []
for path, expected in inventory['source_hashes'].items():
    p=ROOT/path
    actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    if actual != expected: mismatches.append(path)
live_head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
base_m03 = read(prefix+'M03/planning/preview-contract-review/module-spec.json')
cap = read(prefix+'M03/planning/h2-exact-design/viewer-capability.json')
m05 = read(prefix+'M05/planning/catalog-exact-design/module-spec.json')
template = read(prefix+'M02/planning/exact-design/module-spec.json')['first_template']
read(prefix+'M02/planning/activation-source-fence-correction-review/review.json')
read(prefix+'M03/planning/legacy-entry-review/results.json')
product_path='apps/sgenaxis-desktop/crates/sgenaxis-host/src/uidesign_doc.rs'
product= (ROOT/product_path).read_text(encoding='utf-8')
ref(product_path)
start=product.index('pub fn build_preview_html(')
end=product.index('pub fn build_preview_file(',start)
body=product[start:end]
product_facts={
 'kind':'STATIC_SOURCE_EVIDENCE_NOT_RUNTIME',
 'source':ref(product_path),
 'span':{'start_line':product[:start].count('\n')+1,'end_line':product[:end].count('\n')},
 'observations':[
  'Validates DesignDoc then emits one button per node with escaped labels/hints and numeric geometry.',
  'Click listener changes selection classes and textContent summaries; product_pass=false footer.',
  'No img/video/audio/svg element emitted in this function; no media decoder or MIME capability selection in this function.',
  'This bounded function observation does not prove every application path lacks media support.',
  'build_preview_file is a separate filesystem-writing path; this report does not infer no-IO for legacy entry.'
 ],
 'markers':{x: x in body for x in ['doc.validate()?','product_pass=false','textContent','<img','<video','<audio','<svg']}}
write('preview-source-evidence.json',product_facts)

matrix=[]
for ident, family, risks in [
 ('MM01','Raster still image candidate (PNG/JPEG separately selectable)','corrupt/truncated bytes; MIME/extension mismatch; oversized decoded dimensions; orientation/colour handling'),
 ('MM02','SVG candidate','script/event attributes; foreignObject; external href/CSS/font; entity/reference expansion; animation'),
 ('MM03','Animated image candidate','frame count; duration; disposal; aggregate decoded allocation'),
 ('MM04','Video candidate','container versus codec distinction; duration; seek; hardware decoder differences; no executable side effects'),
 ('MM05','Audio candidate','container versus codec distinction; duration; playback permission; device absence'),
 ('MM06','Unknown or opaque imported material','catalog byte availability does not imply rendering support'),
 ('MM07','Unresolved material/binding','placeholder and disabled dependent action; no substitute media or network fetch'),
 ('MM08','Current selection-only communication preview','selection summary is existing static behavior; not full mock/runtime/media acceptance')]:
 matrix.append({'id':ident,'family':family,'support':'UNSELECTED_NOT_APPROVED' if ident not in ('MM07','MM08') else 'EXISTING_FACT_OR_CANDIDATE_BOUNDARY_ONLY',
 'risk_dimensions':risks,'decoder_sdk':None,'version':None,'limits':None,'target_os_dcc':'Windows target context only; DCC N/A for this preparation',
 'source_refs':[ref(prefix+'decisions/G04/decision-request.json','/intent_items/3'),ref(prefix+'M03/planning/h2-exact-design/viewer-capability.json','/materials')],
 'required_evidence':'Exact byte fixture/hash, approved support disposition, decoder/version, resource ceilings, observable success/denial, immutable document hash before/after; native proof remains NOT RUN'})
write('media-minimum-matrix.json',{'status':'PROPOSED_REVIEW_DIMENSIONS_NOT_FORMAT_ADOPTION','delta':'G04 declares media set/SDK/thresholds null. This supplies individually reviewable dimensions and fixture obligations absent from the decision submission, without choosing them.','rows':matrix})

all_paths=subprocess.check_output(['rg','--files','--hidden','-g','!.git','-g','!node_modules','-g','!target'],cwd=ROOT,encoding='utf-8').splitlines()
golden=[]
for i,path in enumerate(template['product_paths'],1):
    suffix=path.replace('\\','/')
    exact=[p.replace('\\','/') for p in all_paths if p.replace('\\','/').endswith('/'+suffix) or p.replace('\\','/')==suffix]
    golden.append({'slot':f'GOLDEN-{i:02}','declared_product_path':path,'existing_exact_suffix_paths':exact[:12],
      'canonical_resource_bytes':None,'resource_sha256':None,'expected_rendered_bytes':None,'status':'MISSING_ACTUAL_TEMPLATE_GOLDEN',
      'why_not_reuse_workspace':'Same basename or application workspace file is not this template resource or standalone transitive dependency solution.',
      'completion_evidence':'Template resource bytes + digest + concrete definition/design input + exact expected output bytes; Cargo.lock must resolve the standalone generated manifest with its toolchain.'})
write('template14-source-inventory.json',{'baseline':template,'baseline_ref':ref(prefix+'M02/planning/exact-design/module-spec.json','/first_template'),'search':'rg --files --hidden excluding .git/node_modules/target; exact declared relative suffix paths only; no package download/build/lock resolution','rows':golden,'remaining_provider':'M02 template author supplies proposed 14 resource bytes and standalone full Cargo.lock; Owner/reviewer adopts exact resource revision before accepted Skeleton/valid RED. No borrowing workspace lock as completed golden.'})

packet={'task_id':'M03-PREP-MEDIA-MINIMUM-CANDIDATE','primary_module':'M03','state':'PREPARATION_INVENTORY_DELIVERED_NEXT_EXACT_DESIGN_ALLOWED','parent':'PD-P1-M01-PREP-01','scope':'Coordination inventory and proposed fixture dimensions only; future M03 planning write requires dispatched original M03 scope.',
 'intent':'Turn unselected G04 media decision into concrete review choices using approved requirements and bounded current source facts.',
 'contracts':['Do not equate opaque material storage with decoder/render support.','Do not infer native safety or product acceptance from generated communication HTML.','Keep selected formats/SDK/limits null until an explicit disposition; examples are not defaults.'],
 'bdd':[{'id':'PREP-MM-01','given':'G04 media support remains unselected and current preview source is available','when':'prepare the media capability candidate','then':'each family states support disposition, decoder/version/limits evidence gaps, fixture oracle and source pointers without claiming support'},
 {'id':'PREP-MM-02','given':'14 declared template paths and no actual resource golden proof','when':'prepare template admission evidence','then':'all 14 paths have explicit bytes/hash/output/standalone-lock obligations; fixture booleans cannot satisfy them'}],
 'tdd_plan':[{'id':'DOC-MM-01','level':'document validation','assert':'8 distinct media dimension rows; decoder/version/limits null; no approved support inferred'}, {'id':'DOC-T14-01','level':'document validation','assert':'exact 14 path equality with adopted baseline; no workspace lock substituted'}],
 'valid_red':'NOT RUN. These are preparation checks, not production behavior RED. Future product test must build/load and fail intended approved behavior assertion; missing SDK/resources/fixture is not RED.',
 'proposed_fixture_inputs':[{'id':x['id'],'data':'bounded valid and invalid byte corpus to be supplied after supported family and thresholds selected','expected':'No assumed decoder success before adoption; retain immutable active document on rejected input'} for x in matrix],
 'acceptance':['Source evidence records exact span/hash and limitation.','8 media rows distinguish fact/candidate/unselected.','14 resource slots preserve existing baseline exactly.','31 live cards receive per-card action/missing condition and provider; no blanket prep blocker.'],
 'next_actions':[{'action':'M03 planner drafts exact supported subset options and explicit rejection semantics using this matrix; proposed fixtures allowed','ready':'ORIGINAL_SCOPE_PREPARATION_ALLOWED_NOW','owner_choice':'adopt exact candidate / return specific fields / defer media rendering; no implicit format/SDK choice'},
 {'action':'M02 planner proposes 14 exact resource bytes and standalone manifest/lock evidence package','ready':'PREPARATION_ALLOWED; ACTUAL_DEPENDENCY_RESOLUTION_NOT_RUN','missing':'Standalone resource bytes/golden not supplied; cannot manufacture success from true fixture gates','provider':'M02 template author + target toolchain/build environment'}],
 'protected':['product','tests','board','spec','hooks','roles','commit'], 'verification':'AUTHOR_DOCUMENT_CHECK_ONLY; independent acceptance/product/native/build/package NOT RUN'}
write('next-task-packet.json',packet)

previous={x['id']:x for x in old['yellow']+old['gray_red']}
cards=[]
for b in board['items']:
 if not b['id'].startswith('PD-P1-') or b.get('light') not in ('Yellow','Gray','Red'):continue
 x=previous.get(b['id'],{})
 row={'id':b['id'],'light':b['light'],'attempt':'Read live card, prior action packet, current bounded canonical/review/feature inputs; no repeated checker or closed acceptance.',
 'source':ref('docs/board.json','/items/'+str(board['items'].index(b))),
 'original_action':x.get('next_concrete_action',x.get('next_action')),
 'missing':x.get('exact_missing_gate',x.get('missing_condition')),
 'provider':'Owner exact candidate disposition and named module/provider evidence; accepted Skeleton/valid RED separately required for product only.',
 'refs':x.get('refs',[]),'action_state':'UNCHANGED_GATE_NO_PRODUCT_AUTHORITY','product_ready':False}
 if 'M02-PREP' in b['id']:
  row.update(action_state='NEW_ORIGINAL_SCOPE_PREPARATION_DELIVERED',action='Completed exact baseline14 path/resource/lock source inventory; next resource-byte candidate authoring remains allowed, not globally Owner-blocked.',provider='M02 template author; toolchain/build provider for standalone lock proof',evidence='template14-source-inventory.json')
 elif 'M03-PREP' in b['id']:
  row.update(action_state='NEW_ORIGINAL_SCOPE_PREPARATION_DELIVERED',action='Completed current preview source evidence and 8-row minimum media decision/fixture matrix; next exact capability candidate may be prepared now.',provider='M03 capability planner; M05 blob authority for availability; renderer/native provider for eventual evidence',evidence='media-minimum-matrix.json')
 elif b['id'].startswith('PD-P1-G0'):
  g=b['id'].split('-')[2];d=decisions[g]
  row.update(action='Canonical decision and fresh independent review already delivered; Owner disposition must identify exact revision/fields, do not redispatch consolidation.',provider='Owner for adopt/return-with-fields/defer; affected module/provider for implementation evidence',refs=[ref(prefix+f'decisions/{g}/decision-request.json')],exact_choices=d.get('owner_exact_selection'),missing='Exact selection is null in canonical decision; candidate publication is not adoption.')
 elif '-F' in b['id'] and 'DELIVERY' in b['id']:
  f=b['id'].split('-')[2];row['feature_refs']=feature_refs.get(f,[]);row['action']='Trace preparation/review already delivered; follow declared module/provider missing inputs, not wrapper delivery or rerun PASS.'
 elif 'M08-VERIFY' in b['id']:
  row.update(action='Corrected admission and independent review already delivered; obtain admitted concrete feature/native inputs before execution; do not promote synthetic admission to real evidence.',provider='Per-feature native/build/report providers identified by corrected admission matrix',refs=[ref(prefix+'M08/verification/input-admission-correction-20261103/missing-inputs.json')])
 elif 'ESS-' in b['id']:
  row['action']='Preserve superseded original card; use replacement module/decision execution scope, not redispatch old plan.'
 cards.append(row)
write('31-card-actions.json',{'owner_heartbeat':'2026-11-03T13:37:06.678Z supplied by parent','ordering':'Yellow then Gray then Red; blocked action recorded and continue','cards':sorted(cards,key=lambda x:({'Yellow':0,'Gray':1,'Red':2}[x['light']],x['id'])),'claim':'Not all current preparation is blocked: new M03 matrix and M02 source inventory delivered; further exact candidate drafting remains allowed.'})
write('source-hashes.json',{'sources':sources,'live_head':live_head,'historical_inventory_head':inventory['head'],'product_inventory_count':len(inventory['source_hashes']),'product_mismatches':mismatches,'feature_refs':feature_refs})
checks={'cards31':len(cards)==31,'media8':len(matrix)==8,'template14':len(golden)==14,'product796':len(inventory['source_hashes'])==796 and not mismatches,'no_format_adoption':all(x['decoder_sdk'] is None and x['limits'] is None for x in matrix),'prior_dispatch_review_read':bool(old_review)}
write('author-checks.json',{'kind':'AUTHOR_DOCUMENT_VALIDATION_ONLY','checks':checks,'pass':all(checks.values()),'not_run':['production RED/GREEN','native media safety','build/package','independent acceptance']})
links=['next-task-packet.json','preview-source-evidence.json','media-minimum-matrix.json','template14-source-inventory.json','31-card-actions.json','source-hashes.json','author-checks.json']
rows=''.join('<tr><td>'+html.escape(x['id'])+'</td><td>'+html.escape(x['light'])+'</td><td>'+html.escape(str(x.get('action',x.get('original_action'))))+'</td><td>'+html.escape(str(x.get('missing')))+'</td></tr>' for x in cards)
(OUT/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Remaining original-scope actions</title><style>body{font:15px system-ui;max-width:1280px;margin:30px auto;background:#111827;color:#e5e7eb}a{color:#93c5fd}td,th{padding:10px;border:1px solid #475569;vertical-align:top}table{border-collapse:collapse}code{color:#fbbf24}</style><h1>Original-scope preparation: concrete next actions</h1><p>New delivery: M03 bounded preview source evidence + 8 media decision dimensions; M02 exact 14 resource/standalone-lock inventory. No format, schema, decoder or threshold adopted. Further candidate preparation is allowed; product remains gated.</p><p>Live HEAD '+live_head+'; historical '+inventory['head']+'; '+str(len(inventory['source_hashes']))+' product hashes, '+str(len(mismatches))+' mismatches. Static evidence only.</p><h2>Artifacts</h2><ul>'+''.join('<li><a href="'+f+'">'+f+'</a></li>' for f in links)+'</ul><h2>31 individual action attempts</h2><table><tr><th>Card</th><th>Light</th><th>Action</th><th>Missing product gate</th></tr>'+rows+'</table><p>Author checks only. Independent acceptance, product RED/GREEN, native decode/safety, build/package NOT RUN. Board and product preserved.</p></html>',encoding='utf-8')
write('seal.json',{'state':'SEALED_STOP_WRITING','author':'/root/remaining_action_dispatch','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'payload':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='seal.json'},'product_ready':False,'independent_review':'NOT RUN'})
print(json.dumps({'output':str(OUT),'checks':checks,'sources':len(sources),'cards':len(cards)}))
