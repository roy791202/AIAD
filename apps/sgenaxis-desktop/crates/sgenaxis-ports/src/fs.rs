//! File system Port — path strings only (no `PathBuf` / `File` in the API).

use crate::PortError;

/// Read / write / existence over opaque path strings.
///
/// Object-safe so hosts can swap `FakeFileSystem` ↔ `StdFileSystem` behind
/// `Box<dyn FileSystemPort>`.
pub trait FileSystemPort: Send + Sync {
    /// Whether `path` exists (file or directory).
    fn exists(&self, path: &str) -> Result<bool, PortError>;

    /// Read entire file as UTF-8 text.
    fn read_to_string(&self, path: &str) -> Result<String, PortError>;

    /// Read entire file as bytes.
    fn read(&self, path: &str) -> Result<Vec<u8>, PortError>;

    /// Write bytes; prefer atomic replace when the adapter can.
    fn write_atomic(&self, path: &str, contents: &[u8]) -> Result<(), PortError>;

    /// Create directory and parents if missing.
    fn create_dir_all(&self, path: &str) -> Result<(), PortError>;

    /// Whether `path` exists and is a regular file (not a directory).
    fn is_file(&self, path: &str) -> Result<bool, PortError>;

    /// Remove a regular file. Missing path → [`PortError::NotFound`].
    fn remove_file(&self, path: &str) -> Result<(), PortError>;
}
