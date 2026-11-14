# M04 save response handoff precision gap

One bounded original F05/M04 planning delta: cx-v3 effective architecture save shorthand has receipt → ACK, while the reviewed M03 save candidate requires verified file → issuer-bound M05 root transfer → captured ACK → authorized response. This packet exposes that missing handoff, without adopting the cross-module proposal.

Run from D:\AIAD:

`python -B docs/requirements-confirmation/phase1-spec/tasks/M04/planning/save-response-handoff/check_documents.py`

`index.html` embeds the structured ModuleSpec. `mapping.json` records full request/result differences rather than inventing a new DTO. `verification.json` contains 11 new witnesses, one unsafe-shortcut counterexample, exact old pointer, HEAD and 796-file authority checks. `artifact-hashes.json` seals all other artifacts. `steps_pending.py` intentionally contains native automation stubs, not passing acceptance tests.

New witnesses are document-model checks only. Independent review, native/UI/IPC, product tests, valid RED/GREEN, build/package/install and full Draft validation are NOT RUN. Root authenticity is an explicit model premise. Parent remains Yellow; owner gates G1-G4 precede approved Skeleton and valid RED.
