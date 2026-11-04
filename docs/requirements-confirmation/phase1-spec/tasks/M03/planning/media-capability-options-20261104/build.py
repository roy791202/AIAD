"""Read-only repository comparison; writes only this document packet."""
from pathlib import Path
import hashlib, json, subprocess, datetime, html, tomllib

ROOT = Path(__file__).resolve().parents[7]
OUT = Path(__file__).resolve().parent
BASE = 'apps/sgenaxis-desktop/'
TASKS = 'docs/requirements-confirmation/phase1-spec/tasks/'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return (ROOT/p).read_text(encoding='utf-8-sig')
def dump(name, value): (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def evidence(path, start, end):
    lines=read(path).splitlines()
    return dict(path=path, sha256=digest(ROOT/path), start=start, end=end,
                snippet='\n'.join(lines[start-1:end]), layer='STATIC_SOURCE_ONLY')

head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
authority_path=TASKS+'M01/planning/s2-green/source-current.json'
authority=json.loads(read(authority_path))
authority_diff=[]
for p,h in authority['source_hashes'].items():
    actual=digest(ROOT/p) if (ROOT/p).is_file() else None
    if actual != h: authority_diff.append(dict(path=p, authority_sha256=h, live_sha256=actual))
refs=[authority_path, 'AGENTS.md', 'docs/board.json',
 TASKS+'M03/planning/current-state.json',
 TASKS+'M01/planning/exact-disposition-correction-20261103/register.json',
 TASKS+'M01/planning/exact-disposition-correction-review-20261103/index.html',
 TASKS+'M01/planning/current-action-blockers-20261103/actions.json',
 TASKS+'M01/planning/current-action-blockers-review-20261103/correction-index.html',
 TASKS+'M03/planning/media-fixture-provenance-20261103/fixtures.json',
 TASKS+'M03/planning/media-fixture-provenance-review-20261103/results.json',
 TASKS+'M03/planning/preview-media-candidate-20261103/candidate.json',
 TASKS+'M03/planning/h2-exact-design/viewer-capability.json']
for p in refs: read(p)
ev=[evidence(BASE+'ui/app.js',3670,3690), evidence(BASE+'ui/app.js',11134,11139),
 evidence(BASE+'ui/app.js',11164,11191), evidence(BASE+'ui/app.js',10722,10737),
 evidence(BASE+'ui/app.js',13323,13348), evidence(BASE+'src-tauri/src/commands.rs',2108,2127),
 evidence(BASE+'src-tauri/src/lib.rs',124,134),
 evidence(BASE+'crates/sgenaxis-host/src/uidesign_doc.rs',335,365)]
manifests=sorted((ROOT/BASE).rglob('Cargo.toml'))
manifests=[p for p in manifests if 'target' not in p.parts and 'node_modules' not in p.parts]
dependency_inventory=[]
for p in manifests:
    obj=tomllib.loads(p.read_text(encoding='utf-8-sig'))
    dependency_inventory.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p),
        sections={k:v for k,v in obj.items() if k.endswith('dependencies')}))
lockpath=BASE+'src-tauri/Cargo.lock'
lock=tomllib.loads(read(lockpath))
png=[dict(name=p['name'],version=p['version'],dependencies=p.get('dependencies',[]))
     for p in lock['package'] if p['name']=='png' or any(d=='png' or d.startswith('png ') for d in p.get('dependencies',[]))]
assets=[]
for rel in ['ui/icons/brand/splash.png','ui/icons/arch/UI.svg']:
    p=ROOT/BASE/rel
    if p.is_file(): assets.append(dict(path=BASE+rel,sha256=digest(p),bytes=p.stat().st_size,
        use='Existing bundled visual asset; candidate fixture seed only, not imported-material proof'))
candidate=json.loads(read(TASKS+'M03/planning/preview-media-candidate-20261103/candidate.json'))
observations=[
 ('Bundled PNG shell asset and transitive png lock entry exist. JPEG imported decode path NOT_PROVEN.', ['asset inventory','dependency inventory'], 'Consider separate PNG and JPEG selections; existing PNG asset can seed a control after Owner approval; acquire JPEG bytes with provider provenance separately.'),
 ('Bundled architecture SVG icons are selected by archKindIconSrc and assigned to img.src. This is shell icon display, not arbitrary imported SVG sanitization.', [0,1,2], 'Compare bundled-icon control with separately supplied imported SVG; active content/external references require explicit policy, not reuse of shell trust.'),
 ('Animation timing/frame decode and imported animated material path NOT_PROVEN by inspected source/manifests.', ['dependency inventory'], 'Owner selects animated format or explicit unsupported disposition; supplier provides single-frame and multi-frame identities plus timing metadata.'),
 ('Video media decoder/player Port or imported video path NOT_PROVEN by inspected source/manifests.', ['dependency inventory'], 'Select container and codec independently before acquisition; supplier records both and immutable bytes; playback permission/deadline needs approved environment.'),
 ('Audio media decoder/player Port or imported audio path NOT_PROVEN by inspected source/manifests.', ['dependency inventory'], 'Select container/codec and audible versus metadata-only behavior; acquire silent control plus signal fixture and independent capture environment after selection.'),
 ('XML FileReader path reads text into architecture import. It does not establish opaque imported-media preservation or decoding.', [3], 'Compare preservation-only candidate with explicit rejection candidate; provider supplies arbitrary immutable bytes, extension/MIME conflicts and original byte digest.'),
 ('Proposed H2 materials policy explicitly forbids file/network/image loading as mock effect and proposes inert placeholders. This is proposed document behavior, not a native result.', ['viewer-capability.json /materials'], 'Acquire unresolved stable material/binding identities from approved owner snapshot; do not create fake media or fetch fallback.'),
 ('UI Build invokes uidesign_build_preview only with IPC; command authorizes, resolves root, calls build_preview_file and optionally opens OS association. Existing preview is communication-only.', [4,5,6,7], 'Keep selection communication control separate from future media cases; retain doc identity, generated path/hash and independent native screenshot if later authorized.')]
rows=[]
for r,(ob,ee,acq) in zip(candidate['rows'],observations):
    rows.append(dict(id=r['id'],family=r['family'],source_observation=ob,evidence=ee,
        imported_format_support='NOT_PROVEN',native_decode_render='NOT RUN',
        owner_selection=None,format=None,sdk=None,thresholds=None,
        acquisition_delta=acq,
        prerequisite='Exact disposition + fixture identity/provenance + approved failure/limits semantics + separate native verifier',
        reuse='Existing seven-category provenance recipes remain authoritative candidate input; this adds source-path comparison only.'))
options=[dict(id='O1',scope='Retain communication-only selection baseline; defer imported decode',
        existing_evidence='UI command and host file path; no new dependency',decision=None,
        gap='Does not satisfy future media decode requirement; Owner must decide disposition.'),
    dict(id='O2',scope='Evaluate existing bundled PNG/SVG as controls only',existing_evidence='Hashed repo assets + shell img path + transitive png lock entry',decision=None,
        gap='Bundled trust/display cannot establish imported material safety; no format adoption or SDK reuse authorized.'),
    dict(id='O3',scope='Evaluate imported format subsets independently',existing_evidence='Eight candidate dimensions and source inventory',decision=None,
        gap='Owner must choose exact subsets, SDK/runtime, thresholds and transaction/permission behavior; new architecture returns to planning.'),
    dict(id='O4',scope='Preservation or explicit unsupported outcomes for selected families',existing_evidence='Opaque-material and unresolved-binding candidate dimensions',decision=None,
        gap='No inferred rejection contract: Owner must approve exact observable outcomes and preservation oracle.' )]
packet=dict(module='M03',author='/root/yellow_remaining_execute',reviewer=None,
 status='SOURCE_COMPARISON_CANDIDATE_PENDING_INDEPENDENT_DOCUMENT_REVIEW',layer='DOCUMENT_ONLY',
 generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),live_head=head,
 authority_head=authority['head'],authority_count=len(authority['source_hashes']),authority_drift=authority_diff,
 scope='Only this new directory; no product/test/spec/board/hook/role/git modifications',
 new_value='Cross-path evidence: bundled icons, XML text import, IPC build chain, transitive dependency consumers. Does not repeat preview HTML 210..334 inventory.',
 rows=rows,options=options,approval=None,module_complete=False,valid_red='N/A_DOCUMENT_ONLY',
 build_package_install_dcc_regression='NOT RUN',
 acceptance=['Eight dimensions bound to existing candidates','No format SDK threshold adopted','Live hashes and bounded source spans present','No transitive dependency treated as product decode proof'])
dump('module-spec.json',packet)
dump('source-evidence.json',dict(evidence=ev,assets=assets,dependency_inventory=dependency_inventory,
    transitive_png_consumers=png,lock=dict(path=lockpath,sha256=digest(ROOT/lockpath)),
    limitation='Manifest/lock/source inspection is not feature activation, target runtime, imported-media support, or decode/render proof. NOT_PROVEN never means unsupported.'))
dump('source-bindings.json',[dict(path=p,sha256=digest(ROOT/p)) for p in refs])
body='<h1>M03 media capability options</h1><p>DOCUMENT ONLY · Owner selection OPEN · native decode/render NOT RUN · module incomplete</p>'
body+='<p>新增比較：shell PNG/SVG、XML text ingress、IPC Build chain、transitive PNG consumers。現有顯示與依賴不代表 imported media 支援。</p>'
body+='<h2>Eight dimensions</h2><table><tr><th>ID / family</th><th>Existing source / limit</th><th>Acquisition decision</th></tr>'
for r in rows: body+='<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in [r['id']+' '+r['family'],r['source_observation'],r['acquisition_delta']])+'</tr>'
body+='</table><h2>Owner comparison, no selection</h2>'
for o in options: body+='<p><b>'+o['id']+'</b> '+html.escape(o['scope']+' — '+o['gap'])+'</p>'
body+='<h2>Verification boundary</h2><p>All format support NOT_PROVEN. SDK, format, thresholds, approval remain null. Existing fixture provenance recipes are reused; no new schema. No product tests or native proof.</p>'
body+='<h2>Structured evidence</h2><p><a href="source-evidence.json">Bounded source snippets / dependency inventory / asset digests</a> · <a href="module-spec.json">Module candidate</a></p>'
payload=json.dumps(packet,ensure_ascii=False).replace('</','<\\/')
(OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M03 source capability options</title><style>body{font:16px system-ui;margin:36px;line-height:1.5}table{border-collapse:collapse}td,th{padding:12px;border:1px solid #bbb;vertical-align:top}h1{color:#805900}</style>'+body+'<script type="application/json" id="module-spec">'+payload+'</script>',encoding='utf-8')
checks=dict(rows=len(rows),unique_ids=len({r['id'] for r in rows}),source_spans=len(ev),
    authority_entries=len(authority['source_hashes']),authority_drift=len(authority_diff),
    null_decisions=all(r[k] is None for r in rows for k in ['owner_selection','format','sdk','thresholds']),
    result='PASS_DOCUMENT_SELF_CHECK_ONLY',independent_review='PENDING',product='NOT RUN')
assert checks['rows']==checks['unique_ids']==8 and checks['null_decisions']
dump('checks.json',checks)
dump('seal.json',dict(status='SEALED_PENDING_INDEPENDENT_REVIEW',live_head=head,
    hashes={p.name:digest(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='seal.json'}))
print(json.dumps(checks))
