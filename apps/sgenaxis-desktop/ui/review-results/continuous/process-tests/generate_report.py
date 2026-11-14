import pathlib,json,html
p=pathlib.Path(__file__).parent
m=json.loads((p/'module.json').read_text(encoding='utf-8'))
s='<html lang="zh-Hant"><meta charset="utf-8"><title>Process Independent Test Gate</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>Process lifecycle — independent test gate</h1>'
for k,v in m.items():s+='<h2>'+html.escape(k)+'</h2><pre>'+html.escape(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,indent=2))+'</pre>'
s+='<script type="application/json" id="module-spec">'+json.dumps(m,ensure_ascii=False).replace('</','<\\/')+'</script></html>'
(p/'module.html').write_text(s,encoding='utf-8')
