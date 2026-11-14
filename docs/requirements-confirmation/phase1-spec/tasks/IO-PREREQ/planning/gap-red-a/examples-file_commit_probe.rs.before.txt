//! Isolated test-fixture process, not a production entry point or lease adapter.
//! `native-hold` establishes an independently acquired Windows handle so tests
//! can exercise the product boundary without relying on unimplemented setup.

#[cfg(windows)]
fn run() -> Result<(), String> {
    use std::io::{self, Write};
    use std::os::windows::fs::OpenOptionsExt;
    use std::path::PathBuf;

    let args: Vec<String> = std::env::args().collect();
    if args.get(1).map(String::as_str) == Some("health") {
        println!("FIXTURE_HELPER_OK");
        return Ok(());
    }
    if args.len() != 4
        || !["native-hold", "acquire-once", "hold-product-lease"].contains(&args[1].as_str())
    {
        return Err(
            "expected health or native-hold/acquire-once/hold-product-lease <owned root> <sidecar>"
                .into(),
        );
    }
    let base = std::env::temp_dir()
        .join("eluslot-io-red-fixtures")
        .canonicalize()
        .map_err(|e| e.to_string())?;
    let root = PathBuf::from(&args[2])
        .canonicalize()
        .map_err(|e| e.to_string())?;
    let name = root
        .file_name()
        .and_then(|n| n.to_str())
        .ok_or("invalid fixture root")?;
    if root.parent() != Some(base.as_path())
        || !name.starts_with("io-")
        || std::fs::read_to_string(root.join(".owned-fixture")).map_err(|e| e.to_string())? != name
    {
        return Err("refusing a non-owned fixture root".into());
    }
    let sidecar = PathBuf::from(&args[3]);
    if sidecar
        .parent()
        .ok_or("missing parent")?
        .canonicalize()
        .map_err(|e| e.to_string())?
        != root
        || sidecar.file_name().and_then(|n| n.to_str()) != Some("document.ess.eluslot-lock")
    {
        return Err("refusing a sidecar outside the owned fixture".into());
    }
    if args[1] != "native-hold" {
        use sgenaxis_adapters::StdFileCommit;
        use sgenaxis_ports::FileCommitPort;
        println!("PROBE_STARTED");
        io::stdout().flush().map_err(|e| e.to_string())?;
        let target = root.join("document.ess").to_string_lossy().into_owned();
        match StdFileCommit::new().acquire_write(&target) {
            Err(e) => {
                // A product error is data for the parent assertion, never a fixture timeout.
                println!("RESULT ERROR {e:?}");
            }
            Ok(lease) => {
                if args[1] == "hold-product-lease" {
                    println!("LEASE_READY");
                    io::stdout().flush().map_err(|e| e.to_string())?;
                    let mut command = String::new();
                    io::stdin()
                        .read_line(&mut command)
                        .map_err(|e| e.to_string())?;
                    if command.trim() != "RELEASE" {
                        return Err("expected RELEASE".into());
                    }
                }
                drop(lease);
                println!("RESULT OK");
            }
        }
        io::stdout().flush().map_err(|e| e.to_string())?;
        return Ok(());
    }
    let _handle = std::fs::OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .share_mode(0)
        .open(sidecar)
        .map_err(|e| e.to_string())?;
    println!("READY");
    io::stdout().flush().map_err(|e| e.to_string())?;
    let mut line = String::new();
    io::stdin()
        .read_line(&mut line)
        .map_err(|e| e.to_string())?;
    Ok(()) // Fixture handle is closed by ownership, not a product implementation.
}

// Cargo's test example build supplies cfg(test) so private checkpoint seams
// remain completely absent from the normal shipped crate and helper build.
#[cfg(all(windows, test))]
#[path = "../src/file_commit.rs"]
mod checkpoint_source;

#[cfg(all(windows, test))]
#[test]
fn checkpoint_probe_entry() {
    use sgenaxis_ports::FileWriteLease;
    use std::io::{self, Write};
    use std::path::PathBuf;
    use std::sync::Arc;
    let root =
        PathBuf::from(std::env::var_os("FILE_COMMIT_CHECKPOINT_ROOT").expect("fixture root"))
            .canonicalize()
            .expect("fixture root canonical");
    let base = std::env::temp_dir()
        .join("eluslot-io-red-fixtures")
        .canonicalize()
        .unwrap();
    assert_eq!(root.parent(), Some(base.as_path()), "invalid fixture root");
    let owner = root.file_name().unwrap().to_str().unwrap();
    assert!(owner.starts_with("io-"));
    assert_eq!(
        std::fs::read_to_string(root.join(".owned-fixture")).unwrap(),
        owner
    );
    let point = std::env::var("FILE_COMMIT_CHECKPOINT_POINT").unwrap();
    assert!([
        "new.synced",
        "prepared.verified",
        "target.published",
        "committed.verified",
        "cleanup.before"
    ]
    .contains(&point.as_str()));
    let desired = point.clone();
    let hooks = checkpoint_source::TestCheckpoints {
        at_point: Some(Arc::new(move |seen| {
            if seen == desired {
                println!("CHECKPOINT {seen}");
                io::stdout().flush().unwrap();
                let mut command = String::new();
                io::stdin().read_line(&mut command).unwrap();
                assert_eq!(command.trim(), "CONTINUE");
            }
        })),
        ..Default::default()
    };
    println!("PROBE_STARTED");
    io::stdout().flush().unwrap();
    let target = root.join("document.ess").to_string_lossy().into_owned();
    match checkpoint_source::StdFileCommit::new().acquire_with_checkpoints(&target, hooks) {
        Err(e) => println!("RESULT ERROR {e:?}"),
        Ok(mut lease) => {
            let old = lease.read_current().expect("product read before commit");
            let expected = old
                .as_ref()
                .map(|v| format!("sha256:{}", sgenaxis_spec::packet::source_sha256(v)));
            println!(
                "RESULT {:?}",
                lease.replace_checked(expected.as_deref(), b"NEW-COMPLETE-DOCUMENT")
            );
        }
    }
    io::stdout().flush().unwrap();
}

#[cfg(windows)]
fn main() {
    if let Err(error) = run() {
        eprintln!("FIXTURE_ERROR:{error}");
        std::process::exit(70);
    }
}

#[cfg(not(windows))]
fn main() {
    eprintln!("fixture requires Windows; not a cross-platform test PASS");
    std::process::exit(78);
}
