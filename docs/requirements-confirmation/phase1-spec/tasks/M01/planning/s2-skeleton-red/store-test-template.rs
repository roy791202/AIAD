//! M01-S2 shared-state Port contract tests; no native filesystem proof.
use sgenaxis_host::project_definition::*;
use sgenaxis_host::project_preferences::PreferenceChoice;
use sgenaxis_ports::*;
use sgenaxis_work::project_definition::*;
use std::collections::BTreeMap;
use std::sync::{Arc, Mutex};
const ROOT: &str = "C:/owned-fixture-parent/Project-A";
const PATH: &str = "C:/owned-fixture-parent/Project-A/.sgenaxis/project-definition.json";
const PREF: &str = "C:/owned-fixture-parent/Project-A/.sgenaxis/preferences.json";
const OLD: &[u8] = BASE_BYTES;
fn base() -> ProjectDefinition { BASE_DOMAIN }
fn context() -> DefinitionAuthorityContext { DefinitionAuthorityContext {selection_id:"selection-A".into(),session_id:"session-A".into(),owner_window:"main".into()} }
fn new_location() -> DefinitionLocation { DefinitionLocation::NewProject{canonical_parent:"C:/owned-fixture-parent".into(),single_name:"Project-A".into()} }
fn existing() -> DefinitionLocation { DefinitionLocation::ExistingProject{canonical_root:ROOT.into()} }
fn digest(b:&[u8])->String {format!("sha256:{}",sgenaxis_spec::packet::source_sha256(b))}
fn raw_digest(b:&[u8])->RawDefinitionDigest { RawDefinitionDigest::try_from_text(&digest(b)).expect("fixture digest is valid") }
#[derive(Debug,Clone,PartialEq,Eq)] enum Node {Dir,File(Vec<u8>)}
#[derive(Default)] struct State {tree:BTreeMap<String,Node>,log:Vec<String>,fault:Option<(String,CommitError)>,receipt_fault:Option<(String,u8)>,reads:usize,read_change:Option<Result<Vec<u8>,PortError>>,first_read_error:Option<PortError>,race_root:bool}
#[derive(Clone,Default)] struct Rig(Arc<Mutex<State>>);
impl Rig {
 fn seed(&self,p:&str,node:Node){self.0.lock().unwrap().tree.insert(p.into(),node);}
 fn tree(&self)->BTreeMap<String,Node>{self.0.lock().unwrap().tree.clone()}
 fn log(&self)->Vec<String>{self.0.lock().unwrap().log.clone()}
 fn fail(&self,op:&str,e:CommitError){self.0.lock().unwrap().fault=Some((op.into(),e));}
 fn call(&self,op:&str)->Result<(),CommitError>{let mut s=self.0.lock().unwrap();s.log.push(op.into());if let Some((key,e))=&s.fault {if key==op{return Err(e.clone())}}Ok(())}
 fn from_existing()->Self {let r=Self::default();r.seed(ROOT,Node::Dir);r.seed(&format!("{ROOT}/.sgenaxis"),Node::Dir);r.seed(PATH,Node::File(OLD.to_vec()));r}
}
impl FileSystemPort for Rig {
 fn exists(&self,p:&str)->Result<bool,PortError>{self.0.lock().unwrap().log.push(format!("exists:{p}"));Ok(self.tree().contains_key(p))}
 fn is_file(&self,p:&str)->Result<bool,PortError>{self.0.lock().unwrap().log.push(format!("is_file:{p}"));Ok(matches!(self.tree().get(p),Some(Node::File(_))))}
 fn read(&self,p:&str)->Result<Vec<u8>,PortError>{let mut s=self.0.lock().unwrap();s.log.push(format!("read:{p}"));s.reads+=1;if s.reads==1{if let Some(e)=&s.first_read_error{return Err(e.clone())}}if s.reads>1{if let Some(v)=&s.read_change{return v.clone()}}match s.tree.get(p){Some(Node::File(b))=>Ok(b.clone()),_=>Err(PortError::NotFound(p.into()))}}
 fn read_to_string(&self,p:&str)->Result<String,PortError>{String::from_utf8(self.read(p)?).map_err(|e|PortError::Other(e.to_string()))}
 fn write_atomic(&self,p:&str,_:&[u8])->Result<(),PortError>{self.0.lock().unwrap().log.push(format!("FORBIDDEN_write:{p}"));Err(PortError::Other("forbidden HOST write".into()))}
 fn create_dir_all(&self,p:&str)->Result<(),PortError>{self.0.lock().unwrap().log.push(format!("FORBIDDEN_mkdir:{p}"));Err(PortError::Other("forbidden recursive create".into()))}
 fn remove_file(&self,p:&str)->Result<(),PortError>{self.0.lock().unwrap().log.push(format!("FORBIDDEN_remove:{p}"));Err(PortError::Other("forbidden delete".into()))}
}
impl FileCommitPort for Rig {
 fn create_directory_exclusive(&self,parent:&str,name:&str)->Result<String,CommitError>{let p=format!("{}/{name}",parent.trim_end_matches(['/', '\\']));self.call(&format!("mkdir:{p}"))?;let mut s=self.0.lock().unwrap();if s.race_root&&p==ROOT{s.tree.insert(p.clone(),Node::Dir);}if s.tree.contains_key(&p){return Err(CommitError::AlreadyExists{path:p})}s.tree.insert(p.clone(),Node::Dir);Ok(p)}
 fn acquire_write(&self,p:&str)->Result<Box<dyn FileWriteLease>,CommitError>{self.call(&format!("acquire:{p}"))?;Ok(Box::new(Lease{rig:self.clone(),path:p.into()}))}
}
struct Lease {rig:Rig,path:String}
impl FileWriteLease for Lease {
 fn read_current(&self)->Result<Option<Vec<u8>>,CommitError>{self.rig.call(&format!("current:{}",self.path))?;Ok(match self.rig.tree().get(&self.path){Some(Node::File(b))=>Some(b.clone()),_=>None})}
 fn replace_checked(&mut self,expected:Option<&str>,bytes:&[u8])->Result<CommitReceipt,CommitError>{self.rig.call(&format!("replace:{}",self.path))?;let mut s=self.rig.0.lock().unwrap();let old=match s.tree.get(&self.path){Some(Node::File(b))=>Some(digest(b)),_=>None};if old.as_deref()!=expected{return Err(CommitError::Conflict{expected:expected.map(String::from),observed:old})}s.tree.insert(self.path.clone(),Node::File(bytes.to_vec()));let mut proof=CommitReceipt{target_path:self.path.clone(),previous_digest:old,committed_digest:digest(bytes),transaction_id:"0123456789abcdef0123456789abcdef".into()};if let Some((p,n))=&s.receipt_fault{if p==&self.path{match n {0=>proof.target_path="C:/wrong".into(),1=>proof.committed_digest=digest(b"wrong"),2=>proof.previous_digest=Some(digest(b"wrong")),_=>proof.transaction_id="bad".into()}}}Ok(proof)}
}
fn binding(r:&Rig,loc:DefinitionLocation,baseline:DefinitionBaseline,prefs:PreparedPreferencePlan)->DefinitionBinding{
 let result=bind_definition(r,context(),loc,base().project_uuid,baseline,prefs,&[]);
 assert!(result.is_ok(),"product binding boundary rejected valid fixture: {result:?}");result.unwrap()
}
fn new_binding(r:&Rig)->DefinitionBinding{binding(r,new_location(),DefinitionBaseline::Absent,PreparedPreferencePlan::Skip)}
fn old_binding(r:&Rig)->DefinitionBinding{binding(r,existing(),DefinitionBaseline::Present{raw_digest:raw_digest(OLD),revision:DefinitionRevision(3),project_uuid:base().project_uuid},PreparedPreferencePlan::Skip)}
fn save_new(r:&Rig)->Result<DefinitionSaveReceipt,DefinitionStoreError>{save_definition(r,r,&new_binding(r),None,&base())}
fn storage(stage:CommitStage,p:&str)->CommitError{CommitError::Storage{stage,path:p.into(),reason:"injected".into()}}
fn recovery(p:&str)->CommitError{CommitError::RecoveryRequired{target_path:p.into(),journal_path:format!("{p}.journal"),old_version_path:Some(format!("{p}.old")),new_version_path:Some(format!("{p}.new")),reason:"uncertain".into()}}
fn assert_no_forbidden(r:&Rig){assert!(!r.log().iter().any(|x|x.starts_with("FORBIDDEN")),"{:?}",r.log());}
fn receipt(r:&Rig,b:DefinitionBinding,d:ProjectDefinition,expected:Option<&str>)->DefinitionSaveReceipt{let result=save_definition(r,r,&b,expected,&d);assert!(result.is_ok(),"save boundary: {result:?}");let p=result.unwrap();assert_eq!(p.definition.project_uuid,d.project_uuid);assert_eq!(p.definition.persisted_revision,d.definition_revision);assert_eq!(p.definition.relative_path,".sgenaxis/project-definition.json");assert_eq!(p.canonical_root,ROOT);assert_eq!(p.definition.transaction_id.len(),32);let bytes=match r.tree().get(PATH).unwrap(){Node::File(b)=>b.clone(),_=>panic!("definition is not a file")};assert_eq!(p.definition.raw_digest.as_str(),digest(&bytes));assert_eq!(decode_definition(&bytes),Ok(d));assert_no_forbidden(r);p}
fn prepared_preset()->PreparedPreferencePlan{
 let p=sgenaxis_spec::project_preferences::preset("balanced").expect("fixture preset");let b=serde_json::to_vec_pretty(&p).expect("fixture preference JSON");PreparedPreferencePlan::Preset{preset_id:"balanced".into(),digest:raw_digest(&b),encoded_bytes:b}
}
fn with_prefs(r:&Rig)->(DefinitionBinding,ProjectDefinition){let b=binding(r,new_location(),DefinitionBaseline::Absent,prepared_preset());let mut d=base();d.draft.preference_source=PreferenceSource::Preset;(b,d)}
#[test] fn fixture_health_same_state_receipts_and_faults(){let r=Rig::default();let p=r.create_directory_exclusive("C:/owned-fixture-parent","Project-A").unwrap();assert_eq!(p,ROOT);let mut l=r.acquire_write(PATH).unwrap();assert_eq!(l.read_current(),Ok(None));let proof=l.replace_checked(None,OLD).unwrap();assert_eq!(proof.committed_digest,digest(OLD));assert_eq!(r.read(PATH).unwrap(),OLD);assert!(matches!(l.replace_checked(None,b"changed"),Err(CommitError::Conflict{..})));let before=r.tree();r.fail(&format!("replace:{PATH}"),recovery(PATH));assert!(matches!(l.replace_checked(Some(&digest(OLD)),b"changed"),Err(CommitError::RecoveryRequired{..})));assert_eq!(r.tree(),before);}
