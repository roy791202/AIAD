//! CliAgentAdapter — Provider A (CLI) via ProcessPort; DryRun first, live under approval.

use std::collections::VecDeque;

use sgenaxis_ports::{ProcessId, ProcessPort};

use crate::error::ExecError;
use crate::events::{AgentChunk, ExitClassification, OutputStream};
use crate::port::{AgentPort, AgentProvider, RunId, StartRunRequest};
use crate::settings::{CliAgentSettings, CliToolKind};

#[derive(Debug)]
enum RunPhase {
    /// DryRun: events already queued; cancel may rewrite terminal event.
    DryRun { finished: bool },
    /// Real spawn (feature `real-spawn` + approved settings): ProcessPort.
    #[cfg_attr(not(feature = "real-spawn"), allow(dead_code))]
    Live {
        process_id: ProcessId,
        finished: bool,
    },
}

struct ActiveRun {
    run_id: RunId,
    phase: RunPhase,
    queue: VecDeque<AgentChunk>,
    #[allow(dead_code)]
    tool: CliToolKind,
}

impl ActiveRun {
    fn is_finished(&self) -> bool {
        match &self.phase {
            RunPhase::DryRun { finished } => *finished,
            RunPhase::Live { finished, .. } => *finished,
        }
    }
}

/// Agent Provider A: local CLI via [`ProcessPort`].
///
/// - **DryRun** (default tests): emits started → chunk → progress → exited without spawn.
/// - **Live**: feature `real-spawn` + [`CliAgentSettings::live_approved`]; streams
///   stdout／stderr via `try_read` into [`AgentChunk::Chunk`]; exit code via `try_wait`.
pub struct CliAgentAdapter {
    settings: CliAgentSettings,
    process: Box<dyn ProcessPort>,
    next_run: u64,
    /// First-wave product rule: single in-flight Agent.
    active: Option<ActiveRun>,
}

impl CliAgentAdapter {
    pub fn new(settings: CliAgentSettings, process: Box<dyn ProcessPort>) -> Self {
        Self {
            settings,
            process,
            next_run: 1,
            active: None,
        }
    }

    pub fn with_defaults(process: Box<dyn ProcessPort>) -> Self {
        Self::new(CliAgentSettings::defaults(), process)
    }

    pub fn settings(&self) -> &CliAgentSettings {
        &self.settings
    }

    pub fn settings_mut(&mut self) -> &mut CliAgentSettings {
        &mut self.settings
    }

    /// Replace CLI settings (host wiring mirrors `agent_active` → `live_approved`).
    pub fn apply_settings(&mut self, settings: CliAgentSettings) {
        self.settings = settings;
    }

    /// True while a run is in flight or still has undrained events (single-agent gate).
    pub fn is_busy(&self) -> bool {
        match &self.active {
            Some(run) => !run.is_finished() || !run.queue.is_empty(),
            None => false,
        }
    }

    fn alloc_run_id(&mut self) -> RunId {
        let id = self.next_run;
        self.next_run = self.next_run.saturating_add(1);
        RunId(id)
    }

    fn ensure_idle(&self) -> Result<(), ExecError> {
        if let Some(run) = &self.active {
            if !run.is_finished() || !run.queue.is_empty() {
                return Err(ExecError::Busy(format!(
                    "run {} still active; only one in-flight Agent allowed (PD-EXEC-SINGLE-01); finish or cancel first",
                    run.run_id.0
                )));
            }
        }
        Ok(())
    }

    fn enqueue_dry_run(run_id: RunId, tool: CliToolKind) -> VecDeque<AgentChunk> {
        let key = tool.config_key();
        let mut q = VecDeque::new();
        q.push_back(AgentChunk::Started {
            run_id,
            provider: AgentProvider::Cli,
            dry_run: true,
            tool: Some(tool),
        });
        q.push_back(AgentChunk::Chunk {
            run_id,
            stream: OutputStream::Stdout,
            text: format!("[dry-run] simulated stdout from {key}"),
        });
        q.push_back(AgentChunk::Progress {
            run_id,
            message: format!("[dry-run] {key} progress"),
        });
        q.push_back(AgentChunk::Exited {
            run_id,
            classification: ExitClassification::Success,
            exit_code: Some(0),
        });
        q
    }

    #[cfg(feature = "real-spawn")]
    fn start_live(&mut self, run_id: RunId, req: &StartRunRequest) -> Result<ActiveRun, ExecError> {
        if !self.settings.live_approved {
            return Err(ExecError::LiveNotApproved);
        }
        let tool = self.settings.selected;
        let cfg = self.settings.selected_config().clone();
        let arg_refs: Vec<&str> = cfg.args.iter().map(String::as_str).collect();
        let cwd = Some(req.project_root.as_str());
        let process_id = self
            .process
            .start(&cfg.path, &arg_refs, cwd)
            .map_err(|e| ExecError::Process(e.to_string()))?;

        let mut queue = VecDeque::new();
        queue.push_back(AgentChunk::Started {
            run_id,
            provider: AgentProvider::Cli,
            dry_run: false,
            tool: Some(tool),
        });
        queue.push_back(AgentChunk::Progress {
            run_id,
            message: format!(
                "[live] spawned {} ({})",
                tool.config_key(),
                cfg.path
            ),
        });

        Ok(ActiveRun {
            run_id,
            phase: RunPhase::Live {
                process_id,
                finished: false,
            },
            queue,
            tool,
        })
    }

    #[cfg(not(feature = "real-spawn"))]
    fn start_live(
        &mut self,
        _run_id: RunId,
        _req: &StartRunRequest,
    ) -> Result<ActiveRun, ExecError> {
        let _ = &self.process;
        if !self.settings.live_approved {
            return Err(ExecError::LiveNotApproved);
        }
        Err(ExecError::RealSpawnDisabled)
    }

    fn drain_process_output(
        process: &mut dyn ProcessPort,
        process_id: ProcessId,
        run_id: RunId,
        queue: &mut VecDeque<AgentChunk>,
    ) -> Result<(), ExecError> {
        let out = process
            .try_read(process_id)
            .map_err(|e| ExecError::Process(e.to_string()))?;
        if !out.stdout.is_empty() {
            queue.push_back(AgentChunk::Chunk {
                run_id,
                stream: OutputStream::Stdout,
                text: out.stdout,
            });
        }
        if !out.stderr.is_empty() {
            queue.push_back(AgentChunk::Chunk {
                run_id,
                stream: OutputStream::Stderr,
                text: out.stderr,
            });
        }
        Ok(())
    }

    fn poll_live_if_needed(process: &mut dyn ProcessPort, run: &mut ActiveRun) -> Result<(), ExecError> {
        let RunPhase::Live {
            process_id,
            finished,
        } = &mut run.phase
        else {
            return Ok(());
        };
        if *finished {
            return Ok(());
        }

        let pid = *process_id;
        let run_id = run.run_id;
        Self::drain_process_output(process, pid, run_id, &mut run.queue)?;

        match process
            .try_wait(pid)
            .map_err(|e| ExecError::Process(e.to_string()))?
        {
            None => Ok(()),
            Some(code) => {
                // Final drain after exit so late pipe bytes become Chunks before Exited.
                Self::drain_process_output(process, pid, run_id, &mut run.queue)?;
                *finished = true;
                run.queue.push_back(AgentChunk::Exited {
                    run_id,
                    classification: ExitClassification::from_exit_code(code),
                    exit_code: Some(code),
                });
                Ok(())
            }
        }
    }
}

impl AgentPort for CliAgentAdapter {
    fn start_run(&mut self, req: StartRunRequest) -> Result<RunId, ExecError> {
        let _binding = crate::bind::require_run_binding(&req)?;
        match req.provider {
            AgentProvider::Cli => {}
            AgentProvider::Mcp => {
                return Err(ExecError::UnsupportedProvider(
                    "Mcp is PD-EXEC-MCP; use Cli here".into(),
                ));
            }
        }

        self.ensure_idle()?;
        if let Some(run) = &self.active {
            if run.is_finished() && run.queue.is_empty() {
                self.active = None;
            }
        }

        let run_id = self.alloc_run_id();
        let tool = self.settings.selected;

        let active = if req.dry_run {
            ActiveRun {
                run_id,
                phase: RunPhase::DryRun { finished: true },
                queue: Self::enqueue_dry_run(run_id, tool),
                tool,
            }
        } else {
            self.start_live(run_id, &req)?
        };

        self.active = Some(active);
        Ok(run_id)
    }

    fn poll_chunks(&mut self, run: RunId) -> Result<Vec<AgentChunk>, ExecError> {
        {
            let Some(active) = &self.active else {
                return Err(ExecError::RunNotFound(format!("{}", run.0)));
            };
            if active.run_id != run {
                return Err(ExecError::RunNotFound(format!("{}", run.0)));
            }
        }

        let Self { process, active, .. } = self;
        let active = active
            .as_mut()
            .ok_or_else(|| ExecError::RunNotFound(format!("{}", run.0)))?;

        Self::poll_live_if_needed(process.as_mut(), active)?;

        let mut out = Vec::new();
        while let Some(ev) = active.queue.pop_front() {
            out.push(ev);
        }
        Ok(out)
    }

    fn cancel(&mut self, run: RunId) -> Result<(), ExecError> {
        let live_pid = {
            let Some(active) = self.active.as_mut() else {
                return Err(ExecError::RunNotFound(format!("{}", run.0)));
            };
            if active.run_id != run {
                return Err(ExecError::RunNotFound(format!("{}", run.0)));
            }

            match &mut active.phase {
                RunPhase::DryRun { finished } => {
                    active
                        .queue
                        .retain(|e| matches!(e, AgentChunk::Started { .. }));
                    active.queue.push_back(AgentChunk::Exited {
                        run_id: run,
                        classification: ExitClassification::Cancelled,
                        exit_code: Some(-1),
                    });
                    *finished = true;
                    None
                }
                RunPhase::Live {
                    process_id,
                    finished,
                } => {
                    if *finished {
                        None
                    } else {
                        Some(*process_id)
                    }
                }
            }
        };

        if let Some(pid) = live_pid {
            self.process
                .cancel(pid)
                .map_err(|e| ExecError::Process(e.to_string()))?;
            if let Some(active) = self.active.as_mut() {
                if let RunPhase::Live { finished, .. } = &mut active.phase {
                    *finished = true;
                }
                active.queue.push_back(AgentChunk::Exited {
                    run_id: run,
                    classification: ExitClassification::Cancelled,
                    exit_code: Some(-1),
                });
            }
        }
        Ok(())
    }
}

/// Helper for tests／callers that want all events until Exited／Failed.
pub fn drain_until_terminal(
    agent: &mut dyn AgentPort,
    run: RunId,
    max_polls: usize,
) -> Result<Vec<AgentChunk>, ExecError> {
    let mut all = Vec::new();
    for _ in 0..max_polls {
        let batch = agent.poll_chunks(run)?;
        let done = batch
            .iter()
            .any(|e| matches!(e, AgentChunk::Exited { .. } | AgentChunk::Failed { .. }));
        all.extend(batch);
        if done {
            return Ok(all);
        }
    }
    Err(ExecError::Other(format!(
        "run {} did not terminate within {max_polls} polls",
        run.0
    )))
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeProcess;

    fn dry_adapter() -> CliAgentAdapter {
        CliAgentAdapter::with_defaults(Box::new(FakeProcess::new()))
    }

    fn approved_live_settings(path: &str) -> CliAgentSettings {
        let mut s = CliAgentSettings::defaults();
        s.claude.path = path.into();
        s.claude.args = vec![];
        s.live_approved = true;
        s
    }

    #[test]
    fn dry_run_event_sequence_started_chunk_progress_exited() {
        let mut agent = dry_adapter();
        let run = agent
            .start_run(StartRunRequest::cli_dry_run())
            .expect("start");
        let events = agent.poll_chunks(run).expect("poll");

        assert_eq!(events.len(), 4);
        assert!(matches!(
            &events[0],
            AgentChunk::Started {
                dry_run: true,
                provider: AgentProvider::Cli,
                tool: Some(CliToolKind::Claude),
                ..
            }
        ));
        assert!(matches!(
            &events[1],
            AgentChunk::Chunk {
                stream: OutputStream::Stdout,
                text,
                ..
            } if text.contains("dry-run")
        ));
        assert!(matches!(&events[2], AgentChunk::Progress { .. }));
        assert!(matches!(
            &events[3],
            AgentChunk::Exited {
                classification: ExitClassification::Success,
                exit_code: Some(0),
                ..
            }
        ));
    }

    #[test]
    fn dry_run_cancel_before_poll_yields_cancelled() {
        let mut agent = dry_adapter();
        let run = agent
            .start_run(StartRunRequest::cli_dry_run())
            .expect("start");
        agent.cancel(run).expect("cancel");
        let events = agent.poll_chunks(run).expect("poll");

        let exited = events
            .iter()
            .find(|e| matches!(e, AgentChunk::Exited { .. }));
        assert!(matches!(
            exited,
            Some(AgentChunk::Exited {
                classification: ExitClassification::Cancelled,
                exit_code: Some(-1),
                ..
            })
        ));
        assert!(!events.iter().any(|e| matches!(
            e,
            AgentChunk::Exited {
                classification: ExitClassification::Success,
                ..
            }
        )));
    }

    #[test]
    fn mcp_provider_rejected() {
        let mut agent = dry_adapter();
        let err = agent
            .start_run(StartRunRequest::mcp_dry_run())
            .expect_err("mcp");
        assert!(matches!(err, ExecError::UnsupportedProvider(_)));
    }

    #[test]
    fn start_run_rejects_missing_binding() {
        let mut agent = dry_adapter();
        let mut req = StartRunRequest::cli_dry_run();
        req.worktree_fingerprint.clear();
        let err = agent.start_run(req).expect_err("bind");
        assert_eq!(
            err,
            ExecError::MissingBinding("worktree_fingerprint".into())
        );
    }

    #[test]
    fn live_without_approval_is_rejected() {
        let mut agent = dry_adapter();
        assert!(!agent.settings().live_approved);
        let err = agent
            .start_run(StartRunRequest::cli_live())
            .expect_err("not approved");
        assert_eq!(err, ExecError::LiveNotApproved);
    }

    #[cfg(not(feature = "real-spawn"))]
    #[test]
    fn real_spawn_without_feature_is_disabled() {
        let fake = FakeProcess::new();
        let mut agent = CliAgentAdapter::new(
            approved_live_settings("claude"),
            Box::new(fake),
        );
        let err = agent
            .start_run(StartRunRequest::cli_live())
            .expect_err("no real spawn");
        assert_eq!(err, ExecError::RealSpawnDisabled);
    }

    #[cfg(feature = "real-spawn")]
    #[test]
    fn live_streams_stdout_stderr_exit_code_and_cancel() {
        let fake = FakeProcess::new();
        let mut agent = CliAgentAdapter::new(
            approved_live_settings("/tools/claude"),
            Box::new(fake.clone()),
        );

        let run = agent
            .start_run(StartRunRequest::cli_live())
            .expect("live start");
        let pid = fake.last_id().expect("pid");

        fake.push_stdout(pid, "out-line\n").expect("stdout");
        fake.push_stderr(pid, "err-line\n").expect("stderr");
        fake.finish(pid, 0).expect("finish");

        let events = drain_until_terminal(&mut agent, run, 8).expect("drain");
        assert!(matches!(
            &events[0],
            AgentChunk::Started {
                dry_run: false,
                provider: AgentProvider::Cli,
                ..
            }
        ));
        assert!(events.iter().any(|e| matches!(
            e,
            AgentChunk::Chunk {
                stream: OutputStream::Stdout,
                text,
                ..
            } if text.contains("out-line")
        )));
        assert!(events.iter().any(|e| matches!(
            e,
            AgentChunk::Chunk {
                stream: OutputStream::Stderr,
                text,
                ..
            } if text.contains("err-line")
        )));
        assert!(matches!(
            events.last(),
            Some(AgentChunk::Exited {
                classification: ExitClassification::Success,
                exit_code: Some(0),
                ..
            })
        ));

        // DryRun still switchable after live finishes.
        let dry = agent
            .start_run(StartRunRequest::cli_dry_run())
            .expect("dry after live");
        let dry_ev = agent.poll_chunks(dry).expect("dry poll");
        assert!(matches!(
            &dry_ev[0],
            AgentChunk::Started { dry_run: true, .. }
        ));
    }

    #[cfg(feature = "real-spawn")]
    #[test]
    fn live_cancel_yields_cancelled_exit() {
        let fake = FakeProcess::new();
        let mut agent = CliAgentAdapter::new(
            approved_live_settings("/tools/claude"),
            Box::new(fake.clone()),
        );
        let run = agent
            .start_run(StartRunRequest::cli_live())
            .expect("start");
        agent.cancel(run).expect("cancel");
        let events = agent.poll_chunks(run).expect("poll");
        assert!(matches!(
            events.iter().find(|e| matches!(e, AgentChunk::Exited { .. })),
            Some(AgentChunk::Exited {
                classification: ExitClassification::Cancelled,
                exit_code: Some(-1),
                ..
            })
        ));
    }

    #[cfg(feature = "real-spawn")]
    #[test]
    fn approve_live_requires_activatable_path() {
        use sgenaxis_adapters::fake::FakeFileSystem;

        let fs = FakeFileSystem::new();
        fs.seed("/bin/claude", b"");
        let mut s = CliAgentSettings::defaults();
        s.claude.path = "/bin/claude".into();
        s.approve_live(&fs).expect("approve");
        assert!(s.live_approved);
        s.revoke_live();
        assert!(!s.live_approved);

        s.claude.path = "/missing".into();
        assert!(s.approve_live(&fs).is_err());
    }

    #[test]
    fn settings_config_keys_match_labels() {
        let s = CliAgentSettings::defaults();
        assert_eq!(CliToolKind::Claude.config_key(), "claude");
        assert_eq!(CliToolKind::CursorAgent.config_key(), "cursor-agent");
        assert_eq!(CliToolKind::Codex.config_key(), "codex");
        assert_eq!(CliToolKind::Antigravity.config_key(), "antigravity");
        assert_eq!(s.selected_config().path, "claude");
        assert!(!s.live_approved);
    }

    /// BDD-PD-EXEC-SINGLE-01: second start_run while first undrained → Busy.
    #[test]
    fn single_agent_busy_until_drained() {
        let mut agent = dry_adapter();
        let _ = agent
            .start_run(StartRunRequest::cli_dry_run())
            .expect("first");
        let err = agent
            .start_run(StartRunRequest::cli_dry_run())
            .expect_err("busy");
        assert!(matches!(err, ExecError::Busy(_)));
        let msg = err.to_string();
        assert!(
            msg.contains("PD-EXEC-SINGLE-01") || msg.contains("busy"),
            "unexpected: {msg}"
        );
    }

    /// BDD-PD-EXEC-SINGLE-01: after drain (end) a new start_run is allowed.
    #[test]
    fn single_agent_after_drain_can_restart() {
        let mut agent = dry_adapter();
        let first = agent
            .start_run(StartRunRequest::cli_dry_run())
            .expect("first");
        let _ = drain_until_terminal(&mut agent, first, 4).expect("drain");
        let second = agent
            .start_run(StartRunRequest::cli_dry_run())
            .expect("second after end");
        assert_ne!(first, second);
    }

    /// BDD-PD-EXEC-SINGLE-01: after cancel＋drain a new start_run is allowed.
    #[test]
    fn single_agent_after_cancel_can_restart() {
        let mut agent = dry_adapter();
        let first = agent
            .start_run(StartRunRequest::cli_dry_run())
            .expect("first");
        agent.cancel(first).expect("cancel");
        let _ = drain_until_terminal(&mut agent, first, 4).expect("drain cancel");
        let second = agent
            .start_run(StartRunRequest::cli_dry_run())
            .expect("second after cancel");
        assert_ne!(first, second);
    }

    #[test]
    fn exit_classification_from_code() {
        assert_eq!(
            ExitClassification::from_exit_code(0),
            ExitClassification::Success
        );
        assert_eq!(
            ExitClassification::from_exit_code(1),
            ExitClassification::Failure
        );
        assert_eq!(
            ExitClassification::from_exit_code(-1),
            ExitClassification::Cancelled
        );
        assert_eq!(
            ExitClassification::from_exit_code(-9),
            ExitClassification::Crashed
        );
    }

    #[test]
    fn drain_until_terminal_collects_sequence() {
        let mut agent = dry_adapter();
        let run = agent
            .start_run(StartRunRequest::cli_dry_run())
            .expect("start");
        let all = drain_until_terminal(&mut agent, run, 4).expect("drain");
        assert_eq!(all.len(), 4);
        assert!(matches!(all.last(), Some(AgentChunk::Exited { .. })));
    }
}
