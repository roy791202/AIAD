//! AgentRouter — selects Cli | Mcp adapter on `start_run` (PRODUCT-DEVELOPMENT §6.3).

use crate::bind::require_run_binding;
use crate::cli::CliAgentAdapter;
use crate::error::ExecError;
use crate::events::AgentChunk;
use crate::mcp::McpAgentAdapter;
use crate::port::{AgentPort, AgentProvider, RunId, StartRunRequest};

/// Which leaf adapter currently owns the single in-flight run (first-wave: one Agent).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ActiveProvider {
    Cli,
    Mcp,
}

/// EXEC façade: UI／FLOW picks `provider: Cli | Mcp`; this routes to the matching adapter.
///
/// Shares the same [`AgentChunk`]／[`AgentPort`] surface as the leaf adapters.
pub struct AgentRouter {
    cli: CliAgentAdapter,
    mcp: McpAgentAdapter,
    /// Tracks which adapter accepted the last `start_run` (for poll／cancel routing).
    active: Option<ActiveProvider>,
}

impl AgentRouter {
    pub fn new(cli: CliAgentAdapter, mcp: McpAgentAdapter) -> Self {
        Self {
            cli,
            mcp,
            active: None,
        }
    }

    pub fn cli(&self) -> &CliAgentAdapter {
        &self.cli
    }

    pub fn cli_mut(&mut self) -> &mut CliAgentAdapter {
        &mut self.cli
    }

    pub fn mcp(&self) -> &McpAgentAdapter {
        &self.mcp
    }

    pub fn mcp_mut(&mut self) -> &mut McpAgentAdapter {
        &mut self.mcp
    }

    /// Replace CLI leaf when idle (PD-REMAIN-LIVE-SPAWN-01: Fake→StdProcess／settings).
    pub fn replace_cli(&mut self, cli: CliAgentAdapter) -> Result<(), ExecError> {
        self.ensure_global_idle()?;
        self.cli = cli;
        Ok(())
    }

    fn ensure_global_idle(&self) -> Result<(), ExecError> {
        if self.cli.is_busy() || self.mcp.is_busy() {
            return Err(ExecError::Busy(
                "another provider still has an active or undrained run; only one in-flight Agent allowed (PD-EXEC-SINGLE-01); finish or cancel first"
                    .into(),
            ));
        }
        Ok(())
    }
}

impl AgentPort for AgentRouter {
    fn start_run(&mut self, req: StartRunRequest) -> Result<RunId, ExecError> {
        let _binding = require_run_binding(&req)?;
        self.ensure_global_idle()?;

        let provider = req.provider;
        let run_id = match provider {
            AgentProvider::Cli => self.cli.start_run(req)?,
            AgentProvider::Mcp => self.mcp.start_run(req)?,
        };
        self.active = Some(match provider {
            AgentProvider::Cli => ActiveProvider::Cli,
            AgentProvider::Mcp => ActiveProvider::Mcp,
        });
        Ok(run_id)
    }

    fn poll_chunks(&mut self, run: RunId) -> Result<Vec<AgentChunk>, ExecError> {
        match self.active {
            Some(ActiveProvider::Cli) => self.cli.poll_chunks(run),
            Some(ActiveProvider::Mcp) => self.mcp.poll_chunks(run),
            None => Err(ExecError::RunNotFound(format!("{}", run.0))),
        }
    }

    fn cancel(&mut self, run: RunId) -> Result<(), ExecError> {
        match self.active {
            Some(ActiveProvider::Cli) => self.cli.cancel(run),
            Some(ActiveProvider::Mcp) => self.mcp.cancel(run),
            None => Err(ExecError::RunNotFound(format!("{}", run.0))),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::events::ExitClassification;
    use crate::mcp_client::StubMcpClient;
    use crate::{drain_until_terminal, AgentProvider};
    use sgenaxis_adapters::FakeProcess;

    fn dry_router() -> AgentRouter {
        AgentRouter::new(
            CliAgentAdapter::with_defaults(Box::new(FakeProcess::new())),
            McpAgentAdapter::with_defaults(Box::new(StubMcpClient)),
        )
    }

    #[test]
    fn provider_switch_cli_then_mcp_on_start_run() {
        let mut exec = dry_router();

        let cli_run = exec
            .start_run(StartRunRequest::cli_dry_run())
            .expect("cli start");
        let cli_events = drain_until_terminal(&mut exec, cli_run, 4).expect("cli drain");
        assert!(matches!(
            &cli_events[0],
            AgentChunk::Started {
                provider: AgentProvider::Cli,
                dry_run: true,
                ..
            }
        ));
        assert!(matches!(
            cli_events.last(),
            Some(AgentChunk::Exited {
                classification: ExitClassification::Success,
                ..
            })
        ));

        let mcp_run = exec
            .start_run(StartRunRequest::mcp_dry_run())
            .expect("mcp start");
        let mcp_events = drain_until_terminal(&mut exec, mcp_run, 4).expect("mcp drain");
        assert!(matches!(
            &mcp_events[0],
            AgentChunk::Started {
                provider: AgentProvider::Mcp,
                dry_run: true,
                ..
            }
        ));
        assert!(matches!(
            mcp_events.last(),
            Some(AgentChunk::Exited {
                classification: ExitClassification::Success,
                ..
            })
        ));
        // RunIds are allocated per leaf adapter; both may be RunId(1) after a full drain.
        // Routing uses `active` provider, not global uniqueness.
        assert_eq!(cli_events[0].run_id(), cli_run);
        assert_eq!(mcp_events[0].run_id(), mcp_run);
    }

    #[test]
    fn provider_switch_mcp_then_cli() {
        let mut exec = dry_router();

        let mcp_run = exec
            .start_run(StartRunRequest::mcp_dry_run())
            .expect("mcp");
        let _ = drain_until_terminal(&mut exec, mcp_run, 4).expect("drain mcp");

        let cli_run = exec
            .start_run(StartRunRequest::cli_dry_run())
            .expect("cli");
        let events = drain_until_terminal(&mut exec, cli_run, 4).expect("drain cli");
        assert!(matches!(
            &events[0],
            AgentChunk::Started {
                provider: AgentProvider::Cli,
                ..
            }
        ));
    }

    /// BDD-PD-EXEC-SINGLE-01: cross-provider second start while first undrained → Busy.
    #[test]
    fn cannot_start_mcp_while_cli_undrained() {
        let mut exec = dry_router();
        let _ = exec
            .start_run(StartRunRequest::cli_dry_run())
            .expect("cli");
        let err = exec
            .start_run(StartRunRequest::mcp_dry_run())
            .expect_err("busy");
        assert!(matches!(err, ExecError::Busy(_)));
        let msg = err.to_string();
        assert!(
            msg.contains("PD-EXEC-SINGLE-01") || msg.contains("busy"),
            "unexpected: {msg}"
        );
    }

    /// BDD-PD-EXEC-SINGLE-01: cancel＋drain clears Busy so another provider may start.
    #[test]
    fn after_cancel_can_start_other_provider() {
        let mut exec = dry_router();
        let cli = exec
            .start_run(StartRunRequest::cli_dry_run())
            .expect("cli");
        exec.cancel(cli).expect("cancel");
        let _ = drain_until_terminal(&mut exec, cli, 4).expect("drain");
        let mcp = exec
            .start_run(StartRunRequest::mcp_dry_run())
            .expect("mcp after cancel");
        let events = drain_until_terminal(&mut exec, mcp, 4).expect("drain mcp");
        assert!(matches!(
            &events[0],
            AgentChunk::Started {
                provider: AgentProvider::Mcp,
                ..
            }
        ));
    }

    #[test]
    fn start_run_rejects_missing_fingerprint() {
        let mut exec = dry_router();
        let mut req = StartRunRequest::cli_dry_run();
        req.worktree_fingerprint.clear();
        let err = exec.start_run(req).expect_err("bind");
        assert_eq!(
            err,
            ExecError::MissingBinding("worktree_fingerprint".into())
        );
    }
}
