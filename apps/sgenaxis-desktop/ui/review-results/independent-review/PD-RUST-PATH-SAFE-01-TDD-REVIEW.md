# PD-RUST-PATH-SAFE-01 independent TDD review

Verdict: **TDD_PASS — yellow; owner acceptance pending.** Date: 2026-10-25 Asia/Taipei.

Reviewed actual working contents of HOST `uidesign_doc.rs`, `scene_doc.rs`, path-safety spec and feature. Rust sources are untracked in Git, so HEAD is not a usable before/after baseline; this is content review, not a verified Git diff. Producer's RED record says the built test rejected the old implementation because it accepted `scene/C:/outside.ess`. That historical RED was inspected but not independently replayed; independent current execution is recorded below.

The fix rejects initial slash/backslash and any colon before joining, and retains parent-component rejection. Scene normalization stops stripping roots before validation. Existing public signatures, ownership, FileSystemPort dependency and validate-before-IO flow remain intact. No new Port, manager or state owner. Scene tests exercise save/load/exists rejection and preservation of existing data. The shared-helper test covers drive-relative, embedded drive, root, UNC and alternate-stream inputs plus a normal nested path. Assertions are substantive; no skip, deleted failure case or weakened assertion was observed in the supplied changes.

Independent command from `D:/AIAD/apps/sgenaxis-desktop`: `C:/Users/g6812/.cargo/bin/cargo.exe test -p sgenaxis-host --locked --offline`. Exit 0: **74 unit + 3 integration tests passed, 0 failed/ignored; 0 doc tests**.

Limits: lexical path protection only. Symlink/junction containment and filesystem canonicalization are not proven and require a separate seam/contract decision. Existing-file preservation does not itself prove a complete zero-IO audit; the production control flow rejects these invalid requests before IO. Full module BDD categories such as real filesystem failure/rollback and all lifecycle paths were not newly verified. No package, desktop/DCC, Live transport, commit or push proof. TDD pass for this slice does not establish complete persistence-module acceptance.
