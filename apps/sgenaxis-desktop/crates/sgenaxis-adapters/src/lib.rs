//! SGenAxis **Adapters** — implement Ports (PD-ADAPT-01 / PD-GIT-01 / PD-GIT-02 / PD-DEPLOY-PORT-01).
//!
//! - **Fake** adapters for unit tests (in-memory, no OS)
//! - **Std** adapters (`std-adapters` feature, default): thin `std::fs` +
//!   Windows-aware path conventions + read-only [`StdGit`] + approving
//!   [`StdGitWrite`] + query-only [`StdDeploy`]
//! - **Default write** remains [`GatedGitWrite`] (deny); approving writes use
//!   [`FakeGitWrite`] / [`StdGitWrite`] with [`sgenaxis_ports::GitWriteApproval`]
//!
//! Core (`sgenaxis-core`) must **not** depend on this crate. Host / use-cases
//! compose Ports at the boundary; see [`compose`] and [`git_summary`].

#![deny(unsafe_code)]

pub mod compose;
pub mod fake;
pub mod ess_codec;
pub mod git_summary;
pub mod git_write;

// IO-PREREQ Skeleton only; Windows adapter is not connected to HOST or UI.
#[cfg(all(windows, feature = "std-adapters"))]
pub mod file_commit;
#[cfg(all(windows, feature = "std-adapters"))]
pub use file_commit::StdFileCommit;

#[cfg(feature = "std-adapters")]
pub mod cli_probe;
#[cfg(feature = "std-adapters")]
pub mod std_deploy;
#[cfg(feature = "std-adapters")]
pub mod std_fs;
#[cfg(feature = "std-adapters")]
pub mod std_git;
#[cfg(feature = "std-adapters")]
pub mod std_git_write;
#[cfg(feature = "std-adapters")]
pub mod std_git_index_commit;
#[cfg(feature = "std-adapters")]
pub mod std_path;
#[cfg(feature = "std-adapters")]
pub mod std_process;

pub use compose::{
    boxed_deploy_fake, ensure_app_config_dir, fake_deploy, BoxedPorts, HostPorts,
};
#[cfg(feature = "std-adapters")]
pub use compose::{boxed_deploy_std, std_deploy};
pub use fake::{FakeDeploy, FakeFileSystem, FakeGit, FakeGitWrite, FakePath, FakeProcess};
pub use git_summary::{summarize_worktree, GitWorkbenchSummary};
pub use git_write::{
    git_error_redacted, redact_credentials, GatedGitWrite, GIT_WRITE_GATED_MSG,
    GIT_WRITE_NOT_APPROVED_MSG,
};

#[cfg(feature = "std-adapters")]
pub use cli_probe::{probe_agent_cli, probe_named_cli, ProbedCli, AGENT_CLI_CANDIDATES};
#[cfg(feature = "std-adapters")]
pub use std_deploy::StdDeploy;
#[cfg(feature = "std-adapters")]
pub use std_fs::StdFileSystem;
#[cfg(feature = "std-adapters")]
pub use std_git::StdGit;
#[cfg(feature = "std-adapters")]
pub use std_git_write::StdGitWrite;
#[cfg(feature = "std-adapters")]
pub use std_git_index_commit::StdGitIndexCommit;
#[cfg(feature = "std-adapters")]
pub use std_path::StdPath;
#[cfg(feature = "std-adapters")]
pub use std_process::StdProcess;

#[cfg(test)]
mod tests_deploy;
#[cfg(test)]
mod tests_swap;
#[cfg(test)]
mod tests_git;
#[cfg(test)]
mod tests_git02;

// EA-A0 approved fixture adapter skeleton; no native composition yet.
#[cfg(any(windows, test))]
pub mod conpty_fixture;
