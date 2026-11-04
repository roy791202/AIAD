//! Approved cancellation acknowledgment and terminal reconciliation, independent tests.
use super::*;
use sgenaxis_exec::{DEMO_PROJECT_ROOT,DEMO_WORKTREE_FINGERPRINT};
use sgenaxis_ports::{PortError,ProcessId,ProcessOutput,ProcessPort,StreamCompletion};
use std::sync::{Arc,Mutex};
#[derive(Default)]struct State{reads:usize,cancels:usize,out:ProcessOutput,exit:Option<i32>}
#[derive(Clone,Default)]struct CountProcess(Arc<Mutex<State>>);
impl ProcessPort for CountProcess{
 fn start(&mut self,_:&str,_:&[&str],_:Option<&str>)->Result<ProcessId,PortError>{Ok(ProcessId(1))}
 fn try_wait(&mut self,_:ProcessId)->Result<Option<i32>,PortError>{Ok(self.0.lock().unwrap().exit)}
 fn cancel(&mut self,_:ProcessId)->Result<(),PortError>{let mut s=self.0.lock().unwrap();s.cancels+=1;s.exit=Some(-1);Ok(())}
 fn try_read(&mut self,_:ProcessId)->Result<ProcessOutput,PortError>{let mut s=self.0.lock().unwrap();s.reads+=1;let out=s.out.clone();s.out.stdout.clear();s.out.stderr.clear();Ok(out)}
}
fn args(provider:ProviderDto,dry_run:bool,id:&str)->StartRunArgs{StartRunArgs{provider,dry_run,work_item_id:Some(id.into()),project_root:Some(DEMO_PROJECT_ROOT.into()),worktree_fingerprint:Some(DEMO_WORKTREE_FINGERPRINT.into()),guard:None}}
#[test]fn proc_host_cancel_never_polls_or_swallows_tail_and_releases_only_at_terminal(){
 let mut h=DispatchHost::new();let p=CountProcess::default();let mut settings=CliAgentSettings::defaults();settings.live_approved=true;settings.claude.path="explicit-scripted-process".into();
 h.wire_cli_live_process(settings,Box::new(p.clone())).unwrap();let run=h.start_run(args(ProviderDto::Cli,false,"proc-tail")).unwrap().run_id;
 let pending=h.cancel_run(run).unwrap();assert_eq!(p.0.lock().unwrap().reads,0,"cancel must not consume any events");assert_eq!(pending.active_run_id,Some(run));assert!(h.active_lease_project.is_some());assert!(h.start_run(args(ProviderDto::Cli,true,"next")).is_err());
 let empty=h.poll_chunks(run).unwrap();assert!(!empty.chunks.iter().any(|c|matches!(c,ChunkDto::Exited{..}|ChunkDto::Failed{..})));assert_eq!(empty.board.active_run_id,Some(run));
 {let mut s=p.0.lock().unwrap();s.out=ProcessOutput{stdout:"late-tail".into(),stderr:"late-error-tail".into(),stdout_completion:StreamCompletion::Eof,stderr_completion:StreamCompletion::Eof};}
 let final_poll=h.poll_chunks(run).unwrap();assert_eq!(final_poll.chunks.iter().filter(|c|matches!(c,ChunkDto::Chunk{..})).count(),2);assert!(matches!(final_poll.chunks.last(),Some(ChunkDto::Exited{..})));assert!(final_poll.board.active_run_id.is_none());assert!(h.active_lease_project.is_none());assert_eq!(final_poll.board.green,0);
 let summary=h.get_evidence_summary("proc-tail");assert_eq!(summary.provider_terminal,"Cancelled");assert_eq!(summary.zone.as_deref(),Some("yellow"));assert!(!summary.ready_for_green);
 assert!(h.poll_chunks(run).unwrap().chunks.is_empty());assert!(h.start_run(args(ProviderDto::Cli,true,"next")).is_ok());
}
#[test]fn proc_host_dry_cli_and_mcp_cancel_ack_preserves_terminal_for_poll(){
 for provider in [ProviderDto::Cli,ProviderDto::Mcp]{let mut h=DispatchHost::new();let run=h.start_run(args(provider,true,"generic-cancel")).unwrap().run_id;let pending=h.cancel_run(run).unwrap();assert_eq!(pending.active_run_id,Some(run));let end=h.poll_chunks(run).unwrap();assert!(end.chunks.iter().any(|c|matches!(c,ChunkDto::Exited{..})));assert!(end.board.active_run_id.is_none());assert_eq!(end.board.green,0);assert!(end.board.yellow>=1);assert_eq!(h.get_evidence_summary("generic-cancel").provider_terminal,"Cancelled");}
}
