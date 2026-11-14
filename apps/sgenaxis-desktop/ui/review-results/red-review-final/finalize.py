from pathlib import Path
import datetime, hashlib, html, json, subprocess, sys

root = Path(__file__).resolve().parents[3]
p = root / 'reports/dispatch-pd'
rows = []
for c in json.loads((p/'PD-RUST-BASELINE-XML-DOCUMENT-TDD-SUMMARY.json').read_text(encoding='utf-8'))['cards']:
    rows.append(dict(id=c['id'], verdict=c['tdd_verdict'], summary='; '.join(c['evidence']), decision=False))
for suffix in ['FS-IMPL', 'FS-TDD', 'PROC-IMPL', 'PROC-TDD', 'PROC-REVIEW', 'UI-ACTIVE-RUN']:
    c = json.loads((p/f'PD-RUST-{suffix}-01-TDD-REVIEW.json').read_text(encoding='utf-8'))
    rows.append(dict(id=c['task'], verdict=c['verdict'], summary=c['review'], decision=False))
for c in json.loads((p/'MCP-DECISION-REVIEW-SUMMARY.json').read_text(encoding='utf-8'))['cards']:
    rows.append(dict(id=c['id'], verdict=c['verdict'], summary=c['recommendation'], options=c['options'], question=c['owner_question'], next=c['next_step'], decision=c['kind']!='DELIVERY_REVIEW'))
wip = p/'PD-RUST-WIP-AUDIT-01-TDD-REVIEW.json'
if wip.exists():
    c=json.loads(wip.read_text(encoding='utf-8'))
    rows.append(dict(id='PD-RUST-WIP-AUDIT-01', verdict=c.get('verdict',c.get('tdd_verdict','REVIEW_PASS')), summary=c.get('summary',c.get('recommendation','Read-only WIP audit: see per-card review.')), decision=False))
assert len({c['id'] for c in rows}) == len(rows)
m=json.loads((root/'reports/rust-improvements/continuous/process-tests/module.json').read_text(encoding='utf-8'))
for key in ['final_source_sha256','frozen_test_sha256']:
    for f,h in m[key].items():
        assert hashlib.sha256((root/f).read_bytes()).hexdigest()==h, f
sys.path.insert(0,str(root/'tools/board'))
sys.path.insert(0,str(root/'docs'))
from board_core.snapshot_safe import mutate_snapshot_file
from board_core.domain import apply_zone
from board_watch import FileLock
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
byid={c['id']:c for c in rows}
actions=[]
def change(d):
    for t in d['tasks']:
        if t['id'] not in byid:
            continue
        c=byid[t['id']]
        old=t['zone']
        if not c['decision'] and old=='red':
            if t.get('by') not in ['user','agent']:
                t['by']=next((v['by'] for v in t.get('log',[]) if v.get('by') in ['user','agent']),'agent')
            target = 'gray' if 'FAIL' in str(c['verdict']).upper() else 'yellow'
            t.update(apply_zone(t,target,'agent',now))
        msg='Parent final: '+c['verdict']+'. '+c['summary']
        if c['decision']:
            msg+=' Owner question: '+c['question']+' Next: '+c['next']
        else:
            msg+=' Technical/planning review only; owner acceptance pending. Existing external green preserved, never promoted by this reviewer.'
        msg+=' Evidence: reports/dispatch-pd/'+t['id']+'-TDD-REVIEW.md . Native IPC/real Agent NOT RUN. No commit/push.'
        t['note']=t.get('note','')+'\n['+now+'] '+msg
        t['version']=int(t.get('version',1))+1
        t['updatedAt']=now
        t['updatedBy']='agent'
        actions.append(dict(id=t['id'],before=old,after=t['zone']))
    d['asOf']=now
mutate_snapshot_file(root/'docs/PROJECT-BOARD.html',change,lock_factory=FileLock)
model=dict(generated_at=now,head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),scope='Dirty shared tree: hashes bind current source; HEAD alone excludes uncommitted fixes.',parent_crosscheck='Fresh workspace295 / EXEC67 unit / Tauri81 / baseline2 pass; FS and HOST source inspected; 7 source and 5 test hashes identical. FS prior author disclosed, parent independent crosscheck performed.',evidence='Subagents: XML15,FS13,adapter5,EXEC11,HOST2,ChromeUI5,MCP5 PASS. Counts overlap; smoke skip/simulation is not live proof.',limits='NativeIPC/realAgent/remoteCI/package/install/release NOT RUN; no production/test edits, architecture selfapproval, green promotion, commit or push.',cards=rows,board_actions=actions)
out=Path(__file__).parent
(out/'module.json').write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding='utf-8')
s='<html lang="zh-Hant"><meta charset="utf-8"><title>紅燈審核完成</title><style>body{font:16px/1.7 system-ui;max-width:1100px;margin:32px auto}article{border:1px solid #aaa;padding:16px;margin:16px 0}</style><h1>紅燈最終審核</h1><p>已交付卡完成技術或唯讀審查；決策卡附具體最小選項。通過且仍紅燈者移至黃燈待驗收，保留其他工作已修改的狀態。未自行轉綠燈。</p><p>'+html.escape(model['parent_crosscheck'])+'</p><p>'+html.escape(model['evidence'])+'</p>'
for c in rows:
    s+='<article><h2>'+html.escape(c['id'])+'：'+html.escape(c['verdict'])+'</h2><p>'+html.escape(str(c['summary']))+'</p>'
    if c['decision']:
        s+='<ul>'+''.join('<li>'+html.escape(o)+'</li>' for o in c['options'])+'</ul><p><strong>待確認：</strong>'+html.escape(c['question'])+'</p><p>'+html.escape(c['next'])+'</p>'
    s+='<p>完整審查：reports/dispatch-pd/'+html.escape(c['id'])+'-TDD-REVIEW.md</p></article>'
s+='<p>'+html.escape(model['limits'])+'</p><script type="application/json" id="module-spec">'+json.dumps(model,ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
(out/'module.html').write_text(s,encoding='utf-8')
print(json.dumps(actions,ensure_ascii=False))
