# SGenAxis product plan 0.1

Open index.html directly; no server, CDN or network is required for the document UI.
Modules have standalone module.html documents with embedded ModuleSpec JSON.
This is a proposed specification, not approved product architecture or running software.

## Generate
python docs/build_plan.py

The Python builder is documentation tooling only. It currently holds the draft authoring data.
Edit this builder to regenerate this draft; do not independently edit generated HTML or snapshots.
The proposed PRODUCT storage design (D-05) uses each module.html embedded ModuleSpec as canonical.
That runtime editor/storage system has NOT been implemented by this documentation generator.

## Agent handoff
Read module.html embedded module-spec and tasks/<ID>/task.json.
Observe dependency order. Before production changes obtain architecture/contract approval,
create approved skeleton, implement tests and observe valid RED.
Task npm commands are planned interfaces and do not exist yet.
Task steps.ts files deliberately return pending; they are not passing tests.
Load only the chosen task steps to avoid duplicate Background definitions across task packages.

## Status
Planning artifacts only. Product build/tests/install/DCC/release: NOT RUN.
Verification.json covers document structure and traceability only.
