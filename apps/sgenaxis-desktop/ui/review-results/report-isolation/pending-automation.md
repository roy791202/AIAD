# Pending automation and assumptions

The Gherkin step stubs are pending and were not executed. Rust integration tests remain the actual RED/GREEN evidence in evidence.txt.

## Pending

- Select and configure a BDD runner and binding to the existing Rust public call boundary.
- Bind each step in behavior.feature to steps_pending.py or equivalent runner-native steps.
- Load fixture.json; snapshot input bytes before invocation; assert unchanged bytes afterward.
- Run simultaneous fixture cases and assert distinct paths and matching DTO/file status and fingerprint.
- Cross-process reservation collision/PID-reuse integration coverage is not run; current Rust concurrency test covers same-process concurrent calls.
- Independent acceptance and full regression remain parent-owned gates.

## Assumptions

- Python and the repository pd_report package are required test dependencies; absence must fail visibly.
- Existing repository fixtures are authoritative; fixture.json references them without duplicating their source content.
- Explicit out_dir preserves caller-controlled destination semantics, including possible caller-selected conflicts.
- Generated reports remain available after return for UI access. No retention cleanup policy is introduced.
- No additional architecture, public API, or persistence contract change is approved or claimed.

## Open questions

- Which existing BDD runner should own these bindings? This does not block the already executed Rust tests.
- Output retention policy and explicit-directory concurrent collision policy require separate scoped planning if requested.
