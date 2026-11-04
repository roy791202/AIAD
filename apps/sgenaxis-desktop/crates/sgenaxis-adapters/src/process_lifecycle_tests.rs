//! Independent reader status and real direct-child/inherited-pipe tests.
use super::*;
use sgenaxis_ports::StreamCompletion;
use std::sync::mpsc;
use std::time::{Duration,Instant};
enum ReadStep {Bytes(Vec<u8>),Interrupted,Error,Eof}
struct ControlledRead(mpsc::Receiver<ReadStep>,mpsc::Sender<()>);
impl Drop for ControlledRead {fn drop(&mut self){let _=self.1.send(());}}
impl Read for ControlledRead {
 fn read(&mut self,out:&mut[u8])->std::io::Result<usize>{match self.0.recv().expect("fixture reader control closed"){
  ReadStep::Bytes(bytes)=>{assert!(bytes.len()<=out.len());out[..bytes.len()].copy_from_slice(&bytes);Ok(bytes.len())},
  ReadStep::Interrupted=>Err(std::io::Error::new(std::io::ErrorKind::Interrupted,"retry")),
  ReadStep::Error=>Err(std::io::Error::new(std::io::ErrorKind::Other,"controlled read failure")),ReadStep::Eof=>Ok(0)
 }}
}
fn wait_state(c:&Arc<Mutex<PipeCapture>>,predicate:impl Fn(&PipeCapture)->bool){let until=Instant::now()+Duration::from_secs(5);loop{if predicate(&c.lock().unwrap()){return;}assert!(Instant::now()<until,"HARNESS/status failure: expected reader state not observed");std::thread::yield_now();}}
#[test] fn proc_adapter_open_empty_is_not_eof_then_tail_and_sticky_eof(){
 let c=Arc::new(Mutex::new(PipeCapture::default()));let(tx,rx)=mpsc::channel();let(done_tx,done_rx)=mpsc::channel();spawn_pipe_reader(ControlledRead(rx,done_tx),c.clone());
 let(data,status)=take_utf8(&c);assert!(data.is_empty());assert_eq!(status,StreamCompletion::Open);
 tx.send(ReadStep::Bytes(b"tail".to_vec())).unwrap();wait_state(&c,|s|s.bytes==b"tail");
 let(data,status)=take_utf8(&c);assert_eq!(data,"tail");assert_eq!(status,StreamCompletion::Open);
 tx.send(ReadStep::Eof).unwrap();done_rx.recv_timeout(Duration::from_secs(5)).expect("HARNESS: reader did not exit after EOF");
 let(data,status)=take_utf8(&c);assert!(data.is_empty());assert_eq!(status,StreamCompletion::Eof);assert_eq!(take_utf8(&c).1,StreamCompletion::Eof);
}
#[test] fn proc_adapter_interrupted_retries_and_error_preserves_partial_bytes(){
 let c=Arc::new(Mutex::new(PipeCapture::default()));let(tx,rx)=mpsc::channel();let(done_tx,done_rx)=mpsc::channel();
 tx.send(ReadStep::Interrupted).unwrap();tx.send(ReadStep::Bytes(b"partial".to_vec())).unwrap();tx.send(ReadStep::Error).unwrap();
 spawn_pipe_reader(ControlledRead(rx,done_tx),c.clone());done_rx.recv_timeout(Duration::from_secs(5)).expect("HARNESS: reader did not exit after error");
 let(data,status)=take_utf8(&c);assert_eq!(data,"partial");assert!(matches!(status,StreamCompletion::Error(s)if s.contains("controlled read failure")));assert!(matches!(take_utf8(&c).1,StreamCompletion::Error(_)));
}
#[test] fn proc_adapter_poison_is_error_not_empty_success(){
 let c=Arc::new(Mutex::new(PipeCapture::default()));let other=c.clone();let _=std::thread::spawn(move||{let _g=other.lock().unwrap();panic!("intentional mutex poison");}).join();let mut p=StdProcess::new();p.children.insert(1,TrackedChild{child:None,exit_code:Some(0),stdout:c,stderr:Arc::new(Mutex::new(PipeCapture::default()))});assert!(p.try_read(ProcessId(1)).is_err(),"poison must be an observable PortError");
}
fn helper_exe()->std::path::PathBuf {
 static HELPER:std::sync::OnceLock<std::path::PathBuf>=std::sync::OnceLock::new();
 HELPER.get_or_init(||{
  let dir=std::env::temp_dir().join(format!("sgenaxis-process-helper-{}",std::process::id()));std::fs::create_dir_all(&dir).unwrap();
  let source=dir.join("helper.rs");let exe=dir.join(if cfg!(windows){"helper.exe"}else{"helper"});
  std::fs::write(&source,r#"use std::{io::Write,process::{Command,Stdio},time::Duration};fn main(){let mode=std::env::args().nth(1).unwrap_or_default();if mode=="hold"{let gate=std::env::args().nth(2).unwrap();let until=std::time::Instant::now()+Duration::from_secs(10);while !std::path::Path::new(&gate).exists(){assert!(std::time::Instant::now()<until,"fixture gate timeout");std::thread::sleep(Duration::from_millis(1));}print!("descendant-tail");std::io::stdout().flush().unwrap();return;}if mode=="inherit"{let _=Command::new(std::env::current_exe().unwrap()).arg("hold").arg(std::env::args().nth(2).unwrap()).stdout(Stdio::inherit()).stderr(Stdio::inherit()).spawn().unwrap();print!("parent-tail");std::io::stdout().flush().unwrap();return;}print!("stdout-final");eprint!("stderr-final");}"#).unwrap();
  let rustc=std::env::var_os("RUSTC").map(std::path::PathBuf::from).or_else(||std::env::var_os(if cfg!(windows){"USERPROFILE"}else{"HOME"}).map(|h|std::path::PathBuf::from(h).join(if cfg!(windows){".cargo/bin/rustc.exe"}else{".cargo/bin/rustc"}))).unwrap_or_else(||"rustc".into());
  let output=Command::new(rustc).arg(&source).arg("-o").arg(&exe).output().expect("HARNESS: rustc helper compiler unavailable");assert!(output.status.success(),"HARNESS helper compile failed: {}",String::from_utf8_lossy(&output.stderr));exe
 }).clone()
}
#[test] fn proc_adapter_real_child_both_final_streams_before_explicit_eof(){
 let mut p=StdProcess::new();let exe=helper_exe();let id=p.start(exe.to_str().unwrap(),&[],None).unwrap();let deadline=Instant::now()+Duration::from_secs(5);let(mut out,mut err)=(String::new(),String::new());let mut code=None;
 loop{let s=p.try_read(id).unwrap();out.push_str(&s.stdout);err.push_str(&s.stderr);if let Some(c)=p.try_wait(id).unwrap(){code=Some(c);}if code.is_some()&&s.stdout_completion==StreamCompletion::Eof&&s.stderr_completion==StreamCompletion::Eof{break;}assert!(Instant::now()<deadline,"real helper/reader failed to settle");std::thread::yield_now();}
 assert_eq!(code,Some(0));assert_eq!(out,"stdout-final");assert_eq!(err,"stderr-final");assert_eq!(p.try_wait(id).unwrap(),Some(0));assert!(p.try_read(id).unwrap().is_empty());
}
struct GateRelease {path:std::path::PathBuf,armed:bool}
impl Drop for GateRelease {fn drop(&mut self){if self.armed {let _=std::fs::write(&self.path,b"release-on-failure");}}}
#[test] fn proc_adapter_real_inherited_pipe_exit_visible_before_eof(){
 let mut p=StdProcess::new();let exe=helper_exe();let gate=exe.parent().unwrap().join("release-inherited-pipe");assert!(!gate.exists(),"fixture gate unexpectedly exists");let mut release=GateRelease{path:gate.clone(),armed:true};let id=p.start(exe.to_str().unwrap(),&["inherit",gate.to_str().unwrap()],None).unwrap();let deadline=Instant::now()+Duration::from_secs(5);let mut out=String::new();
 loop{let s=p.try_read(id).unwrap();out.push_str(&s.stdout);if p.try_wait(id).unwrap().is_some(){assert_eq!(s.stdout_completion,StreamCompletion::Open,"descendant deliberately still holds stdout");break;}assert!(Instant::now()<deadline,"parent did not exit");std::thread::yield_now();}
 std::fs::write(&gate,b"release").unwrap();
 loop{let start=Instant::now();let s=p.try_read(id).unwrap();assert!(start.elapsed()<Duration::from_millis(200),"try_read blocked on inherited pipe");out.push_str(&s.stdout);if s.stdout_completion==StreamCompletion::Eof&&s.stderr_completion==StreamCompletion::Eof{break;}assert!(Instant::now()<deadline,"inherited reader failed to settle");std::thread::yield_now();}
 assert_eq!(out,"parent-taildescendant-tail");release.armed=false;std::fs::remove_file(gate).unwrap();
}
