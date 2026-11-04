# Pending automation
- Remote GitHub runner execution: NOT RUN until workflow is committed and invoked by owner.
- Fresh Windows checkout build and package: NOT RUN; local dirty tree cannot prove it.
- Gherkin runner bindings: pending; executable unittest cases cover acceptance independently.

# Step definition stubs
Given formal Rust boundaries: resolve fixture paths, validate manifests exist.
When Git evaluates paths: execute git check-ignore --no-index.
Then outputs ignored / locks visible: assert fixture dispositions.
When workflow inspected: parse supported jobs, run scripts, working-directory and triggers.
Then checks fail closed: assert mandatory checks and absence of error suppression.

# Assumptions
Only CI/ignore baseline is in scope. No architecture, runtime, dependency upgrade, source behavior, commit, or push is authorized for this test agent.
PyYAML absent. Workflow inspection fallback is bounded to explicit YAML trigger/job/step and run-command structure; it is not a general YAML parser or GitHub evaluation engine.
RED: two intended failures recorded in red.txt: absent Rust workflow and visible workspace target. Nested target and source/lock visibility passed.
