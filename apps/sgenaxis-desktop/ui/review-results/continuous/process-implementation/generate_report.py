"""Project implementation evidence from canonical metadata."""
import html
import json
from pathlib import Path
base = Path(__file__).resolve().parent
data = json.loads((base / 'module.json').read_text(encoding='utf-8'))
def render(v):
    if isinstance(v, dict):
        return '<dl>' + ''.join('<dt>' + html.escape(k) + '</dt><dd>' + render(x) + '</dd>' for k, x in v.items()) + '</dl>'
    if isinstance(v, list):
        return '<ul>' + ''.join('<li>' + render(x) + '</li>' for x in v) + '</ul>'
    return '<pre>' + html.escape(str(v)) + '</pre>'
page = '<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Process final-output implementation</title><style>body{font:16px system-ui;max-width:1100px;margin:32px auto;padding:0 24px;background:#111827;color:#e5e7eb}h1,h2,dt{color:#93c5fd}dt{font-weight:bold;margin-top:15px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 ui-monospace}section{border:1px solid #374151;padding:18px;margin:16px 0}</style><h1>程序最終輸出：實作與驗證</h1>'
page += ''.join('<section><h2>' + html.escape(k) + '</h2>' + render(v) + '</section>' for k,v in data.items())
page += '<script type="application/json" id="module-spec">' + json.dumps(data,ensure_ascii=False).replace('<','\\u003c') + '</script></html>'
(base/'module.html').write_text(page,encoding='utf-8')
print('Rendered process implementation module.html.')
