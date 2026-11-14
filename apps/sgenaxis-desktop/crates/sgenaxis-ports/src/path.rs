//! Path / XDG-style convention Port — returns strings, not OS path types.

use crate::PortError;

/// Config / cache / project convention directories and path helpers.
///
/// Implementations may consult env vars (`LOCALAPPDATA`, `HOME`, …) internally;
/// callers only see `String` paths.
pub trait PathPort: Send + Sync {
    /// App config directory (e.g. `%LOCALAPPDATA%\SGenAxis` on Windows).
    fn config_dir(&self, app_name: &str) -> Result<String, PortError>;

    /// App cache directory.
    fn cache_dir(&self, app_name: &str) -> Result<String, PortError>;

    /// Join `base` with `parts` using this platform's separator semantics.
    fn join(&self, base: &str, parts: &[&str]) -> String;

    /// Light normalize (collapse `/` vs `\`, trim trailing sep) without resolving symlinks.
    fn normalize(&self, path: &str) -> String;
}
