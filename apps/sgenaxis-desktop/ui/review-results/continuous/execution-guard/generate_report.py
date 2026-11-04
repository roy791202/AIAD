import json,html,pathlib
p=pathlib.Path(__file__).parent
m=json.loads((p/'module-spec.json').read_text(encoding='utf-8'))
def esc(v): return html.escape(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,indent=2))
parts=['<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Execution Guard Planning</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px;background:#101823;color:#dde7ef}section{padding:18px;margin:16px 0;background:#1b2939}pre{white-space:pre-wrap;overflow-wrap:anywhere}h1,h2{color:#93c5fd}</style><h1>Execution Guard — 最小設計規劃</h1><p>[Phase: Pre-TDD] [Status: WARNING]</p><p>ARCHITECTURE_GAP · 決策未核准 · 正式碼未改 · 測試 NOT RUN</p>']
for key,value in m.items():
 parts.append('<section><h2>'+esc(key)+'</h2><pre>'+esc(value)+'</pre></section>')
parts.append('<script type="application/json" id="module-spec">'+json.dumps(m,ensure_ascii=False).replace('</','<\\/')+'</script></html>')
(p/'module.html').write_text(''.join(parts),encoding='utf-8')
