"""Independent document review; never imports or runs the author's checker."""
from pathlib import Path
import json, hashlib, re, copy, subprocess, datetime, html
ROOT=Path('D:/AIAD'); OUT=Path(__file__).parent; BASE=OUT.parent/'feature-trace-preparation'
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def emit(n,v): (OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
t=read(BASE/'feature-trace.json'); recipes=read(BASE/'pending-fixture-oracle-recipes.json'); original=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F12-DELIVERY-01.json')
feature=(ROOT/'docs/requirements-confirmation/phase1-spec/phase1.feature').read_text(encoding='utf-8-sig')
fixture=read(ROOT/'docs/requirements-confirmation/phase1-spec/fixtures.json')
board=read(ROOT/'docs/board.json'); card=next(x for x in board['items'] if x['id']==t['task']); old=read(BASE/'board-readonly.json')['card']
source=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
sealed=read(BASE/'seal.json')['files']; seal_checks={p:sha(BASE/p)==h for p,h in sealed.items()}
hash_checks={p:sha(ROOT/p)==h for p,h in source['source_hashes'].items()}
input_checks={p:sha(ROOT/p)==h for p,h in read(BASE/'input-hashes.json').items()}
def diff(a,b,p=''):
    if isinstance(a,dict) and isinstance(b,dict):
        return sum([diff(a.get(k),b.get(k),p+'/'+k) for k in sorted(set(a)|set(b))],[])
    return [] if a==b else [{'path':p,'before':a,'after':b}]
board_diff=diff(old,card)
def original_block(n):
    match=re.search(r'(?m)^  @BDD-'+str(n)+r'\b[\s\S]*?(?=^  @BDD-|\Z)',feature)
    return match.group().rstrip()
def violations(x,r):
    errors=[]
    by={z['bdd']:z for z in x['trace']}
    if set(by)!={f'BDD-{n}' for n in range(22,31)}: errors.append('original scenario set incomplete')
    for n in range(22,31):
        z=by.get(f'BDD-{n}',{})
        if z.get('verbatim')!=original_block(n): errors.append(f'BDD-{n} changed')
        expected='F12_DIRECT' if n in (27,28,29) else 'SHARED_CONTEXTUAL_REGRESSION'
        if z.get('relation')!=expected: errors.append(f'BDD-{n} relation changed')
        if z.get('feature_evidence')!='NOT RUN': errors.append(f'BDD-{n} evidence promoted')
    if x['contracts_verbatim']!=original['contract']: errors.append('contract weakened')
    if x['acceptance_verbatim']!=original['acceptance']: errors.append('acceptance weakened')
    if x['module_complete'] or x['implementation']!=original['status']: errors.append('implementation authority promoted')
    if 'pending Owner' not in ' '.join(x['owner_pending']) or 'no retention policy selected' not in ' '.join(x['owner_pending']): errors.append('D01 adopted')
    if len(r['cases'])!=11: errors.append('prospective recipe missing')
    for z in r['cases']:
        if z['result']!='NOT RUN' or z['product_command'] is not None: errors.append('recipe execution/authority promoted')
        if 'prospective' not in z['classification']: errors.append('prospective classification missing')
    if 'PROSPECTIVE_PENDING_OWNER' not in x['ui_schema_preparation']['status']: errors.append('UI schema adoption promoted')
    return errors
baseline=violations(t,recipes)
probes=[]
def probe(name,mutate,expected):
    a,b=copy.deepcopy(t),copy.deepcopy(recipes); mutate(a,b); errors=violations(a,b)
    probes.append({'id':name,'expected_rejection':expected,'observed':errors,'pass':any(expected in e for e in errors),'scope':'document semantic negative perturbation only; no product execution'})
probe('DROP-CONTEXTUAL-24',lambda a,b:a['trace'].pop(2),'incomplete')
probe('PROMOTE-CONTEXTUAL-30',lambda a,b:a['trace'][-1].update(relation='F12_DIRECT'),'relation changed')
probe('DEMOTE-DIRECT-28',lambda a,b:a['trace'][6].update(relation='SHARED_CONTEXTUAL_REGRESSION'),'relation changed')
probe('ALTER-ORIGINAL-27',lambda a,b:a['trace'][5].update(verbatim=a['trace'][5]['verbatim'].replace('不立即刪除','立即刪除')),'changed')
probe('S1-AS-NATIVE',lambda a,b:a['trace'][6].update(feature_evidence='PASS from S1'),'evidence promoted')
probe('DOCUMENT-AS-RED',lambda a,b:a.update(implementation='READY_FOR_AI_IMPLEMENTATION'),'authority promoted')
probe('MODULE-COMPLETE',lambda a,b:a.update(module_complete=True),'authority promoted')
probe('D01-ADOPTED',lambda a,b:a.update(owner_pending=['D01 permanently retain approved']),'D01 adopted')
probe('RECIPE-APPROVED-BDD',lambda a,b:b['cases'][1].update(classification='approved BDD-28'),'classification missing')
probe('RECIPE-GREEN',lambda a,b:b['cases'][10].update(result='GREEN'),'execution/authority promoted')
probe('GUESSED-RUNNER',lambda a,b:b['cases'][0].update(product_command='cargo test guessed_target'),'execution/authority promoted')
probe('DROP-PORTABLE',lambda a,b:b['cases'].pop(5),'recipe missing')
probe('DROP-FAILED-SAVE-CONTRACT',lambda a,b:a['contracts_verbatim'].pop(),'contract weakened')
probe('DROP-AC12',lambda a,b:a['acceptance_verbatim'].pop(0),'acceptance weakened')
probe('UI-APPROVED',lambda a,b:a['ui_schema_preparation'].update(status='APPROVED'),'adoption promoted')
fixtures_ok=[]
for z in t['trace']:
    i=int(z['original_fixture'].split('/')[-1]); value=fixture['scenarios'][i]
    fixtures_ok.append({'bdd':z['bdd'],'pointer':z['original_fixture'],'value':value,'matches_id':z['bdd'] in json.dumps(value,ensure_ascii=False)})
requirements=[('F12-P01','original task /bdd/flow; REQ-22','history identity and preview before mutation'),('F12-P02','original task /bdd/flow and contract[2]','preview time/location/material completeness'),('F12-P03','BDD-28; original task /bdd/flow','open unsaved; cancel/failure preservation remains prospective detail'),('F12-P04','original task /bdd/flow; BDD-27/28','explicit save original versus Save As'),('F12-P05','AC12 and BDD-28','offline and read-only originals'),('F12-P06','AC12; BDD-32 M08 dependency','portable move remains cross-module verification'),('F12-P07','BDD-29; contract[0]','history removal never physical deletion'),('F12-P08','BDD-27; contract[0]','formal save preserves snapshot and independent baseline'),('F12-P09','contract[1]','fresh-launch Undo empty'),('F12-P10','contract[2]','stale path retained; missing material honestly limited'),('F12-P11','contract[2]; X07','failed save preserves edited state and snapshot')]
emit('coverage.json',{'traceability':[{'case':a,'source':b,'meaning':c,'authority':'prospective recipe, not newly approved BDD','result':'NOT RUN'} for a,b,c in requirements],'original_fixture_resolution':fixtures_ok,'baseline_errors':baseline})
emit('probes.json',{'baseline_valid':not baseline,'negative_probes':probes,'negative_passed':sum(p['pass'] for p in probes),'limitation':'Reviewer invariant validator tests documentary classification and exact original preservation; it neither proves actual behavior nor validates arbitrary natural-language semantics.'})
emit('source-and-board.json',{'live_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'historical_inventory_head':source['head'],'source_count':len(hash_checks),'source_mismatches':[p for p,v in hash_checks.items() if not v],'candidate_seal_checks':seal_checks,'input_hash_drift':[p for p,v in input_checks.items() if not v],'board_current_sha256':sha(ROOT/'docs/board.json'),'board_card_diff':board_diff,'legacyTask_equal':old['legacyTask']==card['legacyTask'],'board_policy':'Management drift evaluated separately from 796 source authority; only notes and updatedAt permitted for this bounded review.','head_difference':subprocess.check_output(['git','diff','--name-only',source['head'],'HEAD'],cwd=ROOT,text=True).splitlines()})
findings=[]
if baseline or not all(hash_checks.values()) or not all(seal_checks.values()) or old['legacyTask']!=card['legacyTask']: findings.append({'id':'FTR-1','severity':'P2','detail':'Integrity or authority invariant failed; inspect structured evidence.'})
unexpected=[z for z in board_diff if z['path'] not in ('/notes','/updatedAt')]
if unexpected: findings.append({'id':'FTR-2','severity':'P2','detail':'Unexpected management card difference','diff':unexpected})
emit('findings.json',{'findings':findings,'observations':[{'id':'FTR-O1','classification':'provenance distinction; not defect','detail':'Candidate records its creation-turn Owner heartbeat 2026-11-03T10:57:03.220Z. Review instruction is current user heartbeat 2026-11-03T11:07:03.888Z relayed by parent, with no verified filesystem path. No requirement to retroactively rewrite the historical candidate. Old on-disk October heartbeat is historical only.'},{'id':'FTR-O2','classification':'evidence limit retained','detail':'S1 is pure policy and its historical same-assistant acceptance is not current delegated-independent acceptance. ACK correction guard PASS does not prove response relation/replay/restart/atomic baseline or malformed trusted issuer behavior. PH-G2..4 and D01 remain pending.'}]})
ok=not findings and not baseline and all(p['pass'] for p in probes) and all(x['matches_id'] for x in fixtures_ok)
result={'verdict':'PASS_BOUNDED_DOCUMENT_PREPARATION_PENDING_OWNER' if ok else 'FINDINGS','reviewer':'/root/f12_feature_trace_review','author':t['author'],'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'task':t['task'],'findings':len(findings),'fresh_negative_probes':len(probes),'passed_negative_probes':sum(p['pass'] for p in probes),'product_acceptance':False,'module_complete':False,'owner_instruction':{'at':'2026-11-03T11:07:03.888Z','source':'current user instruction relayed by parent; no verified filesystem path'},'not_run':['native Windows history/preview/open/save','build/package/install','product tests','valid RED/GREEN','runtime recovery/material/index/provider','module acceptance'],'next':'Owner adopts exact envelope/UI/Skeleton and pending semantics before valid behavioral RED; preserve current board state; no dispatch/commit/push.'}
emit('result.json',result)
page='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>F12 獨立文件審查</title><style>body{font:16px/1.65 system-ui;background:#f5f7fa;color:#22334a;max-width:1100px;margin:32px auto}section{background:white;padding:24px;margin:16px 0;border:1px solid #cbd5e1}table{border-collapse:collapse;width:100%}td,th{border:1px solid #cbd5e1;padding:8px;text-align:left}pre{white-space:pre-wrap}</style><h1>F12 歷史入口、復原與保留：獨立文件審查</h1>'''
page+=f'<section><h2>{result["verdict"]}</h2><p>作者 {html.escape(t["author"])}；審查者 /root/f12_feature_trace_review。只審查文件準備，不授權實作、不宣稱產品驗收。新語意負向擾動 {len(probes)} 項；原始 BDD-22～30 逐字比較；來源 {len(hash_checks)} 檔重新計算 hash。</p></section>'
page+='<section><h2>範圍與追溯</h2><p>BDD-27/28/29 為直接 F12；22～26/30 保留為模組共用 regression，沒有省略完整義務。11 recipes 是待 Owner 採納的 prospective 準備，不冒認 approved BDD。UI schema、預覽、未保存開啟、保存與另存、離線/唯讀、搬移、保留、Undo及失敗保護均對應原卡。</p><table><tr><th>Recipe</th><th>來源</th><th>義務</th></tr>'
page+=''.join('<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in row)+'</tr>' for row in requirements)+'</table></section>'
page+='<section><h2>證據邊界與風險</h2><p>D01 未處理快照永久保留仍為 Owner pending，沒有選定 retention；歷史移除不刪快照和正式保存不立即清除不是永久保留政策的批准。M07-D1..7、CXv3、ACK ordinal 與 PH-G2..4 仍待決。S1 policy 與 ACK 文件 guard 不證明 native recovery。產品 RED/GREEN、runtime、native UI、build/package/install 與 module acceptance 全部 NOT RUN。</p><p>候選生成時指示 10:57；本審查最新 Owner 指示 11:07:03.888Z，沒有已核對檔案路徑。不得把舊檔案 heartbeat 當最新，也不要求歷史候選回填未來時間。</p></section>'
page+='<section><h2>可重現文件驗證</h2><p>執行：python docs/requirements-confirmation/phase1-spec/tasks/M07/F12/feature-trace-review/review.py。未執行作者 checker，未重跑歷史產品 PASS。</p><ul>'+''.join(f'<li><a href="{n}">{n}</a></li>' for n in ['findings.json','coverage.json','probes.json','source-and-board.json','result.json','seal.json'])+'</ul></section></html>'
(OUT/'index.html').write_text(page,encoding='utf-8')
emit('seal.json',{'kind':'review artifact SHA256; not product/Owner approval','files':{p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='seal.json'}})
print(json.dumps(result,ensure_ascii=False))
