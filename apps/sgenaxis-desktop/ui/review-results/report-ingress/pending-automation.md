# Pending automation and review

All specification is PROPOSED. No production tests executed.

- Implement step bindings only after approval/skeleton
- RED must compile and fail behaviorally; no RED evidence exists now
- L2 identity/auth/order/idempotency/failure injection
- L3 HTTP/command/MCP adapter parity
- L4 cancellation/reconnect/acceptance regression
- HTML embedded-spec validation and stale revision detection

## Measurable acceptance matrix

| ID | Behavior | Level | Result |
|---|---|---|---|
| TDD-RI-01 | Record progress through any supported transport | L2 contract / L3 adapter parity | NOT RUN |
| TDD-RI-02 | Retry an identical report | L2 contract / L3 adapter parity | NOT RUN |
| TDD-RI-03 | Reject a conflicting duplicate | L2 contract / L3 adapter parity | NOT RUN |
| TDD-RI-04 | Reject an out of order report | L2 contract / L3 adapter parity | NOT RUN |
| TDD-RI-05 | Reject an obsolete execution attempt | L2 contract / L3 adapter parity | NOT RUN |
| TDD-RI-06 | Reject an identity mismatch | L2 contract / L3 adapter parity | NOT RUN |
| TDD-RI-07 | Completion is not acceptance | L2 contract / L3 adapter parity | NOT RUN |
| TDD-RI-08 | Preserve state on commit failure | L2 contract / L3 adapter parity | NOT RUN |
| TDD-RI-09 | Reconnect with expired authority | L2 contract / L3 adapter parity | NOT RUN |
| TDD-RI-10 | Reject reports after cancellation | L2 contract / L3 adapter parity | NOT RUN |
| TDD-RI-11 | Reject excessive or empty input | L2 contract / L3 adapter parity | NOT RUN |
| TDD-RI-12 | Reject unauthorized reporting | L2 contract / L3 adapter parity | NOT RUN |
| TDD-RI-13 | Retry after a lost acknowledgement | L2 contract / L3 adapter parity | NOT RUN |
| TDD-RI-14 | Reject changed specification binding | L2 contract / L3 adapter parity | NOT RUN |

## Architecture gate

ReportRun interface, authority grant and atomic persistence seam require approval. Python done -> green conflicts with Rust acceptance/EVID gates and is excluded.
