"""Embed this revision's document evidence and seal files; no acceptance claim."""
import hashlib
import html
import json
import pathlib
import re

P = pathlib.Path(__file__).parent
report = (P/'index.html').read_text(encoding='utf8')
report = re.sub(r'<!-- correction-seal-start -->.*?<!-- correction-seal-end -->', '', report, flags=re.S)
verification = json.loads((P/'verification.json').read_text(encoding='utf8'))
inputs = {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(P.iterdir()) if f.is_file() and f.name not in {'index.html','artifact-hashes.json'}}
body = '<!-- correction-seal-start --><h2>New revision document self-check evidence</h2><p>Author self-check only. Independent acceptance NOT RUN.</p><pre>'+html.escape(json.dumps(verification,indent=2))+'</pre><h2>Embedded input SHA256 manifest</h2><p>HTML and external manifest excluded here to avoid self-reference. External manifest additionally seals final HTML.</p><pre>'+html.escape(json.dumps(inputs,indent=2))+'</pre><!-- correction-seal-end -->'
report = report.replace('</html>',body+'</html>')
(P/'index.html').write_text(report,encoding='utf8')
manifest = {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(P.iterdir()) if f.is_file() and f.name!='artifact-hashes.json'}
(P/'artifact-hashes.json').write_text(json.dumps({'algorithm':'SHA256','scope':'all package files except this self-referential manifest','files':manifest},indent=2)+'\n',encoding='utf8')
print('Sealed',len(manifest),'correction package files; no independent acceptance.')
