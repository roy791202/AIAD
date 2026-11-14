import copy, datetime, hashlib, html, json, pathlib, re, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[7]
OUT = pathlib.Path(__file__).parent
BASE = OUT.parent
CAND = BASE / 'current-action-blockers-20261103'
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def resolve(ref):
    p = ROOT / ref['path']
    assert sha(p) == ref['sha256'], ref['path']
    v = load(p)
    for part in ref.get('pointer','').strip('/').split('/') if ref.get('pointer') else []:
        part = part.replace('~1','/').replace('~0','~')
        v = v[int(part)] if isinstance(v,list) else v[part]
    if 'value' in ref: assert v == ref['value']
    return v
d = load(CAND/'actions.json')
register = load(BASE/'exact-disposition-correction-20261103/register.json')
board_before = (ROOT/'docs/board.json').read_bytes()
board = json.loads(board_before)
byid = {x['id']:x for x in board['items']}
candidate_before = {p.name:sha(p) for p in CAND.iterdir() if p.is_file()}
checks=[]
def check(name, value, detail=None):
    checks.append({'name':name,'pass':bool(value),'detail':detail})
def oracle(v):
    assert len(v['cards']) == 31
    assert [x['light'] for x in v['cards']] == ['Yellow']*8+['Gray']*18+['Red']*5
    assert [x['id'] for x in v['cards']] == [x['id'] for x in register['cards']]
    assert v['selected'] is None
    for x,r in zip(v['cards'],register['cards']):
        assert x['missing_conditions']==r['missing_conditions'] and x['provider']==r['provider']
        assert x['selected'] is None and x['already_attempted_or_delivered']
        assert x['current_executable_without_external_input'] is False
        assert x['board_read_time_record']==byid[x['id']]
        assert x['light']==byid[x['id']]['light']
        assert resolve(x['source_register'])==r
        for item in x['current_action_items']:
            assert item['selected'] is None
            if 'source_field' in item: resolve(item['source_field']['source'])
    assert v['IO']['owner_adoption_required'] is False
    assert v['cards'][0]['owner_adoption_required'] is False
    assert '10.0.19045' in v['IO']['observed_os_json']
    assert 'No assertion that all future preparation is impossible' in v['window']
    assert v['remaining_original_scope_assessment']['executable_product_command_now'] is None
    assert len(v['golden14'])==14
    for row in v['golden14']:
        assert resolve(row['source'])==row['row']
        assert row['selected'] is None
        for ref in row['row']['source_refs']: resolve(ref)
        assert row['row']['submitted_resource']['bytes'] is None
        assert row['row']['golden']['expected_rendered_bytes'] is None
    assert v['authority']['count']==796 and v['authority']['drift']==[]
    assert v['authority']['live_HEAD'].startswith('5b709343')
    assert v['authority']['historical_HEAD'].startswith('31babe87')
try: oracle(d); check('31 per-card exact routing, board scope, missing fields and provider oracle',True)
except Exception as e: check('31 per-card exact routing, board scope, missing fields and provider oracle',False,str(e))
mutations=[('drop card',lambda v:v['cards'].pop()),('wrong order',lambda v:v['cards'].reverse()),('missing provider',lambda v:v['cards'][1].update(provider='invented')),('wrong pending value',lambda v:v['cards'][1]['current_action_items'][1]['source_field']['source'].update(value='adopted')),('IO owner adoption',lambda v:v['IO'].update(owner_adoption_required=True)),('Win11 substitution',lambda v:v['IO'].update(observed_os_json='Windows11')),('future impossibility',lambda v:v.update(window='all future preparation impossible')),('invent golden bytes',lambda v:v['golden14'][0]['row']['submitted_resource'].update(bytes='invented')),('golden path swap',lambda v:v['golden14'][0]['row'].update(declared_product_path='wrong')),('source pointer mismatch',lambda v:v['golden14'][0]['source'].update(pointer='/rows/1')),('authority count',lambda v:v['authority'].update(count=795)),('historical HEAD as current',lambda v:v['authority'].update(live_HEAD=v['authority']['historical_HEAD'])),('false executable',lambda v:v['cards'][0].update(current_executable_without_external_input=True)),('implicit decision',lambda v:v.update(selected='accept'))]
probes=[]
for name,mutate in mutations:
    v=copy.deepcopy(d); mutate(v)
    try: oracle(v); rejected=False
    except Exception: rejected=True
    probes.append({'name':name,'rejected':rejected,'layer':'fresh semantic/source negative probe; not product RED'})
check('14 fresh negative probes reject corruption',all(x['rejected'] for x in probes))
source_hashes=load(CAND/'source-hashes.json')
drift=[p for p,h in source_hashes.items() if sha(ROOT/p)!=h]
check('candidate read-time source hashes',not drift,drift)
seal=load(CAND/'seal.json')
check('candidate seal',all(sha(CAND/p)==h for p,h in seal['files'].items()))
authority=load(BASE/'s2-green/source-current.json')
product_drift=[p for p,h in authority['source_hashes'].items() if sha(ROOT/p)!=h]
check('M01 source-current 796 authority',len(authority['source_hashes'])==796 and not product_drift,product_drift)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
check('live HEAD distinct historical baseline',head==d['authority']['live_HEAD'] and authority['head']==d['authority']['historical_HEAD'],head)
page=(CAND/'index.html').read_text(encoding='utf-8')
scripts=re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',page,re.S)
check('HTML embedded exact JSON',any(json.loads(s)==d for s in scripts))
check('review references exact current result records',all(resolve(x['source'])==x['record'] for x in d['review_evidence']))
os_now=subprocess.check_output(['powershell','-NoProfile','-Command','Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,OSArchitecture | ConvertTo-Json -Compress'],text=True,encoding='utf-8',errors='replace')
check('fresh actual Windows10 version; no Win11 proof','10.0.19045' in os_now)
check('candidate immutable during review',candidate_before=={p.name:sha(p) for p in CAND.iterdir() if p.is_file()})
check('board unchanged during this review',board_before==(ROOT/'docs/board.json').read_bytes())
findings=[]
for c in checks:
    if not c['pass']: findings.append({'severity':'P2','issue':c['name'],'detail':c['detail']})
results={'reviewer':'/root/current_action_blockers_review','author':d['author'],'review_heartbeat':'2026-11-03T15:57:09.327Z','candidate_creation_heartbeat':d['heartbeat'],'reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verdict':'PASS_BOUNDED_CURRENT_ACTION_DOCUMENT_ONLY' if not findings else 'FAIL_DOCUMENT_REVIEW','checks':checks,'fresh_negative_probe_count':len(probes),'head':head,'historical_head':authority['head'],'product_authority_count':796,'board_before_sha256':hashlib.sha256(board_before).hexdigest(),'board_after_sha256':sha(ROOT/'docs/board.json'),'management_delta_limit':'Board has prior parent M01 append/item/root updatedAt; no old bytes available here, so no reconstruction or claim of exact historical unchanged board. This review changes no board bytes.','scope_conclusion':'Only known source-bound preparation at read-time is assessed. Missing external inputs block current known actions; no universal future-preparation impossibility claim. No concrete new unfilled original-scope output found.','not_run':['historical PASS reruns','product/native tests','valid RED/GREEN','build/package/install/DCC','Owner adoption','board edits','commit/push'],'candidate_hashes':candidate_before}
for name,obj in [('results.json',results),('findings.json',findings),('probes.json',probes)]: (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Current action independent review</title><h1>'+results['verdict']+'</h1><p>Independent bounded document review only. 31 cards: Yellow 8 → Gray 18 → Red 5. 14 golden paths remain provider handoffs. IO requires Windows11/native fixtures, no new Owner adoption. Creation and review heartbeat are separate.</p><pre>'+html.escape(json.dumps(results,ensure_ascii=False,indent=2))+'</pre><h2>Findings</h2><pre>'+html.escape(json.dumps(findings,ensure_ascii=False,indent=2))+'</pre></html>',encoding='utf-8')
seal_out={'sealed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':results['reviewer'],'stop_writing_after_seal':True,'files':{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='seal.json'}}
(OUT/'seal.json').write_text(json.dumps(seal_out,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'verdict':results['verdict'],'checks':checks,'findings':findings},ensure_ascii=False))

