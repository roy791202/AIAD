"""Validate design documents, not product behavior."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote
import json, struct, subprocess, base64, zipfile

root = Path(__file__).resolve().parent
out = root / 'ui-design'
spec = json.loads((out / 'ui-spec.json').read_text(encoding='utf-8'))
plan = json.loads((root / 'product-plan/plan.snapshot.json').read_text(encoding='utf-8'))
bdd = {b['id'] for t in plan['tasks'] for b in t['bdd']}
tdd = {b['test'] for t in plan['tasks'] for b in t['bdd']}
pages = spec['pages']
assert len(pages) == 14 and len(spec['dialogs']) == 8
assert len({p['id'] for p in pages}) == 14
assert len({p['route'] for p in pages}) == 14
cases = []
for p in pages:
    assert len(p['states']) == 5 and p['fields']
    assert set(p['bdd_refs']) <= bdd and set(p['tdd_refs']) <= tdd
    cases.extend(c['id'] for c in p['ui_tests'])
    data = (out / p['image']).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    assert struct.unpack('>II', data[16:24]) == (1536, 1024)
assert len(cases) == len(set(cases)) == 56
for d in spec['dialogs']:
    assert set(d['tests']) <= bdd
    assert set(d['pages']) <= {p['id'] for p in pages}

class Document(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.ids=[]; self.links=[]; self.scripts=[]; self.embedded=''; self.mode=None
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if 'id' in a: self.ids.append(a['id'])
        if tag=='a' and 'href' in a: self.links.append(a['href'])
        if tag=='img': self.links.append(a['src'])
        if tag=='script': self.mode='json' if a.get('type')=='application/json' else 'js'
    def handle_endtag(self, tag):
        if tag=='script': self.mode=None
    def handle_data(self, data):
        if self.mode=='json': self.embedded+=data
        if self.mode=='js': self.scripts.append(data)

html = (out/'index.html').read_text(encoding='utf-8')
doc=Document(html)
assert len(doc.ids)==len(set(doc.ids))
assert json.loads(doc.embedded)==spec
for link in doc.links:
    file, _, fragment=link.partition('#')
    target=(out/unquote(file)).resolve() if file else out/'index.html'
    if target==out/'verification.json': continue
    assert target.is_file(), link
    if fragment:
        assert fragment in Document(target.read_text(encoding='utf-8')).ids, link
for script in doc.scripts:
    r=subprocess.run(['node','--check','-'],input=script,text=True,capture_output=True)
    assert r.returncode==0,r.stderr
report={'document_validation':'PASS','pages':14,'images':14,'dialog_specs':8,'page_states':70,
        'planned_ui_cases':56,'links_and_traceability':'PASS','embedded_schema':'PASS',
        'javascript_syntax':'PASS','product_tests':'NOT RUN',
        'browser_verification':'NOT RUN: local file URL blocked by browser policy; no workaround attempted',
        'acceptance':'DESIGN PROPOSAL; not product implementation or release approval'}
(out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
# Portable single HTML: image pixels and engineering data travel with the document.
standalone=html
for p in pages:
    uri='data:image/png;base64,'+base64.b64encode((out/p['image']).read_bytes()).decode('ascii')
    standalone=standalone.replace('src="'+p['image']+'"','src="'+uri+'"')
    standalone=standalone.replace('href="'+p['image']+'"','href="#'+p['id']+'"')
for name in ['ui-spec.json','verification.json']:
    uri='data:application/json;base64,'+base64.b64encode((out/name).read_bytes()).decode('ascii')
    standalone=standalone.replace('href="'+name+'"','download="'+name+'" href="'+uri+'"')
# Product-plan references remain optional companion links; visuals/specs are embedded.
(out/'SGenAxis-all-pages.html').write_text(standalone,encoding='utf-8')
archive=root/'SGenAxis-ui-design-v0.1.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for folder in [out,root/'product-plan']:
        for p in folder.rglob('*'):
            if p.is_file(): z.write(p,p.relative_to(root))
    for name in ['build_ui_design.py','verify_ui_design.py']:
        z.write(root/name,name)
with zipfile.ZipFile(archive) as z: assert z.testzip() is None
print(json.dumps(report,ensure_ascii=False))
print(archive)
