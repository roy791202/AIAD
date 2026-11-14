//! SGenAxis **listen bridge** (PD-LISTEN-01 / PD-LISTEN-02 / PD-LISTEN-RECON-01).
//!
//! ```text
//! Fake／Win FS notify · Git watch · AgentChunk pipe｜MCP
//!   → SourceEvent
//!   → EventBridge (debounce; terminal Agent flush + recon)
//!   → DomainEvent → DirtySet／ListenProjection／Engine indicator tasks
//! UI ← Engine::subscribe / ListenProjection only  (never OS)
//! ```
//!
//! PD-LISTEN-02: Windows [`adapters::notify_fs::WinFsNotify`] → EventBridge.
//! Fake path remains via [`FakeFsSource`]. macOS／Linux watcher out of scope.
//!
//! PD-LISTEN-RECON-01: abnormal Agent end → [`DomainEvent::AgentReconcile`];
//! projection mirrors EXEC [`sgenaxis_exec::ExitClassification`]; last Chunk
//! retained; ended runs are not re-ingested.

#![forbid(unsafe_code)]

pub mod adapters;
mod bridge;
mod clock;
mod domain;
mod fake;
mod projection;
mod recon;
mod source;

pub use adapters::notify_fs::{pump_into_bridge, FsNotifySource, NotifyError};
pub use bridge::EventBridge;
pub use clock::{Clock, FakeClock, SystemClock};
pub use domain::{AgentEventKind, DomainEvent};
pub use fake::{FakeAgentSource, FakeFsSource, FakeGitSource};
pub use projection::ListenProjection;
pub use recon::{classification_label, needs_reconcile};
pub use source::{DebounceKey, FsChange, FsChangeKind, GitChange, SourceEvent};

#[cfg(all(windows, feature = "os-notify"))]
pub use adapters::notify_fs::WinFsNotify;

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_core::{DirtySet, Engine};
    use sgenaxis_exec::{
        AgentChunk, AgentProvider, ExitClassification, OutputStream, RunId,
    };
    use std::sync::{Arc, Mutex};
    use std::time::Duration;

    fn bridge_with_fake(window_ms: u64) -> (EventBridge, FakeClock) {
        let clock = FakeClock::new();
        let bridge = EventBridge::with_clock(
            Duration::from_millis(window_ms),
            Box::new(clock.clone()),
        );
        (bridge, clock)
    }

    #[test]
    fn fs_burst_debounces_to_one_domain_event() {
        let (mut bridge, clock) = bridge_with_fake(30);
        let mut fs = FakeFsSource::new();
        fs.emit_burst("/proj/a.rs", FsChangeKind::Modify, 5);

        for ev in fs.drain() {
            bridge.push(ev);
        }
        assert_eq!(bridge.pending_count(), 1);
        assert!(bridge.tick().is_empty(), "inside window → no flush");

        clock.advance(Duration::from_millis(30));
        let out = bridge.tick();
        assert_eq!(out.len(), 1);
        match &out[0] {
            DomainEvent::FsDirty {
                path,
                kind,
                burst_count,
            } => {
                assert_eq!(path, "/proj/a.rs");
                assert_eq!(*kind, FsChangeKind::Modify);
                assert_eq!(*burst_count, 5);
            }
            other => panic!("expected FsDirty, got {other:?}"),
        }
        assert_eq!(bridge.pending_count(), 0);
    }

    #[test]
    fn distinct_fs_paths_stay_separate_after_debounce() {
        let (mut bridge, clock) = bridge_with_fake(10);
        bridge.push(SourceEvent::fs("/a", FsChangeKind::Create));
        bridge.push(SourceEvent::fs("/b", FsChangeKind::Remove));
        clock.advance(Duration::from_millis(10));
        let out = bridge.tick();
        assert_eq!(out.len(), 2);
        let paths: Vec<_> = out
            .iter()
            .filter_map(|e| match e {
                DomainEvent::FsDirty { path, .. } => Some(path.as_str()),
                _ => None,
            })
            .collect();
        assert!(paths.contains(&"/a"));
        assert!(paths.contains(&"/b"));
    }

    #[test]
    fn git_burst_debounces_and_marks_dirty() {
        let (mut bridge, clock) = bridge_with_fake(20);
        let mut git = FakeGitSource::new();
        git.emit_burst("/repo", "status", 3);
        for ev in git.drain() {
            bridge.push(ev);
        }
        clock.advance(Duration::from_millis(20));

        let mut dirty = DirtySet::new();
        let mut proj = ListenProjection::new();
        let events = bridge.drain_into(&mut dirty, &mut proj);

        assert_eq!(events.len(), 1);
        assert!(matches!(
            &events[0],
            DomainEvent::GitDirty {
                repo_root,
                burst_count: 3,
                ..
            } if repo_root == "/repo"
        ));
        assert!(dirty.is_projection_dirty());
        assert!(dirty.is_property_dirty(&events[0].property_id()));
        assert_eq!(proj.last_git_root.as_deref(), Some("/repo"));
        assert_eq!(proj.last_git_burst, 3);
        assert_eq!(proj.generation, 1);
    }

    #[test]
    fn agent_chunks_debounce_by_run_id() {
        let (mut bridge, _clock) = bridge_with_fake(15);
        let mut agent = FakeAgentSource::new();
        let run = RunId(42);
        agent.emit_run_lifecycle(run, true);
        for ev in agent.drain() {
            bridge.push(ev);
        }
        // Exited is terminal → immediate flush on next tick (no clock wait).
        assert_eq!(bridge.pending_count(), 1);
        let out = bridge.tick();
        // Success end: retained Chunk + Exited (no AgentReconcile).
        assert!(
            out.iter().any(|e| matches!(
                e,
                DomainEvent::AgentDirty {
                    last_kind: AgentEventKind::Chunk,
                    ..
                }
            )),
            "last chunk must be retained: {out:?}"
        );
        assert!(
            out.iter().any(|e| matches!(
                e,
                DomainEvent::AgentDirty {
                    run_id: r,
                    last_kind: AgentEventKind::Exited,
                    burst_count: 4,
                    classification: Some(ExitClassification::Success),
                } if *r == run
            )),
            "expected Exited Success: {out:?}"
        );
        assert!(
            !out.iter()
                .any(|e| matches!(e, DomainEvent::AgentReconcile { .. })),
            "Success must not emit reconcile"
        );
        assert!(bridge.is_run_ended(run));
    }

    #[test]
    fn two_runs_produce_two_agent_domain_events() {
        let (mut bridge, clock) = bridge_with_fake(5);
        bridge.push(SourceEvent::agent(AgentChunk::Chunk {
            run_id: RunId(1),
            stream: OutputStream::Stdout,
            text: "a".into(),
        }));
        bridge.push(SourceEvent::agent(AgentChunk::Chunk {
            run_id: RunId(2),
            stream: OutputStream::Stderr,
            text: "b".into(),
        }));
        clock.advance(Duration::from_millis(5));
        let out = bridge.tick();
        assert_eq!(out.len(), 2);
    }

    #[test]
    fn drain_into_engine_updates_projection_for_ui_subscribe() {
        let (mut bridge, clock) = bridge_with_fake(10);
        let mut engine = Engine::new();
        let seen = Arc::new(Mutex::new(Vec::new()));
        let seen_c = Arc::clone(&seen);
        engine.subscribe(move |p| {
            seen_c.lock().unwrap().push(p.yellow);
        });

        bridge.push(SourceEvent::fs("/x", FsChangeKind::Modify));
        clock.advance(Duration::from_millis(10));
        let events = bridge.drain_into_engine(&mut engine);
        assert_eq!(events.len(), 1);

        let snap = engine.snapshot();
        assert!(snap.yellow >= 1, "listen-fs indicator should be yellow");
        assert!(snap.titles.iter().any(|t| t == "FS listen"));
        let history = seen.lock().unwrap().clone();
        assert!(
            !history.is_empty(),
            "UI subscribe must observe projection; not OS"
        );
        assert!(engine.dirty_set().is_empty());
    }

    #[test]
    fn mixed_fs_git_agent_flush_together_after_window() {
        let (mut bridge, clock) = bridge_with_fake(25);
        bridge.push(SourceEvent::fs("/f", FsChangeKind::Any));
        bridge.push(SourceEvent::git("/g", "head"));
        bridge.push(SourceEvent::agent(AgentChunk::Started {
            run_id: RunId(7),
            provider: AgentProvider::Mcp,
            dry_run: true,
            tool: None,
        }));
        assert!(bridge.tick().is_empty());
        clock.advance(Duration::from_millis(25));
        let out = bridge.tick();
        assert_eq!(out.len(), 3);
        assert!(out.iter().any(|e| matches!(e, DomainEvent::FsDirty { .. })));
        assert!(out.iter().any(|e| matches!(e, DomainEvent::GitDirty { .. })));
        assert!(out
            .iter()
            .any(|e| matches!(e, DomainEvent::AgentDirty { .. })));
    }

    #[test]
    fn path_normalization_coalesces_slash_variants() {
        let (mut bridge, clock) = bridge_with_fake(5);
        bridge.push(SourceEvent::fs(r"C:\proj\a", FsChangeKind::Modify));
        bridge.push(SourceEvent::fs("C:/proj/a", FsChangeKind::Modify));
        clock.advance(Duration::from_millis(5));
        let out = bridge.tick();
        assert_eq!(out.len(), 1);
        assert_eq!(
            match &out[0] {
                DomainEvent::FsDirty { burst_count, .. } => *burst_count,
                _ => 0,
            },
            2
        );
    }

    #[test]
    fn failed_agent_chunk_maps_kind() {
        let (mut bridge, _clock) = bridge_with_fake(1);
        bridge.push(SourceEvent::agent(AgentChunk::Failed {
            run_id: RunId(9),
            message: "boom".into(),
        }));
        let out = bridge.tick();
        assert!(
            out.iter().any(|e| matches!(
                e,
                DomainEvent::AgentDirty {
                    last_kind: AgentEventKind::Failed,
                    classification: Some(ExitClassification::Failure),
                    ..
                }
            )),
            "{out:?}"
        );
        assert!(
            out.iter().any(|e| matches!(
                e,
                DomainEvent::AgentReconcile {
                    classification: ExitClassification::Failure,
                    ..
                }
            )),
            "Failed → reconcile: {out:?}"
        );
    }

    /// BDD-PD-LISTEN-RECON-01: crash → reconcile; projection = EXEC class; last chunk kept; no re-dispatch.
    #[test]
    fn crash_emits_reconcile_keeps_last_chunk_blocks_redispatch() {
        let (mut bridge, _clock) = bridge_with_fake(50);
        let run = RunId(77);
        bridge.push(SourceEvent::agent(AgentChunk::Started {
            run_id: run,
            provider: AgentProvider::Cli,
            dry_run: false,
            tool: None,
        }));
        bridge.push(SourceEvent::agent(AgentChunk::Chunk {
            run_id: run,
            stream: OutputStream::Stdout,
            text: "final-line".into(),
        }));
        bridge.push(SourceEvent::agent(AgentChunk::Exited {
            run_id: run,
            classification: ExitClassification::Crashed,
            exit_code: Some(-9),
        }));

        let mut dirty = DirtySet::new();
        let mut proj = ListenProjection::new();
        let events = bridge.drain_into(&mut dirty, &mut proj);

        assert!(
            events.iter().any(|e| matches!(
                e,
                DomainEvent::AgentDirty {
                    last_kind: AgentEventKind::Chunk,
                    ..
                }
            )),
            "不丟最後 chunk: {events:?}"
        );
        assert!(
            events.iter().any(|e| matches!(
                e,
                DomainEvent::AgentDirty {
                    last_kind: AgentEventKind::Exited,
                    classification: Some(ExitClassification::Crashed),
                    ..
                }
            )),
            "投影／事件與 EXEC Crashed 一致: {events:?}"
        );
        assert!(
            events.iter().any(|e| matches!(
                e,
                DomainEvent::AgentReconcile {
                    classification: ExitClassification::Crashed,
                    exit_code: Some(-9),
                    last_chunk_retained: true,
                    ..
                }
            )),
            "異常結束 → 對帳事件: {events:?}"
        );

        assert_eq!(proj.last_agent_classification.as_deref(), Some("crashed"));
        assert_eq!(proj.last_agent_exit_code, Some(-9));
        assert!(proj.pending_reconcile);
        assert!(proj.is_run_ended(run));
        assert!(dirty.is_projection_dirty());

        // 不重複派發已結束 Run
        let accepted = bridge.push(SourceEvent::agent(AgentChunk::Chunk {
            run_id: run,
            stream: OutputStream::Stdout,
            text: "late".into(),
        }));
        assert!(!accepted);
        assert!(bridge.tick().is_empty());
        assert!(!bridge.push(SourceEvent::agent(AgentChunk::Started {
            run_id: run,
            provider: AgentProvider::Cli,
            dry_run: true,
            tool: None,
        })));
    }

    #[test]
    fn cancelled_exit_reconciles_with_exec_class() {
        let (mut bridge, _clock) = bridge_with_fake(10);
        let run = RunId(3);
        bridge.push(SourceEvent::agent(AgentChunk::Exited {
            run_id: run,
            classification: ExitClassification::Cancelled,
            exit_code: Some(-1),
        }));
        let mut dirty = DirtySet::new();
        let mut proj = ListenProjection::new();
        let events = bridge.drain_into(&mut dirty, &mut proj);
        assert!(events.iter().any(|e| matches!(
            e,
            DomainEvent::AgentReconcile {
                classification: ExitClassification::Cancelled,
                exit_code: Some(-1),
                ..
            }
        )));
        assert_eq!(proj.last_agent_classification.as_deref(), Some("cancelled"));
        assert_eq!(
            classification_label(ExitClassification::Cancelled),
            "cancelled"
        );
    }

    #[test]
    fn success_exit_no_reconcile_still_marks_ended() {
        let (mut bridge, _clock) = bridge_with_fake(10);
        let run = RunId(5);
        bridge.push(SourceEvent::agent(AgentChunk::Exited {
            run_id: run,
            classification: ExitClassification::Success,
            exit_code: Some(0),
        }));
        let out = bridge.tick();
        assert!(!out
            .iter()
            .any(|e| matches!(e, DomainEvent::AgentReconcile { .. })));
        assert!(bridge.is_run_ended(run));
        assert_eq!(
            needs_reconcile(ExitClassification::Success),
            false
        );
    }

    /// BDD-PD-LISTEN-02: fake path still testable via [`FsNotifySource`].
    #[test]
    fn fake_fs_notify_source_pumps_into_bridge_and_dirty() {
        let (mut bridge, clock) = bridge_with_fake(10);
        let mut fs = FakeFsSource::new();
        fs.emit_burst("/proj/root/a.txt", FsChangeKind::Modify, 3);

        let n = pump_into_bridge(&mut fs as &mut dyn FsNotifySource, &mut bridge);
        assert_eq!(n, 3);
        assert_eq!(bridge.pending_count(), 1);

        clock.advance(Duration::from_millis(10));
        let mut dirty = DirtySet::new();
        let mut proj = ListenProjection::new();
        let events = bridge.drain_into(&mut dirty, &mut proj);
        assert_eq!(events.len(), 1);
        assert!(dirty.is_projection_dirty());
        assert!(matches!(
            &events[0],
            DomainEvent::FsDirty {
                burst_count: 3,
                ..
            }
        ));
    }

    #[test]
    fn fake_fs_notify_stop_drains_queue() {
        let mut fs = FakeFsSource::new();
        fs.emit("/x", FsChangeKind::Create);
        fs.stop();
        assert!(fs.drain().is_empty());
    }
}

#[cfg(all(test, windows, feature = "os-notify"))]
mod win_notify_tests {
    use super::*;
    use crate::adapters::notify_fs::WinFsNotify;
    use sgenaxis_core::DirtySet;
    use std::fs;
    use std::path::PathBuf;
    use std::thread;
    use std::time::{Duration, Instant};

    fn temp_project_root() -> PathBuf {
        let base = std::env::temp_dir().join(format!(
            "sgenaxis-listen02-{}-{}",
            std::process::id(),
            Instant::now().elapsed().as_nanos()
        ));
        fs::create_dir_all(&base).expect("temp root");
        base
    }

    fn wait_for_events(source: &mut WinFsNotify, timeout: Duration) -> Vec<SourceEvent> {
        let deadline = Instant::now() + timeout;
        let mut all = Vec::new();
        while Instant::now() < deadline {
            all.extend(source.drain());
            if !all.is_empty() {
                return all;
            }
            thread::sleep(Duration::from_millis(15));
        }
        all.extend(source.drain());
        all
    }

    /// BDD-PD-LISTEN-02: 專案 root 內檔案變更經 debounce 進 Dirty（真 OS）.
    #[test]
    fn win_fs_notify_change_debounces_into_dirty() {
        let root = temp_project_root();
        let mut watcher = WinFsNotify::watch(&root).expect("start win watch");
        assert!(watcher.is_running());

        let target = root.join("listen02.txt");
        fs::write(&target, b"hello").expect("write file");

        let raw = wait_for_events(&mut watcher, Duration::from_secs(2));
        assert!(
            !raw.is_empty(),
            "expected at least one OS notify for {}",
            target.display()
        );

        let mut bridge = EventBridge::new(Duration::from_millis(40));
        for ev in raw {
            bridge.push(ev);
        }
        assert!(bridge.pending_count() >= 1);

        thread::sleep(Duration::from_millis(60));
        let mut dirty = DirtySet::new();
        let mut proj = ListenProjection::new();
        let events = bridge.drain_into(&mut dirty, &mut proj);
        assert!(
            !events.is_empty(),
            "debounce window elapsed → DomainEvent／Dirty"
        );
        assert!(dirty.is_projection_dirty());
        assert!(events.iter().any(|e| matches!(e, DomainEvent::FsDirty { .. })));
        assert_eq!(proj.generation, 1);

        watcher.stop();
        assert!(!watcher.is_running());
        let _ = fs::remove_dir_all(&root);
    }

    /// BDD-PD-LISTEN-02: 停止 watch 無洩漏（無殘留 OS handle／停後不進 Dirty）.
    #[test]
    fn win_fs_notify_stop_clears_watch_no_further_dirty() {
        let root = temp_project_root();
        let mut watcher = WinFsNotify::watch(&root).expect("start win watch");
        watcher.stop();
        assert!(!watcher.is_running());

        // After stop, new writes must not surface as SourceEvents.
        fs::write(root.join("after-stop.txt"), b"nope").expect("write after stop");
        thread::sleep(Duration::from_millis(200));
        let leftover = watcher.drain();
        assert!(
            leftover.is_empty(),
            "stopped watcher must not emit new events: {leftover:?}"
        );

        let mut bridge = EventBridge::new(Duration::from_millis(20));
        let n = pump_into_bridge(&mut watcher as &mut dyn FsNotifySource, &mut bridge);
        assert_eq!(n, 0);
        thread::sleep(Duration::from_millis(40));
        assert!(bridge.tick().is_empty());

        // Drop must be quiet (no double-free / hang).
        drop(watcher);
        let _ = fs::remove_dir_all(&root);
    }
}
