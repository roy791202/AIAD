# PD-GIT-SET-UPSTREAM-01 — High-tier review (section B)

**Verdict:** **PASS** (architecture / layering / git contract) · **BLOCKED** (merge / Guard — see process)

Independent high-tier review of implementation PR #78. Reviewer is **not** implementer **bc-321ccf88** (nor PR author agent **bc-ebcf4a54**). This agent did **not** merge, did **not** set Done/Blue, and did **not** change product code or `docs/board.json`.

**Date (UTC):** 2026-11-15  
**Reviewer:** independent high-tier (this Cloud Agent run)  
**Impl PR:** https://github.com/roy791202/AIAD/pull/78  
**Implementation branch:** `feature/PD-GIT-SET-UPSTREAM-01-set-upstream` @ `1924b56986bc6a72b93475995e0326a94267b117`  
**Base:** `main` @ `98355b1891b0a3cbe1e4697eeced2df457fe6ef9`

## Identity

| Role | Identity | Same as reviewer? |
|------|----------|-------------------|
| Implementer | Cloud dev agent (`cloud-dev-agent-cursor` / PR `cursor[bot]`, run bc-ebcf4a54) | No |
| High-tier | This review | — |
| Independent TDD verifier | Not observed in this run | N/A |

## Scope (PR #78 files)

4 files, +900 / −1. **No** changes to `std_git_write.rs`, `fake.rs`, `git_write.rs`, `sgenaxis-host`, UI, or hooks.

| Path | Role |
|------|------|
| `sgenaxis-adapters/src/git_set_upstream.rs` | New TDD-lock module: 3 scenario-ID tests (Fake + Gated + `#[cfg(std-adapters)]` Std) |
| `sgenaxis-adapters/src/lib.rs` | `#[cfg(test)] mod git_set_upstream;` |
| `docs/bdd/PD-GIT-SET-UPSTREAM-01.feature` | New Gherkin (3 scenarios) |
| `docs/board.json` | Next-batch queue + `PD-GIT-SET-UPSTREAM-01` moved to **In Review**, `tdd: Green` |

Task note allowed: port comment, adapter tests (`tests_git*` or dedicated file), optional **host** `git_set_upstream.rs` tests only, dispatch report. Impl stayed in adapters only — within allowance.

## Layering (host vs adapters)

| Layer | Artifact | PR change? | Dependency direction |
|-------|----------|------------|----------------------|
| Port | `GitWritePort::set_upstream` in `sgenaxis-ports` | None | Inner contract |
| Adapter (std) | `StdGitWrite::set_upstream` — `git branch --set-upstream-to=…` only | None (already on `main`) | Implements port |
| Adapter (fake / gated) | Fake + `GatedGitWrite` | None | Test doubles |
| Host / application | `perform_git_set_upstream` in `sgenaxis-host/src/git_set_upstream.rs` | None | Calls `&dyn GitWritePort`; host tests remain separate |

New tests live in **adapters** and import `sgenaxis_ports` + `FakeGitWrite` / `StdGitWrite` / `GatedGitWrite`. They do **not** import Tauri, UI, or host application code. Host layer is unchanged; no skip-layer (UI → git CLI).

`StdGitWrite::set_upstream` on `main` (unchanged by PR) already documents and implements: approval gate → remote list → local + tracking ref checks → `run(["branch", spec, "--", local])` — never fetch/pull/push/checkout/switch (`std_git_write.rs` ~813–864).

## No fetch / checkout (under test)

| Scenario | Fake / Gated | Std integration |
|----------|--------------|-----------------|
| PD-GIT-SET-UPSTREAM-01-1 | Denied: no `last_set_upstream`, `push_count == 0`, `last_fetch` none, `switched_branch` none; Gated still `GIT_WRITE_GATED_MSG` | Denied: `main@{upstream}` absent; `HEAD` SHA unchanged |
| PD-GIT-SET-UPSTREAM-01-2 | Granted: tracks `origin/main`; push/fetch/switch counters unchanged | Granted: `main` → `origin/main`; **abbrev-ref HEAD** unchanged; `origin/main` OID unchanged |
| PD-GIT-SET-UPSTREAM-01-3 | Unknown remote / missing ref / bad names → fail; no ghost remote / branch | Same failures on real repo; no new remote `ghost` |

Fixture setup uses raw `git` for init/push/unset-upstream/**`git branch topic`** to build state; assertions target **`StdGitWrite::set_upstream`** only. That matches sibling git-write TDD-lock PRs (setup ≠ product path).

## TDD (reviewer re-run)

```text
cd apps/sgenaxis-desktop/crates/sgenaxis-adapters
cargo test --features std-adapters pd_git_set_upstream_01
# 3 passed (pd_git_set_upstream_01_1/2/3)
```

Prior coverage in `tests_git.rs` / `tests_git02.rs` for `set_upstream` remains; this PR adds **scenario-ID** locks required by dispatch. Acceptable overlap for traceability.

## Board — **In Review** token

| Check | Result |
|-------|--------|
| Task `PD-GIT-SET-UPSTREAM-01.status` | **`In Review`** (exact token — not `In Review / In QA`) ✓ |
| Done / blue | Not set ✓ |
| `tdd` | `Green` on task |
| `ci` | `None` (Guard **failed** on PR — see below) |
| `prUrl` | Missing on card (impl PR #78 exists) |
| Story `S-GIT-WRITE-SET-UPSTREAM-01` | `Todo` / gray; nested `bdd[].status` all **`None`** while task claims TDD Green |

Guard @ `1924b569` (**failure**, job `guard`):

1. Task TDD Green but scenarios `PD-GIT-SET-UPSTREAM-01-{1,2,3}` not Green on board.
2. New/changed `docs/bdd/PD-GIT-SET-UPSTREAM-01.feature` without **`spec-change`** label / CODEOWNERS path.

Other checks on same SHA: `tests` success, `lint + test subset` success; `rust-windows` was in progress at review time. PR mergeable state: **unstable** (Guard).

**Board note:** PR also appends the full next-batch block (4 stories + 4 tasks). Only `PD-GIT-SET-UPSTREAM-01` should move on this impl PR; batch siblings belong on the coordinator branch to avoid cross-task noise.

## `.feature` — coordinator vs duplicate

| Location | `PD-GIT-SET-UPSTREAM-01.feature` |
|----------|----------------------------------|
| `main` | Absent |
| `cursor/next-batch-set-rename-remote-upstream-0111` | Present (SHA `2e58bba…`) |
| PR #78 branch | Same content (byte-identical to coordinator) |

**Finding:** Gherkin already lives on the **coordinator** branch. Re-adding it on the task impl PR triggers AI Dev Guard **spec-change** rules and duplicates pre-production BDD. **Prefer:** drop `.feature` from PR #78 (rely on coordinator merge) **or** add `spec-change` + approver review if the file must ride this PR.

## Architecture findings

### Must-fix (architecture)

None.

### Blocking merge / Done (process — not architecture FAIL)

1. AI Dev Guard red (bdd status on Story vs task `tdd: Green`; `.feature` / spec-change).
2. Story card BDD scenario statuses should be **`Green`** when task `tdd` is Green (or task `tdd` must not be Green until verifier updates Story).
3. Remove duplicate `.feature` from impl PR if coordinator branch will land first.
4. Set `prUrl` on task when PR is open; set `ci` to reflect Guard once stable.
5. Do **not** set Done/Blue from this review.

### Suggestions (non-blocking)

1. Deduplicate helper boilerplate in `git_set_upstream.rs` (three copies of temp-repo helpers) — refactor only if a shared test fixture already exists elsewhere.
2. Trailing newline at EOF of `git_set_upstream.rs` (minor style).
3. Host `perform_git_set_upstream` tests on `main` are thin vs adapter scenario locks; no change required for this TDD-lock task.

## Decision

**PASS** high-tier architecture review: host/adapters boundaries respected, no product mutation on PR #78, `set_upstream` contract honors **no fetch / no checkout / no push** on the exercised path, scenario tests align with BDD IDs.

**Do not merge** until Guard green and board/BDD/process items above are resolved. **Do not** set Done/Blue.

**Evidence path:** `reports/dispatch-pd/PD-GIT-SET-UPSTREAM-01-HIGH-TIER-REVIEW.md`  
**Compare:** https://github.com/roy791202/AIAD/compare/main...feature/PD-GIT-SET-UPSTREAM-01-set-upstream