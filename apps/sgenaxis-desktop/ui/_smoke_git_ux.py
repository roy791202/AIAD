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
assert "mapLiveConflict" in js
assert "state.conflict=mapLiveConflict(dto)" in js
assert "dto.settings" in js
assert "state.author=typeof s.author==='string'?s.author:''" in js
assert "state.email=typeof s.email==='string'?s.email:''" in js
assert "state.ignore=typeof s.ignore==='string'?s.ignore:''" in js
assert "typeof c.author==='string'?c.author:''" in js
assert "typeof c.date==='string'?c.date:''" in js
assert "state.live?(h.author||''):(h.author||'Example Developer')" in js
assert "state.live?(h.date||''):(h.date||'剛剛')" in js
assert "typeof t.peeled==='string'?t.peeled:''" in js
assert "function tagPeeled" in js
assert "state.live?esc(tagPeeled(t))" in js
assert "tested:r.tested===true" in js
assert "state.remoteEntries[0].tested===true" in js
assert "r.tested === true" in js
assert "本機已有遠端追蹤紀錄" in js
assert "tested 來自本機 refs/remotes" in js
assert "liveHooks.saveIdentity" in js
assert "liveHooks.saveIgnore" in js
assert "git_write_identity／git_write_ignore" in js
assert "liveHooks.stashApply" in js
assert "liveHooks.stashPop" in js
assert "git_write_stash_apply／git_write_stash_pop" in js
assert "liveHooks.tagCreate" in js
assert "git_write_tag" in js
assert "liveHooks.tagDelete" in js
assert "git_write_tag_delete" in js
assert "liveHooks.branchCreate" in js
assert "git_write_branch_create" in js
assert "liveHooks.branchDelete" in js
assert "git_write_branch_delete" in js
assert "liveHooks.remoteAdd" in js
assert "liveHooks.remoteRemove" in js
assert "liveHooks.remoteSetUrl" in js
assert "git_write_remote_add" in js
assert "git_write_remote_remove" in js
assert "git_write_remote_set_url" in js
assert "liveHooks.conflictSave" in js
assert "liveHooks.conflictContinue" in js
assert "liveHooks.conflictAbort" in js
assert "git_write_conflict_save" in js
assert "git_write_conflict_continue" in js
assert "git_write_conflict_abort" in js
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
