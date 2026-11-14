//! Path probe Port — validate project roots without OS types in the API.
//!
//! Fake implementation is in-crate for unit tests (PD-WORK-01: Fake ports OK).

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use sgenaxis_ports::PortError;

/// Result of probing a candidate project root.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PathProbeResult {
    pub exists: bool,
    pub readable: bool,
    pub writable: bool,
    /// Canonical form used for identity / dedup (alias / case folded).
    pub canonical: String,
    /// Normalized display path (separators collapsed; trailing sep trimmed).
    pub normalized: String,
}

impl PathProbeResult {
    pub fn is_usable(&self) -> bool {
        self.exists && self.readable && self.writable
    }
}

/// Output Port: probe a local path for WORK register / rebind.
pub trait PathProbePort: Send + Sync {
    fn probe(&self, path: &str) -> Result<PathProbeResult, PortError>;
}

/// In-memory fake probe — seed dirs, deny lists, and alias → canonical maps.
#[derive(Debug, Default, Clone)]
pub struct FakePathProbe {
    inner: Arc<Mutex<FakeProbeState>>,
}

#[derive(Debug, Default)]
struct FakeProbeState {
    /// path key → access flags (exists implied true when present)
    dirs: HashMap<String, Access>,
    /// alias path → canonical path
    aliases: HashMap<String, String>,
    /// When true, any non-empty path probes as usable (host DryRun／CMD demos).
    accept_any: bool,
}

#[derive(Debug, Clone, Copy)]
struct Access {
    readable: bool,
    writable: bool,
}

impl FakePathProbe {
    pub fn new() -> Self {
        Self::default()
    }

    fn key(path: &str) -> String {
        normalize_light(path)
    }

    /// Seed a usable directory (exists + r/w).
    pub fn seed_dir(&self, path: &str) {
        let mut st = self.inner.lock().expect("fake probe lock");
        st.dirs.insert(
            Self::key(path),
            Access {
                readable: true,
                writable: true,
            },
        );
    }

    /// Seed a path that exists but is not accessible (permission failure).
    pub fn seed_denied(&self, path: &str) {
        let mut st = self.inner.lock().expect("fake probe lock");
        st.dirs.insert(
            Self::key(path),
            Access {
                readable: false,
                writable: false,
            },
        );
    }

    /// Map an alias path onto an existing canonical root (case / junction).
    pub fn seed_alias(&self, alias: &str, canonical: &str) {
        let mut st = self.inner.lock().expect("fake probe lock");
        st.aliases
            .insert(Self::key(alias), Self::key(canonical));
    }

    /// Accept any non-empty path as a usable project root (CMD／UI DryRun host).
    pub fn accept_any_path(&self) {
        let mut st = self.inner.lock().expect("fake probe lock");
        st.accept_any = true;
    }
}

impl PathProbePort for FakePathProbe {
    fn probe(&self, path: &str) -> Result<PathProbeResult, PortError> {
        if path.trim().is_empty() {
            return Err(PortError::InvalidPath(path.into()));
        }
        let st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(path);
        let canonical = st
            .aliases
            .get(&key)
            .cloned()
            .unwrap_or_else(|| case_fold_key(&key));

        // Look up access under the original key or the alias target.
        let access = st
            .dirs
            .get(&key)
            .or_else(|| st.dirs.get(&canonical))
            .or_else(|| {
                // Case-insensitive match against seeded dirs.
                st.dirs
                    .iter()
                    .find(|(k, _)| case_fold_key(k) == case_fold_key(&canonical))
                    .map(|(_, v)| v)
            })
            .copied();

        match access {
            Some(a) => Ok(PathProbeResult {
                exists: true,
                readable: a.readable,
                writable: a.writable,
                canonical: case_fold_key(&canonical),
                normalized: key,
            }),
            None if st.accept_any => Ok(PathProbeResult {
                exists: true,
                readable: true,
                writable: true,
                canonical: case_fold_key(&canonical),
                normalized: key,
            }),
            None => Ok(PathProbeResult {
                exists: false,
                readable: false,
                writable: false,
                canonical: case_fold_key(&canonical),
                normalized: key,
            }),
        }
    }
}

fn normalize_light(path: &str) -> String {
    let mut s: String = path
        .chars()
        .map(|c| if c == '\\' { '/' } else { c })
        .collect();
    while s.ends_with('/') && s.len() > 1 {
        s.pop();
    }
    s
}

fn case_fold_key(path: &str) -> String {
    // Windows-style identity: case-insensitive path key for dedup.
    normalize_light(path).to_lowercase()
}
