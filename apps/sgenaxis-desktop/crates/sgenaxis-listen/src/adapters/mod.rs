//! FS notify adapters that produce [`crate::SourceEvent`] for [`crate::EventBridge`].
//!
//! - [`FakeFsSource`](crate::FakeFsSource) — in-memory (always available)
//! - [`notify_fs::WinFsNotify`] — real Windows FS watcher (PD-LISTEN-02)
//!
//! macOS／Linux watchers are **out of scope** for this card.

pub mod notify_fs;

pub use notify_fs::{FsNotifySource, NotifyError};
