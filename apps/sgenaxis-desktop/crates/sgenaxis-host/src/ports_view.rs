//! PD-REMAIN-PORTS-UI-01 — read-only Ports／adapter registry projection.
//!
//! Built from composition labels at boot — **never** enumerates OS devices／paths
//! from the UI. Empty registry is a valid observable state.

use serde::Serialize;

/// One registered Port ↔ adapter binding (projection only).
#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct PortBindingView {
    /// Port trait name (e.g. `FileSystemPort`).
    pub port: String,
    /// Concrete adapter label (e.g. `FakeFileSystem`／`StdGit`).
    pub adapter: String,
    /// `bound`｜`gated`｜`approving`｜`query`｜`empty`
    pub status: String,
    /// Short human-readable note (no secrets／no absolute OS dumps).
    pub detail: String,
}

/// Registry projection consumed by the Ports panel via Command.
#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct PortsStatusView {
    /// `ok`｜`empty`
    pub status: String,
    pub entry_count: usize,
    pub entries: Vec<PortBindingView>,
    pub message: Option<String>,
}

/// Adapter kind labels captured at composition boot (dyn ports lose concrete type).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PortAdapterLabels {
    pub fs: &'static str,
    pub path: &'static str,
    pub process: &'static str,
    pub git: &'static str,
    pub git_write: &'static str,
    pub deploy: &'static str,
}

impl PortAdapterLabels {
    pub const FAKE: Self = Self {
        fs: "FakeFileSystem",
        path: "FakePath",
        process: "FakeProcess",
        git: "FakeGit",
        git_write: "GatedGitWrite",
        deploy: "FakeDeploy",
    };

    pub const FAKE_APPROVING_WRITE: Self = Self {
        fs: "FakeFileSystem",
        path: "FakePath",
        process: "FakeProcess",
        git: "FakeGit",
        git_write: "FakeGitWrite",
        deploy: "FakeDeploy",
    };

    #[cfg(feature = "std-adapters")]
    pub const STD_APPROVING: Self = Self {
        fs: "StdFileSystem",
        path: "StdPath",
        process: "StdProcess",
        git: "StdGit",
        git_write: "StdGitWrite",
        deploy: "StdDeploy",
    };

    #[cfg(feature = "std-adapters")]
    pub const STD_GATED_WRITE: Self = Self {
        fs: "StdFileSystem",
        path: "StdPath",
        process: "StdProcess",
        git: "StdGit",
        git_write: "GatedGitWrite",
        deploy: "StdDeploy",
    };
}

fn binding(port: &str, adapter: &str, status: &str, detail: &str) -> PortBindingView {
    PortBindingView {
        port: port.into(),
        adapter: adapter.into(),
        status: status.into(),
        detail: detail.into(),
    }
}

/// Build projection from boot labels + write-gate flag. Empty labels → empty ok.
pub fn project_ports_status(
    labels: Option<&PortAdapterLabels>,
    git_writes_enabled: bool,
) -> PortsStatusView {
    let Some(labels) = labels else {
        return PortsStatusView {
            status: "empty".into(),
            entry_count: 0,
            entries: Vec::new(),
            message: Some("no ports registered".into()),
        };
    };

    let git_write_status = if git_writes_enabled {
        "approving"
    } else {
        "gated"
    };
    let git_write_detail = if git_writes_enabled {
        "mutations require GitWriteApproval per call"
    } else {
        "default-deny gate; UI writes disabled"
    };

    let entries = vec![
        binding(
            "FileSystemPort",
            labels.fs,
            "bound",
            "exists／read／write_atomic／create_dir_all",
        ),
        binding(
            "PathPort",
            labels.path,
            "bound",
            "config_dir／cache_dir／join／normalize",
        ),
        binding(
            "ProcessPort",
            labels.process,
            "bound",
            "start／wait／cancel／read — not Agent CLI itself",
        ),
        binding(
            "GitPort",
            labels.git,
            "bound",
            "read-only status／log／diff",
        ),
        binding(
            "GitWritePort",
            labels.git_write,
            git_write_status,
            git_write_detail,
        ),
        binding(
            "DeployPort",
            labels.deploy,
            "query",
            "capability／artifacts only; no elevated install",
        ),
    ];

    let entry_count = entries.len();
    PortsStatusView {
        status: if entry_count == 0 {
            "empty".into()
        } else {
            "ok".into()
        },
        entry_count,
        entries,
        message: None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_labels_yield_empty_ok() {
        let v = project_ports_status(None, false);
        assert_eq!(v.status, "empty");
        assert_eq!(v.entry_count, 0);
        assert!(v.entries.is_empty());
        assert!(v.message.as_deref().unwrap_or("").contains("no ports"));
    }

    #[test]
    fn fake_boot_lists_six_ports_gated_write() {
        let v = project_ports_status(Some(&PortAdapterLabels::FAKE), false);
        assert_eq!(v.status, "ok");
        assert_eq!(v.entry_count, 6);
        assert_eq!(v.entries[0].port, "FileSystemPort");
        assert_eq!(v.entries[0].adapter, "FakeFileSystem");
        let gw = v
            .entries
            .iter()
            .find(|e| e.port == "GitWritePort")
            .expect("git_write");
        assert_eq!(gw.status, "gated");
        assert_eq!(gw.adapter, "GatedGitWrite");
        let dep = v
            .entries
            .iter()
            .find(|e| e.port == "DeployPort")
            .expect("deploy");
        assert_eq!(dep.status, "query");
    }

    #[test]
    fn approving_write_flag_reflected() {
        let v = project_ports_status(Some(&PortAdapterLabels::FAKE_APPROVING_WRITE), true);
        let gw = v
            .entries
            .iter()
            .find(|e| e.port == "GitWritePort")
            .unwrap();
        assert_eq!(gw.status, "approving");
        assert_eq!(gw.adapter, "FakeGitWrite");
    }
}
