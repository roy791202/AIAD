//! Thin PathPort using env conventions — Windows `LOCALAPPDATA` / Unix home+XDG.
//!
//! No extra crates (`dirs`, `directories`, …). Suitable for Win-first stub.

use std::path::{Component, Path, PathBuf};

use sgenaxis_ports::{PathPort, PortError};

/// Platform path conventions via `std::env` + `std::path`.
#[derive(Debug, Default, Clone, Copy)]
pub struct StdPath;

impl StdPath {
    pub fn new() -> Self {
        Self
    }
}

fn home_dir() -> Result<PathBuf, PortError> {
    if let Ok(h) = std::env::var("HOME") {
        if !h.is_empty() {
            return Ok(PathBuf::from(h));
        }
    }
    // Windows often has USERPROFILE when HOME is unset.
    if let Ok(h) = std::env::var("USERPROFILE") {
        if !h.is_empty() {
            return Ok(PathBuf::from(h));
        }
    }
    Err(PortError::Other(
        "HOME / USERPROFILE not set; cannot resolve user dirs".into(),
    ))
}

impl PathPort for StdPath {
    fn config_dir(&self, app_name: &str) -> Result<String, PortError> {
        #[cfg(windows)]
        {
            if let Ok(local) = std::env::var("LOCALAPPDATA") {
                if !local.is_empty() {
                    return Ok(self.join(&local, &[app_name]));
                }
            }
            // Fallback: %USERPROFILE%\AppData\Local\<app>
            let home = home_dir()?;
            let s = home.to_string_lossy();
            return Ok(self.join(&s, &["AppData", "Local", app_name]));
        }
        #[cfg(not(windows))]
        {
            if let Ok(xdg) = std::env::var("XDG_CONFIG_HOME") {
                if !xdg.is_empty() {
                    return Ok(self.join(&xdg, &[app_name]));
                }
            }
            let home = home_dir()?;
            let s = home.to_string_lossy();
            Ok(self.join(&s, &[".config", app_name]))
        }
    }

    fn cache_dir(&self, app_name: &str) -> Result<String, PortError> {
        #[cfg(windows)]
        {
            if let Ok(local) = std::env::var("LOCALAPPDATA") {
                if !local.is_empty() {
                    return Ok(self.join(&local, &[app_name, "Cache"]));
                }
            }
            let home = home_dir()?;
            let s = home.to_string_lossy();
            return Ok(self.join(&s, &["AppData", "Local", app_name, "Cache"]));
        }
        #[cfg(not(windows))]
        {
            if let Ok(xdg) = std::env::var("XDG_CACHE_HOME") {
                if !xdg.is_empty() {
                    return Ok(self.join(&xdg, &[app_name]));
                }
            }
            let home = home_dir()?;
            let s = home.to_string_lossy();
            Ok(self.join(&s, &[".cache", app_name]))
        }
    }

    fn join(&self, base: &str, parts: &[&str]) -> String {
        let mut buf = PathBuf::from(base);
        for p in parts {
            for c in Path::new(p).components() {
                match c {
                    Component::CurDir => {}
                    Component::ParentDir => {
                        buf.pop();
                    }
                    other => buf.push(other.as_os_str()),
                }
            }
        }
        buf.to_string_lossy().into_owned()
    }

    fn normalize(&self, path: &str) -> String {
        let p = PathBuf::from(path);
        let mut out = PathBuf::new();
        for c in p.components() {
            match c {
                Component::CurDir => {}
                Component::ParentDir => {
                    out.pop();
                }
                other => out.push(other.as_os_str()),
            }
        }
        out.to_string_lossy().into_owned()
    }
}
