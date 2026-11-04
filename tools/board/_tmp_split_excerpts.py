import json
from pathlib import Path

cards = json.loads(Path("tools/board/_tmp_dispatch_excerpts.json").read_text(encoding="utf-8"))
out = Path("tools/board/_tmp_card_excerpts")
out.mkdir(exist_ok=True)
for c in cards:
    p = out / f"{c['id']}.json"
    p.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    print(p.name)
