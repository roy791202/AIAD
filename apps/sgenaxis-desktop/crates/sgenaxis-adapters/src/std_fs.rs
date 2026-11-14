//! Thin `std::fs` FileSystemPort — no extra crates.

use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

use sgenaxis_ports::{FileSystemPort, PortError};

/// Real-ish filesystem adapter via `std::fs`.
///
/// Atomic write: exclusively prepare an owned sibling, then rename over target.
/// Concurrent successful commits use last-commit-wins; no crash durability promise.
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

// Private transaction seams; production supplies a no-op checkpoint closure.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum WriteCheckpoint { TempCreated, BeforeWrite, BeforeSync, BeforeRename, BeforeCleanup }

fn temp_candidate(target: &Path) -> PathBuf {
    let mut name = target.as_os_str().to_owned();
    // Naming assistance only: exclusive creation below determines ownership.
    static NEXT_TEMP: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let sequence = NEXT_TEMP.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    name.push(format!(".sgenaxis-tmp-{}-{sequence}", std::process::id()));
    PathBuf::from(name)
}

fn write_atomic_with<C, H>(path: &str, contents: &[u8], mut candidate: C, mut checkpoint: H) -> Result<(), PortError>
where C: FnMut() -> PathBuf, H: FnMut(WriteCheckpoint, &Path) -> std::io::Result<()>,
{
    let target = Path::new(path);
    if let Some(parent) = target.parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent).map_err(|e| map_io(e, path))?;
        }
    }
    let mut prepared = None;
    for _ in 0..128 {
        let tmp = candidate();
        match fs::OpenOptions::new().write(true).create_new(true).open(&tmp) {
            Ok(file) => { prepared = Some((tmp, file)); break; }
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(error) => return Err(map_io(error, path)),
        }
    }
    let (tmp, file) = prepared.ok_or_else(|| PortError::AlreadyExists(path.into()))?;
    let result = (|| -> std::io::Result<()> {
        {
            // Keep the handle inside this scope so every early failure closes it
            // before outer cleanup, including on Windows.
            let mut file = file;
            checkpoint(WriteCheckpoint::TempCreated, &tmp)?;
            checkpoint(WriteCheckpoint::BeforeWrite, &tmp)?;
            file.write_all(contents)?;
            checkpoint(WriteCheckpoint::BeforeSync, &tmp)?;
            file.sync_all()?;
        }
        checkpoint(WriteCheckpoint::BeforeRename, &tmp)?;
        fs::rename(&tmp, target)
    })();
    result.map_err(|error| {
        if checkpoint(WriteCheckpoint::BeforeCleanup, &tmp).is_ok() {
            let _ = fs::remove_file(&tmp);
        }
        map_io(error, path)
    })?;
    Ok(())
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
        write_atomic_with(path, contents, || temp_candidate(Path::new(path)), |_, _| Ok(()))
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

#[cfg(test)]
#[path = "std_fs_tests.rs"]
mod std_fs_tests;
