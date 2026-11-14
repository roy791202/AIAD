import pathlib,json,html
p=pathlib.Path(__file__).parent
m=json.loads((p/'module.json').read_text())
s='<html><meta charset="utf-8"><title>FS Independent Test Gate</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto}pre{white-space:pre-wrap}</style><h1>Filesystem persistence: independent TDD gate</h1>'
for k,v in m.items(): s+='<h2>'+html.escape(k)+'</h2><pre>'+html.escape(v if isinstance(v,str) else json.dumps(v,indent=2))+'</pre>'
s+='<script type="application/json" id="module-spec">'+json.dumps(m).replace('</','<\\/')+'</script></html>'
(p/'module.html').write_text(s,encoding='utf-8')
