import copy, hashlib, json, pathlib, subprocess, datetime
ROOT=pathlib.Path(__file__).resolve().parents[7]
OUT=pathlib.Path(__file__).resolve().parent
BASE=OUT.parent/'remaining-action-dispatch-20261103'
def read(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'))
def write(name,obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
taskroot='docs/requirements-confirmation/phase1-spec/tasks/'
cards=read(BASE/'31-card-actions.json')
cards['owner_heartbeat']='2026-11-03T13:57:06.633Z supplied by coordinator'
cards['cards'][0]['provider']='Windows11 x64 isolated machine/environment provider + native reparse/8.3 fixture provider; different verification role executes existing remaining matrix. No new Owner adoption required.'
write('31-card-actions.json',cards)
packets=[]
for module,slug,purpose in [('M03','preview-media-candidate-20261103','Preview source and media capability candidate preparation'),('M02','golden14-lock-inventory-20261103','14 resource golden and standalone lock evidence inventory')]:
    prefix=taskroot+module+'/planning/'+slug+'/'
    p={'task_id':module+'-PREP-'+slug.upper(),'parent':'PD-P1-'+module+'-PREP-01','primary_module':module,'allowed_modules':[module],
       'state':'BOUNDED_PLANNING_PACKET_ONLY','intent':purpose,'authority':'Original planning scope only; no implementation authorization or decision adoption.',
       'allowed_files':[prefix+n for n in ['candidate.json','module.feature','steps.py','fixtures.json','pending.json','index.html']],
       'protected':['all product source','all product tests','board','spec','hooks','roles','existing reports','other module packages','commit/push/release'],
       'source_refs':[taskroot+'PD-P1-'+module+'-PREP-01.json',str((BASE/('media-minimum-matrix.json' if module=='M03' else 'template14-source-inventory.json')).relative_to(ROOT)).replace('\\','/'),str((BASE/'preview-source-evidence.json').relative_to(ROOT)).replace('\\','/') if module=='M03' else taskroot+'M02/planning/exact-design/module-spec.json'],
       'bdd_requirements':{'format':'Feature → Background → Rule → Scenario → Given/When/Then; observable document outcomes only','scenarios':['success: source-bound complete candidate','failure: unsupported adoption claim rejected','boundary: exact 8 media dimensions' if module=='M03' else 'boundary: exact 14 baseline paths','missing evidence remains explicit NOT RUN'],'steps':'steps.py contains pending step stubs; never claim executable product behavior'},
       'fixture_requirements':{'source': 'media-minimum-matrix.json' if module=='M03' else 'template14-source-inventory.json','expected':'8 rows with null format/SDK/threshold decisions' if module=='M03' else 'exact baseline 14 paths; per-path bytes/hash/output/provenance and independent standalone manifest/lock proof obligations; absent admitted proof remains missing','negative':['missing source','false approval claim','wrong row/path count']},
       'deliverable_schema':{'candidate.json':['primary_module','source_refs','rows','not_run'],'fixtures.json':['primary_module','cases'],'pending.json':['primary_module','automation','open_questions']},
       'commands':['python '+str((OUT/'check.py').relative_to(ROOT)).replace('\\','/')+' --packet '+module,'python '+str((OUT/'check.py').relative_to(ROOT)).replace('\\','/')+' --deliverables '+module],
       'acceptance':['Packet checker exits 0; deliverable checker exits 0 after all six exact files are authored','Every row has source refs and observable oracle; missing evidence is retained','No writes outside exact allowed files; existing evidence preserved','BDD .feature, step stubs, fixtures and pending automation/open questions exist','Independent document review remains separate; no product approval'],
       'valid_red':'N/A: document preparation; no product test, build/native/package verification NOT RUN',
       'constraints':['formats/SDK/thresholds are candidates, never self-adopted','golden14 missing means no admitted verifiable evidence; not repository-wide nonexistence','coordination brief cannot authorize implementation']}
    packets.append(p)
write('task-packets.json',packets)
write('coordination-brief.json',{'role':'coordination only','finding_closure':{'F01':'IO native environment/fixture provider restored; no additional design gate','F02':'M03 and M02 split into one-primary-module original planning scope packets'},'not_authorized':['product implementation','new adoption','native acceptance','board changes'],'remaining':'Packets may prepare evidence in original planning scope; no product/valid RED/native claim.'})
write('diff.json',{'changed':[{'id':cards['cards'][0]['id'],'field':'provider','before':read(BASE/'31-card-actions.json')['cards'][0]['provider'],'after':cards['cards'][0]['provider']}],'preserved':'31 original card actions, blockers, refs, state and product_ready retained. Only IO provider and heartbeat metadata corrected. F02 original mixed packet replaced by coordination brief + two task packets.'})
write('closure.json',{'F01':'CORRECTED_PENDING_INDEPENDENT_REVIEW','F02':'CORRECTED_PENDING_INDEPENDENT_REVIEW','author':'/root/remaining_action_correction_packet','verification':'Author static checks only; no independent review','product':'NOT RUN','valid_red':'N/A','board':'UNCHANGED'})
sources=[ROOT/'AGENTS.md',ROOT/'docs/board.json',BASE/'31-card-actions.json',BASE/'next-task-packet.json',BASE/'media-minimum-matrix.json',BASE/'preview-source-evidence.json',BASE/'template14-source-inventory.json']
sources+=list((OUT.parent/'remaining-action-dispatch-review-20261103').glob('*.json'))
sources += [ROOT/(taskroot+'PD-P1-'+m+'-PREP-01.json') for m in ['M02','M03']]
sources += [ROOT/(taskroot+'IO-PREREQ/implementation/'+n) for n in ['verification.json','architecture-review.json']]
authority=OUT.parent/'s2-green/source-current.json'; sources.append(authority)
write('source-hashes.json',{'live_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'historical_head':read(authority)['head'],'authority':str(authority.relative_to(ROOT)).replace('\\','/'),'product_hash_count':len(read(authority)['source_hashes']),'sources':{str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for p in sources}})
(OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Remaining action correction</title><h1>F01/F02 bounded correction</h1><p>Author document preparation only. Independent review pending. Product/native/build/valid RED NOT RUN (RED N/A).</p><p>IO: Windows11 machine + reparse/8.3 fixture provider; no new Owner adoption required.</p><p>M03 preview/media and M02 golden14/standalone-lock preparation are separate primary-module task packets. Candidates do not adopt formats/SDK/thresholds; missing golden proof does not mean repository-wide absence.</p>'+''.join('<p><a href="'+n+'">'+n+'</a></p>' for n in ['31-card-actions.json','task-packets.json','coordination-brief.json','closure.json','diff.json','source-hashes.json','check.py','author-checks.json','seal.json']),encoding='utf-8')
