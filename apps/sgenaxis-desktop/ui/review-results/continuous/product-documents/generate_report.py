"""Render current product-document contract metadata without inspecting product state."""
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

page = '''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Product document current contracts</title>
<style>body{font:16px system-ui;max-width:1150px;margin:32px auto;padding:0 24px;background:#111827;color:#e5e7eb}dt,h1,h2{color:#93c5fd}dt{font-weight:bold;margin-top:16px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 ui-monospace}section{border:1px solid #374151;padding:18px;margin:18px 0;border-radius:8px}.status{padding:14px;background:#78350f}</style>
<h1>產品文件：目前格式、契約與相容性缺口</h1>
<p class="status">靜態現況審核；沒有修改 schema、production、tests 或原始文件。行為驗證 NOT RUN，DOCUMENT 決策待核准。</p>
<p>保留 XML 與 JSON 各自用途。先釐清實際讀寫與資料遺失風險，不增加統一格式、migration 框架或 Manager。</p>'''
page += ''.join('<section><h2>' + html.escape(k) + '</h2>' + render(v) + '</section>' for k, v in data.items())
page += '<script type="application/json" id="module-spec">' + json.dumps(data, ensure_ascii=False).replace('<', '\\u003c') + '</script></html>'
(base / 'module.html').write_text(page, encoding='utf-8')
print('Rendered product-documents module.html from canonical JSON.')
