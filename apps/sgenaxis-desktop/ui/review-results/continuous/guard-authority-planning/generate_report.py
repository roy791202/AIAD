"""Render the unapproved authority refinement from canonical JSON only."""
import html
import json
from pathlib import Path
b = Path(__file__).resolve().parent
s = json.loads((b/'module.json').read_text(encoding='utf-8'))
def esc(x): return html.escape(str(x))
def render(x):
    if isinstance(x,dict): return '<dl>'+''.join('<dt>'+esc(k)+'</dt><dd>'+render(v)+'</dd>' for k,v in x.items())+'</dl>'
    if isinstance(x,list): return '<ul>'+''.join('<li>'+render(v)+'</li>' for v in x)+'</ul>'
    return '<pre>'+esc(x)+'</pre>'
page='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Guard authority planning: caller matrix and bindings</title>
<style>body{font:16px/1.65 system-ui;max-width:1150px;margin:30px auto;padding:0 24px;background:#111827;color:#e5e7eb}h1,h2,dt{color:#93c5fd}dt{font-weight:bold;margin-top:16px}section{border:1px solid #374151;padding:18px;margin:16px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 ui-monospace}td,th{padding:9px;border:1px solid #374151;text-align:left;vertical-align:top}table{border-collapse:collapse}.status{padding:16px;background:#78350f}a{color:#93c5fd}</style>
<h1>Guard 核准權限：最小權限矩陣與精確綁定</h1>
<p class="status">PLANNING · ARCHITECTURE_GAP · NOT_READY_FOR_IMPLEMENTATION。以下均為待核准方案；native confirmation／caller 分離尚無實作證據。未建立 Skeleton、RED 或正式程式。</p>
<p>本次只補既有提案缺少的權限矩陣、來源比較與失效契約，<a href="../execution-guard/module.html">既有提案</a>保持不變。</p>'''
for key,value in s.items():
    if key=='minimum_command_tool_matrix_PROPOSED':
        cols=['operation','main','editor_viewer','Agent','rule']
        body='<table><tr>'+''.join('<th>'+esc(c)+'</th>' for c in cols)+'</tr>'+''.join('<tr>'+''.join('<td>'+esc(row[c])+'</td>' for c in cols)+'</tr>' for row in value)+'</table>'
    else: body=render(value)
    page+='<section><h2>'+esc(key)+'</h2>'+body+'</section>'
page+='<script type="application/json" id="module-spec">'+json.dumps(s,ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
(b/'module.html').write_text(page,encoding='utf-8')
print('Rendered unapproved Guard authority planning report.')
