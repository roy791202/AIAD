//! McpAgentAdapter — Provider B (local MCP); DryRun first.
//!
//! Live MCP (feature `real-mcp`) uses [`McpClientPort`] over stdio or local HTTP／SSE
//! to a **user-explicit** endpoint／server name. Approval gates (PD-MCP-LIVE-01):
//! - endpoint must be activatable (not empty／`:8788`／`:8787`) before connect;
//! - tool must be on `approved_tools` before `call_tool`;
//! - tool results／failures emit into the shared Run event stream.
//! Default tests never dial a live server.

use std::collections::VecDeque;

use crate::error::ExecError;
use crate::events::{AgentChunk, ExitClassification, OutputStream};
use crate::mcp_client::{McpClientPort, McpSessionId, StubMcpClient};
use crate::port::{AgentPort, AgentProvider, RunId, StartRunRequest};
use crate::settings::{is_mcp_endpoint_activatable, McpAgentSettings};

#[derive(Debug)]
enum RunPhase {
    DryRun { finished: bool },
    #[cfg_attr(not(feature = "real-mcp"), allow(dead_code))]
    Live {
        session: McpSessionId,
        finished: bool,
    },
}

struct ActiveRun {
    run_id: RunId,
    phase: RunPhase,
    queue: VecDeque<AgentChunk>,
}

impl ActiveRun {
    fn is_finished(&self) -> bool {
        match &self.phase {
            RunPhase::DryRun { finished } => *finished,
            RunPhase::Live { finished, .. } => *finished,
        }
    }
}

/// Agent Provider B: local／explicit MCP via [`McpClientPort`].
///
/// - **DryRun** (default tests): emits started → chunk → progress → exited without network.
/// - **Live**: behind feature `real-mcp`; otherwise `dry_run: false` → [`ExecError::RealMcpDisabled`]
///   (after endpoint／tool approval gates).
pub struct McpAgentAdapter {
    settings: McpAgentSettings,
    client: Box<dyn McpClientPort>,
    next_run: u64,
    active: Option<ActiveRun>,
}

impl McpAgentAdapter {
    pub fn new(settings: McpAgentSettings, client: Box<dyn McpClientPort>) -> Self {
        Self {
            settings,
            client,
            next_run: 1,
            active: None,
        }
    }

    pub fn with_defaults(client: Box<dyn McpClientPort>) -> Self {
        Self::new(McpAgentSettings::defaults(), client)
    }

    /// Convenience: stub client + default settings (DryRun-only host).
    pub fn dry_defaults() -> Self {
        Self::with_defaults(Box::new(StubMcpClient))
    }

    pub fn settings(&self) -> &McpAgentSettings {
        &self.settings
    }

    pub fn settings_mut(&mut self) -> &mut McpAgentSettings {
        &mut self.settings
    }

    /// Host wiring: replace MCP settings (endpoint／approved tools／secret) before Live.
    pub fn apply_settings(&mut self, settings: McpAgentSettings) {
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

    fn enqueue_dry_run(run_id: RunId, settings: &McpAgentSettings) -> VecDeque<AgentChunk> {
        let name = &settings.server_name;
        let transport = settings.transport.config_key();
        let mut q = VecDeque::new();
        q.push_back(AgentChunk::Started {
            run_id,
            provider: AgentProvider::Mcp,
            dry_run: true,
            tool: None,
        });
        q.push_back(AgentChunk::Chunk {
            run_id,
            stream: OutputStream::Stdout,
            text: format!(
                "[dry-run] simulated MCP message from server={name} transport={transport}"
            ),
        });
        q.push_back(AgentChunk::Progress {
            run_id,
            message: format!("[dry-run] MCP {name} progress (no network)"),
        });
        q.push_back(AgentChunk::Exited {
            run_id,
            classification: ExitClassification::Success,
            exit_code: Some(0),
        });
        q
    }

    /// Shared approval gates — run even when `real-mcp` is off so unapproved never dials.
    fn gate_live(settings: &McpAgentSettings, req: &StartRunRequest) -> Result<String, ExecError> {
        if !is_mcp_endpoint_activatable(&settings.endpoint) {
            return Err(ExecError::EndpointNotApproved(settings.endpoint.clone()));
        }
        let tool_name = req
            .mcp_tool
            .clone()
            .or_else(|| settings.approved_tools.first().cloned())
            .unwrap_or_default();
        if tool_name.is_empty() || !settings.is_tool_approved(&tool_name) {
            return Err(ExecError::ToolNotApproved(if tool_name.is_empty() {
                "(none)".into()
            } else {
                tool_name
            }));
        }
        Ok(tool_name)
    }

    #[cfg(feature = "real-mcp")]
    fn start_live(&mut self, run_id: RunId, req: &StartRunRequest) -> Result<ActiveRun, ExecError> {
        let tool_name = Self::gate_live(&self.settings, req)?;
        let args = req.mcp_tool_args.as_deref().unwrap_or("{}");
        let name = self.settings.server_name.clone();

        let session = self.client.connect(&self.settings)?;

        let mut queue = VecDeque::new();
        queue.push_back(AgentChunk::Started {
            run_id,
            provider: AgentProvider::Mcp,
            dry_run: false,
            tool: None,
        });
        queue.push_back(AgentChunk::Progress {
            run_id,
            message: format!(
                "[real-mcp] connected to local server={name}; calling tool={tool_name}"
            ),
        });

        match self.client.call_tool(session, &tool_name, args) {
            Ok(result) => {
                queue.push_back(AgentChunk::Chunk {
                    run_id,
                    stream: OutputStream::Stdout,
                    text: format!("[mcp-tool:{tool_name}] {result}"),
                });
                queue.push_back(AgentChunk::Exited {
                    run_id,
                    classification: ExitClassification::Success,
                    exit_code: Some(0),
                });
            }
            Err(e) => {
                queue.push_back(AgentChunk::Failed {
                    run_id,
                    message: e.to_string(),
                });
                queue.push_back(AgentChunk::Exited {
                    run_id,
                    classification: ExitClassification::Failure,
                    exit_code: Some(1),
                });
            }
        }

        let _ = self.client.disconnect(session);
        Ok(ActiveRun {
            run_id,
            phase: RunPhase::Live {
                session,
                finished: true,
            },
            queue,
        })
    }

    #[cfg(not(feature = "real-mcp"))]
    fn start_live(
        &mut self,
        _run_id: RunId,
        req: &StartRunRequest,
    ) -> Result<ActiveRun, ExecError> {
        // Still enforce approval so unapproved endpoints／tools never reach a client.
        let _tool = Self::gate_live(&self.settings, req)?;
        let _ = &self.client;
        Err(ExecError::RealMcpDisabled)
    }
}

impl AgentPort for McpAgentAdapter {
    fn start_run(&mut self, req: StartRunRequest) -> Result<RunId, ExecError> {
        let _binding = crate::bind::require_run_binding(&req)?;
        match req.provider {
            AgentProvider::Mcp => {}
            AgentProvider::Cli => {
                return Err(ExecError::UnsupportedProvider(
                    "Cli is PD-EXEC-CLI; use Mcp here or AgentRouter".into(),
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
        let active = if req.dry_run {
            ActiveRun {
                run_id,
                phase: RunPhase::DryRun { finished: true },
                queue: Self::enqueue_dry_run(run_id, &self.settings),
            }
        } else {
            self.start_live(run_id, &req)?
        };

        self.active = Some(active);
        Ok(run_id)
    }

    fn poll_chunks(&mut self, run: RunId) -> Result<Vec<AgentChunk>, ExecError> {
        let active = self
            .active
            .as_mut()
            .ok_or_else(|| ExecError::RunNotFound(format!("{}", run.0)))?;
        if active.run_id != run {
            return Err(ExecError::RunNotFound(format!("{}", run.0)));
        }

        let mut out = Vec::new();
        while let Some(ev) = active.queue.pop_front() {
            out.push(ev);
        }
        Ok(out)
    }

    fn cancel(&mut self, run: RunId) -> Result<(), ExecError> {
        let live_session = {
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
                    session,
                    finished,
                } => {
                    if *finished {
                        None
                    } else {
                        Some(*session)
                    }
                }
            }
        };

        if let Some(session) = live_session {
            self.client.disconnect(session)?;
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::drain_until_terminal;
    use crate::mcp_client::FakeMcpClient;
    use std::sync::{Arc, Mutex};

    #[test]
    fn dry_run_mcp_sequence_started_chunk_progress_exited() {
        let mut agent = McpAgentAdapter::dry_defaults();
        let run = agent
            .start_run(StartRunRequest::mcp_dry_run())
            .expect("start");
        let events = agent.poll_chunks(run).expect("poll");

        assert_eq!(events.len(), 4);
        assert!(matches!(
            &events[0],
            AgentChunk::Started {
                dry_run: true,
                provider: AgentProvider::Mcp,
                tool: None,
                ..
            }
        ));
        assert!(matches!(
            &events[1],
            AgentChunk::Chunk {
                stream: OutputStream::Stdout,
                text,
                ..
            } if text.contains("dry-run") && text.contains("MCP")
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
    fn dry_run_cancel_yields_cancelled() {
        let mut agent = McpAgentAdapter::dry_defaults();
        let run = agent
            .start_run(StartRunRequest::mcp_dry_run())
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

    #[test]
    fn cli_provider_rejected_on_mcp_adapter() {
        let mut agent = McpAgentAdapter::dry_defaults();
        let err = agent
            .start_run(StartRunRequest::cli_dry_run())
            .expect_err("cli");
        assert!(matches!(err, ExecError::UnsupportedProvider(_)));
    }

    #[test]
    fn unapproved_endpoint_8788_must_not_connect() {
        let client = Arc::new(Mutex::new(FakeMcpClient::default()));
        let client_port = TrackingClient {
            inner: Arc::clone(&client),
        };
        let mut settings = McpAgentSettings::defaults();
        settings.endpoint = "http://127.0.0.1:8788/sse".into();
        let mut agent = McpAgentAdapter::new(settings, Box::new(client_port));
        let err = agent
            .start_run(StartRunRequest::mcp_live("list_tools"))
            .expect_err("8788 blocked");
        assert!(matches!(err, ExecError::EndpointNotApproved(ref e) if e.contains("8788")));
        assert_eq!(client.lock().expect("lock").connect_count, 0);
        assert_eq!(client.lock().expect("lock").call_tool_count, 0);
    }

    #[test]
    fn unapproved_tool_must_not_call() {
        let client = Arc::new(Mutex::new(FakeMcpClient::default()));
        let client_port = TrackingClient {
            inner: Arc::clone(&client),
        };
        let mut settings = McpAgentSettings::defaults();
        settings.endpoint = "http://127.0.0.1:3920/sse".into();
        settings.approved_tools = vec!["list_tools".into()];
        let mut agent = McpAgentAdapter::new(settings, Box::new(client_port));
        let err = agent
            .start_run(StartRunRequest::mcp_live("shell_exec"))
            .expect_err("tool blocked");
        assert!(matches!(
            err,
            ExecError::ToolNotApproved(ref t) if t == "shell_exec"
        ));
        assert_eq!(client.lock().expect("lock").connect_count, 0);
        assert_eq!(client.lock().expect("lock").call_tool_count, 0);
    }

    #[cfg(not(feature = "real-mcp"))]
    #[test]
    fn real_mcp_without_feature_is_disabled_after_gates() {
        let mut settings = McpAgentSettings::defaults();
        settings.endpoint = "http://127.0.0.1:3920/sse".into();
        let mut agent = McpAgentAdapter::new(settings, Box::new(StubMcpClient));
        let err = agent
            .start_run(StartRunRequest::mcp_live("list_tools"))
            .expect_err("no real mcp");
        assert_eq!(err, ExecError::RealMcpDisabled);
    }

    #[cfg(feature = "real-mcp")]
    #[test]
    fn live_approved_endpoint_tool_call_enters_run_events() {
        let client = Arc::new(Mutex::new(FakeMcpClient::default()));
        let client_port = TrackingClient {
            inner: Arc::clone(&client),
        };
        let mut settings = McpAgentSettings::defaults();
        settings.endpoint = "http://127.0.0.1:3920/sse".into();
        settings.approved_tools = vec!["list_tools".into(), "read".into()];
        let mut agent = McpAgentAdapter::new(settings, Box::new(client_port));
        let mut req = StartRunRequest::mcp_live("list_tools");
        req.mcp_tool_args = Some(r#"{"limit":1}"#.into());
        let run = agent.start_run(req).expect("live");
        let events = agent.poll_chunks(run).expect("poll");

        assert!(matches!(
            &events[0],
            AgentChunk::Started {
                provider: AgentProvider::Mcp,
                dry_run: false,
                ..
            }
        ));
        assert!(events.iter().any(|e| matches!(
            e,
            AgentChunk::Progress { message, .. } if message.contains("calling tool=list_tools")
        )));
        assert!(events.iter().any(|e| matches!(
            e,
            AgentChunk::Chunk { text, .. } if text.contains("[mcp-tool:list_tools]") && text.contains("\"ok\":true")
        )));
        assert!(matches!(
            events.last(),
            Some(AgentChunk::Exited {
                classification: ExitClassification::Success,
                exit_code: Some(0),
                ..
            })
        ));

        let c = client.lock().expect("lock");
        assert_eq!(c.connect_count, 1);
        assert_eq!(c.call_tool_count, 1);
        assert_eq!(c.last_tool.as_deref(), Some("list_tools"));
        assert_eq!(c.last_endpoint.as_deref(), Some("http://127.0.0.1:3920/sse"));
    }

    #[cfg(feature = "real-mcp")]
    #[test]
    fn live_connect_failure_is_observable() {
        let mut fake = FakeMcpClient::default();
        fake.fail_connect = Some("refused by fake".into());
        let mut settings = McpAgentSettings::defaults();
        settings.endpoint = "stdio://local-agent".into();
        let mut agent = McpAgentAdapter::new(settings, Box::new(fake));
        let err = agent
            .start_run(StartRunRequest::mcp_live("list_tools"))
            .expect_err("connect fail");
        assert!(matches!(err, ExecError::Mcp(ref m) if m.contains("refused")));
    }

    #[cfg(feature = "real-mcp")]
    #[test]
    fn live_tool_failure_emits_failed_event() {
        let mut fake = FakeMcpClient::default();
        fake.fail_call_tool = Some("tool blew up".into());
        let mut settings = McpAgentSettings::defaults();
        settings.endpoint = "http://127.0.0.1:3920/sse".into();
        let mut agent = McpAgentAdapter::new(settings, Box::new(fake));
        let run = agent
            .start_run(StartRunRequest::mcp_live("list_tools"))
            .expect("start after connect");
        let events = agent.poll_chunks(run).expect("poll");
        assert!(events.iter().any(|e| matches!(
            e,
            AgentChunk::Failed { message, .. } if message.contains("tool blew up")
        )));
        assert!(matches!(
            events.last(),
            Some(AgentChunk::Exited {
                classification: ExitClassification::Failure,
                exit_code: Some(1),
                ..
            })
        ));
    }

    #[test]
    fn projection_omits_secret_token() {
        let mut s = McpAgentSettings::defaults();
        s.secret_token = Some("super-secret-token".into());
        let p = s.projection();
        assert!(p.has_secret);
        assert_eq!(p.server_name, s.server_name);
        assert_eq!(p.endpoint, s.endpoint);
        assert_eq!(p.approved_tools, s.approved_tools);
        let debug = format!("{p:?}");
        assert!(!debug.contains("super-secret-token"));
    }

    #[test]
    fn drain_until_terminal_mcp() {
        let mut agent = McpAgentAdapter::dry_defaults();
        let run = agent
            .start_run(StartRunRequest::mcp_dry_run())
            .expect("start");
        let all = drain_until_terminal(&mut agent, run, 4).expect("drain");
        assert!(matches!(all.last(), Some(AgentChunk::Exited { .. })));
    }

    /// Shared fake behind `Arc<Mutex<_>>` so tests can assert dial／call counts after gates.
    struct TrackingClient {
        inner: Arc<Mutex<FakeMcpClient>>,
    }

    impl McpClientPort for TrackingClient {
        fn connect(&mut self, settings: &McpAgentSettings) -> Result<McpSessionId, ExecError> {
            self.inner.lock().expect("lock").connect(settings)
        }

        fn call_tool(
            &mut self,
            session: McpSessionId,
            tool: &str,
            args_json: &str,
        ) -> Result<String, ExecError> {
            self.inner
                .lock()
                .expect("lock")
                .call_tool(session, tool, args_json)
        }

        fn disconnect(&mut self, session: McpSessionId) -> Result<(), ExecError> {
            self.inner.lock().expect("lock").disconnect(session)
        }
    }
}
