//! SGenAxis **WORK** — project registry, root bind, execution lease (PD-WORK-01).
//!
//! ```text
//! register(path) → PathProbePort → WorkspaceStorePort  (ProjectId + root)
//! rebind(id, path)  ──rejects──▶ if ExecutionLease active
//! select(id)        ──view only─▶ WorkspaceProjection (Run root untouched)
//! ```
//!
//! Depends on `sgenaxis-ports` for [`sgenaxis_ports::PortError`] only.
//! Fake [`PathProbePort`] / [`WorkspaceStorePort`] live in-crate for unit tests.
//! Does **not** touch HoneyBadger / `:8788` / `:8787`.

#![forbid(unsafe_code)]

mod error;
mod id;
mod lease;
mod probe;
mod project;
mod projection;
mod service;
mod store;

pub use error::WorkError;
pub use id::ProjectId;
pub use lease::ExecutionLease;
pub use probe::{FakePathProbe, PathProbePort, PathProbeResult};
pub use project::{Project, RegisterOutcome};
pub use projection::{LeaseSummary, ProjectSummary, WorkspaceProjection};
pub use service::WorkspaceService;
pub use store::{FakeWorkspaceStore, WorkspaceStorePort};
