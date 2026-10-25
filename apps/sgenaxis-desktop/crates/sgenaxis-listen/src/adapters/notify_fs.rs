//! Windows FS notify → [`crate::SourceEvent`] (PD-LISTEN-02).
//!
//! Real OS watcher is `#[cfg(windows)]` + feature `os-notify`. Fake path uses
//! [`crate::FakeFsSource`] via [`FsNotifySource`] so unit tests never need OS.

use std::path::Path;

use crate::fake::FakeFsSource;
use crate::source::SourceEvent;

/// Drainable FS notify source (fake or OS).
pub trait FsNotifySource: Send {
    /// Project root being watched (canonical display path).
    fn root(&self) -> &Path;

    /// Whether the watcher is still active.
    fn is_running(&self) -> bool;

    /// Drain pending notifications as listen [`SourceEvent`]s.
    fn drain(&mut self) -> Vec<SourceEvent>;

    /// Stop watching. After this, [`drain`] returns empty for new OS events;
    /// dropping the adapter must not leave a live OS watch handle.
    fn stop(&mut self);
}

/// Adapter／notify errors (path missing, OS watch failed, unsupported platform).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NotifyError {
    pub message: String,
}

impl NotifyError {
    pub fn new(msg: impl Into<String>) -> Self {
        Self {
            message: msg.into(),
        }
    }
}

impl std::fmt::Display for NotifyError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for NotifyError {}

impl FsNotifySource for FakeFsSource {
    fn root(&self) -> &Path {
        Path::new("(fake)")
    }

    fn is_running(&self) -> bool {
        true
    }

    fn drain(&mut self) -> Vec<SourceEvent> {
        FakeFsSource::drain(self)
    }

    fn stop(&mut self) {
        let _ = FakeFsSource::drain(self);
    }
}

/// Push all drained source events into an [`crate::EventBridge`].
pub fn pump_into_bridge(
    source: &mut dyn FsNotifySource,
    bridge: &mut crate::EventBridge,
) -> usize {
    let events = source.drain();
    let n = events.len();
    for ev in events {
        bridge.push(ev);
    }
    n
}

#[cfg(all(windows, feature = "os-notify"))]
mod win {
    use std::path::{Path, PathBuf};
    use std::sync::mpsc::{self, Receiver, TryRecvError};

    use notify::event::ModifyKind;
    use notify::{Config, Event, EventKind, RecommendedWatcher, RecursiveMode, Watcher};

    use super::{FsNotifySource, NotifyError};
    use crate::source::{FsChangeKind, SourceEvent};

    /// Windows FS watcher (ReadDirectoryChanges via `notify`) scoped to a project root.
    pub struct WinFsNotify {
        root: PathBuf,
        watcher: Option<RecommendedWatcher>,
        rx: Receiver<notify::Result<Event>>,
        running: bool,
    }

    impl WinFsNotify {
        /// Start a recursive watch on `root` (must exist and be a directory).
        pub fn watch(root: impl AsRef<Path>) -> Result<Self, NotifyError> {
            let root = root
                .as_ref()
                .canonicalize()
                .map_err(|e| NotifyError::new(format!("canonicalize root: {e}")))?;
            if !root.is_dir() {
                return Err(NotifyError::new(format!(
                    "root is not a directory: {}",
                    root.display()
                )));
            }

            let (tx, rx) = mpsc::channel();
            let mut watcher = RecommendedWatcher::new(
                move |res| {
                    let _ = tx.send(res);
                },
                Config::default(),
            )
            .map_err(|e| NotifyError::new(format!("create watcher: {e}")))?;

            watcher
                .watch(&root, RecursiveMode::Recursive)
                .map_err(|e| NotifyError::new(format!("watch {}: {e}", root.display())))?;

            Ok(Self {
                root,
                watcher: Some(watcher),
                rx,
                running: true,
            })
        }
    }

    impl FsNotifySource for WinFsNotify {
        fn root(&self) -> &Path {
            &self.root
        }

        fn is_running(&self) -> bool {
            self.running
        }

        fn drain(&mut self) -> Vec<SourceEvent> {
            let mut out = Vec::new();
            if !self.running && self.watcher.is_none() {
                // Still drain any leftover channel noise once stopped.
            }
            loop {
                match self.rx.try_recv() {
                    Ok(Ok(event)) => {
                        for ev in map_event(&self.root, event) {
                            out.push(ev);
                        }
                    }
                    Ok(Err(_)) => {
                        // OS notify error — skip; host may stop.
                    }
                    Err(TryRecvError::Empty) => break,
                    Err(TryRecvError::Disconnected) => {
                        self.running = false;
                        break;
                    }
                }
            }
            out
        }

        fn stop(&mut self) {
            if let Some(mut w) = self.watcher.take() {
                let _ = w.unwatch(&self.root);
            }
            self.running = false;
            // Drop any pending events so stop is a hard cut for new observation.
            while let Ok(_) = self.rx.try_recv() {}
        }
    }

    impl Drop for WinFsNotify {
        fn drop(&mut self) {
            self.stop();
        }
    }

    fn map_event(root: &Path, event: Event) -> Vec<SourceEvent> {
        let kind = map_kind(event.kind);
        let mut out = Vec::new();
        for path in event.paths {
            if !is_under_root(root, &path) {
                continue;
            }
            let display = path_to_string(&path);
            out.push(SourceEvent::fs(display, kind));
        }
        out
    }

    fn map_kind(kind: EventKind) -> FsChangeKind {
        match kind {
            EventKind::Create(_) => FsChangeKind::Create,
            EventKind::Modify(ModifyKind::Name(_)) => FsChangeKind::Rename,
            EventKind::Modify(_) => FsChangeKind::Modify,
            EventKind::Remove(_) => FsChangeKind::Remove,
            EventKind::Any | EventKind::Access(_) | EventKind::Other => FsChangeKind::Any,
        }
    }

    fn is_under_root(root: &Path, path: &Path) -> bool {
        if path.starts_with(root) {
            return true;
        }
        let root_s = root.to_string_lossy().replace('\\', "/").to_lowercase();
        let path_s = path.to_string_lossy().replace('\\', "/").to_lowercase();
        path_s.starts_with(&root_s)
    }

    fn path_to_string(path: &Path) -> String {
        path.to_string_lossy().replace('\\', "/")
    }
}

#[cfg(all(windows, feature = "os-notify"))]
pub use win::WinFsNotify;

/// Placeholder when OS notify is unavailable (non-Windows or feature off).
#[cfg(not(all(windows, feature = "os-notify")))]
pub struct WinFsNotify;

#[cfg(not(all(windows, feature = "os-notify")))]
impl WinFsNotify {
    /// Real Windows watcher is out of scope / feature-gated on this build.
    pub fn watch(_root: impl AsRef<Path>) -> Result<Self, NotifyError> {
        Err(NotifyError::new(
            "WinFsNotify requires Windows + feature os-notify (macOS/Linux watcher out of scope)",
        ))
    }
}
