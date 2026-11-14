"""Readable existing-run guard report, projected from canonical metadata."""
import html
import json
from pathlib import Path
base = Path(__file__).resolve().parent
s = json.loads((base/'module.json').read_text(encoding='utf-8'))
def esc(x): return html.escape(str(x))
def listing(items): return '<ul>'+''.join('<li>'+esc(x)+'</li>' for x in items)+'</ul>'
def block(title, content): return '<section><h2>'+esc(title)+'</h2>'+content+'</section>'
page='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Active run: minimal Assign guard</title>
<style>body{font:16px/1.6 system-ui;max-width:1000px;margin:32px auto;padding:0 24px;background:#111827;color:#e5e7eb}h1,h2{color:#93c5fd}section{border:1px solid #374151;padding:18px;margin:16px 0;border-radius:8px}pre{white-space:pre-wrap;overflow-wrap:anywhere}td,th{text-align:left;padding:8px;border-bottom:1px solid #374151}a{color:#93c5fd}.state{background:#78350f;padding:14px}</style>
<h1>保留執行中 Run：再次派工的最小防護</h1>'''
page+='<p class="state">'+esc(s['phase'])+' · owner acceptance PENDING · yellow</p>'
page+=block('目的與變更','<p>執行或收尾期間再次按派工，直接以既有 Busy 提示返回，保留目前 Run 與輸出輪詢。只增加既有函式內 5 行，不新增狀態、API 或依賴。</p><p>'+esc(s['intent'])+'</p>')
page+=block('既有架構與責任','<pre>'+esc(s['hexagonal'])+'\n'+esc(s['dependency_view'])+'</pre><p>'+esc(s['state_owner'])+'</p><p>'+esc(s['mutation'])+'</p>')
page+=block('可見行為與契約',listing(s['bdd'])+'<table><tr><th>控制</th><th>執行／收尾中</th><th>真正結束後</th></tr><tr><td>既有派工按鈕</td><td>Busy 提示，零額外 start_run；不修改 generation</td><td>既有正常派工路徑恢復</td></tr><tr><td>既有取消與 log</td><td>持續輪詢，保留尾端輸出</td><td>真實 terminal 決定分類</td></tr></table>')
page+=block('驗收與證據',listing(s['acceptance'])+'<p>歷史 RED：'+esc(s['red'])+'</p><p>目前：'+esc(s.get('verification','Pending independent gate'))+'</p><p>獨立來源審查：'+esc(s.get('independent_review','PENDING'))+'</p><p><a href="../process-tests/module.html">獨立測試與回歸報告</a></p>')
page+=block('精確範圍與限制',listing(s['allowed_files'])+'<p>'+esc(s['protected'])+'</p>'+listing(s.get('risks',[])))
page+=block('建置與版本資訊','<p>JavaScript 語法檢查：'+esc(s.get('syntax_check','NOT RUN'))+'</p><p>完整應用／原生 Tauri／真實 Agent：NOT RUN 此微卡。無 package、install、commit 或 push。</p><p>app.js SHA-256：'+esc(s.get('source_sha256','pending'))+'</p>')
page+='<script type="application/json" id="module-spec">'+json.dumps(s,ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
(base/'module.html').write_text(page,encoding='utf-8')
print('Rendered active-run module HTML.')
