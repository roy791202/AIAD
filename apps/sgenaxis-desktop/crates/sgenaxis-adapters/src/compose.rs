//! Host composition — how Core / Tauri will wire Ports later (no Agent CLI/MCP here).
//!
//! ```text
//! Vanilla UI ──Tauri──► Host (this crate wired at boot)
//!                              │
//!                              ├─ FileSystemPort  (Fake | Std)
//!                              ├─ PathPort        (Fake | Std)
//!                              ├─ ProcessPort     (Fake | Std)  → PD-EXEC-CLI (CliAgentAdapter)
//!                              │                                 PD-EXEC-MCP uses McpClientPort (not ProcessPort)
//!                              ├─ GitPort         (Fake | StdGit)  PD-GIT-01 read
//!                              ├─ GitWritePort    (GatedGitWrite default deny;
//!                              │                   StdGitWrite / FakeGitWrite + approval = PD-GIT-02)
//!                              └─ DeployPort      (Fake | Std)  PD-DEPLOY-PORT-01 — query only
//!
//! sgenaxis-core stays free of this crate; use-cases take `&dyn …Port`.
//! ```

use sgenaxis_ports::{DeployPort, FileSystemPort, GitPort, GitWritePort, PathPort, ProcessPort};

use crate::fake::{FakeDeploy, FakeFileSystem, FakeGit, FakeGitWrite, FakePath, FakeProcess};
use crate::git_write::GatedGitWrite;

#[cfg(feature = "std-adapters")]
use crate::{StdDeploy, StdFileSystem, StdGit, StdGitWrite, StdPath, StdProcess};

/// Typed host bundle — swap concrete adapters at construction time.
pub struct HostPorts<Fs, Path, Proc, Git, GitW = GatedGitWrite> {
    pub fs: Fs,
    pub path: Path,
    pub process: Proc,
    pub git: Git,
    /// Write port; default [`GatedGitWrite`] (deny). Swap to [`StdGitWrite`] for PD-GIT-02.
    pub git_write: GitW,
}

impl HostPorts<FakeFileSystem, FakePath, FakeProcess, FakeGit> {
    /// All-fake bundle for unit tests / DryRun without OS.
    pub fn fake() -> Self {
        Self {
            fs: FakeFileSystem::new(),
            path: FakePath::new(),
            process: FakeProcess::new(),
            git: FakeGit::new(),
            git_write: GatedGitWrite::new(),
        }
    }
}

#[cfg(feature = "std-adapters")]
impl HostPorts<StdFileSystem, StdPath, StdProcess, FakeGit> {
    /// Std FS/Path/Process + fake Git (tests / DryRun without shelling `git`).
    pub fn std_fs_path_process_fake_git() -> Self {
        Self {
            fs: StdFileSystem::new(),
            path: StdPath::new(),
            process: StdProcess::new(),
            git: FakeGit::new(),
            git_write: GatedGitWrite::new(),
        }
    }
}

#[cfg(feature = "std-adapters")]
impl HostPorts<StdFileSystem, StdPath, StdProcess, StdGit> {
    /// Std FS/Path/Process + read-only [`StdGit`] (PD-GIT-01). Writes remain gated.
    pub fn std_with_git() -> Self {
        Self {
            fs: StdFileSystem::new(),
            path: StdPath::new(),
            process: StdProcess::new(),
            git: StdGit::new(),
            git_write: GatedGitWrite::new(),
        }
    }
}

#[cfg(feature = "std-adapters")]
impl HostPorts<StdFileSystem, StdPath, StdProcess, StdGit, StdGitWrite> {
    /// Std read + approving write (`StdGitWrite`). Still requires
    /// [`sgenaxis_ports::GitWriteApproval::granted`] per call.
    pub fn std_with_approving_git_write() -> Self {
        Self {
            fs: StdFileSystem::new(),
            path: StdPath::new(),
            process: StdProcess::new(),
            git: StdGit::new(),
            git_write: StdGitWrite::new(),
        }
    }
}

/// Dyn-dispatch bundle — proves Fake ↔ Std swap behind the same Port traits.
pub struct BoxedPorts {
    pub fs: Box<dyn FileSystemPort>,
    pub path: Box<dyn PathPort>,
    pub process: Box<dyn ProcessPort>,
    pub git: Box<dyn GitPort>,
    pub git_write: Box<dyn GitWritePort>,
}

impl BoxedPorts {
    pub fn fake() -> Self {
        Self {
            fs: Box::new(FakeFileSystem::new()),
            path: Box::new(FakePath::new()),
            process: Box::new(FakeProcess::new()),
            git: Box::new(FakeGit::new()),
            git_write: Box::new(GatedGitWrite::new()),
        }
    }

    /// Fake read + approving [`FakeGitWrite`] (PD-GIT-02 / PD-GIT-WRITE-UI-01 tests).
    pub fn fake_with_approving_git_write() -> Self {
        Self {
            fs: Box::new(FakeFileSystem::new()),
            path: Box::new(FakePath::new()),
            process: Box::new(FakeProcess::new()),
            git: Box::new(FakeGit::new()),
            git_write: Box::new(FakeGitWrite::new()),
        }
    }

    #[cfg(feature = "std-adapters")]
    pub fn std_fs_path_process_fake_git() -> Self {
        Self {
            fs: Box::new(StdFileSystem::new()),
            path: Box::new(StdPath::new()),
            process: Box::new(StdProcess::new()),
            git: Box::new(FakeGit::new()),
            git_write: Box::new(GatedGitWrite::new()),
        }
    }

    #[cfg(feature = "std-adapters")]
    pub fn std_with_git() -> Self {
        Self {
            fs: Box::new(StdFileSystem::new()),
            path: Box::new(StdPath::new()),
            process: Box::new(StdProcess::new()),
            git: Box::new(StdGit::new()),
            git_write: Box::new(GatedGitWrite::new()),
        }
    }

    /// Std read + approving [`StdGitWrite`] (PD-GIT-02). Default boot still uses
    /// [`Self::std_with_git`] (gated deny).
    #[cfg(feature = "std-adapters")]
    pub fn std_with_approving_git_write() -> Self {
        Self {
            fs: Box::new(StdFileSystem::new()),
            path: Box::new(StdPath::new()),
            process: Box::new(StdProcess::new()),
            git: Box::new(StdGit::new()),
            git_write: Box::new(StdGitWrite::new()),
        }
    }
}

/// Example use-case helper: resolve config path then ensure it exists via Ports only.
pub fn ensure_app_config_dir(
    path: &dyn PathPort,
    fs: &dyn FileSystemPort,
    app_name: &str,
) -> Result<String, sgenaxis_ports::PortError> {
    let dir = path.config_dir(app_name)?;
    fs.create_dir_all(&dir)?;
    Ok(dir)
}

/// M3 Fake deploy bundle (Windows WiX Supported; macOS/Linux Unsupported).
pub fn fake_deploy() -> FakeDeploy {
    FakeDeploy::m3_defaults()
}

/// Std deploy bound to a repo root (probes WiX `out/` MSI; never installs).
#[cfg(feature = "std-adapters")]
pub fn std_deploy(repo_root: impl Into<String>) -> StdDeploy {
    StdDeploy::with_repo_root(repo_root)
}

/// Prove Fake ↔ Std swap behind `dyn DeployPort` (composition seam for host).
pub fn boxed_deploy_fake() -> Box<dyn DeployPort> {
    Box::new(FakeDeploy::m3_defaults())
}

#[cfg(feature = "std-adapters")]
pub fn boxed_deploy_std(repo_root: impl Into<String>) -> Box<dyn DeployPort> {
    Box::new(StdDeploy::with_repo_root(repo_root))
}
