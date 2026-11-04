# M03 bounded Viewer close integration proposal

This new planning folder covers exactly `design_viewer_close`. Original H2 and
CX-v3 documents, product source/tests, management files and roles are unchanged.
Apply the ai-dev-preproduction instructions embedded in the repository AGENTS;
this author is not an independent verifier. No production implementation envelope
is approved by these files. No `docs/LESSONS.md` exists at this checkout.

Run from repository root, always without bytecode writes:

```
python -B docs/requirements-confirmation/phase1-spec/tasks/M03/planning/viewer-close-integration/build_packet.py
python -B docs/requirements-confirmation/phase1-spec/tasks/M03/planning/viewer-close-integration/fixtures_builder.py
python -B docs/requirements-confirmation/phase1-spec/tasks/M03/planning/viewer-close-integration/checker.py
```

`fixtures.json` contains complete expected response, state, calls, delivery, UI
and automatic-retry results. The fixture generator never calls the reducer to
derive its expected values. Harness-owned initial state is assumed valid, with
one or four occupied slots; this packet does not create a new state ingestion
API. Native capture/close/delivery observations are proposed *trusted* seams,
never user-supplied booleans or evidence that native provenance exists.

Capture/delivery are eager exact-type checked before request validation; this
changes possible failure precedence and is explicitly pending Owner. Error
wire roots preserve original branch definitions; provider error forwarding is
restricted to five applicable error codes. Other error branches are checked for
root shape only, not claimed reachable outcomes of this command.

Request `preview_session` alone carries no ownership authority. Native consumer,
actual window instance, project, root, runtime epoch, document UUID, owner session,
generation and preview identity must match; local origin and native liveness are
checked independently. Trusted native registry and provider authenticity remain
premises. A valid typed proof cannot establish that the real provider acted.

`ResponseLostAfterCommit` is an explicit failure-injection premise, not a wire
response or an admitted closed proof. It records provider retirement while UI
stays uncertain. Malformed or missing observations generally leave modeled
*confirmed* state unchanged; they do not prove that a real provider rolled back.
Nothing retries automatically, reopens a preview or restores provider state.

Repeated removed references -> PreviewClosed with replayed=false, no tombstone
and no reservation, plus release-one-slot at capacity, are **options pending
Owner**, not inherited approved H2 policies. Original request-record limits apply
to request_id-bearing commands; this command has none. Do not borrow binding-close
detach/tombstone behavior. Dirty-document discard confirmation does not apply to
preview-only cleanup; no binding detach/documentclose/content/history/formalSave/
FileCommit/ACK/pin/root mutation is authorized.

Schema changes are exact physical before/after rows only: `$` to a shared-engine
strict-end negative lookahead, including carried shared definitions. The bounded
evaluator audits its supported keyword set; it is not a full Draft2020 validator
and does not certify JavaScript/native regex behavior. Checked U64 semantic
generation admission is separate from lexical schema limits.

The HTML embeds `module-spec.json` as a human projection. ModuleSpec, complete
fixture/trace results and hashes are the reviewable artifact. Source authority is
the 796-file M01 `s2-green/source-current.json` inventory, historical HEAD
31babe87a7ef1e40a0d4bedc523077e7a45d63ab; current HEAD is recorded separately as
5b709343a890503ebbe24a802e43cda5647df124. Parent remains Yellow. Author checks
cannot establish independent review, native behavior, build, product tests, valid
RED, module acceptance or release readiness; all are NOT RUN.
