//! Thin ProcessPort via `std::process::Command` — real Agent CLI spawn seam (PD-EXEC-LIVE-01).
//!
//! Spawns with piped stdout／stderr; background reader threads fill buffers for
//! non-blocking [`ProcessPort::try_read`]. No arbitrary shell — caller supplies
//! an explicit program path + argv (never `cmd.exe /c` unless the approved
//! settings path is literally that program).

use std::collections::HashMap;
use std::io::Read;
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;

use sgenaxis_ports::{PortError, ProcessId, ProcessOutput, ProcessPort};

struct TrackedChild {
    child: Option<Child>,
    exit_code: Option<i32>,
    stdout: Arc<Mutex<Vec<u8>>>,
    stderr: Arc<Mutex<Vec<u8>>>,
}

/// Real process launcher implementing [`ProcessPort`].
pub struct StdProcess {
    next_id: u64,
    children: HashMap<u64, TrackedChild>,
}

impl Default for StdProcess {
    fn default() -> Self {
        Self::new()
    }
}

impl StdProcess {
    pub fn new() -> Self {
        Self {
            next_id: 1,
            children: HashMap::new(),
        }
    }
}

fn spawn_pipe_reader(mut pipe: impl Read + Send + 'static, buf: Arc<Mutex<Vec<u8>>>) {
    thread::spawn(move || {
        let mut tmp = [0u8; 4096];
        loop {
            match pipe.read(&mut tmp) {
                Ok(0) => break,
                Ok(n) => {
                    if let Ok(mut g) = buf.lock() {
                        g.extend_from_slice(&tmp[..n]);
                    }
                }
                Err(_) => break,
            }
        }
    });
}

fn take_utf8(buf: &Arc<Mutex<Vec<u8>>>) -> String {
    let Ok(mut g) = buf.lock() else {
        return String::new();
    };
    if g.is_empty() {
        return String::new();
    }
    let bytes = std::mem::take(&mut *g);
    String::from_utf8_lossy(&bytes).into_owned()
}

impl ProcessPort for StdProcess {
    fn start(
        &mut self,
        program: &str,
        args: &[&str],
        cwd: Option<&str>,
    ) -> Result<ProcessId, PortError> {
        let mut cmd = Command::new(program);
        cmd.args(args)
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        if let Some(dir) = cwd {
            cmd.current_dir(dir);
        }
        let mut child = cmd
            .spawn()
            .map_err(|e| PortError::Process(format!("{program}: {e}")))?;

        let stdout_buf = Arc::new(Mutex::new(Vec::new()));
        let stderr_buf = Arc::new(Mutex::new(Vec::new()));
        if let Some(out) = child.stdout.take() {
            spawn_pipe_reader(out, Arc::clone(&stdout_buf));
        }
        if let Some(err) = child.stderr.take() {
            spawn_pipe_reader(err, Arc::clone(&stderr_buf));
        }

        let id = self.next_id;
        self.next_id = self.next_id.saturating_add(1);
        self.children.insert(
            id,
            TrackedChild {
                child: Some(child),
                exit_code: None,
                stdout: stdout_buf,
                stderr: stderr_buf,
            },
        );
        Ok(ProcessId(id))
    }

    fn try_wait(&mut self, id: ProcessId) -> Result<Option<i32>, PortError> {
        let tracked = self
            .children
            .get_mut(&id.0)
            .ok_or_else(|| PortError::NotFound(format!("process {}", id.0)))?;
        if let Some(code) = tracked.exit_code {
            return Ok(Some(code));
        }
        let child = tracked
            .child
            .as_mut()
            .ok_or_else(|| PortError::Other(format!("process {} missing child", id.0)))?;
        match child.try_wait() {
            Ok(Some(status)) => {
                let code = status.code().unwrap_or(-1);
                tracked.exit_code = Some(code);
                tracked.child = None;
                Ok(Some(code))
            }
            Ok(None) => Ok(None),
            Err(e) => Err(PortError::Process(e.to_string())),
        }
    }

    fn cancel(&mut self, id: ProcessId) -> Result<(), PortError> {
        let Some(tracked) = self.children.get_mut(&id.0) else {
            return Ok(()); // already gone — idempotent
        };
        if tracked.exit_code.is_some() {
            return Ok(());
        }
        if let Some(mut child) = tracked.child.take() {
            let _ = child.kill();
            let _ = child.wait();
            tracked.exit_code = Some(-1);
        }
        Ok(())
    }

    fn try_read(&mut self, id: ProcessId) -> Result<ProcessOutput, PortError> {
        let tracked = self
            .children
            .get(&id.0)
            .ok_or_else(|| PortError::NotFound(format!("process {}", id.0)))?;
        Ok(ProcessOutput {
            stdout: take_utf8(&tracked.stdout),
            stderr: take_utf8(&tracked.stderr),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{Duration, Instant};

    #[test]
    fn std_process_echo_stdout_and_exit_code() {
        let mut proc = StdProcess::new();
        #[cfg(windows)]
        let id = proc
            .start("cmd", &["/C", "echo hello-live"], None)
            .expect("start");
        #[cfg(not(windows))]
        let id = proc
            .start("sh", &["-c", "echo hello-live"], None)
            .expect("start");

        let deadline = Instant::now() + Duration::from_secs(5);
        let mut stdout = String::new();
        let mut code = None;
        while Instant::now() < deadline {
            let out = proc.try_read(id).expect("read");
            stdout.push_str(&out.stdout);
            if let Some(c) = proc.try_wait(id).expect("wait") {
                // Final drain after exit.
                let tail = proc.try_read(id).expect("final read");
                stdout.push_str(&tail.stdout);
                code = Some(c);
                break;
            }
            thread::sleep(Duration::from_millis(20));
        }
        assert_eq!(code, Some(0));
        assert!(
            stdout.contains("hello-live"),
            "stdout was {stdout:?}"
        );
    }

    #[test]
    fn std_process_cancel_running() {
        let mut proc = StdProcess::new();
        #[cfg(windows)]
        let id = proc
            .start("cmd", &["/C", "ping -n 30 127.0.0.1 >nul"], None)
            .expect("start");
        #[cfg(not(windows))]
        let id = proc.start("sleep", &["30"], None).expect("start");

        // Still running briefly.
        assert_eq!(proc.try_wait(id).expect("wait"), None);
        proc.cancel(id).expect("cancel");
        assert_eq!(proc.try_wait(id).expect("after cancel"), Some(-1));
    }
}
