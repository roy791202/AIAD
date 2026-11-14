"""Render the canonical proposal; never inspect or mutate product state."""
import html
import json
from pathlib import Path

base = Path(__file__).resolve().parent
spec = json.loads((base / 'module.json').read_text(encoding='utf-8'))

def render(value):
    if isinstance(value, dict):
        return '<dl>' + ''.join('<dt>' + html.escape(str(k)) + '</dt><dd>' + render(v) + '</dd>' for k, v in value.items()) + '</dl>'
    if isinstance(value, list):
        return '<ul>' + ''.join('<li>' + render(v) + '</li>' for v in value) + '</ul>'
    return '<pre>' + html.escape(str(value)) + '</pre>'

payload = json.dumps(spec, ensure_ascii=False).replace('<', '\\u003c')
page = '''<!doctype html><html lang="zh-Hant"><meta charset="utf-8">
<title>Process lifecycle — frozen minimal final drain plan</title>
<style>body{font:16px system-ui;margin:32px auto;max-width:1100px;padding:0 24px;background:#111827;color:#e5e7eb}h1,h2,dt{color:#93c5fd}dt{font-weight:bold;margin-top:18px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 ui-monospace}section{border:1px solid #374151;padding:18px;margin:18px 0;border-radius:10px}a{color:#a5d6ff}.state{background:#78350f;padding:16px}</style>
<h1>程序退出與最終輸出收尾</h1><p>[Phase: Planning] [Status: FROZEN_PACKET · READY_FOR_TDD]</p>
<p class="state">PD-RUST-PROC-PLAN-02 殘餘規劃已凍結：A1–A14、兩張圖、最小方案、contracts/BDD/AC/skeleton、source evidence。不自改綠板；sibling IMPL/TDD/REVIEW 與 owner 驗收另卡。</p>
<p>最小範圍：保留 try_wait 的子程序退出語義，明確辨識 stdout / stderr EOF，再發布一次終止事件。不增加 Manager、框架、程序樹管理或新事件種類。</p>'''
page += ''.join('<section><h2>' + html.escape(key) + '</h2>' + render(value) + '</section>' for key, value in spec.items())
page += '<script type="application/json" id="module-spec">' + payload + '</script></html>'
(base / 'module.html').write_text(page, encoding='utf-8')
print('Rendered module.html from module.json; frozen planning packet.')
