#[path = "../src/dispatch.rs"] mod dispatch;
#[path = "../src/dto.rs"] mod dto;
#[path = "../src/git_index_commit.rs"] mod git_index_commit;
use dispatch::DispatchHost;
use dto::{DocumentAdoptArgs,DocumentAdoptErrorDto as E};
use sgenaxis_ports::{FileSystemPort,PortError};
use std::sync::{Mutex,atomic::{AtomicBool,AtomicUsize,Ordering}};
use std::collections::{BTreeMap,BTreeSet};
const ROOT:&str="/doc-entry/A";
const SOURCE:&str="/doc-entry/A/docs/sample.ess";
const MANIFEST:&str="/doc-entry/A/.sgenaxis/project-manifest.json";
const UUID:&str="a2b7aa65-87e8-4ad1-9f4c-f191401a0c11";
#[derive(Default)]
struct Fs { files:Mutex<BTreeMap<String,Vec<u8>>>,dirs:Mutex<BTreeSet<String>>,probes:AtomicUsize,reads:AtomicUsize,writes:AtomicUsize,fail_write:AtomicBool,fail_readback:AtomicBool,fail_exists:AtomicBool,fail_is_file:AtomicBool }
impl Fs {fn put(&self,p:&str,b:&[u8]){self.files.lock().unwrap().insert(p.into(),b.into());} fn bytes(&self,p:&str)->Option<Vec<u8>>{self.files.lock().unwrap().get(p).cloned()}}
impl FileSystemPort for Fs {
 fn exists(&self,p:&str)->Result<bool,PortError>{self.probes.fetch_add(1,Ordering::SeqCst);if self.fail_exists.load(Ordering::SeqCst){return Err(PortError::Io("exists".into()))}Ok(self.bytes(p).is_some()||self.dirs.lock().unwrap().contains(p))}
 fn read(&self,p:&str)->Result<Vec<u8>,PortError>{self.reads.fetch_add(1,Ordering::SeqCst);if self.fail_readback.load(Ordering::SeqCst)&&self.writes.load(Ordering::SeqCst)>0&&p==MANIFEST{return Err(PortError::Io("readback".into()))}self.bytes(p).ok_or_else(||PortError::NotFound(p.into()))}
 fn read_to_string(&self,p:&str)->Result<String,PortError>{String::from_utf8(self.read(p)?).map_err(|_|PortError::Io("utf8".into()))}
 fn write_atomic(&self,p:&str,b:&[u8])->Result<(),PortError>{if self.fail_write.load(Ordering::SeqCst){return Err(PortError::Io("before replace".into()))}self.put(p,b);self.writes.fetch_add(1,Ordering::SeqCst);Ok(())}
 fn create_dir_all(&self,_:&str)->Result<(),PortError>{Ok(())}
 fn is_file(&self,p:&str)->Result<bool,PortError>{self.probes.fetch_add(1,Ordering::SeqCst);if self.fail_is_file.load(Ordering::SeqCst){return Err(PortError::Io("is_file".into()))}Ok(self.bytes(p).is_some())}
 fn remove_file(&self,_:&str)->Result<(),PortError>{panic!("adoption must not delete")}
}
fn fixture()->(DispatchHost,Fs,DocumentAdoptArgs){let mut h=DispatchHost::new();let id=h.document_test_register(ROOT);let fs=Fs::default();fs.put(SOURCE,b"source bytes stay unchanged");(h,fs,DocumentAdoptArgs{expected_project_id:id,reference:"docs/sample.ess".into()})}
#[test]
fn doc_e01_adopts_and_preserves_source(){let(mut h,fs,a)=fixture();let v=h.project_document_adopt(&fs,ROOT,&a,UUID,"main",true).unwrap();assert_eq!(v.outcome,"Adopted");assert_eq!(v.document_id,UUID);assert_eq!(fs.bytes(SOURCE).unwrap(),b"source bytes stay unchanged");assert!(fs.bytes(MANIFEST).is_some());}
#[test]
fn doc_e02_untrusted_callers_reject_before_reads(){let(mut h,fs,a)=fixture();for(label,local)in[("secondary",true),("main",false)]{assert_eq!(h.project_document_adopt(&fs,ROOT,&a,UUID,label,local),Err(E::UnauthorizedCaller));}assert_eq!(fs.reads.load(Ordering::SeqCst),0);assert_eq!(fs.writes.load(Ordering::SeqCst),0);}
#[test]
fn doc_e02_unbound_and_stale_projects_reject_before_reads(){let(mut h,fs,mut a)=fixture();assert_eq!(h.project_document_adopt(&fs,"",&a,UUID,"main",true),Err(E::ProjectNotBound));assert_eq!(h.project_document_adopt(&fs,"/doc-entry/B",&a,UUID,"main",true),Err(E::ProjectMismatch));a.expected_project_id="unknown".into();assert_eq!(h.project_document_adopt(&fs,ROOT,&a,UUID,"main",true),Err(E::ProjectNotBound));assert_eq!(fs.reads.load(Ordering::SeqCst),0);}
#[test]
fn doc_e03_repeat_is_idempotent_without_write(){let(mut h,fs,a)=fixture();h.project_document_adopt(&fs,ROOT,&a,UUID,"main",true).unwrap();let before=fs.bytes(MANIFEST);let writes=fs.writes.load(Ordering::SeqCst);let v=h.project_document_adopt(&fs,ROOT,&a,"b2b7aa65-87e8-4ad1-9f4c-f191401a0c11","main",true).unwrap();assert_eq!(v.outcome,"AlreadyAdopted");assert_eq!(v.document_id,UUID);assert_eq!(fs.writes.load(Ordering::SeqCst),writes);assert_eq!(fs.bytes(MANIFEST),before);}
#[test]
fn doc_e04_revision_conflict_preserves_manifest(){let(mut h,fs,a)=fixture();h.project_document_adopt(&fs,ROOT,&a,UUID,"main",true).unwrap();let before=fs.bytes(MANIFEST);fs.put(SOURCE,b"changed");assert_eq!(h.project_document_adopt(&fs,ROOT,&a,UUID,"main",true),Err(E::RevisionConflict));assert_eq!(fs.bytes(MANIFEST),before);}
#[test]
fn doc_e04_atomic_failure_preserves_manifest(){let(mut h,fs,a)=fixture();fs.put(MANIFEST,br#"{"schema":"sgenaxis.project-manifest","schemaVersion":1,"documents":[]}"#);let before=fs.bytes(MANIFEST);fs.fail_write.store(true,Ordering::SeqCst);assert!(matches!(h.project_document_adopt(&fs,ROOT,&a,UUID,"main",true),Err(E::Write(_))));assert_eq!(fs.bytes(MANIFEST),before);}
#[test]
fn doc_e05_readback_failure_reports_uncertain_commit(){let(mut h,fs,a)=fixture();fs.fail_readback.store(true,Ordering::SeqCst);assert_eq!(h.project_document_adopt(&fs,ROOT,&a,UUID,"main",true),Err(E::DurabilityUnverified));assert!(fs.bytes(MANIFEST).is_some());assert_eq!(fs.bytes(SOURCE).unwrap(),b"source bytes stay unchanged");}
#[test]
fn doc_dto_rejects_caller_root_or_identity_authority(){assert!(serde_json::from_value::<DocumentAdoptArgs>(serde_json::json!({"expected_project_id":"A","reference":"docs/a.ess","document_id":UUID})).is_err());}
#[test]
fn doc_e02_fresh_host_requires_existing_work_registration() {
    let mut host = DispatchHost::new();
    let fs = Fs::default();
    let args = DocumentAdoptArgs {
        expected_project_id: sgenaxis_work::ProjectId::from_canonical_root(ROOT).to_string(),
        reference: "docs/sample.ess".into(),
    };
    assert_eq!(host.project_document_adopt(&fs, ROOT, &args, UUID, "main", true), Err(E::ProjectNotBound));
    assert_eq!(fs.reads.load(Ordering::SeqCst), 0);
    assert_eq!(fs.writes.load(Ordering::SeqCst), 0);
}

use dto::{DocumentPrepareArgs,DocumentPrepareErrorDto as P};
fn prep_fixture()->(DispatchHost,Fs,DocumentPrepareArgs){let fs=Fs::default();fs.dirs.lock().unwrap().insert(ROOT.into());(DispatchHost::new(),fs,DocumentPrepareArgs{expected_project_root:ROOT.into()})}
#[test]
fn ui02_prepare_registers_selects_and_repeats_without_manifest_write(){let(mut h,fs,a)=prep_fixture();assert_eq!(h.document_test_projection().0,0);let first=h.project_document_prepare(&fs,ROOT,&a,"main",true).unwrap();assert_eq!(first.project_root,ROOT);assert_eq!(h.document_test_projection(),(1,Some(first.project_id.clone())));let second=h.project_document_prepare(&fs,ROOT,&a,"main",true).unwrap();assert_eq!(first,second);assert_eq!(h.document_test_projection().0,1);assert_eq!(fs.writes.load(Ordering::SeqCst),0);assert_eq!(fs.reads.load(Ordering::SeqCst),0);}
#[test]
fn ui02_caller_rejection_precedes_root_or_filesystem(){let(mut h,fs,a)=prep_fixture();for(label,local)in[("secondary",true),("main",false)]{assert_eq!(h.project_document_prepare(&fs,"",&a,label,local),Err(P::UnauthorizedCaller));}assert_eq!(fs.probes.load(Ordering::SeqCst),0);assert_eq!(h.document_test_projection().0,0);}
#[test]
fn ui02_unbound_and_changed_root_precede_filesystem(){let(mut h,fs,a)=prep_fixture();assert_eq!(h.project_document_prepare(&fs,"",&a,"main",true),Err(P::ProjectNotBound));assert_eq!(h.project_document_prepare(&fs,"/other",&a,"main",true),Err(P::ProjectChanged));assert_eq!(fs.probes.load(Ordering::SeqCst),0);assert_eq!(h.document_test_projection().0,0);}
#[test]
fn ui02_unavailable_root_never_registers_or_changes_selection(){for kind in ["missing","file","exists_error","is_file_error"]{let(mut h,fs,a)=prep_fixture();h.document_test_register("/prior");let before=h.document_test_projection();match kind{"missing"=>{fs.dirs.lock().unwrap().clear();},"file"=>fs.put(ROOT,b"file"),"exists_error"=>fs.fail_exists.store(true,Ordering::SeqCst),_=>fs.fail_is_file.store(true,Ordering::SeqCst)}assert_eq!(h.project_document_prepare(&fs,ROOT,&a,"main",true),Err(P::RootUnavailable),"{kind}");assert_eq!(h.document_test_projection(),before);assert_eq!(fs.writes.load(Ordering::SeqCst),0);}}
#[test]
fn ui02_all_busy_predicates_reject_before_filesystem(){for kind in ["run","lease_flag","capture","active_lease"]{let(mut h,fs,a)=prep_fixture();h.document_test_busy(kind,ROOT);let before=h.document_test_projection();assert_eq!(h.project_document_prepare(&fs,ROOT,&a,"main",true),Err(P::Busy),"{kind}");assert_eq!(fs.probes.load(Ordering::SeqCst),0);assert_eq!(h.document_test_projection(),before);}}
#[test]
fn ui02_reserved_and_unresolved_keep_work_error_category(){for kind in ["reserved","unresolved"]{let(mut h,fs,a)=prep_fixture();h.document_test_busy(kind,ROOT);let before=h.document_test_projection();let result=h.project_document_prepare(&fs,ROOT,&a,"main",true);match result{Err(P::WorkspaceRejected{reason})=>assert!(reason.contains(if kind=="reserved"{"RunBindingReserved"}else{"RunBindingUnresolved"}),"{reason}"),other=>panic!("{kind}: {other:?}")}assert_eq!(h.document_test_projection(),before);assert_eq!(fs.writes.load(Ordering::SeqCst),0);}}
#[test]
fn ui02_prepare_may_select_bound_project_without_rewriting_settings(){let(mut h,fs,a)=prep_fixture();h.document_test_register(ROOT);let prior=h.document_test_register("/prior");assert_eq!(h.document_test_projection().1,Some(prior));let p=h.project_document_prepare(&fs,ROOT,&a,"main",true).unwrap();assert_eq!(h.document_test_projection().1,Some(p.project_id));assert_eq!(p.project_root,ROOT);}
#[test]
fn ui02_windows_and_unicode_root_spellings_match_existing_work_identity(){for bound in ["C:\\Fixture\\Ä","c:/fixture/ä/","C:/FIXTURE/Ä"]{let mut h=DispatchHost::new();let id=h.document_test_register("C:\\Fixture\\Ä");let fs=Fs::default();fs.put("C:/Fixture/Ä/docs/sample.ess",b"unchanged");let a=DocumentAdoptArgs{expected_project_id:id,reference:"docs/sample.ess".into()};assert!(h.project_document_adopt(&fs,bound,&a,UUID,"main",true).is_ok(),"{bound}");}}
#[test]
fn ui02_sibling_and_drive_mismatch_still_reject_before_reads(){let(mut h,fs,a)=fixture();for root in ["/doc-entry/AB","D:/doc-entry/A"]{assert_eq!(h.project_document_adopt(&fs,root,&a,UUID,"main",true),Err(E::ProjectMismatch));}assert_eq!(fs.reads.load(Ordering::SeqCst),0);}
