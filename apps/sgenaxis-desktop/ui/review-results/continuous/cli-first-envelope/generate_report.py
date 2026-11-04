"""Render the proposed CLI-first envelope; never execute commands/providers."""
import html
import json
from pathlib import Path
b=Path(__file__).resolve().parent
s=json.loads((b/'module.json').read_text(encoding='utf-8'))
def esc(x): return html.escape(str(x))
def view(x):
    if isinstance(x,dict): return '<dl>'+''.join('<dt>'+esc(k)+'</dt><dd>'+view(v)+'</dd>' for k,v in x.items())+'</dl>'
    if isinstance(x,list): return '<ul>'+''.join('<li>'+view(v)+'</li>' for v in x)+'</ul>'
    return '<pre>'+esc(x)+'</pre>'
page='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>CLI-first envelope proposal</title>
<style>body{font:16px/1.6 system-ui;max-width:1100px;margin:30px auto;padding:0 24px;background:#111827;color:#e5e7eb}h1,h2,dt{color:#93c5fd}dt{font-weight:bold;margin-top:14px}section{border:1px solid #374151;padding:18px;margin:16px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 ui-monospace}.status{background:#78350f;padding:16px}a{color:#93c5fd}</style>
<h1>CLI 首片：沿用既有 HOST／EXEC 的非互動封包</h1>
<p class="status">PROPOSED · 待 owner 核准。只讀來源及規劃，未啟動 Agent、未讀 secret、未建立正式 Skeleton／RED 或實作。</p>
<p>先測本機 benign fixture，再分別核對指定的 Claude Code／Codex 安裝。來源中的預設旗標只代表設定值，不能當作已驗證的 provider 介面。</p>'''
page+=''.join('<section><h2>'+esc(k)+'</h2>'+view(v)+'</section>' for k,v in s.items())
page+='<script type="application/json" id="module-spec">'+json.dumps(s,ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
(b/'module.html').write_text(page,encoding='utf-8')
print('Rendered proposed CLI-first envelope HTML.')
