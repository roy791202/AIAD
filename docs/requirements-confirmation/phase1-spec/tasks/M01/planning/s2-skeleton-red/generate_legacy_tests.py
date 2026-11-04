from pathlib import Path
import json,re
import generate_codec_tests as codec
HERE=Path(__file__).parent
H=codec.ROOT/'apps/sgenaxis-desktop/crates/sgenaxis-host'
source='''//! Deprecated creation entries must fail before any filesystem access.
use sgenaxis_host::{project_new::*,project_preferences::*};
use sgenaxis_host::error::HostError;
use sgenaxis_ports::{FileSystemPort,PortError};
use sgenaxis_adapters::FakeFileSystem;
use std::sync::Mutex;
struct Spy{fs:FakeFileSystem,calls:Mutex<Vec<String>>}
impl Spy{fn new()->Self{Self{fs:FakeFileSystem::new(),calls:Mutex::new(vec![])}}fn hit(&self,s:&str){self.calls.lock().unwrap().push(s.into());}}
impl FileSystemPort for Spy{
fn exists(&self,p:&str)->Result<bool,PortError>{self.hit("exists");self.fs.exists(p)}
fn is_file(&self,p:&str)->Result<bool,PortError>{self.hit("is_file");self.fs.is_file(p)}
fn read(&self,p:&str)->Result<Vec<u8>,PortError>{self.hit("read");self.fs.read(p)}
fn read_to_string(&self,p:&str)->Result<String,PortError>{self.hit("read_to_string");self.fs.read_to_string(p)}
fn write_atomic(&self,p:&str,b:&[u8])->Result<(),PortError>{self.hit("write");self.fs.write_atomic(p,b)}
fn create_dir_all(&self,p:&str)->Result<(),PortError>{self.hit("mkdir");self.fs.create_dir_all(p)}
fn remove_file(&self,p:&str)->Result<(),PortError>{self.hit("remove");self.fs.remove_file(p)}
}
'''
cases=[]
for n in range(91,100):
 route=(n-91)//3;kind=(n-91)%3
 body='let s=Spy::new();'
 if kind==1:body+='s.fs.seed("C:/parent/Project-A",b"original file");'
 if kind==2:body+='s.fs.create_dir_all("C:/parent/Project-A").unwrap();s.fs.seed("C:/parent/Project-A/keep.ess",b"original document");'
 body+='let before=(s.fs.exists("C:/parent/Project-A").unwrap(),s.fs.is_file("C:/parent/Project-A").unwrap(),s.fs.read("C:/parent/Project-A"),s.fs.read("C:/parent/Project-A/keep.ess"));let count=(s.fs.write_count(),s.fs.mkdir_count());'
 call=['create_new_project_root(&s,"C:/parent/Project-A")','create_new_project_under(&s,"C:/parent","Project-A")','create_project_with_preferences(&s,"C:/parent/Project-A",PreferenceChoice::Skip)'][route]
 body+='let result='+call+';'
 if route<2:body+='assert!(matches!(result,Err(HostError::Settings(ref m)) if m.starts_with("WIZARD_REQUIRED:")),"deprecated entry denial: {result:?}");'
 else:body+='assert_eq!(result,Err(ProjectPreferenceError::WizardRequired));'
 body+='assert!(s.calls.lock().unwrap().is_empty(),"even reads forbidden");assert_eq!((s.fs.write_count(),s.fs.mkdir_count()),count);assert_eq!((s.fs.exists("C:/parent/Project-A").unwrap(),s.fs.is_file("C:/parent/Project-A").unwrap(),s.fs.read("C:/parent/Project-A"),s.fs.read("C:/parent/Project-A/keep.ess")),before);'
 name=f't{n:03}_deprecated';source+='\n#[test] fn '+name+'(){'+body+'}\n';cases.append({'test':name,'plan':f'M01-S2-T{n:03}','target':'phase1_project_creation_legacy'})
for i,name in enumerate(['','..','a/b']):
 source+=f'\n#[test] fn t100_name_{i}(){{let s=Spy::new();assert!(matches!(create_new_project_under(&s,"C:/parent",{codec.q(name)}),Err(HostError::Settings(ref m)) if !m.starts_with("WIZARD_REQUIRED:")));assert!(s.calls.lock().unwrap().is_empty());}}\n'
 cases.append({'test':f't100_name_{i}','plan':'M01-S2-T100','target':'phase1_project_creation_legacy'})
source+='\n#[test] fn t100_demo(){let s=Spy::new();assert!(matches!(create_new_project_root(&s,"/demo/root"),Err(HostError::Settings(ref m)) if m.contains("/demo/root")&&!m.starts_with("WIZARD_REQUIRED:")));assert!(s.calls.lock().unwrap().is_empty());}\n'
cases.append({'test':'t100_demo','plan':'M01-S2-T100','target':'phase1_project_creation_legacy'})
(H/'tests/phase1_project_creation_legacy.rs').write_text(source,encoding='utf-8')
(HERE/'legacy-test-map.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
# Three named unit expectations change under Owner-adopted migration, bodies only.
p=H/'src/project_new.rs';s=p.read_text(encoding='utf-8')
for name,body in {
 'create_via_fake_fs':'let fs=FakeFileSystem::new();let result=create_new_project_root(&fs,"/work/new-proj");assert!(matches!(result,Err(HostError::Settings(ref m)) if m.starts_with("WIZARD_REQUIRED:")));assert!(!fs.exists("/work/new-proj").unwrap());assert_eq!(fs.mkdir_count(),0);assert_eq!(fs.write_count(),0);',
 'create_under_parent_name':'let fs=FakeFileSystem::new();let result=create_new_project_under(&fs,"/work","MyProj");assert!(matches!(result,Err(HostError::Settings(ref m)) if m.starts_with("WIZARD_REQUIRED:")));assert!(!fs.exists("/work/MyProj").unwrap());assert_eq!(fs.mkdir_count(),0);assert_eq!(fs.write_count(),0);',
 'create_replaces_existing_file_residue':'let fs=FakeFileSystem::new();fs.seed("/work/NewProject",b"original");let result=create_new_project_root(&fs,"/work/NewProject");assert!(matches!(result,Err(HostError::Settings(ref m)) if m.starts_with("WIZARD_REQUIRED:")));assert_eq!(fs.read("/work/NewProject").unwrap(),b"original");assert!(fs.is_file("/work/NewProject").unwrap());assert_eq!(fs.mkdir_count(),0);assert_eq!(fs.write_count(),0);'
}.items():
 pattern=r'(    fn '+name+r'\(\) \{).*?\n    \}'
 s,count=re.subn(pattern,lambda m:m.group(1)+'\n        // Owner-approved S2 migration; original archived in exact-design/legacy-history.\n        '+body+'\n    }',s,flags=re.S);assert count==1
p.write_text(s,encoding='utf-8')
print('Legacy 9 new denial cases +4 existing validation checks; three named unit migrations')
