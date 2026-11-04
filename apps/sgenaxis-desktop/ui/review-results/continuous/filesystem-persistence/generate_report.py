import json,html,pathlib,hashlib,subprocess
p=pathlib.Path('reports/rust-improvements/continuous/filesystem-persistence')
A={
'A1 System context':'Existing HOST document/settings save callers invoke FileSystemPort. Only real StdFileSystem implementation changes; no UI or generic save redesign.',
'A2 Hexagonal system boundary':'Driving UI/CLI -> existing HOST use cases -> FileSystemPort <- StdFileSystem -> OS filesystem. Domain has no filesystem dependency.',
'A3 Module dependency':'HOST -> sgenaxis-ports; sgenaxis-adapters -> sgenaxis-ports and std. No application -> concrete adapter dependency added.',
'A4 Responsibilities':'Caller owns save intent and payload. FileSystemPort owns opaque IO contract. StdFileSystem owns one write transaction and temporary file lifecycle. OS implements rename.',
'A5 Input ports':'Existing FileSystemPort::write_atomic(path:&str, contents:&[u8])->Result<(),PortError>; no signature changes.',
'A6 Output ports':'No new output ports; adapter calls std::fs/OpenOptions/Write behind existing IO boundary.',
'A7 Driving adapters':'Existing UI/CLI/HOST callers unchanged; tests call FileSystemPort.',
'A8 Driven adapters':'StdFileSystem only. FakeFileSystem unchanged; real adapter tests establish OS-specific guarantees.',
'A9 Dependency direction':'Caller -> existing port <- real adapter -> standard library/OS. Domain and HOST never acquire concrete filesystem dependency.',
'A10 State ownership':'Destination is committed persistent state; caller owns submitted byte slice. Each invocation exclusively owns its temp path and open handle; no authoritative global state. Atomic counter, if used, is naming assistance only; create_new decides ownership.',
'A11 Mutation boundary':'Only owning invocation writes/removes its temporary file. Destination changes only at successful rename. Never delete destination as replacement fallback.',
'A12 Transaction boundary':'Create sibling exclusively -> write all -> sync file -> close -> rename over destination. Before successful rename, prior destination bytes remain unchanged. Error cleanup removes only owned temp, best effort; cannot promise cleanup if OS denies removal.',
'A13 External system boundary':'Local filesystem behavior; Windows machine probe only. Network filesystems, adversarial directory mutation, symlink sandboxing, power loss and parent-directory fsync excluded.',
'A14 Forbidden dependencies':'No new Manager/service/port/crate, per-target lock table, serialization change, CAS/version arbitration, background cleanup daemon, caller rewrite, public error variant, or remove-destination fallback.'}
contracts=[
('FS-C1','Success means destination contains exactly one complete submitted payload at this invocation commit; later successful writers may replace it.'),
('FS-C2','Concurrent successful writes use last successful commit wins, not request-start order. No merged/torn payload.'),
('FS-C3','Before commit failure leaves previous destination unchanged; existing parent-directory creation remains allowed and is not rolled back.'),
('FS-C4','Exclusive create collision never truncates existing temp. Retry bounded at 128 candidates; exhaustion returns existing PortError mapping and preserves destination.'),
('FS-C5','Owned temp is closed then cleanup attempted on write/sync/rename failure. Cleanup never targets peer files or replaces primary error. Residual temp may remain if cleanup is denied.'),
('FS-C6','No CAS, locking, multi-file transaction, power-loss durability or universal filesystem atomicity guarantee. Supported Windows local filesystem overwrite is tested; additional platforms require own evidence.')]
tests=[
('FS-T01','Create missing destination and replace existing destination with nonempty and zero-byte payloads; byte equality, no owned leftovers.','FS-C1'),
('FS-T02','Deterministic barrier after both exclusively-created temp handles: both writers must reach barrier; assert different owned paths; release A commit then B commit and final bytes B; reverse ordering final A. Timeout is harness failure, not valid RED.','FS-C1,FS-C2'),
('FS-T03','Place candidate collision sentinel; force first private candidate then next unused candidate; sentinel bytes unchanged and successful retry. Force 128 collisions -> error, target/sentinels unchanged.','FS-C4'),
('FS-T04','Inject write failure after partial owned temp bytes, and sync failure independently; close, cleanup attempted, previous target exact. Inject cleanup denial -> original error retained, residue reported by harness only.','FS-C3,FS-C5'),
('FS-T05','Inject rename denial; existing destination remains; owned temp removed when permitted. Never remove destination.','FS-C3,FS-C5'),
('FS-T06','Peer prepares temp at barrier; failing invocation cleans up; peer temp survives and peer commits intact.','FS-C2,FS-C5'),
('FS-T07','Real Windows replacement integration: existing file -> new complete bytes; target directory failure preserves directory; no owned leftovers.','FS-C1,FS-C3'),
('FS-T08','Distinct target paths, nested missing parents, unicode/spaces path, bytes containing zero/invalid UTF8 preserve exact bytes; regression existing swap/host save/settings tests.','FS-C1')]
coverage={f'B{i}':v for i,v in enumerate(['Applicable success','Applicable empty/large bytes and path','Applicable invalid/missing path','Applicable create/write/sync/rename','Applicable partial write','Applicable old/new intact','Applicable commit only','Applicable handle close/cleanup','Applicable owned cleanup','Applicable existing HOST saves','Applicable Windows; other OS deferred until runner available','Applicable existing swap/save/settings regressions'],1)}
spec={'module':'filesystem-persistence','task':'PD-RUST-FS-PLAN-02','decision':'PD-RUST-FS-DEC-01','date':'2026-10-26 Asia/Taipei','state':'READY_FOR_GREEN','architecture_status':'OWNER_APPROVED_A','implementation':'IMPLEMENTATION_COMPLETE_OWNER_ACCEPTANCE_PENDING','tests':'Independent RED 13 compiled, 4 PASS/9 intended FAIL; independent focused13/workspace290/EXEC56/Tauri79 PASS; architecture review PASS','intent':'Avoid same-process concurrent save temp collision and preserve old destination before commit without new architecture.','assumptions':['Local filesystem ordinary file target','Callers accept last successful commit wins','Existing error enum unchanged'],'architecture':A,'contracts':contracts,'bdd_categories':coverage,'tests_planned':tests,'cost':{'production_files_modified':1,'test_files_expected':1,'new_ports':0,'new_crates':0,'new_managers':0,'estimated_private_lines':'60-100 plus tests','pattern':'none; retain current adapter, private helper and test-only seam'},'allowed_after_approval':['apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/std_fs.rs','one private adapter test module and lib test registration only if needed'],'protected':['ports API','HOST','Domain','UI','Cargo manifests','other adapters'],'acceptance':['All FS-T01..08 pass; planned normal/error/controlled concurrency assertions execute','Independent behavioral RED demonstrated after approved skeleton; compile/setup failure not RED','Existing adapter and HOST save/settings regressions pass or individually classified','No public API/dependency/state owner changes; source scope reviewed','Report generated from this structured model with actual result metadata'],'owner_approval':'Owner approved exact A: 核准最小方案，接續 RED 與實作.','remaining_question':'No remaining A decision; approved scope: existing FileSystemPort unchanged; exclusive unique sibling temp; last successful commit wins complete payload; precommit preserves prior target; best-effort owned-temp cleanup; Windows local replacement verified; no CAS/power-loss durability?','evidence':{'independent_test_report':'../filesystem-persistence-tests/module.html','independent_review':'../filesystem-persistence-review/module.html','verified_counts':{'focused':13,'workspace':290,'exec_allfeatures':56,'tauri':79},'owner_light':'YELLOW; READY_FOR_GREEN is not owner acceptance','historical_date':'2026-10-26 Asia/Taipei; counts belong to completed FS slice before later process changes','source_sha256':{f:hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest() for f in ['apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/std_fs.rs','apps/sgenaxis-desktop/crates/sgenaxis-ports/src/fs.rs']},'windows_probe':'PASS existing regular-file replacement and create_new collision preservation on this Windows machine; no concurrency/error-injection claim; not behavioral RED; no production edits','git_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()},'risks':['OS denies cleanup: residual owned temp may remain','Open target sharing modes may reject rename; report error and preserve target','No validation on non-Windows or remote filesystem yet'],'deferred':['Crash recovery/durability','CAS/conflict UI','Cross-process lock service','Transactional multi-file persistence']}
(p/'module.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
(p/'steps.pending.txt').write_text('EXECUTED: T01-T08 represented by13 independent frozen tests; valid RED4pass9intendedfail, then independent GREEN13; workspace290/EXEC56/Tauri79 PASS.\nEXECUTED: Windows replacement, deterministic ordered concurrent commits, candidate collision/exhaustion, checkpoint write/sync/rename failure and cleanup denial, peer ownership.\nSources: ../filesystem-persistence-tests/module.html and ../filesystem-persistence-review/module.html.\nNOT RUN: non-Windows/remote filesystem/hardware IO failure/powerloss; no such guarantee claimed.\nPENDING: owner acceptance only. No commit/push.\n',encoding='utf-8')
feature='''Feature: Safe concurrent file persistence
  Background:
    Given an isolated writable local directory
  Rule: Each writer owns its preparation and commits a complete payload
    Scenario: Replace an existing file
      Given a file containing old bytes
      When new bytes are saved successfully
      Then the file contains exactly the new bytes
    Scenario: Concurrent saves commit complete payloads
      Given two saves are preparing different complete payloads for one file
      When both saves commit successfully in a controlled order
      Then the file contains exactly the last committed payload
    Scenario: Failure before commit preserves old bytes
      Given a file containing old bytes
      When saving fails before commit
      Then the file still contains exactly the old bytes
    Scenario: One failed save cannot damage another preparing save
      Given two saves are preparing independent payloads for one file
      When one save fails before commit and the other succeeds
      Then the file contains exactly the successful payload
    Scenario: Existing preparation collision is preserved
      Given an existing file conflicts with a preparation candidate
      When new bytes are saved successfully using another candidate
      Then the existing conflicting file remains unchanged
    Scenario: Empty payload is valid
      Given a file containing old bytes
      When an empty payload is saved successfully
      Then the file contains zero bytes
    Scenario: Replacement is denied
      Given replacement of the existing destination is denied
      When a save is attempted
      Then saving reports failure
      And the previous destination remains unchanged
'''
feature=(p/'module.feature').read_text(encoding='utf-8')  # approved BDD is input, never rewritten
def e(x):return html.escape(str(x))
body='<h1>Filesystem persistence: minimal safe-write proposal</h1><p>[Phase: Green] [Status: OK] OWNER_APPROVED_A — verified RED completed; final helper implemented; independent focused13/workspace290/EXEC56/Tauri79 PASS; architecture review PASS; owner acceptance pending.</p>'
body+='<p>Keep the existing FileSystemPort. Fix only the real adapter\u2019s shared temporary path and failure cleanup. No new patterns or layers.</p>'
body+='<h2>Two architecture views</h2><pre>UI / CLI driving adapters\n  ↓ existing HOST use cases (application)\n  ↓ FileSystemPort input boundary\n  ↑ StdFileSystem driven adapter implements port\n  ↓ std::fs / OS\nDomain: no filesystem dependency</pre><pre>HOST ──depends──► sgenaxis-ports ◄──implements── sgenaxis-adapters\n                                                    │\n                                                    ▼\n                                                  std / OS\nTransaction: exclusive sibling → write → sync → close → rename(commit)\nFailure before commit: target unchanged; cleanup owned temp only</pre>'
body+='<h2>Architecture A1-A14</h2>'+''.join('<h3>'+e(k)+'</h3><p>'+e(v)+'</p>' for k,v in A.items())
for title,key in [('Contracts / invariants','contracts'),('BDD coverage','bdd_categories'),('TDD / traceability','tests_planned'),('Acceptance','acceptance'),('Skeleton envelope','allowed_after_approval'),('Protected scope','protected'),('Risks','risks'),('Deferred work','deferred')]:
 body+='<h2>'+title+'</h2><pre>'+e(json.dumps(spec[key],ensure_ascii=False,indent=2))+'</pre>'
body+='<h2>BDD specification</h2><pre>'+e(feature)+'</pre><h2>Minimal skeleton after approval</h2><pre>write_atomic: keep public signature\nprivate candidate naming: pid + AtomicU64 sequence; create_new is ownership authority; retry max128\nprivate transaction helper: prepare / write_all / sync_all / close / rename\nprivate test-only phase/failure callback: deterministic barriers and failure injection\nerror: close then best-effort cleanup owned temp; preserve original PortError\nno public hook, global lock table, dependency, port, or manager</pre>'
body+='<h2>Task sequence</h2><p>Owner decision → architecture approved → lock contracts/BDD → private skeleton/test seams → independent executable RED → adapter implementation → focused GREEN → adapter/HOST regressions → independent architecture and acceptance review. This package does not approve itself.</p>'
body+='<h2>Pattern ROI</h2><p>Pattern: none. Cost: one production file, one test module; zero ports/crates/managers; about 60–100 private production lines. Benefit: isolate temp ownership and cleanup with no caller migration. Extra abstraction DEFERRED: no test forces it.</p>'
body+='<h2>Experiment / evidence</h2><pre>'+e(json.dumps(spec['evidence'],indent=2))+'</pre><p>Windows probe PASS is an isolated std experiment only; independent RED is recorded separately and implementation focused GREEN is 13/13; independent FS slice regressions passed (13/290/56/79); non-Windows, remote-filesystem and hardware failure checks NOT RUN.</p>'
body+='<h2>Owner-approved scope</h2><p>'+e(spec['remaining_question'])+'</p><h2>Module health</h2><p>READY_FOR_GREEN yellow; independent behavior and architecture review PASS; owner acceptance pending. No acceptance or release claim.</p>'
blob=json.dumps(spec,ensure_ascii=False).replace('<','\\u003c')
(p/'module.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Filesystem persistence proposal</title><style>body{max-width:1100px;margin:32px auto;font:16px system-ui;line-height:1.6;padding:16px;color:#182435}pre{white-space:pre-wrap;background:#eef2f7;padding:18px}h2{border-bottom:1px solid #ccd;padding-top:20px}</style>'+body+'<script type="application/json" id="module-spec">'+blob+'</script></html>',encoding='utf-8')
(p/'architecture.md').write_text('[Phase: Green]\n[Status: OK]\n\nOWNER_APPROVED_A; implemented after verified RED; independent focused13/workspace290/EXEC56/Tauri79 and architecture review PASS; yellow owner acceptance pending. Canonical structured model: module.json; generated human surface: module.html.\n\n'+'\n\n'.join('## '+k+'\n'+v for k,v in A.items())+'\n\nOwner approved A. Independent RED verified before production body implementation; independent GREEN/review passed; owner acceptance remains pending.\n',encoding='utf-8')
print('Generated module package:',p)
