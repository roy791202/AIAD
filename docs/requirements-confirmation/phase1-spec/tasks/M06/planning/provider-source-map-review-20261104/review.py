import json,hashlib,subprocess,copy,html,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[7]
OUT=Path(__file__).resolve().parent
C=OUT.parent/'provider-source-map-20261104'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snap():return {p.name:sha(p) for p in C.iterdir() if p.is_file()}
before=snap();checks=[]
def ck(n,b):checks.append({'id':n,'pass':bool(b)})
spec=read(C/'module-spec.json');spans=read(C/'source-spans.json');seal=read(C/'seal.json');hashes=read(C/'source-hashes.json')
for n,h in seal['files'].items():ck('seal:'+n,sha(C/n)==h)
for n,h in hashes.items():ck('source:'+n,sha(ROOT/n)==h)
for i,x in enumerate(spans):
 lines=(ROOT/x['path']).read_text(encoding='utf-8').splitlines();ck('span:'+str(i), '\n'.join(lines[x['start']-1:x['end']])==x['text'] and sha(ROOT/x['path'])==x['sha256'])
ck('nine_spans',len(spans)==9)
auth=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')['source_hashes'];drift=[n for n,h in auth.items() if not (ROOT/n).exists() or sha(ROOT/n)!=h];ck('796_authority',len(auth)==796 and not drift)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();ck('live_HEAD',head==spec['live_head']);ck('different_historical_HEAD',head!=spec['historical_product_head'])
proposal=ROOT/spec['proposal_binding']['path'];ck('proposal_binding',sha(proposal)==spec['proposal_binding']['sha256'] and read(proposal)['owner_choices']==spec['owner_choices'])
cmd=spec['search']['argv'];res=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);ck('limited_search_reproduced',res.returncode==spec['search']['exit'] and res.stdout==spec['search']['stdout']);ck('scope_qualified','no global/runtime absence' in spec['search']['scope'])
source=(ROOT/spans[0]['path']).read_text(encoding='utf-8');ck('plain_plan_not_authority','Plain plan data is not authority' in source);ck('prepare_asset_union','required.contains(version)' in spans[4]['text']);ck('local_guard_coverage','plan.required_asset_versions.contains(version)' in spans[5]['text']);ck('commit_local_mutation','self.state.content = plan.after' in spans[6]['text'] and 'root' not in spans[6]['text']);ck('undo_new_revision','self.next_revision()?' in spans[7]['text'] and 'self.state.redo.push(entry)' in spans[7]['text']);ck('constructor_structural','not parsing or validation' in spans[0]['text']);ck('digest_not_ESS','Codec owns normalization/hashing' in spans[8]['text'])
feature=ROOT/'docs/requirements-confirmation/phase1-spec/phase1.feature';ft=feature.read_text(encoding='utf-8');ck('BDD19_original_full_restoration','當 合併在任一提交階段失敗' in ft and '回到合併前完整狀態、來源不變且不增加Undo' in ft)
def semantic(d):
 return (len(d['bridges'])==4 and all(x['selected'] is None for x in d['bridges']) and len(d['owner_choices'])==6 and all(x['status']=='PROPOSED_PENDING_OWNER' for x in d['owner_choices']) and 'remains authoritative' in d['bdd19_boundary'] and 'not approval to narrow' in d['bdd19_boundary'] and 'explicit BEHAVIOR_CHANGE' in d['bdd19_boundary'] and 'no native' in d['limits'][0] and all('not ' in x['fact'] or 'do not ' in x['fact'] for x in d['bridges']) and 'no global/runtime absence' in d['search']['scope'])
ck('semantic_boundaries',semantic(spec));ck('five_earlier_yellow',len(spec['earlier_yellow_attempts'])==5 and all(x['remaining_missing'] for x in spec['earlier_yellow_attempts']))
probes=[]
for name,mut in [
 ('adopted_bridge',lambda d:d['bridges'][0].update(selected='APPROVED')),
 ('adopted_MH',lambda d:d['owner_choices'][4].update(status='ADOPTED')),
 ('BDD19_narrowed',lambda d:d.update(bdd19_boundary='Old wording stale; deferred retention approved')),
 ('native_claim',lambda d:d['limits'].__setitem__(0,'Native rollback proven')),
 ('authenticated_plan',lambda d:d['bridges'][0].update(fact='Plain MutationPlan proves authenticated issuer')),
 ('undo_distributed_rollback',lambda d:d['bridges'][2].update(fact='Local undo proves full distributed rollback')),
 ('ESS_complete_claim',lambda d:d['bridges'][3].update(fact='Digest guard proves all ESS reference rewrites')),
 ('global_absence_claim',lambda d:d['search'].update(scope='Whole product has no merge behavior'))]:
 d=copy.deepcopy(spec);mut(d);ok=not semantic(d);probes.append({'id':name,'rejected':ok});ck('negative:'+name,ok)
ck('candidate_unchanged',snap()==before)
result={'reviewer':'/root/m06_provider_review','author':spec['author'],'status':'BOUNDED_DOCUMENT_REVIEW_PASS' if all(x['pass'] for x in checks) else 'CHANGES_REQUESTED','checks':checks,'passed':sum(x['pass'] for x in checks),'failed':sum(not x['pass'] for x in checks),'new_negative_probes':probes,'candidate_before':before,'candidate_after':snap(),'BDD19_source':{'path':str(feature.relative_to(ROOT)).replace('\\','/'),'sha256':sha(feature),'lines':'134-139'},'authority_count':len(auth),'drift':drift,'HEAD':head,'findings':[],'limits':['Static source/document review only','Product/native/build/regression NOT RUN','Historical PASS not rerun','No decisions adopted']}
(OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
body='<h1>M06 provider 來源獨立審查</h1><p>'+result['status']+'</p><p>'+str(result['passed'])+' checks / '+str(len(probes))+' new negative probes. No findings.</p><p>9 段來源逐行比對；plain plan、asset union、本地 commit/Undo 與 digest guard 不構成 authenticated issuer、跨模組 rollback 或 ESS 完整引用重寫證據。</p><p>BDD-19 任一提交階段失敗須完整恢復，仍為權威。MH1–6 待採納；deferred retention 只能透過明確 BEHAVIOR_CHANGE/replan，不因提案稱舊文字 stale 就自動縮小。</p><p>五張較早黃卡的嘗試與缺條件保留；產品/native/build/regression NOT RUN，歷史 PASS 未重跑。</p><pre>'+html.escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre>'
(OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M06 independent provider review</title><style>body{max-width:1100px;margin:40px auto;font:16px system-ui;line-height:1.6}pre{white-space:pre-wrap}</style>'+body,encoding='utf-8')
(OUT/'seal.json').write_text(json.dumps({'reviewer':result['reviewer'],'status':result['status'],'files':{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='seal.json'}},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':result['status'],'checks':len(checks),'failed':result['failed'],'probes':len(probes)},ensure_ascii=False))
