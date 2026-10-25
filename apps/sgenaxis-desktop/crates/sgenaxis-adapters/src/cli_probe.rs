//! Probe PATH for known Agent CLIs (PD-LIVE-TARGET-01 / PD-LIVE-CLI-SMOKE-01).
//!
//! Returns an explicit absolute／found path suitable for [`crate::StdProcess`] spawn.
//! Prefers `.cmd`／`.exe` on Windows (not `.ps1`). Secrets are never involved.

use std::env;
use std::path::{Path, PathBuf};

/// Well-known Agent CLI names (PRODUCT-DEVELOPMENT §6.3 Provider A).
pub const AGENT_CLI_CANDIDATES: &[&str] = &["claude", "cursor-agent", "codex", "antigravity"];

/// One probed local CLI — path only; no tokens／secrets.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProbedCli {
    /// Canonical tool key (`claude`／`cursor-agent`／…).
    pub key: String,
    /// Absolute or PATH-resolved program path for spawn.
    pub path: PathBuf,
}

/// Walk `PATH` for the first existing Agent CLI program file.
///
/// On Windows, prefers `{name}.cmd` then `{name}.exe` then bare `{name}`; skips `.ps1`.
/// Returns `None` when none are found (callers treat as NOT RUN).
pub fn probe_agent_cli() -> Option<ProbedCli> {
    let path_var = env::var_os("PATH")?;
    let dirs: Vec<PathBuf> = env::split_paths(&path_var).collect();
    for key in AGENT_CLI_CANDIDATES {
        if let Some(path) = find_in_dirs(key, &dirs) {
            return Some(ProbedCli {
                key: (*key).to_string(),
                path,
            });
        }
    }
    None
}

/// Probe a single tool key (e.g. `"claude"`).
pub fn probe_named_cli(key: &str) -> Option<ProbedCli> {
    let path_var = env::var_os("PATH")?;
    let dirs: Vec<PathBuf> = env::split_paths(&path_var).collect();
    find_in_dirs(key, &dirs).map(|path| ProbedCli {
        key: key.to_string(),
        path,
    })
}

fn find_in_dirs(name: &str, dirs: &[PathBuf]) -> Option<PathBuf> {
    let candidates = windows_or_unix_names(name);
    for dir in dirs {
        for cand in &candidates {
            let p = dir.join(cand);
            if file_exists(&p) {
                return Some(p);
            }
        }
    }
    None
}

fn windows_or_unix_names(name: &str) -> Vec<String> {
    #[cfg(windows)]
    {
        // Prefer cmd／exe wrappers that `std::process::Command` can spawn directly.
        vec![
            format!("{name}.cmd"),
            format!("{name}.exe"),
            format!("{name}.bat"),
            name.to_string(),
        ]
    }
    #[cfg(not(windows))]
    {
        vec![name.to_string()]
    }
}

fn file_exists(p: &Path) -> bool {
    match std::fs::metadata(p) {
        Ok(m) => m.is_file(),
        Err(_) => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn candidate_list_covers_known_keys() {
        assert!(AGENT_CLI_CANDIDATES.contains(&"claude"));
        assert!(AGENT_CLI_CANDIDATES.contains(&"cursor-agent"));
        assert!(AGENT_CLI_CANDIDATES.contains(&"codex"));
    }

    #[test]
    fn probe_is_optional_without_panic() {
        // May be Some or None depending on host — must not panic.
        let _ = probe_agent_cli();
    }
}
