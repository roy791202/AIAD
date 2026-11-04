# CI-IR-F1 root cause and prevention

The command packet rebuilt a bounded U64 regex with `$`. Python `re.search` lets `$` match before a terminal LF. Earlier vector success did not prove strict end-of-input behavior. The independent review reproduced 13 whole-root LF admissions; ECMAScript behavior differed.

Reuse the already reviewed `save-proof-correction/request.schema.json` `$defs/U64Decimal` object, including minLength/maxLength and the parsed single-backslash `(?![\s\S])` strict end assertion. Do not recreate a command-specific U64 grammar. Future command packets must reuse this reviewed definition and run actual control-codepoint, max-bound and fullroot branch/reference probes. No field-name custom hook or fullmatch bypass may mask a schema error.

The correction inventories four definition sites, including inline request fields and both `$defs`. Reachability expands to 20 branch/reference occurrences. Branch-specific valid base fixtures distinguish Applied, NoChange and AppliedRetentionDeferred, plus both error arms. This includes every original 13 reviewer path/branch case. New 400 cases run in two engines; old 104/367 evidence is preserved, not recounted as progress.

This is author self-check only. Independent acceptance, full Draft validation, native product behavior and valid TDD RED remain NOT RUN. Candidate grammar correction does not adopt architecture or change NoChange/consume/retention/replay policy.
