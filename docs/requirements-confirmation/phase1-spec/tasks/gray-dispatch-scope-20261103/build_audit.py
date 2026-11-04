import pathlib,json,hashlib,subprocess,re,html,os
R=pathlib.Path.cwd(); O=pathlib.Path(__file__).resolve().parent
B=R/'docs/requirements-confirmation/phase1-spec/tasks'
sources={}
def read(p):
 p=pathlib.Path(p); sources[p.relative_to(R).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest(); return json.loads(p.read_text(encoding='utf-8-sig'))
board=read(R/'docs/board.json'); yellow=read(B/'yellow-dispatch-gates-20261103/audit.json')
byid={x['id']:x for x in board['items']}; mods={x['module']:x for x in yellow['actions']}
rows=[]
for card in board['items']:
 if card['light'] not in ['Gray','Red']:continue
 legacy=card['legacyTask']; pid=card['id']; pp=B/(pid+'.json'); packet=read(pp) if pp.exists() else None
 row={'id':pid,'light':card['light'],'title':legacy['title'],'legacy':legacy,'migrated_state':{k:card.get(k) for k in ['status','tdd','ci','lightReason']},'original_packet':packet,'method':'Read individual original legacyTask, original task packet when present, dependencies, current module state and latest reviewed preparation; do not infer readiness from color or migrated None.'}
 if legacy.get('executionStatus')=='SUPERSEDED_FOR_EXECUTION':
  row.update(classification='SUPERSEDED_NOT_REDISPATCH',missing_condition='Explicit replacement execution scope required; original card says do not repeat dispatch.',preparation='Preserve history and follow replacement module entry; not a new task.',product_ready=False)
 else:
  deps=packet.get('dependencies',[]) if packet else []
  row['dependencies']=[{'id':d,'light':byid.get(d,{}).get('light'),'legacy_execution':byid.get(d,{}).get('legacyTask',{}).get('executionStatus'),'latest_note':byid.get(d,{}).get('notes',[None])[-1]} for d in deps]
  module=packet['module']; cp=B/module/'planning/current-state.json'
  if cp.exists(): row['current_state']=read(cp)
  if module in mods:
   ma=mods[module]; row['latest_preparation']={k:ma.get(k) for k in ['candidate','review','missing_gate','authorized_preparation','latest_note']}
   for s in ma.get('references',[]):
    q=R/s
    if q.exists(): sources[s]=hashlib.sha256(q.read_bytes()).hexdigest()
   row.update(classification='PRODUCT_GATE_NOT_READY',missing_condition=ma['missing_gate'],product_ready=False,preparation='Original-scope read-only evidence inventory remains authorized. Existing accepted slices and reviewed candidates are preserved; no repeat probes. This audit does not establish a NEW product envelope.')
  elif module=='M08':
   row.update(classification='NATIVE_VERIFICATION_INPUTS_NOT_READY',missing_condition='Accepted module deliveries F01-F12 plus exact versioned portable artifact and independent native harness admission; M08-PD1..PD3 approval before harness Skeleton. Do not reopen accepted PREP.',product_ready=False,preparation='Only an isolated input/evidence inventory is executable in this audit; no native launch or new harness approved.')
  else:
   row.update(classification='OWNER_DECISION_NOT_IMPLEMENTATION',missing_condition='Owner must adopt exact reviewed contracts/envelope; directional adoption is not exact approval. No decision author may approve its own proposal.',product_ready=False,preparation='Read-only consolidation of original decision-scope missing deliverables is authorized; decisions/Gxx namespace is absent. Existing module proposals must be linked, not recreated.')
  if packet:
   row['exact_original_scope']=packet.get('allowed_files'); row['original_acceptance']=packet.get('acceptance'); row['original_bdd']=packet.get('bdd');row['original_tdd']=packet.get('tdd')
 rows.append(row)
# NEW bounded witness: each original decision requests concrete deliverables; distinguish
# absent canonical destinations from absent engineering work (module proposals exist).
witness=[]
for row in rows:
 p=row['original_packet']
 if not p or p.get('kind')!='decision':continue
 g=row['id'].split('-')[2]; target=B/'decisions'/g
 affected=p['affected_features']; candidates=[]
 for a in mods.values():
  if set(a.get('original_envelope',{}).get('feature_refs',[])) & set(affected):
   candidates.append({k:a.get(k) for k in ['module','candidate','review','missing_gate']})
 witness.append({'decision':row['id'],'original_deliverables':p['deliverables'],'canonical_destination':target.relative_to(R).as_posix(),'destination_exists':target.exists(),'affected_features':affected,'existing_module_candidates':candidates,'finding':'Canonical decision consolidation not present; module proposals/reviews exist. This is a location/traceability witness, not proof that design work is missing or permission to invent it.','next_action':'One bounded original-scope decision consolidation linking existing exact candidate/review and explicit unresolved adoption. No new defaults/schema or test reruns.','role':'planning document author; separate read-only reviewer required','allowed_write_files':[str((O/(g+'-decision-witness.json')).relative_to(R)).replace('\\','/')],'bdd':'Given original decision deliverables and existing module proposals, When their locations are inventoried, Then absent canonical consolidation is distinguished from absent design and all adoption gates remain pending.','tdd':'Document witness assertions only; no product RED: source hashes, every G01-G04 once, affected feature references and candidate paths exist.'})
 forlast=witness[-1]
 (O/(g+'-decision-witness.json')).write_text(json.dumps(forlast,ensure_ascii=False,indent=2),encoding='utf8')
inv=read(B/'M01/planning/s2-green/source-current.json'); mismatches=[]
for s,h in inv['source_hashes'].items():
 q=R/s
 if not q.exists() or hashlib.sha256(q.read_bytes()).hexdigest()!=h:mismatches.append(s)
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
d={'kind':'original-gray-red-scope-and-decision-deliverable-witness','author':'/root/gray_dispatch_scope_audit','head':head,'required_head':'5b709343a890503ebbe24a802e43cda5647df124','historical_inventory_head':inv['head'],'inventory_count':len(inv['source_hashes']),'inventory_mismatches':mismatches,'gray_count':sum(r['light']=='Gray' for r in rows),'red_count':sum(r['light']=='Red' for r in rows),'rows':rows,'executed_new_action':witness,'sources':sources,'not_run':['independent acceptance','product tests','native UI','build/package/install','valid product RED','architecture adoption'],'conclusion':'All 18 Gray and 5 Red original cards individually inventoried. No new product-ready slice established. Five legacy Gray and one legacy Red explicitly superseded. Four original decision deliverable location witnesses executed as bounded authorized preparation. This does not claim all possible preparation is blocked, nor replace Owner decisions.'}
(O/'audit.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
links=''.join('<li><a href="'+html.escape(os.path.relpath(R/s,O).replace('\\','/'))+'">'+html.escape(s)+'</a></li>' for s in sources)
body=''.join('<tr><td>'+html.escape(r['light']+' '+r['id'])+'</td><td>'+html.escape(r['classification'])+'</td><td>'+html.escape(r['missing_condition'])+'</td></tr>' for r in rows)
page='<!doctype html><meta charset="utf-8"><title>Gray / Red original scope audit</title><style>body{font:16px system-ui;max-width:1400px;margin:auto;padding:30px;background:#f4f6f8}td,th{border:1px solid #bbb;padding:12px;vertical-align:top}table{border-collapse:collapse}pre{white-space:pre-wrap}</style><h1>18 Gray + 5 Red original-scope audit</h1><p>'+html.escape(d['conclusion'])+'</p><p>Preparation evidence only. No independent acceptance, product RED, native, build or architecture approval.</p><table><tr><th>Original card</th><th>Action class</th><th>Exact missing condition</th></tr>'+body+'</table><h2>NEW executed original-decision witness</h2><pre>'+html.escape(json.dumps(witness,ensure_ascii=False,indent=2))+'</pre><h2>Source links</h2><ul>'+links+'</ul><script type="application/json" id="module-spec">'+json.dumps(d,ensure_ascii=False).replace('</','<\\/')+'</script>'
(O/'index.html').write_text(page,encoding='utf8')
print(json.dumps({'gray':d['gray_count'],'red':d['red_count'],'new_witnesses':len(witness),'product_hashes':len(inv['source_hashes']),'mismatches':mismatches,'sources':len(sources)}))
