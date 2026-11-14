//! Deprecated creation entries must fail before any filesystem access.
use sgenaxis_adapters::FakeFileSystem;
use sgenaxis_host::error::HostError;
use sgenaxis_host::{project_new::*, project_preferences::*};
use sgenaxis_ports::{FileSystemPort, PortError};
use std::sync::Mutex;
struct Spy {
    fs: FakeFileSystem,
    calls: Mutex<Vec<String>>,
}
impl Spy {
    fn new() -> Self {
        Self {
            fs: FakeFileSystem::new(),
            calls: Mutex::new(vec![]),
        }
    }
    fn hit(&self, s: &str) {
        self.calls.lock().unwrap().push(s.into());
    }
}
impl FileSystemPort for Spy {
    fn exists(&self, p: &str) -> Result<bool, PortError> {
        self.hit("exists");
        self.fs.exists(p)
    }
    fn is_file(&self, p: &str) -> Result<bool, PortError> {
        self.hit("is_file");
        self.fs.is_file(p)
    }
    fn read(&self, p: &str) -> Result<Vec<u8>, PortError> {
        self.hit("read");
        self.fs.read(p)
    }
    fn read_to_string(&self, p: &str) -> Result<String, PortError> {
        self.hit("read_to_string");
        self.fs.read_to_string(p)
    }
    fn write_atomic(&self, p: &str, b: &[u8]) -> Result<(), PortError> {
        self.hit("write");
        self.fs.write_atomic(p, b)
    }
    fn create_dir_all(&self, p: &str) -> Result<(), PortError> {
        self.hit("mkdir");
        self.fs.create_dir_all(p)
    }
    fn remove_file(&self, p: &str) -> Result<(), PortError> {
        self.hit("remove");
        self.fs.remove_file(p)
    }
}

#[test]
fn t091_deprecated() {
    let s = Spy::new();
    let before = (
        s.fs.exists("C:/parent/Project-A").unwrap(),
        s.fs.is_file("C:/parent/Project-A").unwrap(),
        s.fs.read("C:/parent/Project-A"),
        s.fs.read("C:/parent/Project-A/keep.ess"),
    );
    let count = (s.fs.write_count(), s.fs.mkdir_count());
    let result = create_new_project_root(&s, "C:/parent/Project-A");
    assert!(
        matches!(result,Err(HostError::Settings(ref m)) if m.starts_with("WIZARD_REQUIRED:")),
        "deprecated entry denial: {result:?}"
    );
    assert!(s.calls.lock().unwrap().is_empty(), "even reads forbidden");
    assert_eq!((s.fs.write_count(), s.fs.mkdir_count()), count);
    assert_eq!(
        (
            s.fs.exists("C:/parent/Project-A").unwrap(),
            s.fs.is_file("C:/parent/Project-A").unwrap(),
            s.fs.read("C:/parent/Project-A"),
            s.fs.read("C:/parent/Project-A/keep.ess")
        ),
        before
    );
}

#[test]
fn t092_deprecated() {
    let s = Spy::new();
    s.fs.seed("C:/parent/Project-A", b"original file");
    let before = (
        s.fs.exists("C:/parent/Project-A").unwrap(),
        s.fs.is_file("C:/parent/Project-A").unwrap(),
        s.fs.read("C:/parent/Project-A"),
        s.fs.read("C:/parent/Project-A/keep.ess"),
    );
    let count = (s.fs.write_count(), s.fs.mkdir_count());
    let result = create_new_project_root(&s, "C:/parent/Project-A");
    assert!(
        matches!(result,Err(HostError::Settings(ref m)) if m.starts_with("WIZARD_REQUIRED:")),
        "deprecated entry denial: {result:?}"
    );
    assert!(s.calls.lock().unwrap().is_empty(), "even reads forbidden");
    assert_eq!((s.fs.write_count(), s.fs.mkdir_count()), count);
    assert_eq!(
        (
            s.fs.exists("C:/parent/Project-A").unwrap(),
            s.fs.is_file("C:/parent/Project-A").unwrap(),
            s.fs.read("C:/parent/Project-A"),
            s.fs.read("C:/parent/Project-A/keep.ess")
        ),
        before
    );
}

#[test]
fn t093_deprecated() {
    let s = Spy::new();
    s.fs.create_dir_all("C:/parent/Project-A").unwrap();
    s.fs.seed("C:/parent/Project-A/keep.ess", b"original document");
    let before = (
        s.fs.exists("C:/parent/Project-A").unwrap(),
        s.fs.is_file("C:/parent/Project-A").unwrap(),
        s.fs.read("C:/parent/Project-A"),
        s.fs.read("C:/parent/Project-A/keep.ess"),
    );
    let count = (s.fs.write_count(), s.fs.mkdir_count());
    let result = create_new_project_root(&s, "C:/parent/Project-A");
    assert!(
        matches!(result,Err(HostError::Settings(ref m)) if m.starts_with("WIZARD_REQUIRED:")),
        "deprecated entry denial: {result:?}"
    );
    assert!(s.calls.lock().unwrap().is_empty(), "even reads forbidden");
    assert_eq!((s.fs.write_count(), s.fs.mkdir_count()), count);
    assert_eq!(
        (
            s.fs.exists("C:/parent/Project-A").unwrap(),
            s.fs.is_file("C:/parent/Project-A").unwrap(),
            s.fs.read("C:/parent/Project-A"),
            s.fs.read("C:/parent/Project-A/keep.ess")
        ),
        before
    );
}

#[test]
fn t094_deprecated() {
    let s = Spy::new();
    let before = (
        s.fs.exists("C:/parent/Project-A").unwrap(),
        s.fs.is_file("C:/parent/Project-A").unwrap(),
        s.fs.read("C:/parent/Project-A"),
        s.fs.read("C:/parent/Project-A/keep.ess"),
    );
    let count = (s.fs.write_count(), s.fs.mkdir_count());
    let result = create_new_project_under(&s, "C:/parent", "Project-A");
    assert!(
        matches!(result,Err(HostError::Settings(ref m)) if m.starts_with("WIZARD_REQUIRED:")),
        "deprecated entry denial: {result:?}"
    );
    assert!(s.calls.lock().unwrap().is_empty(), "even reads forbidden");
    assert_eq!((s.fs.write_count(), s.fs.mkdir_count()), count);
    assert_eq!(
        (
            s.fs.exists("C:/parent/Project-A").unwrap(),
            s.fs.is_file("C:/parent/Project-A").unwrap(),
            s.fs.read("C:/parent/Project-A"),
            s.fs.read("C:/parent/Project-A/keep.ess")
        ),
        before
    );
}

#[test]
fn t095_deprecated() {
    let s = Spy::new();
    s.fs.seed("C:/parent/Project-A", b"original file");
    let before = (
        s.fs.exists("C:/parent/Project-A").unwrap(),
        s.fs.is_file("C:/parent/Project-A").unwrap(),
        s.fs.read("C:/parent/Project-A"),
        s.fs.read("C:/parent/Project-A/keep.ess"),
    );
    let count = (s.fs.write_count(), s.fs.mkdir_count());
    let result = create_new_project_under(&s, "C:/parent", "Project-A");
    assert!(
        matches!(result,Err(HostError::Settings(ref m)) if m.starts_with("WIZARD_REQUIRED:")),
        "deprecated entry denial: {result:?}"
    );
    assert!(s.calls.lock().unwrap().is_empty(), "even reads forbidden");
    assert_eq!((s.fs.write_count(), s.fs.mkdir_count()), count);
    assert_eq!(
        (
            s.fs.exists("C:/parent/Project-A").unwrap(),
            s.fs.is_file("C:/parent/Project-A").unwrap(),
            s.fs.read("C:/parent/Project-A"),
            s.fs.read("C:/parent/Project-A/keep.ess")
        ),
        before
    );
}

#[test]
fn t096_deprecated() {
    let s = Spy::new();
    s.fs.create_dir_all("C:/parent/Project-A").unwrap();
    s.fs.seed("C:/parent/Project-A/keep.ess", b"original document");
    let before = (
        s.fs.exists("C:/parent/Project-A").unwrap(),
        s.fs.is_file("C:/parent/Project-A").unwrap(),
        s.fs.read("C:/parent/Project-A"),
        s.fs.read("C:/parent/Project-A/keep.ess"),
    );
    let count = (s.fs.write_count(), s.fs.mkdir_count());
    let result = create_new_project_under(&s, "C:/parent", "Project-A");
    assert!(
        matches!(result,Err(HostError::Settings(ref m)) if m.starts_with("WIZARD_REQUIRED:")),
        "deprecated entry denial: {result:?}"
    );
    assert!(s.calls.lock().unwrap().is_empty(), "even reads forbidden");
    assert_eq!((s.fs.write_count(), s.fs.mkdir_count()), count);
    assert_eq!(
        (
            s.fs.exists("C:/parent/Project-A").unwrap(),
            s.fs.is_file("C:/parent/Project-A").unwrap(),
            s.fs.read("C:/parent/Project-A"),
            s.fs.read("C:/parent/Project-A/keep.ess")
        ),
        before
    );
}

#[test]
fn t097_deprecated() {
    let s = Spy::new();
    let before = (
        s.fs.exists("C:/parent/Project-A").unwrap(),
        s.fs.is_file("C:/parent/Project-A").unwrap(),
        s.fs.read("C:/parent/Project-A"),
        s.fs.read("C:/parent/Project-A/keep.ess"),
    );
    let count = (s.fs.write_count(), s.fs.mkdir_count());
    let result = create_project_with_preferences(&s, "C:/parent/Project-A", PreferenceChoice::Skip);
    assert_eq!(result, Err(ProjectPreferenceError::WizardRequired));
    assert!(s.calls.lock().unwrap().is_empty(), "even reads forbidden");
    assert_eq!((s.fs.write_count(), s.fs.mkdir_count()), count);
    assert_eq!(
        (
            s.fs.exists("C:/parent/Project-A").unwrap(),
            s.fs.is_file("C:/parent/Project-A").unwrap(),
            s.fs.read("C:/parent/Project-A"),
            s.fs.read("C:/parent/Project-A/keep.ess")
        ),
        before
    );
}

#[test]
fn t098_deprecated() {
    let s = Spy::new();
    s.fs.seed("C:/parent/Project-A", b"original file");
    let before = (
        s.fs.exists("C:/parent/Project-A").unwrap(),
        s.fs.is_file("C:/parent/Project-A").unwrap(),
        s.fs.read("C:/parent/Project-A"),
        s.fs.read("C:/parent/Project-A/keep.ess"),
    );
    let count = (s.fs.write_count(), s.fs.mkdir_count());
    let result = create_project_with_preferences(&s, "C:/parent/Project-A", PreferenceChoice::Skip);
    assert_eq!(result, Err(ProjectPreferenceError::WizardRequired));
    assert!(s.calls.lock().unwrap().is_empty(), "even reads forbidden");
    assert_eq!((s.fs.write_count(), s.fs.mkdir_count()), count);
    assert_eq!(
        (
            s.fs.exists("C:/parent/Project-A").unwrap(),
            s.fs.is_file("C:/parent/Project-A").unwrap(),
            s.fs.read("C:/parent/Project-A"),
            s.fs.read("C:/parent/Project-A/keep.ess")
        ),
        before
    );
}

#[test]
fn t099_deprecated() {
    let s = Spy::new();
    s.fs.create_dir_all("C:/parent/Project-A").unwrap();
    s.fs.seed("C:/parent/Project-A/keep.ess", b"original document");
    let before = (
        s.fs.exists("C:/parent/Project-A").unwrap(),
        s.fs.is_file("C:/parent/Project-A").unwrap(),
        s.fs.read("C:/parent/Project-A"),
        s.fs.read("C:/parent/Project-A/keep.ess"),
    );
    let count = (s.fs.write_count(), s.fs.mkdir_count());
    let result = create_project_with_preferences(&s, "C:/parent/Project-A", PreferenceChoice::Skip);
    assert_eq!(result, Err(ProjectPreferenceError::WizardRequired));
    assert!(s.calls.lock().unwrap().is_empty(), "even reads forbidden");
    assert_eq!((s.fs.write_count(), s.fs.mkdir_count()), count);
    assert_eq!(
        (
            s.fs.exists("C:/parent/Project-A").unwrap(),
            s.fs.is_file("C:/parent/Project-A").unwrap(),
            s.fs.read("C:/parent/Project-A"),
            s.fs.read("C:/parent/Project-A/keep.ess")
        ),
        before
    );
}

#[test]
fn t100_name_0() {
    let s = Spy::new();
    assert!(
        matches!(create_new_project_under(&s,"C:/parent",""),Err(HostError::Settings(ref m)) if !m.starts_with("WIZARD_REQUIRED:"))
    );
    assert!(s.calls.lock().unwrap().is_empty());
}

#[test]
fn t100_name_1() {
    let s = Spy::new();
    assert!(
        matches!(create_new_project_under(&s,"C:/parent",".."),Err(HostError::Settings(ref m)) if !m.starts_with("WIZARD_REQUIRED:"))
    );
    assert!(s.calls.lock().unwrap().is_empty());
}

#[test]
fn t100_name_2() {
    let s = Spy::new();
    assert!(
        matches!(create_new_project_under(&s,"C:/parent","a/b"),Err(HostError::Settings(ref m)) if !m.starts_with("WIZARD_REQUIRED:"))
    );
    assert!(s.calls.lock().unwrap().is_empty());
}

#[test]
fn t100_demo() {
    let s = Spy::new();
    assert!(
        matches!(create_new_project_root(&s,"/demo/root"),Err(HostError::Settings(ref m)) if m.contains("/demo/root")&&!m.starts_with("WIZARD_REQUIRED:"))
    );
    assert!(s.calls.lock().unwrap().is_empty());
}
