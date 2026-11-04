# PD-RUST-NATIVE-UI-VERIFY-01 verification planning review

**PLAN_READY_FOR_OWNER_REVIEW. Execution NOT RUN.**

Existing report has environment/smokeNOTRUN matrix; lacks minimal native observation protocol and phasedAC. Correct SDK dependency inference from actual globalTauri wiring.

## Complete minimal plan

See [unified human plan](module.html) and [structured canonical data](module.json). Both architecture views, module ownership, BDD, evidence/isolation/failure matrix, dependencies and measurable AC are explicit. No future-provider framework.

## Next slices

- NATIVE-V1: Environment/build identity+isolated project preparation and evidence protocol; no UI launch in current planning
- NATIVE-V2: Native launch and one real registered query/action; verify bridge identity without monkeypatching __TAURI__
- NATIVE-V3: Scene and UI-design save/load/invalid/failure/reopen using existing commands and approved contract
- NATIVE-V4: Native run emptypoll/cancel/tailterminal and repeatAssign/restart; local approved fixtures only
- NATIVE-V5: Cross-module system fixtures only after SYS ready

## Owner decision

Approve minimal native evidence checklist/fixture plan and staged transport/persistence smoke, keeping full UI behavior/system cases dependency-gated. Before execution identify available native control/observation capability; absence is environment NOT RUN, never browser PASS.

No production/test/harness/nativeUI/realAgent action performed. Parent owns review/board disposition; this document does not self-approve architecture or claim end-to-end/native PASS.
