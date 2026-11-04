# -*- coding: utf-8 -*-
from pathlib import Path
import re

ui = Path(__file__).resolve().parent
html = (ui / "index.html").read_text(encoding="utf-8")
js = (ui / "git-ux-mock.js").read_text(encoding="utf-8")
assert "git-ux-root" in html
assert "git-ux-mock.js" in html
assert "git-ux-mock.css" in html
assert 'id="git-empty"' in html
assert "EluSlotGitUxMock" in js
ids = re.findall(r'"id": "([^"]+)"', js)
print("ops", len(ids), "unique", len(set(ids)))
assert len(set(ids)) == 65
for need in (
    "git-ux-scenario",
    "git-ux-rail",
    "git-ux-view",
    "git-ux-op-dialog",
    "git-ux-toast",
):
    assert need in html, need
print("OK")
