[Phase: Pre-TDD]
[Status: WARNING]

# ARCHITECTURE_GAP — execution-guard

Required behavior: implementation dispatch must be authorized by current human-approved task/project/fingerprint/architecture/BDD/skeleton and qualified RED identity; generic execution must remain genuinely generic.

Current skeleton: caller supplies EnvelopeDto.approved and RedKindDto. start_run guard is optional; start_implementation checks those caller values. SpecStore approve locks a contract hash but has no actor/task/project binding. CORE TaskRecord has only id/title/zone; WORK owns project/lease, not intent. EVID records qualified RED but only spec_hash/worktree version binding. SPEC UI currently loads a bundled fixture.

Missing seam: authoritative task intent, protected human approval source and complete immutable binding. Additional DTO validation or hashing is not authority proof.

Smallest honest action: leave production unchanged, keep decision RED, publish this gap and continue unrelated ready work.

Candidate bounded option: owner approves session-only human confirmation and host-owned binding, with a single private record map and shared validation in existing DispatchHost. Agent can reference but cannot create/approve/reclassify. No repository/service/trait/crate/dependency is proposed. The actual protected confirmation mechanism and atomic revalidation must be decided before a skeleton is frozen. This document does not claim the existing command transport can distinguish a human from an Agent.

Compatibility: explicitly trusted generic tasks retain generic execution. Unknown tasks reject rather than default generic; this changes legacy unclassified-task behavior and requires explicit approval. No blanket non-DryRun rule is proposed.

One owner question: 是否核准採本機桌面的人類確認作為唯一核准入口，由 HOST 保存僅本次 session 有效的工項意圖及 task/project/fingerprint/架構-BDD-skeleton revision/RED evidence 綁定；Agent 只能引用，重啟須重核准，既有未分類工項先拒絕執行？核准後先確認人類確認入口不允許 Agent 自行呼叫，再建立 Skeleton 與 RED。

Cost: zero new crates, traits or dependencies; candidate changes ~2 existing dispatch/dto files plus tests, UI boundary cost pending. No speculative registry or persistent approval infrastructure. Pattern ROI: reject new repository/authentication framework by YAGNI. No production estimate is a commitment before architecture approval.

Status: ARCHITECTURE_GAP / NOT_READY_FOR_IMPLEMENTATION. Production/tests read-only; no tests executed, no RED claimed. Proposed BDD/test stubs and data are design artifacts only.
