# sgenaxis-adapters (PD-ADAPT-01 + PD-GIT-01 + PD-GIT-02 + PD-DEPLOY-PORT-01)

Implementations of `sgenaxis-ports` for SGenAxis stage 2.5 / Git / Deploy slices.

| Adapter | Kind | Notes |
|---------|------|--------|
| `FakeFileSystem` / `FakePath` / `FakeProcess` / `FakeGit` | Fake | In-memory; unit tests / DryRun (`FakeProcess` supports `push_stdout`／`try_read`) |
| `FakeDeploy` | Fake | M3: Windows WiX/MSI Supported; macOS/Linux Unsupported; settable last path |
| `StdProcess` | Std | Real spawn + piped stdout／stderr readers (`try_read`／`try_wait`／`cancel`) |
| `FakeGitWrite` | Fake write | Approving commit/push in memory; injectable push fail |
| `StdFileSystem` | Std | Thin `std::fs` + temp+rename atomic write |
| `StdPath` | Std | Win: `LOCALAPPDATA\<app>`; Unix: XDG / `~/.config` |
| `StdProcess` | Std stub | `std::process::Command` — **not** Agent CLI |
| `StdGit` | Std read | Shells `git -C <repo> status\|log\|diff` only |
| `StdGitWrite` | Std write | Approving `commit` / `push`; no force; redacts credentials |
| `StdDeploy` | Std | Query-only WiX path convention + optional MSI probe; **no** elevated install |
| `GatedGitWrite` | Gate | Default deny (`PermissionDenied`) regardless of approval |

Feature `std-adapters` is **default**. Disable with `--no-default-features` for fake-only builds.

## Approval gate (PD-GIT-02)

`GitWritePort::commit` / `push` take `GitWriteApproval::{denied, granted}`.

- Unapproved → `PermissionDenied` (`GIT_WRITE_NOT_APPROVED_MSG`); no mutation.
- `GatedGitWrite` always denies (safe compose default).
- `StdGitWrite` / `FakeGitWrite` mutate only when `granted()`.
- Push failure preserves local commits; errors pass through `redact_credentials`.

## Git summary use-case

`git_summary::summarize_worktree(&dyn GitPort, repo, log_limit) → GitWorkbenchSummary`

DTO fields: `branch`, `entries` / `entry_count`, `recent_commits`, `diff_text`, `writes_enabled` (`false` here — write enablement is host-side via approving adapter). Never mutates the repo.

## Composition

```text
UI ──Tauri commands──► host boot
                         │
                         ├─ BoxedPorts::fake()                         # gated write
                         ├─ BoxedPorts::std_with_git()                 # StdGit + GatedGitWrite
                         ├─ BoxedPorts::std_with_approving_git_write() # StdGit + StdGitWrite
                         └─ boxed_deploy_fake() | boxed_deploy_std(repo)  # DeployPort swap

sgenaxis-core  ──does not import──►  sgenaxis-adapters
use-cases      ──&dyn GitPort──►  FakeGit | StdGit
               ──&dyn GitWritePort──►  GatedGitWrite | FakeGitWrite | StdGitWrite
               ──&dyn DeployPort──►  FakeDeploy | StdDeploy
```

See `compose::{HostPorts, BoxedPorts, fake_deploy, std_deploy}` and `git_summary::summarize_worktree`.

## Test

Requires Rust toolchain (`rustc` + `cargo`) on `PATH`. Write tests use **FakeGitWrite** and **temp dirs** for `StdGitWrite` — never commit/push against user repos.

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cd D:\AIAD\apps\sgenaxis-desktop\crates\sgenaxis-adapters
cargo test
```

Also:

```powershell
cd D:\AIAD\apps\sgenaxis-desktop\crates\sgenaxis-ports
cargo check
```

Expected coverage: Fake FS / Path / Process; FakeGit; FakeGitWrite approval / preserve / redact; `GatedGitWrite` deny; `StdGit` porcelain; `StdGitWrite` temp-repo commit/push / non-ff preserve; FakeDeploy / StdDeploy capability + Unsupported + Fake↔Std swap; compose bundles.

## Non-goals

- Force push
- Agent CLI / MCP (`PD-EXEC-*`)
- Elevated `msiexec` / install (DeployPort is query-only)
- macOS / Linux packagers
- HoneyBadger, 8788/8787
- Pulling adapters into `sgenaxis-core`
