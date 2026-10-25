//! Thin `std::fs` FileSystemPort — no extra crates.

use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

use sgenaxis_ports::{FileSystemPort, PortError};

/// Real-ish filesystem adapter via `std::fs`.
///
/// Atomic write: write to `path.tmp.<pid>` then rename over target.
#[derive(Debug, Default, Clone, Copy)]
pub struct StdFileSystem;

impl StdFileSystem {
    pub fn new() -> Self {
        Self
    }
}

fn map_io(err: std::io::Error, path: &str) -> PortError {
    use std::io::ErrorKind;
    match err.kind() {
        ErrorKind::NotFound => PortError::NotFound(path.into()),
        ErrorKind::PermissionDenied => PortError::PermissionDenied(path.into()),
        ErrorKind::AlreadyExists => PortError::AlreadyExists(path.into()),
        _ => PortError::Io(format!("{path}: {err}")),
    }
}

impl FileSystemPort for StdFileSystem {
    fn exists(&self, path: &str) -> Result<bool, PortError> {
        Ok(Path::new(path).exists())
    }

    fn read_to_string(&self, path: &str) -> Result<String, PortError> {
        fs::read_to_string(path).map_err(|e| map_io(e, path))
    }

    fn read(&self, path: &str) -> Result<Vec<u8>, PortError> {
        fs::read(path).map_err(|e| map_io(e, path))
    }

    fn write_atomic(&self, path: &str, contents: &[u8]) -> Result<(), PortError> {
        let target = PathBuf::from(path);
        if let Some(parent) = target.parent() {
            if !parent.as_os_str().is_empty() {
                fs::create_dir_all(parent).map_err(|e| map_io(e, path))?;
            }
        }
        let mut tmp_os = target.as_os_str().to_owned();
        tmp_os.push(format!(".sgenaxis-tmp-{}", std::process::id()));
        let tmp = PathBuf::from(tmp_os);
        {
            let mut f = fs::File::create(&tmp).map_err(|e| map_io(e, path))?;
            f.write_all(contents).map_err(|e| map_io(e, path))?;
            f.sync_all().map_err(|e| map_io(e, path))?;
        }
        fs::rename(&tmp, &target).map_err(|e| {
            let _ = fs::remove_file(&tmp);
            map_io(e, path)
        })?;
        Ok(())
    }

    fn create_dir_all(&self, path: &str) -> Result<(), PortError> {
        fs::create_dir_all(path).map_err(|e| map_io(e, path))
    }

    fn is_file(&self, path: &str) -> Result<bool, PortError> {
        Ok(Path::new(path).is_file())
    }

    fn remove_file(&self, path: &str) -> Result<(), PortError> {
        fs::remove_file(path).map_err(|e| map_io(e, path))
    }
}
