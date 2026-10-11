"""Static document validation only. Does not execute product tests or browser UI."""
from pathlib import Path
from html.parser import HTMLParser
import json, subprocess
from urllib.parse import unquote

root=Path(__file__).resolve().parent/'product-plan'
class Document(HTMLParser):
    def __init__(self,text):
        super().__init__();self.ids=[];self.links=[];self.script=False;self.scripts=[];self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='a' and 'href' in a:self.links.append(a['href'])
        if tag=='script':self.script=a.get('type')!='application/json'
        assert not (tag=='script' and 'src' in a),'Document must not require remote scripts'
    def handle_endtag(self,tag):
        if tag=='script':self.script=False
    def handle_data(self,data):
        if self.script and data.strip():self.scripts.append(data)

docs={p:Document(p.read_text(encoding='utf-8')) for p in root.rglob('*.html')}
for p,d in docs.items():
    assert len(d.ids)==len(set(d.ids)),f'duplicate IDs: {p}'
    for link in d.links:
        if link.startswith(('https:','http:','mailto:')):continue
        file,_,fragment=link.partition('#')
        target=(p.parent/unquote(file)).resolve() if file else p.resolve()
        assert target.exists(),f'broken link {p}: {link}'
        if fragment and target.suffix=='.html':
            other=docs.get(target) or Document(target.read_text(encoding='utf-8'))
            assert fragment in other.ids,f'broken anchor {p}: {link}'
    for script in d.scripts:
        result=subprocess.run(['node','--check','-'],input=script,text=True,capture_output=True)
        assert result.returncode==0,result.stderr

plan=json.loads((root/'plan.snapshot.json').read_text(encoding='utf-8'))
all_bdd=[];all_tdd=[]
for task in plan['tasks']:
    p=root/'tasks'/task['id']
    for file in ['task.json','behavior.feature','steps.ts','fixtures.json','tests.plan.json','pending-automation.md']:
        assert (p/file).is_file()
    for b in task['bdd']:
        assert b['invariant']==task['invariant']
        assert b['id'] in (p/'behavior.feature').read_text(encoding='utf-8')
        all_bdd.append(b['id']);all_tdd.append(b['test'])
    cases=json.loads((p/'tests.plan.json').read_text(encoding='utf-8'))
    assert {c['id'] for c in cases}=={b['test'] for b in task['bdd']}
    assert all(c['assertions'] and c['red_expected'] and c['precondition'] for c in cases)
assert len(set(all_bdd))==len(all_bdd)
assert len(set(all_tdd))==len(all_tdd)
v=json.loads((root/'verification.json').read_text(encoding='utf-8'))
v['checks'].update({'local_links_and_anchors':'PASS','unique_html_ids':'PASS','javascript_syntax':'PASS','all_task_export_files':'PASS','unique_bdd_tdd_ids':'PASS'})
v['browser_visual_check']='NOT RUN — browser tool policy blocks local file URL; no workaround attempted'
(root/'verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(v,ensure_ascii=False))
