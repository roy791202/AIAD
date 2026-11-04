//! Native adapter for the additive staged-Index-only Git port (A1).
//! All process calls go through a private seam; tests inject a recorder and never invoke Git.

use std::{collections::BTreeMap, io::Write, path::Path, process::{Command, Stdio}};
use sgenaxis_ports::{GitIndexCommitPort, GitOperationState as Operation, GitWriteApproval,
    IndexCommitError as Error, IndexCommitFacts as Facts, IndexCommitFingerprint as Fingerprint,
    IndexCommitObservation as Observation};

#[derive(Debug, Clone, PartialEq, Eq)]
struct CommandResult { code: Option<i32>, stdout: Vec<u8>, stderr: Vec<u8> }

#[derive(Debug, Clone, PartialEq, Eq)]
enum InvocationError { Spawn(String), AfterSpawn(String) }

trait GitCommandInvoker: Send + Sync {
    fn invoke(&self, program: &str, args: &[String], stdin: Option<&[u8]>) -> Result<CommandResult, InvocationError>;
    fn canonicalize(&self, path: &str) -> Result<String, String>;
    fn path_exists(&self, path: &str) -> bool;
}

impl<T: GitCommandInvoker + ?Sized> GitCommandInvoker for std::sync::Arc<T> {
    fn invoke(&self, program: &str, args: &[String], stdin: Option<&[u8]>) -> Result<CommandResult, InvocationError> {
        (**self).invoke(program, args, stdin)
    }
    fn canonicalize(&self, path: &str) -> Result<String, String> { (**self).canonicalize(path) }
    fn path_exists(&self, path: &str) -> bool { (**self).path_exists(path) }
}

struct SystemInvoker;
impl GitCommandInvoker for SystemInvoker {
    fn invoke(&self, program: &str, args: &[String], stdin: Option<&[u8]>) -> Result<CommandResult, InvocationError> {
        let mut cmd = Command::new(program);
        cmd.args(args).stdout(Stdio::piped()).stderr(Stdio::piped());
        if stdin.is_some() { cmd.stdin(Stdio::piped()); }
        let mut child = cmd.spawn().map_err(|e| InvocationError::Spawn(e.to_string()))?;
        if let Some(bytes) = stdin {
            child.stdin.take().ok_or_else(|| InvocationError::AfterSpawn("stdin unavailable".into()))?
                .write_all(bytes).map_err(|e| InvocationError::AfterSpawn(e.to_string()))?;
        }
        let output = child.wait_with_output().map_err(|e| InvocationError::AfterSpawn(e.to_string()))?;
        Ok(CommandResult { code: output.status.code(), stdout: output.stdout, stderr: output.stderr })
    }
    fn canonicalize(&self, path: &str) -> Result<String, String> {
        std::fs::canonicalize(path).map(|p| p.to_string_lossy().into_owned()).map_err(|e| e.to_string())
    }
    fn path_exists(&self, path: &str) -> bool { Path::new(path).exists() }
}

pub struct StdGitIndexCommit { program: String, invoker: Box<dyn GitCommandInvoker> }
impl std::fmt::Debug for StdGitIndexCommit {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("StdGitIndexCommit").field("program", &self.program).finish()
    }
}
impl Default for StdGitIndexCommit { fn default() -> Self { Self::new() } }
impl StdGitIndexCommit {
    pub fn new() -> Self { Self { program: "git".into(), invoker: Box::new(SystemInvoker) } }
    pub fn with_program(program: impl Into<String>) -> Self { Self { program: program.into(), invoker: Box::new(SystemInvoker) } }

    fn run(&self, repo: &str, args: &[String], input: Option<&[u8]>) -> Result<CommandResult, Error> {
        if repo.trim().is_empty() { return Err(Error::InvalidInput("empty repository path".into())); }
        let mut argv = vec!["-C".into(), repo.into()]; argv.extend_from_slice(args);
        self.invoker.invoke(&self.program, &argv, input).map_err(|e| match e {
            InvocationError::Spawn(_) => Error::Unavailable("Git process could not be started".into()),
            InvocationError::AfterSpawn(_) => Error::Unreadable("Git process observation failed after spawn".into()),
        })
    }
    fn invoke_commit(&self, repo: &str, message: &str) -> Result<CommandResult, InvocationError> {
        let args = vec!["-C".into(), repo.into(), "commit".into(), "-m".into(), message.into()];
        if repo.trim().is_empty() { return Err(InvocationError::Spawn("empty repo path".into())); }
        self.invoker.invoke(&self.program, &args, None)
    }
    fn query(&self, repo: &str, args: &[&str]) -> Result<CommandResult, Error> {
        self.run(repo, &args.iter().map(|s| (*s).to_string()).collect::<Vec<_>>(), None)
    }
    fn hash_tree(&self, repo: &str, raw: &[u8]) -> Result<String, Error> {
        let result = self.run(repo, &["hash-object".into(), "-t".into(), "tree".into(), "--stdin".into()], Some(raw))?;
        if result.code != Some(0) { return Err(Error::Unreadable("read-only tree hash failed".into())); }
        decode_line(&result.stdout, "tree object id")
    }
    fn operation(&self, repo: &str) -> Result<Operation, Error> {
        for (marker, operation) in [
            ("MERGE_HEAD", Operation::Merge), ("CHERRY_PICK_HEAD", Operation::CherryPick),
            ("REVERT_HEAD", Operation::Revert), ("BISECT_LOG", Operation::Bisect),
            ("rebase-merge", Operation::Rebase), ("rebase-apply", Operation::Rebase),
        ] {
            let result = self.query(repo, &["rev-parse", "--git-path", marker])?;
            require_success(&result, "Git operation marker query")?;
            let path = decode_line(&result.stdout, "Git operation marker")?;
            let path = if Path::new(&path).is_absolute() { path } else { Path::new(repo).join(path).to_string_lossy().into_owned() };
            if self.invoker.path_exists(&path) { return Ok(operation); }
        }
        Ok(Operation::None)
    }
    fn inspect_internal(&self, requested_root: &str, allow_empty: bool) -> Result<Facts, Error> {
        if requested_root.trim().is_empty() || requested_root.contains('\0') {
            return Err(Error::InvalidInput("project root must be nonempty and contain no NUL".into()));
        }
        let project_root = self.invoker.canonicalize(requested_root).map_err(|_| Error::InvalidInput("project root cannot be resolved".into()))?;
        let version = self.invoker.invoke(&self.program, &["--version".into()], None)
            .map_err(|_| Error::Unavailable("Git executable is unavailable".into()))?;
        if version.code != Some(0) { return Err(Error::Unavailable("Git version query failed".into())); }
        let root_result = self.query(&project_root, &["rev-parse", "--show-toplevel"])?;
        if root_result.code != Some(0) {
            let diagnostic = String::from_utf8_lossy(&root_result.stderr).to_ascii_lowercase();
            return if diagnostic.contains("not a git repository") {
                Err(Error::NonRepo("project root is not in a Git repository".into()))
            } else {
                Err(Error::Unreadable("repository root query failed".into()))
            };
        }
        let repo_root = self.invoker.canonicalize(&decode_line(&root_result.stdout, "repository root")?)
            .map_err(|_| Error::Unreadable("repository root cannot be resolved".into()))?;
        let project_rel = Path::new(&project_root).strip_prefix(Path::new(&repo_root))
            .map_err(|_| Error::OutsideProjectScope("project root is outside repository".into()))?;
        let prefix = project_rel.to_string_lossy().replace('\\', "/");

        let operation = self.operation(&repo_root)?;
        if operation != Operation::None { return Err(Error::OperationInProgress); }
        let unmerged = self.query(&repo_root, &["ls-files", "--unmerged", "-z"])?;
        require_success(&unmerged, "unmerged Index query")?;
        if !unmerged.stdout.is_empty() { return Err(Error::Conflicted); }
        let listed = self.query(&repo_root, &["ls-files", "--stage", "-z"])?;
        require_success(&listed, "Index entry query")?;
        let entries = parse_entries(&listed.stdout)?;
        let changed = self.query(&repo_root, &["diff", "--cached", "--name-only", "--no-renames", "-z"])?;
        require_success(&changed, "staged path query")?;
        let changed_text = std::str::from_utf8(&changed.stdout)
            .map_err(|_| Error::UnsupportedPolicy("staged paths must be UTF-8 in A1".into()))?;
        let mut paths: Vec<String> = changed_text.split_terminator('\0').map(str::to_string).collect();
        paths.sort_by(|a, b| a.as_bytes().cmp(b.as_bytes())); paths.dedup();
        for path in &paths { validate_path(path, &prefix)?; }

        let tree = self.tree_oid(&repo_root, &entries)?;
        let diff = self.query(&repo_root, &["diff", "--cached", "--quiet"])?;
        let nonempty = match diff.code { Some(0) => false, Some(1) => true, _ => return Err(Error::Unreadable("staged diff query failed".into())) };
        if !allow_empty && (!nonempty || paths.is_empty()) { return Err(Error::NothingStaged); }
        let head = self.query(&repo_root, &["rev-parse", "--verify", "-q", "HEAD"])?;
        let head_oid = match head.code { Some(0) => Some(decode_line(&head.stdout, "HEAD object id")?), Some(1) => None, _ => return Err(Error::Unreadable("HEAD query failed".into())) };
        Ok(Facts { fingerprint: Fingerprint { repo_root, project_root, head_oid, index_tree_oid: tree, staged_paths: paths }, index_nonempty: nonempty, unmerged: false, operation })
    }
    fn tree_oid(&self, repo: &str, entries: &[StageEntry]) -> Result<String, Error> {
        let raw = self.tree_bytes(repo, entries)?; self.hash_tree(repo, &raw)
    }
    fn tree_bytes(&self, repo: &str, entries: &[StageEntry]) -> Result<Vec<u8>, Error> {
        let mut groups: BTreeMap<Vec<u8>, (Option<&StageEntry>, Vec<StageEntry>)> = BTreeMap::new();
        for entry in entries {
            let (first, tail) = entry.path.split_once('/').unwrap_or((&entry.path, ""));
            let group = groups.entry(first.as_bytes().to_vec()).or_default();
            if tail.is_empty() { group.0 = Some(entry); } else { group.1.push(StageEntry { mode: entry.mode.clone(), oid: entry.oid.clone(), path: tail.into() }); }
        }
        let mut records: Vec<(Vec<u8>, bool, String, String)> = Vec::new();
        for (name, (file, children)) in groups {
            if !children.is_empty() { records.push((name, true, "40000".into(), self.tree_oid(repo, &children)?)); }
            else if let Some(file) = file { records.push((name, false, file.mode.clone(), file.oid.clone())); }
        }
        records.sort_by(|a,b| { let mut ak=a.0.clone(); let mut bk=b.0.clone(); ak.push(if a.1 {b'/'} else {0}); bk.push(if b.1 {b'/'} else {0}); ak.cmp(&bk) });
        let mut raw=Vec::new();
        for (name, _is_dir, mode, oid) in records {
            raw.extend_from_slice(mode.as_bytes()); raw.push(b' '); raw.extend_from_slice(&name); raw.push(0); raw.extend(hex_bytes(&oid)?);
        }
        Ok(raw)
    }
}

impl GitIndexCommitPort for StdGitIndexCommit {
    fn inspect_index(&self, project_root: &str) -> Result<Facts, Error> { self.inspect_internal(project_root, false) }
    fn commit_index(&self, project_root: &str, message: &str, expected: &Fingerprint, approval: GitWriteApproval) -> Result<Observation, Error> {
        if !approval.is_granted() { return Err(Error::ApprovalRequired); }
        if message.trim().is_empty() || message.contains('\0') { return Err(Error::InvalidInput("message must be nonempty and contain no NUL".into())); }
        let before = self.inspect_internal(project_root, false)?;
        if before.fingerprint != *expected { return Err(Error::StalePreview); }
        // This is the sole mutating invocation: no add/stage/reset/checkout/clean is ever issued.
        let attempt = self.invoke_commit(&before.fingerprint.repo_root, message);
        let (invocation_started, exit_code, diagnostic) = match attempt {
            Ok(r) => (true, r.code, (r.code != Some(0)).then(|| "Git commit returned nonzero".into())),
            Err(InvocationError::Spawn(_)) => (false, None, Some("Git commit spawn failed".into())),
            Err(InvocationError::AfterSpawn(_)) => (true, None, Some("Git commit observation failed after spawn".into())),
        };
        let mut after = self.inspect_internal(project_root, true).ok();
        let mut readback_diagnostic = None;
        let readback = match self.query(&before.fingerprint.repo_root, &["rev-list", "--parents", "-n", "1", "HEAD"]) {
            Ok(result) if result.code == Some(0) => match parse_commit_parent(&result.stdout) {
                Ok(value) => Some(value),
                Err(_) => { readback_diagnostic = Some("commit parent readback was invalid".to_string()); None }
            },
            _ => { readback_diagnostic = Some("commit parent readback failed".to_string()); None }
        };
        let mut parent = None;
        let mut tree = None;
        if let Some((commit_oid, observed_parent)) = readback {
            let after_head = after.as_ref().and_then(|facts| facts.fingerprint.head_oid.as_deref());
            if after_head != Some(commit_oid.as_str()) {
                after = None;
                readback_diagnostic = Some("commit parent readback does not match reread HEAD".into());
            } else {
                parent = observed_parent;
                tree = self.query(&before.fingerprint.repo_root, &["rev-parse", "--verify", "-q", &format!("{commit_oid}^{{tree}}")])
                    .ok().and_then(|r| (r.code == Some(0)).then(|| decode_line(&r.stdout, "commit tree").ok()).flatten());
            }
        }
        if tree.is_none() && readback_diagnostic.is_none() {
            readback_diagnostic = Some("commit tree readback failed".to_string());
        }
        if readback_diagnostic.is_some() {
            after = None;
            parent = None;
            tree = None;
        }
        let diagnostic = diagnostic.or(readback_diagnostic);
        Ok(Observation { invocation_started, exit_code, after, observed_parent_oid: parent, observed_tree_oid: tree, diagnostic })
    }
}

#[derive(Debug)]
struct StageEntry { mode: String, oid: String, path: String }

fn decode_line(bytes: &[u8], label: &str) -> Result<String, Error> {
    let text = std::str::from_utf8(bytes).map_err(|_| Error::Unreadable(format!("{label} is not UTF-8")))?;
    let value = text.trim_end_matches(['\r','\n']);
    if value.is_empty() { Err(Error::Unreadable(format!("{label} was empty"))) } else { Ok(value.into()) }
}
fn parse_commit_parent(bytes: &[u8]) -> Result<(String, Option<String>), Error> {
    let line = decode_line(bytes, "commit parent listing")?;
    let fields: Vec<_> = line.split_whitespace().collect();
    let valid_oid = |value: &str| matches!(value.len(), 40 | 64) && value.bytes().all(|byte| byte.is_ascii_hexdigit());
    match fields.as_slice() {
        [commit] if valid_oid(commit) => Ok((commit.to_ascii_lowercase(), None)),
        [commit, parent] if valid_oid(commit) && valid_oid(parent) => Ok((commit.to_ascii_lowercase(), Some((*parent).to_ascii_lowercase()))),
        _ => Err(Error::Unreadable("commit parent listing was malformed".into())),
    }
}
fn require_success(result: &CommandResult, label: &str) -> Result<(), Error> {
    if result.code == Some(0) { Ok(()) } else { Err(Error::Unreadable(format!("{label} failed"))) }
}
fn parse_entries(bytes: &[u8]) -> Result<Vec<StageEntry>, Error> {
    let text = std::str::from_utf8(bytes).map_err(|_| Error::UnsupportedPolicy("Index paths must be UTF-8 in A1".into()))?;
    let mut out=Vec::new();
    for rec in text.split_terminator('\0') {
        let (metadata,path)=rec.split_once('\t').ok_or_else(|| Error::Unreadable("malformed Index entry".into()))?;
        let mut fields=metadata.split_whitespace(); let mode=fields.next().unwrap_or(""); let oid=fields.next().unwrap_or(""); let stage=fields.next().unwrap_or("");
        if stage!="0" { return Err(Error::Conflicted); }
        if !matches!(mode,"100644"|"100755"|"120000"|"160000") { return Err(Error::UnsupportedPolicy(format!("unsupported mode {mode}"))); }
        if !matches!(oid.len(),40|64) || !oid.bytes().all(|b|b.is_ascii_hexdigit()) { return Err(Error::Unreadable("invalid Index object id".into())); }
        out.push(StageEntry{mode:mode.into(),oid:oid.to_ascii_lowercase(),path:path.into()});
    }
    Ok(out)
}
fn validate_path(path:&str,prefix:&str)->Result<(),Error>{
    let p=Path::new(path); if path.is_empty()||p.is_absolute()||p.components().any(|c|matches!(c,std::path::Component::ParentDir)){return Err(Error::OutsideProjectScope(path.into()));}
    let normalized=path.replace('\\',"/"); if !prefix.is_empty()&&normalized!=prefix&&!normalized.starts_with(&(prefix.to_string()+"/")){return Err(Error::OutsideProjectScope(path.into()));} Ok(())
}
fn hex_bytes(oid:&str)->Result<Vec<u8>,Error>{
    if !matches!(oid.len(),40|64)||oid.len()%2!=0{return Err(Error::Unreadable("invalid object id length".into()));}
    (0..oid.len()).step_by(2).map(|i|u8::from_str_radix(&oid[i..i+2],16).map_err(|_|Error::Unreadable("invalid object id".into()))).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{Arc, Mutex};

    #[derive(Default)]
    struct RecordingInvoker {
        calls: Mutex<Vec<(String, Vec<String>, Option<Vec<u8>>)>>,
        committed: Mutex<bool>,
        hash_count: Mutex<usize>,
        fail_commit_after_spawn: Mutex<bool>,
        root_failure: Mutex<Option<(String, String)>>,
        unborn: Mutex<bool>,
        fail_parent_readback: Mutex<bool>,
        reported_readback_commit: Mutex<Option<String>>,
    }
    fn output(code: i32, text: &str) -> CommandResult { CommandResult { code: Some(code), stdout: text.as_bytes().to_vec(), stderr: Vec::new() } }
    impl GitCommandInvoker for RecordingInvoker {
    fn invoke(&self, program: &str, args: &[String], stdin: Option<&[u8]>) -> Result<CommandResult, InvocationError> {
            self.calls.lock().unwrap().push((program.into(), args.to_vec(), stdin.map(|b| b.to_vec())));
            let cmd = if args.first().is_some_and(|arg| arg == "--version") { args.iter().map(String::as_str).collect::<Vec<_>>() }
                else { args.iter().skip_while(|arg| arg.as_str() != "-C").skip(2).map(String::as_str).collect::<Vec<_>>() };
            let committed = *self.committed.lock().unwrap();
            let result = match cmd.as_slice() {
                ["--version"] => output(0, "git version recording\n"),
                ["rev-parse", "--show-toplevel"] => match self.root_failure.lock().unwrap().as_ref() {
                    Some((stdout, stderr)) => CommandResult { code: Some(128), stdout: stdout.as_bytes().to_vec(), stderr: stderr.as_bytes().to_vec() },
                    None => output(0, "/repo\n"),
                },
                ["rev-parse", "--git-path", marker] => output(0, &format!("/repo/.git/{marker}\n")),
                ["ls-files", "--unmerged", "-z"] => output(0, ""),
                ["ls-files", "--stage", "-z"] => output(0, "100644 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 0\tproject/a.rs\0"),
                ["diff", "--cached", "--name-only", "--no-renames", "-z"] if !committed => output(0, "project/a.rs\0"),
                ["diff", "--cached", "--name-only", "--no-renames", "-z"] => output(0, ""),
                ["diff", "--cached", "--quiet"] if !committed => output(1, ""),
                ["diff", "--cached", "--quiet"] => output(0, ""),
                ["hash-object", "-t", "tree", "--stdin"] => {
                    let mut n = self.hash_count.lock().unwrap();
                    let oid = if *n % 2 == 0 { "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" } else { "cccccccccccccccccccccccccccccccccccccccc" };
                    *n += 1;
                    output(0, &format!("{oid}\n"))
                }
                ["rev-parse", "--verify", "-q", "HEAD"] => {
                    if !committed && *self.unborn.lock().unwrap() { output(1, "") }
                    else { output(0, if committed { "dddddddddddddddddddddddddddddddddddddddd\n" } else { "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n" }) }
                }
                ["commit", "-m", _] => {
                    *self.committed.lock().unwrap() = true;
                    if *self.fail_commit_after_spawn.lock().unwrap() { return Err(InvocationError::AfterSpawn("simulated wait_with_output error after spawn".into())); }
                    output(0, "")
                }
                ["rev-list", "--parents", "-n", "1", "HEAD"] => {
                    if *self.fail_parent_readback.lock().unwrap() { output(128, "") }
                    else {
                        let commit = self.reported_readback_commit.lock().unwrap().clone().unwrap_or_else(|| "dddddddddddddddddddddddddddddddddddddddd".into());
                        if *self.unborn.lock().unwrap() { output(0, &format!("{commit}\n")) }
                        else { output(0, &format!("{commit} aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n")) }
                    }
                }
                ["rev-parse", "--verify", "-q", tree_ref] if tree_ref.ends_with("^{tree}") => output(0, "cccccccccccccccccccccccccccccccccccccccc\n"),
                _ => return Err(InvocationError::AfterSpawn(format!("unexpected scripted argv: {args:?}"))),
            };
            Ok(result)
        }
        fn canonicalize(&self, path: &str) -> Result<String, String> { Ok(path.into()) }
        fn path_exists(&self, _path: &str) -> bool { false }
    }
    fn adapter(fake: Arc<RecordingInvoker>) -> StdGitIndexCommit {
        StdGitIndexCommit { program: "git-recording-sentinel".into(), invoker: Box::new(fake) }
    }

    #[test]
    fn inspect_index_uses_read_only_queries_and_never_writes_objects() {
        let fake = Arc::new(RecordingInvoker::default());
        let facts = adapter(fake.clone()).inspect_index("/repo/project").expect("scripted Index inspection");
        assert_eq!(facts.fingerprint.staged_paths, vec!["project/a.rs"]);
        assert_eq!(facts.fingerprint.index_tree_oid, "cccccccccccccccccccccccccccccccccccccccc");
        let calls = fake.calls.lock().unwrap();
        assert!(calls.iter().all(|(program, _, _)| program == "git-recording-sentinel"));
        assert!(calls.iter().flat_map(|(_, args, _)| args).all(|arg| !matches!(arg.as_str(), "add" | "write-tree" | "reset" | "checkout" | "clean" | "push")));
        assert!(calls.iter().any(|(_, args, input)| args.iter().any(|x| x == "hash-object") && input.is_some()));
        assert!(calls.iter().filter_map(|(_,_,input)| input.as_ref()).all(|_| true));
        let hash_calls: Vec<_> = calls.iter().filter(|(_, args, input)| args.iter().any(|a| a == "hash-object") && input.is_some()).collect();
        assert!(!hash_calls.is_empty());
        assert!(hash_calls.iter().all(|(_, args, _)| args.ends_with(&["hash-object".into(), "-t".into(), "tree".into(), "--stdin".into()])));
        assert!(hash_calls.iter().all(|(_, args, _)| !args.iter().any(|arg| arg == "-w")));
    }

    #[test]
    fn commit_index_uses_one_commit_invocation_and_never_stages() {
        let fake = Arc::new(RecordingInvoker::default());
        let adapter = adapter(fake.clone());
        let facts = adapter.inspect_index("/repo/project").expect("scripted facts");
        let observation = adapter.commit_index("/repo/project", "message", &facts.fingerprint, GitWriteApproval::granted()).expect("commit observation");
        assert_eq!(observation.exit_code, Some(0));
        let calls = fake.calls.lock().unwrap();
        let commits: Vec<_> = calls.iter().filter(|(_, args, _)| args.iter().any(|arg| arg == "commit")).collect();
        assert_eq!(commits.len(), 1);
        assert_eq!(commits[0].1, vec!["-C", "/repo", "commit", "-m", "message"]);
        assert!(calls.iter().flat_map(|(_, args, _)| args).all(|arg| !matches!(arg.as_str(), "add" | "write-tree" | "reset" | "checkout" | "clean" | "push")));
        assert!(commits[0].1.windows(2).any(|pair| pair == ["commit", "-m"]));
    }

    #[test]
    fn denied_write_approval_never_invokes_commit() {
        let fake = Arc::new(RecordingInvoker::default());
        let adapter = adapter(fake.clone());
        let facts = adapter.inspect_index("/repo/project").expect("scripted facts");
        assert!(matches!(adapter.commit_index("/repo/project", "message", &facts.fingerprint, GitWriteApproval::denied()), Err(Error::ApprovalRequired)));
        assert!(fake.calls.lock().unwrap().iter().all(|(_, args, _)| !args.iter().any(|arg| arg == "commit")));
    }

    #[test]
    fn tree_serialization_uses_virtual_slash_only_for_directory_sorting() {
        let fake = Arc::new(RecordingInvoker::default());
        let adapter = adapter(fake);
        let entries = vec![
            StageEntry { mode: "100644".into(), oid: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".into(), path: "foo/child".into() },
            StageEntry { mode: "100644".into(), oid: "cccccccccccccccccccccccccccccccccccccccc".into(), path: "foo.bar".into() },
        ];
        let raw = adapter.tree_bytes("/repo", &entries).expect("tree serialization");
        let mut expected = Vec::new();
        expected.extend_from_slice(b"100644 foo.bar\0"); expected.extend(vec![0xcc; 20]);
        expected.extend_from_slice(b"40000 foo\0"); expected.extend(vec![0xbb; 20]);
        assert_eq!(raw, expected, "tree entry names never contain slash; dir suffix is sorting-only");
    }

    #[test]
    fn post_spawn_wait_failure_is_not_misreported_as_no_invocation() {
        let fake = Arc::new(RecordingInvoker::default());
        *fake.fail_commit_after_spawn.lock().unwrap() = true;
        let adapter = adapter(fake);
        let facts = adapter.inspect_index("/repo/project").expect("scripted facts");
        let observation = adapter.commit_index("/repo/project", "message", &facts.fingerprint, GitWriteApproval::granted()).expect("ambiguous observation");
        assert!(observation.invocation_started, "a wait failure after spawn cannot be reported as no invocation");
        assert_eq!(observation.exit_code, None);
        assert!(observation.after.is_some(), "attempt must reread after an ambiguous wait failure");
    }

    #[test]
    fn root_commit_readback_distinguishes_no_parent_from_parent_query_failure() {
        let root = Arc::new(RecordingInvoker::default());
        *root.unborn.lock().unwrap() = true;
        let root_adapter = adapter(root);
        let facts = root_adapter.inspect_index("/repo/project").expect("unborn staged facts");
        let observation = root_adapter.commit_index("/repo/project", "initial", &facts.fingerprint, GitWriteApproval::granted()).expect("root commit observation");
        assert_eq!(observation.observed_parent_oid, None);
        assert!(observation.diagnostic.is_none(), "a successful one-field rev-list is positive proof of a root commit");

        let failed = Arc::new(RecordingInvoker::default());
        *failed.unborn.lock().unwrap() = true;
        *failed.fail_parent_readback.lock().unwrap() = true;
        let adapter = adapter(failed);
        let facts = adapter.inspect_index("/repo/project").expect("unborn staged facts");
        let observation = adapter.commit_index("/repo/project", "initial", &facts.fingerprint, GitWriteApproval::granted()).expect("ambiguous root commit observation");
        assert_eq!(observation.observed_parent_oid, None);
        assert!(observation.after.is_none(), "failed parent readback cannot leave a success-shaped HEAD proof");
        assert!(observation.observed_tree_oid.is_none(), "failed parent readback cannot leave tree proof");
        assert_eq!(observation.diagnostic.as_deref(), Some("commit parent readback failed"));
    }

    #[test]
    fn parent_readback_commit_oid_must_match_the_reread_head() {
        let fake = Arc::new(RecordingInvoker::default());
        *fake.reported_readback_commit.lock().unwrap() = Some("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee".into());
        let adapter = adapter(fake.clone());
        let facts = adapter.inspect_index("/repo/project").expect("staged facts");
        let observation = adapter.commit_index("/repo/project", "message", &facts.fingerprint, GitWriteApproval::granted()).expect("observation");
        assert!(observation.after.is_none(), "a mismatched observed commit must invalidate the readback");
        assert!(observation.observed_tree_oid.is_none(), "tree must not be read through mutable HEAD after mismatch");
        assert_eq!(observation.diagnostic.as_deref(), Some("commit parent readback does not match reread HEAD"));
        let calls = fake.calls.lock().unwrap();
        assert!(!calls.iter().any(|(_, args, _)| args.iter().any(|arg| arg == "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee^{tree}")));
    }

    #[test]
    fn generic_root_query_failure_is_not_fabricated_as_non_repo() {
        let fake = Arc::new(RecordingInvoker::default());
        *fake.root_failure.lock().unwrap() = Some((String::new(), "fatal: permission denied while reading config".into()));
        assert!(matches!(adapter(fake).inspect_index("/repo/project"), Err(Error::Unreadable(_))));
    }

    #[test]
    fn explicit_not_a_repository_diagnostic_is_the_only_root_failure_classified_non_repo() {
        let fake = Arc::new(RecordingInvoker::default());
        *fake.root_failure.lock().unwrap() = Some((String::new(), "fatal: not a git repository (or any of the parent directories): .git".into()));
        assert!(matches!(adapter(fake).inspect_index("/repo/project"), Err(Error::NonRepo(_))));
    }
}
