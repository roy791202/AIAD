"""Project a nine-card approval reconciliation, without changing the board."""
import html
import json
from pathlib import Path
b=Path(__file__).resolve().parent
s=json.loads((b/'module.json').read_text(encoding='utf-8'))
def esc(x): return html.escape(str(x))
def link(p):
    prefix='reports/rust-improvements/'
    url='http://127.0.0.1:8770/review-results/'+p[len(prefix):].replace('/','-') if p.startswith(prefix) and p.endswith('.html') else p
    return '<a href="'+esc(url)+'">'+esc(p)+'</a>'
page='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Red decision approval reconciliation</title><style>body{font:15px/1.6 system-ui;max-width:1250px;margin:28px auto;padding:0 20px;background:#111827;color:#e5e7eb}h1,h2{color:#93c5fd}table{border-collapse:collapse;width:100%}td,th{border:1px solid #374151;padding:10px;vertical-align:top;text-align:left}section{border:1px solid #374151;padding:16px;margin:18px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#93c5fd}.status{background:#78350f;padding:14px}</style>
<h1>紅燈決策：既有批准與真正阻塞核對</h1><p class="status">只讀 API 快照核對；不新增批准、不改燈色、不重跑測試。PM 將卡轉紅不等於 owner 撤回既有批准。</p>'''
page+='<p>'+esc(s['summary'])+'</p><table><tr><th>卡片</th><th>分類／是否真阻塞</th><th>最小剩餘問題</th><th>下游</th></tr>'
for c in s['decisions']:
    downstream='直接依賴：'+(', '.join(c['direct_declared_downstream']) or '無')+'；間接／範圍受影響：'+(', '.join(c['other_affected_or_indirect']) or '無')
    page+='<tr><td>'+esc(c['id'])+'</td><td>'+esc(c['classification'])+'<br>'+esc(c['actual_block'])+'</td><td>'+esc(c['minimal_question'])+'</td><td>'+esc(downstream)+'</td></tr>'
page+='</table>'
for c in s['decisions']:
    note=c.get('not_blocked_by_this_decision',c.get('related_delivery_not_new_blocker',''))
    page+='<section><h2>'+esc(c['id'])+'</h2><p>'+esc(c['resolution'])+'</p><p>批准／需求來源：</p><pre>'+esc('\n'.join(c['approval_evidence'] or ['未找到本卡具體方案的 owner 明確核准。通用派工授權不代替架構核准。']))+'</pre><p>尚缺：'+esc('; '.join(c['missing']) or '無新的架構缺件')+'</p><p>'+esc(note)+'</p><p>既有方案：'+link(c['proposal'])+'</p><p>最小問題：'+esc(c['minimal_question'])+'</p></section>'
page+='<section><h2>核對界線</h2><p>'+esc(s['limits'])+'</p><pre>'+esc(json.dumps(s['source_binding'],ensure_ascii=False,indent=2))+'</pre></section>'
page+='<script type="application/json" id="module-spec">'+json.dumps(s,ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
(b/'module.html').write_text(page,encoding='utf-8')
print('Rendered nine-card decision reconciliation.')
