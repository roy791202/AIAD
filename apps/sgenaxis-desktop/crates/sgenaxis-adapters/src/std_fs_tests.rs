//! Independent FS contract tests. Frozen private seam; tests exercise approved FS-C1..C6.
use super::*;
use std::sync::atomic::{AtomicU64, Ordering};
static NEXT_TEST_DIR: AtomicU64 = AtomicU64::new(0);
struct TestDir(PathBuf);
impl TestDir {
    fn new(label: &str) -> Self {
        let path = std::env::temp_dir().join(format!("sgenaxis-fs-contract-{}-{}-{}", std::process::id(), label, NEXT_TEST_DIR.fetch_add(1, Ordering::Relaxed)));
        fs::create_dir(&path).expect("fixture directory must be fresh and writable");
        Self(path)
    }
    fn path(&self, name: &str) -> PathBuf { self.0.join(name) }
    fn assert_only(&self, names: &[&str]) {
        let mut actual: Vec<_> = fs::read_dir(&self.0).unwrap().map(|e| e.unwrap().file_name().to_string_lossy().into_owned()).collect();
        actual.sort();
        let mut expected: Vec<_> = names.iter().map(|s| s.to_string()).collect(); expected.sort();
        assert_eq!(actual, expected, "unexpected transaction residue");
    }
}
impl Drop for TestDir {
    fn drop(&mut self) { let _ = fs::remove_dir_all(&self.0); }
}
fn text_path(p: &Path) -> &str { p.to_str().expect("fixture path must be Unicode") }

#[test]
fn fs_t01_real_create_replace_empty_and_large_binary() {
    let d = TestDir::new("bytes"); let target = d.path("target.bin");
    let adapter = StdFileSystem::new();
    let payload: Vec<u8> = (0..=255).cycle().take(1024 * 1024 + 1).collect();
    adapter.write_atomic(text_path(&target), &payload).unwrap();
    assert_eq!(fs::read(&target).unwrap(), payload);
    adapter.write_atomic(text_path(&target), b"replacement").unwrap();
    assert_eq!(fs::read(&target).unwrap(), b"replacement");
    adapter.write_atomic(text_path(&target), b"").unwrap();
    assert_eq!(fs::read(&target).unwrap(), b""); d.assert_only(&["target.bin"]);
}

#[test]
fn fs_t07_real_directory_target_failure_preserves_directory() {
    let d=TestDir::new("directory"); let target=d.path("target"); fs::create_dir(&target).unwrap();
    fs::write(target.join("keep"), b"old").unwrap();
    assert!(StdFileSystem::new().write_atomic(text_path(&target), b"new").is_err());
    assert_eq!(fs::read(target.join("keep")).unwrap(), b"old"); d.assert_only(&["target"]);
}

#[test]
fn fs_t08_nested_unicode_space_paths_and_invalid_path() {
    let d=TestDir::new("paths"); let a=d.path("unicode space/測試/a"); let b=d.path("other");
    let adapter=StdFileSystem::new();
    adapter.write_atomic(text_path(&a), &[0,255,128,42]).unwrap();
    adapter.write_atomic(text_path(&b), b"other").unwrap();
    assert_eq!(fs::read(&a).unwrap(), [0,255,128,42]); assert_eq!(fs::read(&b).unwrap(),b"other");
    assert!(adapter.write_atomic("invalid\0path", b"reject").is_err());
}

fn injected(kind: std::io::ErrorKind, message: &str) -> std::io::Error { std::io::Error::new(kind, message.to_string()) }

#[test]
fn fs_t03_collision_preserves_sentinel_and_retries() {
    let d=TestDir::new("collision"); let target=d.path("target"); let sentinel=d.path("candidate-one"); let next=d.path("candidate-two");
    fs::write(&target,b"old").unwrap(); fs::write(&sentinel,b"SENTINEL").unwrap(); let mut attempts=0;
    let result=write_atomic_with(text_path(&target),b"new",|| {attempts+=1; if attempts==1 {sentinel.clone()} else {next.clone()}},|_,_|Ok(()));
    assert!(result.is_ok(), "{result:?}");
    assert_eq!(fs::read(&sentinel).expect("collision sentinel must survive"),b"SENTINEL");
    assert_eq!(attempts,2); assert_eq!(fs::read(&target).unwrap(),b"new"); d.assert_only(&["target","candidate-one"]);
}

#[test]
fn fs_t03_exhaustion_is_bounded_and_preserves_all_existing_bytes() {
    let d=TestDir::new("exhaustion"); let target=d.path("target"); let sentinel=d.path("occupied");
    fs::write(&target,b"old").unwrap(); fs::write(&sentinel,b"SENTINEL").unwrap(); let mut attempts=0;
    let result=write_atomic_with(text_path(&target),b"new",|| {attempts+=1; sentinel.clone()},|_,_|Ok(()));
    assert!(matches!(result,Err(PortError::AlreadyExists(_))),"{result:?}");
    assert_eq!(attempts,128); assert_eq!(fs::read(&target).unwrap(),b"old"); assert_eq!(fs::read(&sentinel).unwrap(),b"SENTINEL");
    d.assert_only(&["target","occupied"]);
}

fn failure_case(stage: WriteCheckpoint, deny_cleanup: bool) {
    let d=TestDir::new("failure"); let target=d.path("target"); let owned=d.path("owned"); let peer=d.path("peer");
    fs::write(&target,b"old").unwrap(); fs::write(&peer,b"peer-bytes").unwrap(); let mut cleanup=0;
    let result=write_atomic_with(text_path(&target),b"new",||owned.clone(),|checkpoint,tmp| {
        if checkpoint==stage {
            if stage==WriteCheckpoint::BeforeWrite { fs::write(tmp,b"partially written")?; }
            return Err(injected(std::io::ErrorKind::PermissionDenied,"PRIMARY_WRITE_SYNC_OR_RENAME"));
        }
        if checkpoint==WriteCheckpoint::BeforeCleanup { cleanup+=1; if deny_cleanup {return Err(injected(std::io::ErrorKind::Other,"SECONDARY_CLEANUP"));} }
        Ok(())
    });
    assert!(matches!(result,Err(PortError::PermissionDenied(_))),"primary failure replaced: {result:?}");
    assert_eq!(fs::read(&target).unwrap(),b"old"); assert_eq!(fs::read(&peer).unwrap(),b"peer-bytes");
    assert_eq!(cleanup,1,"owned cleanup must be attempted exactly once");
    assert_eq!(owned.exists(),deny_cleanup,"cleanup ownership/denial must be respected");
    if deny_cleanup {d.assert_only(&["target","owned","peer"]);} else {d.assert_only(&["target","peer"]);}
}
#[test] fn fs_t04_partial_write_failure_preserves_and_cleans() {failure_case(WriteCheckpoint::BeforeWrite,false);}
#[test] fn fs_t04_sync_failure_preserves_and_cleans() {failure_case(WriteCheckpoint::BeforeSync,false);}
#[test] fn fs_t05_rename_failure_preserves_and_cleans() {failure_case(WriteCheckpoint::BeforeRename,false);}
#[test] fn fs_t04_cleanup_denial_keeps_primary_error_and_owned_residue() {failure_case(WriteCheckpoint::BeforeWrite,true);}

#[test]
fn fs_t02_real_candidates_are_distinct_sibling_paths() {
    let d=TestDir::new("names"); let target=d.path("target"); let a=temp_candidate(&target); let b=temp_candidate(&target);
    assert_ne!(a,b,"same process invocations must not share candidates");
    assert_eq!(a.parent(),target.parent()); assert_eq!(b.parent(),target.parent());
}

fn ordered_concurrent(first: usize) {
    use std::sync::mpsc; use std::time::Duration;
    let d=TestDir::new("concurrent"); let target=d.path("target"); fs::write(&target,b"old").unwrap();
    let payloads=[vec![b'A';65537],vec![b'B';65539]];
    let (ready_tx,ready_rx)=mpsc::channel(); let mut permits=Vec::new(); let mut workers=Vec::new();
    for id in 0..2 {
        let path=target.clone(); let bytes=payloads[id].clone(); let tx=ready_tx.clone(); let (permit,rx)=mpsc::channel(); permits.push(permit);
        workers.push(Some(std::thread::spawn(move || write_atomic_with(text_path(&path),&bytes,||temp_candidate(&path),|point,tmp| {
            if point==WriteCheckpoint::BeforeRename { tx.send((id,tmp.to_path_buf())).expect("ready receiver"); rx.recv_timeout(Duration::from_secs(10)).expect("HARNESS failure: commit permit timeout"); }
            Ok(())
        }))));
    }
    drop(ready_tx);
    let a=ready_rx.recv_timeout(Duration::from_secs(10)).expect("HARNESS failure: first writer never prepared");
    let b=ready_rx.recv_timeout(Duration::from_secs(10)).expect("HARNESS failure: second writer never prepared");
    let before=fs::read(&target).unwrap();
    permits[first].send(()).unwrap(); let first_result=workers[first].take().unwrap().join().expect("worker panic"); let after_first=fs::read(&target).unwrap();
    permits[1-first].send(()).unwrap(); let second_result=workers[1-first].take().unwrap().join().expect("worker panic"); let after_second=fs::read(&target).unwrap();
    // Assert only after both workers released: an assertion never strands a peer.
    assert_ne!(a.1,b.1,"both prepared writers must own different paths"); assert_eq!(before,b"old");
    assert!(first_result.is_ok(),"{first_result:?}"); assert!(second_result.is_ok(),"{second_result:?}");
    assert_eq!(after_first,payloads[first]); assert_eq!(after_second,payloads[1-first]); d.assert_only(&["target"]);
}
#[test] fn fs_t02_a_then_b_last_commit_wins() {ordered_concurrent(0);}
#[test] fn fs_t02_b_then_a_last_commit_wins() {ordered_concurrent(1);}

#[test]
fn fs_t06_failed_writer_cannot_delete_prepared_peer_and_peer_commits() {
    use std::sync::mpsc; use std::time::Duration;
    let d=TestDir::new("peer"); let target=d.path("target"); let peer=d.path("peer-owned"); let failing=d.path("failed-owned"); fs::write(&target,b"old").unwrap();
    let (ready_tx,ready_rx)=mpsc::channel(); let (release_tx,release_rx)=mpsc::channel(); let peer_copy=peer.clone(); let path=target.clone();
    let worker=std::thread::spawn(move ||write_atomic_with(text_path(&path),b"peer-committed",||peer_copy.clone(),|point,_| {
        if point==WriteCheckpoint::BeforeRename {ready_tx.send(()).unwrap(); release_rx.recv_timeout(Duration::from_secs(10)).expect("HARNESS failure: peer release timeout");} Ok(())
    }));
    ready_rx.recv_timeout(Duration::from_secs(10)).expect("HARNESS failure: peer readiness timeout");
    let failure=write_atomic_with(text_path(&target),b"failed",||failing.clone(),|point,_|if point==WriteCheckpoint::BeforeSync {Err(injected(std::io::ErrorKind::PermissionDenied,"sync"))}else{Ok(())});
    let peer_present=fs::read(&peer); let old=fs::read(&target).unwrap(); let residue=failing.exists();
    release_tx.send(()).unwrap(); let success=worker.join().unwrap();
    assert!(failure.is_err()); assert_eq!(peer_present.unwrap(),b"peer-committed"); assert_eq!(old,b"old"); assert!(!residue,"failed writer must clean only its own temp");
    assert!(success.is_ok(),"{success:?}"); assert_eq!(fs::read(&target).unwrap(),b"peer-committed"); d.assert_only(&["target"]);
}
