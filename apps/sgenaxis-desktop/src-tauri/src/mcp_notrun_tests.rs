use super::*;
use std::sync::{Arc, atomic::{AtomicUsize, Ordering}};
use sgenaxis_exec::{McpClientPort, McpSessionId, ExecError};

const SECRET: &str = "notrun-secret-token";
const TARGET: &str = "http://127.0.0.1:3920/sse";
fn host(endpoint: &str) -> DispatchHost {
    let mut h = DispatchHost::new();
    let mut s = McpAgentSettings::defaults();
    s.endpoint = endpoint.into();
    s.approved_tools = vec!["list_tools".into()];
    s.secret_token = Some(SECRET.into());
    h.apply_mcp_settings(s);
    h
}
fn args(dry_run: bool) -> StartRunArgs {
    StartRunArgs { provider: ProviderDto::Mcp, dry_run,
        work_item_id: Some("notrun-work".into()), project_root: Some(DEMO_PROJECT_ROOT.into()),
        worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()), guard: None }
}
fn unchanged(h: &DispatchHost, before: &str) {
    assert_eq!(serde_json::to_string(&h.get_board()).unwrap(), before);
    assert!(h.active_run_id.is_none());
    assert!(h.active_work_item.is_none());
    assert!(h.active_lease_project.is_none());
    assert!(h.work.projection().unwrap().active_leases.is_empty());
    assert!(h.provider_by_work.is_empty());
    assert!(h.flows.is_empty());
    assert!(h.evid.is_empty());
}
fn unavailable(error: &str) {
    assert!(error.contains("NOT RUN"), "{error}");
    assert!(error.to_lowercase().contains("unavailable"), "{error}");
    assert!(!error.contains(SECRET), "secret disclosed");
}
#[test]
fn default_live_rejects_without_accepted_state() {
    let mut h=host(TARGET);
    let before=serde_json::to_string(&h.get_board()).unwrap();
    unavailable(&h.start_run(args(false)).expect_err("default has no real transport"));
    unchanged(&h,&before);
}
#[test]
fn repeated_rejection_then_dryrun_recovers() {
    let mut h=host(TARGET);
    let before=serde_json::to_string(&h.get_board()).unwrap();
    for _ in 0..2 {
        unavailable(&h.start_run(args(false)).expect_err("retry remains unavailable"));
        unchanged(&h,&before);
    }
    let run=h.start_run(args(true)).expect("DryRun after rejection");
    assert!(run.dry_run);
    let poll=h.poll_chunks(run.run_id).unwrap();
    assert!(poll.chunks.iter().any(|c| matches!(c,ChunkDto::Exited{classification,..} if classification=="success")));
    assert!(h.work.projection().unwrap().active_leases.is_empty());
    assert!(h.active_run_id.is_none());
    assert_eq!(poll.board.green,0);
}
#[test]
fn guarded_implementation_unavailable_keeps_execution_uncommitted() {
    let mut h=host(TARGET);
    let before=serde_json::to_string(&h.get_board()).unwrap();
    let a=args(false);
    let err=h.start_implementation(StartImplementationArgs {provider:a.provider,dry_run:a.dry_run,
        work_item_id:a.work_item_id,project_root:a.project_root,worktree_fingerprint:a.worktree_fingerprint,
        guard:sample_guard_packet(true)}).expect_err("guard approval cannot supply real transport");
    unavailable(&err);
    unchanged(&h,&before);
}
#[test]
fn unavailable_diagnostics_do_not_echo_credentials() {
    let endpoint="http://endpoint-user:endpoint-password@127.0.0.1:3920/sse";
    let mut h=host(endpoint);
    let err=h.start_run(args(false)).expect_err("credential target cannot execute");
    assert!(err.contains("NOT RUN"),"{err}");
    for secret in [SECRET,endpoint,"endpoint-password","endpoint-user"] {assert!(!err.contains(secret),"credential disclosed: {err}");}
}
struct NeverDial(Arc<AtomicUsize>);
impl McpClientPort for NeverDial {
    fn connect(&mut self,_:&McpAgentSettings)->Result<McpSessionId,ExecError>{self.0.fetch_add(1,Ordering::SeqCst);panic!("forbidden target dialed")}
    fn call_tool(&mut self,_:McpSessionId,_:&str,_:&str)->Result<String,ExecError>{panic!("forbidden target called")}
    fn disconnect(&mut self,_:McpSessionId)->Result<(),ExecError>{panic!("forbidden target disconnected")}
}
#[test]
fn empty_and_reserved_targets_never_contact_transport_or_echo_credentials() {
    for endpoint in ["","http://endpoint-user:endpoint-password@127.0.0.1:8788/sse","http://endpoint-user:endpoint-password@127.0.0.1:8787/events"] {
        let mut h=host(endpoint);
        let calls=Arc::new(AtomicUsize::new(0));
        h.exec=AgentRouter::new(CliAgentAdapter::with_defaults(Box::new(FakeProcess::new())),McpAgentAdapter::with_defaults(Box::new(NeverDial(calls.clone()))));
        let mut settings=McpAgentSettings::defaults();settings.endpoint=endpoint.into();settings.approved_tools=vec!["list_tools".into()];settings.secret_token=Some(SECRET.into());h.apply_mcp_settings(settings);
        let before=serde_json::to_string(&h.get_board()).unwrap();
        let err=h.start_run(args(false)).expect_err("forbidden target");
        assert!(err.contains("NOT RUN"),"{err}");
        for secret in [SECRET,"endpoint-password","endpoint-user"] {assert!(!err.contains(secret),"credential disclosed: {err}");}
        assert_eq!(calls.load(Ordering::SeqCst),0);
        unchanged(&h,&before);
    }
}
