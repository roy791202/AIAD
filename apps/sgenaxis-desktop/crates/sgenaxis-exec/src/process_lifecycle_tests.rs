//! Independent approved process lifecycle contract tests: private controlled Instant.
#![cfg(feature = "real-spawn")]
use super::*;
use sgenaxis_ports::{PortError, ProcessOutput, StreamCompletion};
use std::sync::{Arc,Mutex};
use std::time::{Duration,Instant};
#[derive(Default)]
struct Script {out:ProcessOutput, exit:Option<i32>, cancels:usize, cancel_error:bool, wait_error:bool}
#[derive(Clone,Default)] struct ScriptProcess(Arc<Mutex<Script>>);
impl ProcessPort for ScriptProcess {
 fn start(&mut self,_:&str,_:&[&str],_:Option<&str>)->Result<ProcessId,PortError>{Ok(ProcessId(1))}
 fn try_wait(&mut self,_:ProcessId)->Result<Option<i32>,PortError>{let s=self.0.lock().unwrap();if s.wait_error {Err(PortError::Process("controlled wait failure".into()))}else{Ok(s.exit)}}
 fn cancel(&mut self,_:ProcessId)->Result<(),PortError>{let mut s=self.0.lock().unwrap();s.cancels+=1;if s.cancel_error {return Err(PortError::Process("cancel denied".into()));}s.exit=Some(-1);Ok(())}
 fn try_read(&mut self,_:ProcessId)->Result<ProcessOutput,PortError>{let mut s=self.0.lock().unwrap();let mut out=s.out.clone();out.stdout=std::mem::take(&mut s.out.stdout);out.stderr=std::mem::take(&mut s.out.stderr);Ok(out)}
}
fn setup()->(CliAgentAdapter,ScriptProcess,RunId,Instant){
 let p=ScriptProcess::default();let mut settings=CliAgentSettings::defaults();settings.live_approved=true;settings.claude.path="explicit-test-program".into();settings.claude.args=vec![];
 let mut a=CliAgentAdapter::new(settings,Box::new(p.clone()));let run=a.start_run(StartRunRequest::cli_live()).unwrap();(a,p,run,Instant::now())
}
fn sample(p:&ScriptProcess,exit:Option<i32>,out:&str,err:&str,stdout:StreamCompletion,stderr:StreamCompletion){let mut s=p.0.lock().unwrap();s.exit=exit;s.out=ProcessOutput{stdout:out.into(),stderr:err.into(),stdout_completion:stdout,stderr_completion:stderr};}
fn terminals(v:&[AgentChunk])->usize{v.iter().filter(|e|matches!(e,AgentChunk::Exited{..}|AgentChunk::Failed{..})).count()}
fn chunks(v:&[AgentChunk])->String{v.iter().filter_map(|e|if let AgentChunk::Chunk{text,..}=e{Some(text.as_str())}else{None}).collect()}
fn assert_terminal_last(v:&[AgentChunk]){assert_eq!(terminals(v),1);assert!(matches!(v.last(),Some(AgentChunk::Exited{..}|AgentChunk::Failed{..})));}
#[test] fn proc_t01_exit_before_independent_stdout_stderr_eof_preserves_tail(){
 let(mut a,p,r,t)=setup();sample(&p,Some(0),"","",StreamCompletion::Open,StreamCompletion::Open);
 let first=a.poll_chunks_at(r,t).unwrap();assert_eq!(terminals(&first),0,"exit is not stream completion");
 sample(&p,Some(0),"stdout-tail","",StreamCompletion::Eof,StreamCompletion::Open);
 let second=a.poll_chunks_at(r,t+Duration::from_millis(10)).unwrap();assert_eq!(chunks(&second),"stdout-tail");assert_eq!(terminals(&second),0);
 sample(&p,Some(0),"","stderr-tail",StreamCompletion::Eof,StreamCompletion::Eof);
 let last=a.poll_chunks_at(r,t+Duration::from_millis(20)).unwrap();assert_eq!(chunks(&last),"stderr-tail");assert_terminal_last(&last);
 assert!(matches!(last.last(),Some(AgentChunk::Exited{classification:ExitClassification::Success,..})));assert!(a.poll_chunks_at(r,t+Duration::from_millis(30)).unwrap().is_empty());
}
#[test] fn proc_t02_empty_open_polls_remain_active_and_busy(){
 let(mut a,p,r,t)=setup();sample(&p,Some(0),"","",StreamCompletion::Open,StreamCompletion::Open);
 for ms in [0,1,20,1999]{assert_eq!(terminals(&a.poll_chunks_at(r,t+Duration::from_millis(ms)).unwrap()),0,"empty/Open is not terminal at {ms}");}
 assert!(matches!(a.start_run(StartRunRequest::cli_dry_run()),Err(ExecError::Busy(_))));
}
#[test] fn proc_t03_error_keeps_partial_bytes_before_failed_once(){
 let(mut a,p,r,t)=setup();sample(&p,Some(0),"captured-out","captured-err",StreamCompletion::Error("read broken".into()),StreamCompletion::Eof);
 let v=a.poll_chunks_at(r,t).unwrap();assert_eq!(chunks(&v),"captured-outcaptured-err");assert_terminal_last(&v);assert!(matches!(v.last(),Some(AgentChunk::Failed{message,..}) if message.contains("read broken")));assert!(a.poll_chunks_at(r,t).unwrap().is_empty());
}
#[test] fn proc_t04_deadline_1999_pending_2000_failed_without_extension(){
 let(mut a,p,r,t)=setup();sample(&p,Some(0),"","",StreamCompletion::Open,StreamCompletion::Open);
 assert_eq!(terminals(&a.poll_chunks_at(r,t).unwrap()),0);
 sample(&p,Some(0),"late-one","",StreamCompletion::Open,StreamCompletion::Eof);
 let v=a.poll_chunks_at(r,t+Duration::from_millis(1999)).unwrap();assert_eq!(chunks(&v),"late-one");assert_eq!(terminals(&v),0);
 sample(&p,Some(0),"late-two","",StreamCompletion::Open,StreamCompletion::Eof);
 let v=a.poll_chunks_at(r,t+Duration::from_millis(2000)).unwrap();assert_eq!(chunks(&v),"late-two");assert_terminal_last(&v);assert!(matches!(v.last(),Some(AgentChunk::Failed{message,..})if message.contains("2000")||message.to_lowercase().contains("timeout")||message.to_lowercase().contains("incomplete")));
 assert!(a.poll_chunks_at(r,t+Duration::from_millis(2001)).unwrap().is_empty());assert!(a.start_run(StartRunRequest::cli_dry_run()).is_ok());
}
#[test] fn proc_t05_dual_eof_wins_exact_deadline_tie(){
 let(mut a,p,r,t)=setup();sample(&p,Some(0),"","",StreamCompletion::Open,StreamCompletion::Open);assert_eq!(terminals(&a.poll_chunks_at(r,t).unwrap()),0);
 sample(&p,Some(0),"tail","",StreamCompletion::Eof,StreamCompletion::Eof);
 let v=a.poll_chunks_at(r,t+Duration::from_millis(2000)).unwrap();assert_eq!(chunks(&v),"tail");assert!(matches!(v.last(),Some(AgentChunk::Exited{classification:ExitClassification::Success,..})));
}
#[test] fn proc_t06_cancel_request_idempotent_then_drains_and_restarts(){
 let(mut a,p,r,t)=setup();a.cancel(r).unwrap();a.cancel(r).unwrap();assert_eq!(p.0.lock().unwrap().cancels,1,"cancel should reach direct child once");
 let initial=a.poll_chunks_at(r,t).unwrap();assert_eq!(terminals(&initial),0,"cancel request is not completed drain");assert!(matches!(a.start_run(StartRunRequest::cli_dry_run()),Err(ExecError::Busy(_))));
 sample(&p,Some(-1),"cancel-tail","cancel-error-tail",StreamCompletion::Eof,StreamCompletion::Eof);
 let v=a.poll_chunks_at(r,t+Duration::from_millis(1)).unwrap();assert_eq!(chunks(&v),"cancel-tailcancel-error-tail");assert_terminal_last(&v);assert!(matches!(v.last(),Some(AgentChunk::Exited{classification:ExitClassification::Cancelled,..})));assert!(a.poll_chunks_at(r,t).unwrap().is_empty());assert!(a.start_run(StartRunRequest::cli_dry_run()).is_ok());
}
#[test] fn proc_t07_cancel_after_observed_natural_exit_preserves_classification(){
 let(mut a,p,r,t)=setup();sample(&p,Some(0),"","",StreamCompletion::Open,StreamCompletion::Open);assert_eq!(terminals(&a.poll_chunks_at(r,t).unwrap()),0);a.cancel(r).unwrap();
 assert_eq!(p.0.lock().unwrap().cancels,0,"already observed exit must not be killed/reclassified");
 sample(&p,Some(0),"tail","",StreamCompletion::Eof,StreamCompletion::Eof);let v=a.poll_chunks_at(r,t+Duration::from_millis(1)).unwrap();assert!(matches!(v.last(),Some(AgentChunk::Exited{classification:ExitClassification::Success,..})));
}
#[test] fn proc_t08_nonzero_exit_waits_for_eof(){
 let(mut a,p,r,t)=setup();sample(&p,Some(7),"","",StreamCompletion::Open,StreamCompletion::Open);assert_eq!(terminals(&a.poll_chunks_at(r,t).unwrap()),0);
 sample(&p,Some(7),"","diagnostic",StreamCompletion::Eof,StreamCompletion::Eof);let v=a.poll_chunks_at(r,t+Duration::from_millis(1)).unwrap();assert_eq!(chunks(&v),"diagnostic");assert!(matches!(v.last(),Some(AgentChunk::Exited{classification:ExitClassification::Failure,exit_code:Some(7),..})));
}
#[test] fn proc_t09_running_child_has_no_postexit_deadline(){
 let(mut a,p,r,t)=setup();sample(&p,None,"","",StreamCompletion::Open,StreamCompletion::Open);
 assert_eq!(terminals(&a.poll_chunks_at(r,t).unwrap()),0);assert_eq!(terminals(&a.poll_chunks_at(r,t+Duration::from_secs(100)).unwrap()),0);
}
#[test] fn proc_t10_cancel_error_is_request_error_not_terminal(){
 let(mut a,p,r,t)=setup();p.0.lock().unwrap().cancel_error=true;assert!(a.cancel(r).is_err());assert_eq!(terminals(&a.poll_chunks_at(r,t).unwrap()),0);
 sample(&p,Some(0),"surviving-tail","",StreamCompletion::Eof,StreamCompletion::Eof);let v=a.poll_chunks_at(r,t+Duration::from_millis(1)).unwrap();assert_eq!(chunks(&v),"surviving-tail");assert!(matches!(v.last(),Some(AgentChunk::Exited{classification:ExitClassification::Success,..})));
}

#[test] fn proc_r1_known_read_error_and_wait_error_preserve_tail_then_failed_once(){
 let(mut a,p,r,t)=setup();sample(&p,None,"read-error-tail","stderr-tail",StreamCompletion::Error("controlled reader broken".into()),StreamCompletion::Eof);p.0.lock().unwrap().wait_error=true;
 let v=a.poll_chunks_at(r,t).expect("known reader failure must produce Failed event rather than naked wait Err");
 assert_eq!(chunks(&v),"read-error-tailstderr-tail");assert_terminal_last(&v);assert!(matches!(v.last(),Some(AgentChunk::Failed{message,..})if message.contains("controlled reader broken")));
 assert_eq!(p.0.lock().unwrap().cancels,1,"unknown child exit must request direct-child cleanup once");
 assert!(a.poll_chunks_at(r,t+Duration::from_millis(1)).unwrap().is_empty());assert_eq!(p.0.lock().unwrap().cancels,1);assert!(a.start_run(StartRunRequest::cli_dry_run()).is_ok());
}
