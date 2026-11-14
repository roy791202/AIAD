# -*- coding: utf-8 -*-
"""PD-UIDESIGN-INDEX-01 — sync index.html embed + alignment banner / page pills."""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

OUT = Path(__file__).resolve().parent / "ui-design"
SPEC_PATH = OUT / "ui-spec.json"
INDEX_PATH = OUT / "index.html"

CSS_EXTRA = (
    ".align-banner{margin:16px 0;padding:14px 18px;border:1px solid #34383e;"
    "border-left:3px solid #f2b544;background:#1b1d1f;border-radius:4px}"
    ".align-banner .pill-row{margin:8px 0 0;display:flex;gap:6px;flex-wrap:wrap}"
    ".pill-row{display:inline-flex;gap:6px;flex-wrap:wrap;vertical-align:middle;margin-left:8px}"
    ".pill.impl-merged{border-color:#5bc98b;color:#5bc98b}"
    ".pill.impl-partial{border-color:#f2b544;color:#f2b544}"
    ".pill.impl-implemented{border-color:#56a8ff;color:#56a8ff}"
    ".pill.impl-oos{border-color:#a4adba;color:#a4adba}"
    ".pill.muted-pill{border-color:#34383e;color:#aeb5bf}"
)

BANNER_HTML = (
    '<div id="align-banner" class="align-banner" role="status">'
    "<strong>對齊狀態</strong>"
    '<span class="muted"> · 讀自嵌入 #ui-spec（須 ≡ ui-spec.json）· Workbench IA SSOT</span>'
    '<div class="pill-row" id="align-banner-pills"></div>'
    '<p class="muted" id="align-banner-detail" style="margin:8px 0 0"></p>'
    "</div>"
)

HYDRATE_JS = (
    "(function(){"
    "var el=document.getElementById('ui-spec');"
    "if(!el)return;"
    "var spec;try{spec=JSON.parse(el.textContent);}catch(e){return;}"
    "var meta=spec.metadata||{};"
    "function pill(text,cls){var s=document.createElement('span');"
    "s.className='pill '+(cls||'');s.textContent=text;return s;}"
    "function implClass(v){"
    "if(v==='MERGED')return 'impl-merged';"
    "if(v==='PARTIAL')return 'impl-partial';"
    "if(v==='IMPLEMENTED')return 'impl-implemented';"
    "if(v==='OUT_OF_SCOPE_V01')return 'impl-oos';"
    "return 'muted-pill';}"
    "var banner=document.getElementById('align-banner-pills');"
    "if(banner){banner.textContent='';"
    "banner.appendChild(pill(meta.status||'DESIGN PROPOSAL'));"
    "banner.appendChild(pill('產品實作 '+(meta.product_implementation||'NOT IMPLEMENTED'),implClass(meta.product_implementation)));"
    "banner.appendChild(pill('測試 '+(meta.product_test_results||'NOT RUN'),'muted-pill'));"
    "if(meta.ia_ssot)banner.appendChild(pill('IA SSOT '+meta.ia_ssot,'muted-pill'));}"
    "var detail=document.getElementById('align-banner-detail');"
    "if(detail){var bits=[];"
    "if(meta.authority_order&&meta.authority_order.length)bits.push('權威: '+meta.authority_order.join(' → '));"
    "bits.push('mock≠產品 PASS');"
    "if(meta.aligned_at)bits.push('aligned_at '+meta.aligned_at);"
    "if(meta.bdd_ref)bits.push(meta.bdd_ref);"
    "detail.textContent=bits.join(' · ');}"
    "var hp=document.querySelector('header .pill');"
    "if(hp){hp.textContent='對齊 · '+(meta.product_implementation||'NOT IMPLEMENTED')+' · 非產品 PASS';"
    "hp.className='pill '+implClass(meta.product_implementation);}"
    "(spec.pages||[]).forEach(function(p){"
    "var row=document.querySelector('.page-status-pills[data-page-id=\"'+p.id+'\"]');"
    "if(!row)return;row.textContent='';"
    "row.appendChild(pill(p.status||'DESIGNED / PROPOSED','muted-pill'));"
    "row.appendChild(pill(p.implementation||'NOT IMPLEMENTED',implClass(p.implementation)));"
    "if(p.product_panel)row.appendChild(pill('panel:'+p.product_panel,'muted-pill'));"
    "if(p.workbench_view)row.appendChild(pill(p.workbench_view,'muted-pill'));"
    "else row.appendChild(pill('無主視圖','muted-pill'));"
    "row.appendChild(pill('驗 '+(p.verification||'NOT RUN'),'muted-pill'));"
    "});"
    "})();"
)


class Doc(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.embedded = ""
        self.mode = None
        self.ids: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "script":
            self.mode = "json" if a.get("type") == "application/json" else "js"

    def handle_endtag(self, tag):
        if tag == "script":
            self.mode = None

    def handle_data(self, data):
        if self.mode == "json":
            self.embedded += data


def main() -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    html = INDEX_PATH.read_text(encoding="utf-8")

    pill_css = (
        ".pill{font-size:12px;padding:3px 9px;border:1px solid #5b4b29;"
        "color:#f2b544;border-radius:4px}"
    )
    if ".align-banner{" not in html and pill_css in html:
        html = html.replace(pill_css, pill_css + CSS_EXTRA, 1)

    if 'id="align-banner"' not in html:
        needle = '<div class="actions"><a href="../product-plan/index.html">產品規畫</a>'
        if needle not in html:
            raise SystemExit("actions block not found")
        html = html.replace(needle, BANNER_HTML + needle, 1)

    # Replace hardcoded per-page design pill with hydrate target (once each).
    for i in range(1, 15):
        pid = f"UI-{i:02d}"
        old = f'<section id="{pid}" class="design-page">'
        if f'data-page-id="{pid}"' in html:
            continue
        # Find h2 pill for this page only: after section id, first 設計提案 pill.
        marker = f'<section id="{pid}" class="design-page">'
        start = html.find(marker)
        if start < 0:
            raise SystemExit(f"missing section {pid}")
        # Limit search to this section (until next UI section or dialogs).
        end_markers = [html.find(f'<section id="UI-{i+1:02d}"', start + 1)] if i < 14 else []
        end_markers.append(html.find('<section id="dialogs"', start + 1))
        end = min(m for m in end_markers if m >= 0)
        chunk = html[start:end]
        old_pill = ' <span class="pill">設計提案</span>'
        new_pill = f' <span class="pill-row page-status-pills" data-page-id="{pid}"></span>'
        if old_pill not in chunk:
            # Already something else; force insert after first </h2> opener content
            if f'data-page-id="{pid}"' not in chunk:
                raise SystemExit(f"pill not found for {pid}")
            continue
        chunk2 = chunk.replace(old_pill, new_pill, 1)
        html = html[:start] + chunk2 + html[end:]

    # Sync embedded #ui-spec with ui-spec.json (verify requires equality).
    embed = json.dumps(spec, ensure_ascii=False).replace("<", "\\u003c")
    m = re.search(
        r'<script type="application/json" id="ui-spec">.*?</script>',
        html,
        flags=re.S,
    )
    if not m:
        raise SystemExit("embedded #ui-spec not found")
    html = html[: m.start()] + (
        '<script type="application/json" id="ui-spec">' + embed + "</script>"
    ) + html[m.end() :]

    if "getElementById('align-banner-pills')" not in html:
        close = "</body></html>"
        if not html.rstrip().endswith(close):
            # tolerate trailing whitespace
            idx = html.rfind(close)
            if idx < 0:
                raise SystemExit("html close not found")
            html = html[:idx] + "<script>" + HYDRATE_JS + "</script>" + html[idx:]
        else:
            html = html[: -len(close)] + "<script>" + HYDRATE_JS + "</script>" + close

    INDEX_PATH.write_text(html, encoding="utf-8")

    doc = Doc()
    doc.feed(INDEX_PATH.read_text(encoding="utf-8"))
    assert json.loads(doc.embedded) == spec, "embedded #ui-spec != ui-spec.json"
    assert "align-banner" in doc.ids
    assert "align-banner-pills" in doc.ids
    for i in range(1, 15):
        assert f"UI-{i:02d}" in doc.ids
    assert "page-status-pills" in INDEX_PATH.read_text(encoding="utf-8")
    print(
        json.dumps(
            {
                "patched": str(INDEX_PATH),
                "embedded_eq_spec": True,
                "align_banner": True,
                "pages": len(spec["pages"]),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
