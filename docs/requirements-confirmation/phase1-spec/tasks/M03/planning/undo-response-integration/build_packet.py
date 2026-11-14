"""Render the frozen candidate ModuleSpec; no source/schema/fixture rewriting."""
import pathlib,json,html
P=pathlib.Path(__file__).parent
spec=json.loads((P/'module-spec.json').read_text(encoding='utf8'))
body='<h1>M03 · Undo response integration</h1><p>PROPOSED_PENDING_REACCEPTANCE_AND_OWNER · FullDraft MISSING · Product tests NOT RUN</p>'
for k,v in spec.items():body+='<section><h2>'+html.escape(k)+'</h2><pre>'+html.escape(json.dumps(v,ensure_ascii=False,indent=2))+'</pre></section>'
(P/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>M03 Undo</title><style>body{max-width:1100px;margin:40px auto;font:16px system-ui;background:#101721;color:#dbe6f3}section{border:1px solid #415166;padding:20px;margin:16px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}h1,h2{color:#f0c465}</style>'+body+'<script id="module-spec" type="application/json">'+json.dumps(spec,ensure_ascii=False).replace('<','\\u003c')+'</script></html>',encoding='utf8')
