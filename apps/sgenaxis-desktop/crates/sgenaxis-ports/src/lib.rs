//! SGenAxis **Ports** — OS / CLI boundary traits (stage 2.5 / PD-ADAPT-01 / PD-DEPLOY-PORT-01).
//!
//! Traits only: no `std::fs`, no `std::process`, no `std::path::PathBuf` in the
//! public surface. Paths and IDs are `String` / opaque handles so Core / domain
//! code can depend on this crate without importing OS types.
//!
//! Adapters live in `sgenaxis-adapters`. Core must **not** depend on adapters.

#![forbid(unsafe_code)]

mod deploy;
mod error;
mod fs;
pub mod file_commit;
mod git;
mod git_index_commit;
mod interactive;
mod path;
mod process;

pub use deploy::{
    unsupported_platform_reason, windows_wix_artifact_relpath, windows_wix_supported, DeployCapability,
    DeployPlatform, DeployPort, DeployStatus, DeploySupport, WINDOWS_WIX_FORMAT,
    WINDOWS_WIX_PACKAGER, WINDOWS_WIX_PRODUCT_VERSION,
};
pub use error::PortError;
pub use fs::FileSystemPort;
pub use file_commit::{CommitError, CommitReceipt, CommitStage, FileCommitPort, FileWriteLease};
pub use git::{
    GitBranch, GitCommit, GitConflictFile, GitConflictState, GitPort, GitRemote, GitSettings,
    GitStash, GitStatus, GitStatusEntry, GitStatusKind, GitTag, GitUpstream, GitWriteApproval,
    GitWritePort,
};
pub use git_index_commit::{
    GitIndexCommitPort, GitOperationState, IndexCommitError, IndexCommitFacts,
    IndexCommitFingerprint, IndexCommitObservation,
};
pub use interactive::{
    Cleanup, InteractiveError, InteractiveErrorKind, InteractiveFixturePort, InteractiveId,
    InteractiveObservation, InteractiveSize, ReadState,
};
pub use path::PathPort;
pub use process::{ProcessId, ProcessOutput, ProcessPort, StreamCompletion};
